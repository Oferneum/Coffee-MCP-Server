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
    build_schema_guide,
    chunk_text,
    extract_from_chunk,
    normalize_edges,
    deduplicate_nodes,
    deduplicate_edges,
    validate_extracted,
    ensure_expert_node,
    upsert_nodes_with_embeddings,
    upsert_edges,
)

load_dotenv()

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


def run(query: str, url: str, source_name: str, supabase: Client, openai_client: OpenAI) -> int:
    """Execute the full pipeline with live progress output. Returns exit code."""

    # 1. Resolve candidate URLs
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

    # 2. Scrape the first candidate with enough prose
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

    # 3. Provenance
    domain = urlparse(chosen).netloc.replace("www.", "")
    expert = (source_name or "").strip() or domain or "Web Research"
    print(f"\n[3/5] Provenance → Expert node: {expert!r}")

    # 4. Schema-aware LLM extraction
    schema_guide = build_schema_guide()
    chunks = chunk_text(text, chunk_size=1200)[:8]
    print(f"\n[4/5] Extracting knowledge ({len(chunks)} chunk(s)) ...")

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
    print(f"\n[5/5] Normalising, deduplicating, validating ...")
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

    print(f"  {len(valid_nodes)} valid nodes, {len(valid_edges)} valid edges.")

    # 6. Upsert to Supabase
    print(f"\n  Writing to Supabase ...")
    ensure_expert_node(supabase, openai_client, expert)
    id_map = upsert_nodes_with_embeddings(supabase, openai_client, valid_nodes)
    edge_ok, edge_skip = upsert_edges(supabase, valid_edges, id_map)

    breakdown = Counter(n["node_type"] for n in valid_nodes)

    print(f"\n✓ Done.")
    print(f"  Source  : {chosen}")
    print(f"  Expert  : {expert}")
    print(f"  Nodes   : {len(id_map)} upserted")
    print(f"  Edges   : {edge_ok} written, {edge_skip} skipped")
    print(f"  Breakdown: {', '.join(f'{t}:{c}' for t, c in sorted(breakdown.items(), key=lambda x: -x[1]))}")
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
    parser.add_argument("--source", default="", metavar="NAME",
                        help="Override Expert node name (default: article domain)")

    args = parser.parse_args()

    supabase = create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_KEY"],
    )
    openai_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    sys.exit(run(
        query=args.query or "",
        url=args.url or "",
        source_name=args.source,
        supabase=supabase,
        openai_client=openai_client,
    ))


if __name__ == "__main__":
    main()
