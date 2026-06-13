"""
research_ingest.py — standalone CLI for the DIALED knowledge-graph ingestion pipeline.

Usage:
    python research_ingest.py "coffee bed channeling causes"
    python research_ingest.py --url https://baristahustle.com/article
    python research_ingest.py "extraction yield" --source "Barista Hustle"
"""

import os
import sys
import argparse
from collections import Counter
from urllib.parse import urlparse

from dotenv import load_dotenv
from openai import OpenAI
from supabase import create_client, Client

from extract_book import (
    load_text,
    build_schema_guide,
    chunk_text,
    extract_from_chunk,
    normalize_entity_name,
    normalize_node_names,
    normalize_edges,
    deduplicate_nodes,
    deduplicate_edges,
    validate_extracted,
    generate_embeddings,
    ingest_document_rpc,
)

load_dotenv()


def purge_source(doc_id: str, supabase: Client) -> tuple[int, int]:
    """
    Delete all nodes (and their edges) previously ingested from `doc_id`.

    `doc_id` is the document identifier — the filename or URL of the specific
    paper, NOT the expert/author name (one author may have multiple papers).
    Relies on the `_source` field stamped into every node's properties at
    upsert time — NOT on SOURCED_FROM edges, which the LLM only creates for
    some node types and could miss entirely.

    Returns (nodes_deleted, edges_deleted).
    """
    # Find every node tagged with this document — covers all node types uniformly
    resp = (
        supabase.table("knowledge_nodes")
        .select("id")
        .eq("properties->>_source", doc_id)
        .execute()
    )
    if not resp.data:
        return 0, 0

    all_ids = [row["id"] for row in resp.data]

    # Delete all edges touching any of those nodes (both directions)
    edges_deleted = 0
    for node_id in all_ids:
        r1 = supabase.table("knowledge_edges").delete().eq("source_id", node_id).execute()
        r2 = supabase.table("knowledge_edges").delete().eq("target_id", node_id).execute()
        edges_deleted += len(r1.data or []) + len(r2.data or [])

    # Delete the nodes
    nodes_deleted = 0
    for node_id in all_ids:
        r = supabase.table("knowledge_nodes").delete().eq("id", node_id).execute()
        nodes_deleted += len(r.data or [])

    return nodes_deleted, edges_deleted


_NON_ARTICLE_HOSTS = (
    "youtube.com", "youtu.be", "twitter.com", "x.com", "instagram.com",
    "tiktok.com", "facebook.com", "pinterest.com", "reddit.com",
)


def search_candidate_urls(query: str, max_results: int = 8) -> list[str]:
    try:
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS
        urls: list[str] = []
        with DDGS() as ddgs:
            for result in ddgs.text(query, max_results=max_results):
                href = result.get("href") or result.get("url")
                if not href:
                    continue
                host = urlparse(href).netloc.replace("www.", "").lower()
                if any(host == h or host.endswith("." + h) for h in _NON_ARTICLE_HOSTS):
                    continue
                if href not in urls:
                    urls.append(href)
        return urls
    except Exception as e:
        print(f"  [search] error: {e}", file=sys.stderr)
        return []


def scrape_article(url: str) -> str | None:
    try:
        import trafilatura
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return None
        return trafilatura.extract(
            downloaded,
            include_comments=False,
            include_tables=True,
            favor_recall=True,
        )
    except Exception as e:
        print(f"  [scrape] error: {e}", file=sys.stderr)
        return None


def run(query: str, url: str, file: str, source: str, expert_name: str, supabase: Client, openai_client: OpenAI, dry_run: bool = False) -> int:
    """Execute the full pipeline with live progress output. Returns exit code."""

    # 1 & 2. Resolve text — local file skips search and scraping entirely
    if file:
        print(f"\n[1/5] Reading local file: {file}")
        text = load_text(file)
        words = len(text.split())
        print(f"  ✓ {words} words extracted.")
        chosen = file
        default_source = os.path.splitext(os.path.basename(file))[0]
        default_expert = default_source
    else:
        if url:
            candidates = [url]
        else:
            print(f"\n[1/5] Searching: {query!r} ...")
            candidates = search_candidate_urls(query)
            if not candidates:
                print(f"  No web results found.", file=sys.stderr)
                return 1
            print(f"  Found {len(candidates)} candidate(s):")
            for c in candidates:
                print(f"    {c}")

        MIN_WORDS = 150
        text, chosen, tried = None, None, []

        print(f"\n[2/5] Scraping ...")
        for candidate in candidates:
            print(f"  Trying: {candidate}")
            scraped = scrape_article(candidate)
            words = len((scraped or "").split())
            tried.append(f"{candidate} ({words}w)")
            if scraped and words >= MIN_WORDS:
                text, chosen = scraped, candidate
                print(f"  ✓ {words} words extracted.")
                break
            else:
                print(f"  ✗ Only {words} words — skipping.")

        if not text:
            print("\nCould not extract enough readable text. Tried:", file=sys.stderr)
            for t in tried:
                print(f"  - {t}", file=sys.stderr)
            return 1

        default_source = chosen   # URL is the natural document identifier
        default_expert = urlparse(chosen).netloc.replace("www.", "")

    # 3. Provenance — two separate identifiers:
    #   doc_id : the article title / filename — unique per document, used as _source stamp
    #   expert : the author name — used for the Expert node and SOURCED_FROM edges
    doc_id = (source or "").strip() or default_source or chosen
    expert = (expert_name or "").strip() or default_expert or "Web Research"
    print(f"\n[3/5] Provenance → document: {doc_id!r}  |  expert: {expert!r}")

    # 3b. Purge by document id — skipped in dry-run mode.
    if dry_run:
        print(f"  [dry-run] skipping purge.")
    else:
        print(f"  Purging previous ingestion for {doc_id!r} ...")
        n_del, e_del = purge_source(doc_id, supabase)
        if n_del or e_del:
            print(f"  ✓ Removed {n_del} node(s) and {e_del} edge(s).")
        else:
            print(f"  (nothing to purge — first ingestion)")

    # 4. Schema-aware LLM extraction
    schema_guide = build_schema_guide()
    chunks = chunk_text(text, chunk_size=500)
    print(f"\n[4/6] Extracting knowledge ({len(chunks)} chunk(s)) ...")

    expert_stub = {
        "node_type":  "Expert",
        "name":       expert,
        "properties": {"full_name": expert, "organisation": "Web source", "source_url": chosen},
    }
    all_nodes: list[dict] = [expert_stub]
    all_edges: list[dict] = []

    for i, chunk in enumerate(chunks, 1):
        print(f"  Chunk {i}/{len(chunks)} ...", end=" ", flush=True)
        result = extract_from_chunk(openai_client, chunk, expert, schema_guide, i, len(chunks))
        n, e = len(result.get("nodes", [])), len(result.get("edges", []))
        print(f"{n} nodes, {e} edges")
        all_nodes.extend(result.get("nodes", []))
        all_edges.extend(result.get("edges", []))

    # 5. Normalize → dedup → validate
    print(f"\n[5/6] Normalising, deduplicating, validating ...")
    all_nodes, all_edges = normalize_node_names(all_nodes, all_edges)
    all_edges = normalize_edges(all_edges)
    all_nodes = deduplicate_nodes(all_nodes)
    all_edges = deduplicate_edges(all_edges)
    valid_nodes, valid_edges, errors = validate_extracted(all_nodes, all_edges)

    if errors:
        print("\nSchema validation errors — nothing written:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    if len(valid_nodes) <= 1:
        print(f"\nNo schema-conformant knowledge extracted from {chosen}.", file=sys.stderr)
        return 1

    breakdown = Counter(n["node_type"] for n in valid_nodes)
    print(f"  {len(valid_nodes)} valid nodes, {len(valid_edges)} valid edges.")
    print(f"  Breakdown: {', '.join(f'{t}:{c}' for t, c in sorted(breakdown.items(), key=lambda x: -x[1]))}")

    if dry_run:
        print(f"\n── DRY RUN complete — no DB writes. ──")
        print(f"  Nodes that would be ingested:")
        for n in valid_nodes:
            print(f"    [{n['node_type']}] {n['name']}")
        return 0

    # Stamp every node with the document identifier (filename or URL) so
    # purge_source can find them reliably on re-ingestion. Uses `chosen`, not
    # `expert` — an author may publish multiple papers; purging by author would
    # wipe all of them.
    for node in valid_nodes:
        node.setdefault("properties", {})["_source"] = doc_id

    # 6. Generate embeddings then write everything in one transaction
    print(f"\n[6/6] Writing to Supabase ...")
    valid_nodes = generate_embeddings(openai_client, valid_nodes)
    nodes_ok, edge_ok, edge_skip = ingest_document_rpc(supabase, valid_nodes, valid_edges)

    print(f"\n✓ Done.")
    print(f"  Source  : {os.path.abspath(chosen) if file else chosen}")
    print(f"  Expert  : {expert}")
    print(f"  Nodes   : {nodes_ok} upserted")
    print(f"  Edges   : {edge_ok} written, {edge_skip} skipped")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest a coffee-science article into the DIALED knowledge graph.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("query", nargs="?", help="Search query (DuckDuckGo)")
    group.add_argument("--url", help="Direct URL to scrape (skips search)")
    group.add_argument("--file", metavar="PATH", help="Local PDF or .txt file (skips search and scraping)")
    parser.add_argument("--source", default="", metavar="TITLE",
                        help="Article title — used as the document identifier for purge/re-ingestion (default: filename or URL)")
    parser.add_argument("--expert", default="", metavar="NAME",
                        help="Expert node name — author attribution (default: filename or article domain)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Extract and print nodes without writing to the database")

    args = parser.parse_args()

    supabase = create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_KEY"],
    )
    openai_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    sys.exit(run(
        query=args.query or "",
        url=args.url or "",
        file=args.file or "",
        source=args.source,
        expert_name=args.expert,
        dry_run=args.dry_run,
        supabase=supabase,
        openai_client=openai_client,
    ))


if __name__ == "__main__":
    main()
