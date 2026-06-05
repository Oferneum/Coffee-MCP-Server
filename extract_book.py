"""
extract_book.py — Extract coffee knowledge nodes and edges from expert literature.

Reads a PDF or plain-text file, chunks it, sends each chunk to GPT-4o with
the full schema.py ontology as a guide, validates the output, deduplicates
across chunks, generates embeddings, and upserts everything into Supabase.

Every extracted BrewingRule and BrewingTechnique automatically gets a
SOURCED_FROM edge pointing to the book's Expert node — so Bean can always
say "according to Scott Rao..." with full provenance.

Usage:
    python extract_book.py --file path/to/book.pdf --expert "Scott Rao"
    python extract_book.py --file chapter.txt     --expert "James Hoffmann"

    # Validate extraction without writing to DB:
    python extract_book.py --file book.pdf --expert "Scott Rao" --dry-run

    # Smaller chunks for denser books (default 3000 chars):
    python extract_book.py --file book.pdf --expert "Scott Rao" --chunk-size 2000
"""

import os
import sys
import json
import time
import argparse
from collections import Counter
from dotenv import load_dotenv
from openai import OpenAI, RateLimitError
from supabase import create_client, Client

load_dotenv()


# =============================================================================
# TEXT LOADING AND CHUNKING
# =============================================================================

def load_text(file_path: str) -> str:
    """Load text from a PDF or plain-text file."""
    if file_path.lower().endswith(".pdf"):
        try:
            import pypdf
        except ImportError:
            sys.exit(
                "pypdf is required for PDF files.\n"
                "Install it with:  pip install pypdf\n"
                "Or convert the PDF to .txt first."
            )
        reader = pypdf.PdfReader(file_path)
        pages  = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(pages)
    else:
        with open(file_path, encoding="utf-8") as f:
            return f.read()


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """
    Split text into overlapping word-boundary chunks.

    chunk_size and overlap are in WORDS.  Default 500 words ≈ 3000 chars.
    Use --chunk-size 1500 for denser scientific papers that need more context
    per LLM call.  Overlap ensures claims spanning chunk boundaries are seen
    in full by at least one extraction pass.
    """
    words = text.split()

    chunks: list[str] = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i : i + chunk_size])
        if len(chunk.strip()) > 80:   # skip near-empty tail chunks
            chunks.append(chunk)
        i += chunk_size - overlap
    return chunks


# =============================================================================
# SCHEMA GUIDE — built from schema.py at runtime, not hardcoded
#
# This is the ontology reference the LLM reads before each extraction.
# Because it imports from schema.py, it automatically reflects any new
# node types or relationship types added for future book ingestion.
# =============================================================================

def build_schema_guide() -> str:
    from schema import NODE_TYPES, RELATIONSHIP_TYPES

    lines = ["=== VALID NODE TYPES ==="]
    for type_name, type_def in NODE_TYPES.items():
        # Truncate description to first sentence — enough for the LLM to classify
        desc       = type_def.get("description", "").split(".")[0].strip() + "."
        key_props  = ", ".join(type_def.get("key_properties", [])[:6])
        examples   = ", ".join(type_def.get("example_names", [])[:4])
        lines.append(f"\n{type_name}:")
        lines.append(f"  {desc}")
        lines.append(f"  key_properties: {key_props}")
        lines.append(f"  examples: {examples}")

    lines.append("\n\n=== VALID RELATIONSHIP TYPES ===")
    for rel_name, rel_def in RELATIONSHIP_TYPES.items():
        src = ", ".join(rel_def.get("valid_sources", []))
        tgt = ", ".join(rel_def.get("valid_targets", []))
        lines.append(f"\n{rel_name}:")
        lines.append(f"  {rel_def['description']}")
        lines.append(f"  Valid: {src}  →  {tgt}")
        if rel_def.get("example"):
            lines.append(f"  e.g.  {rel_def['example']}")

    lines.append("""

=== MANDATORY BrewingRule JSONB CONTRACT ===
Every BrewingRule node's properties dict MUST contain ALL of these keys exactly:
{
  "description": "one or two sentences explaining the rule and why it matters",
  "dictates": {
    "parameter":   "snake_case name, e.g. water_temperature | extraction_time | brew_ratio | grind_size | bloom_time | yield_ratio",
    "direction":   "target_range | increase | decrease | concentrate_then_dilute",
    "value_range": "numeric range string, e.g. 94-96 or 1:15-1:17 or 25-35",
    "unit":        "e.g. °C | seconds | g coffee per g water | microns"
  },
  "pid_specificity": {
    "requires_pid":        true | false | null,
    "reason":              "why PID matters or does not for this rule — use null + 'Not applicable' for water chemistry or non-equipment rules",
    "non_pid_alternative": "MUST be a concrete actionable workaround — never a restriction or 'you need a PID'. Use 'Not applicable' for non-equipment rules."
  },
  "confidence": 0.7-1.0,
  "evidence":   "book title + chapter or page if mentioned in the text"
}
""")

    return "\n".join(lines)


# =============================================================================
# LLM EXTRACTION
# =============================================================================

_SYSTEM_PROMPT = """\
You are a coffee knowledge graph extraction specialist.

Your task: read a passage from a coffee book and extract structured nodes
and edges that conform exactly to the schema below.

RULES:
1. Only extract claims clearly stated in the passage. Never infer or hallucinate.
2. Every BrewingRule and BrewingTechnique MUST have a SOURCED_FROM edge to
   the Expert node named "{expert}".
3. Use exact node_type and relationship names from the schema. No invented types.
4. For BrewingRule nodes, every field in the JSONB contract is mandatory.
5. non_pid_alternative must always be an actionable workaround — never a
   restriction ("you need a PID machine" is forbidden).
6. Be specific with names: "Rao Spin" not "spinning", "WDT" not "distribution".
7. If the passage contradicts an existing known rule, still extract it — note the
   conflict in the evidence field. Do not omit contradictions.
8. Extract only high-quality knowledge. Skip anecdotal opinions and vague marketing
   language, but DO extract scientific findings — even when expressed in technical
   terms (binding energies, thermodynamics, particle physics, fluid dynamics). Translate
   them into actionable BrewingRule, SensoryDescriptor, BrewParameter, or PhysicsModel
   nodes. For example, "Mg2+ has higher binding energy to coffee organics than Ca2+"
   becomes a BrewingRule whose dictates target BrewParameter:Water Magnesium Content.
9. Dissolved ions (Na+, Mg2+, Ca2+) and water minerals are valid SensoryDescriptor
   nodes. Water mineral concentrations are valid BrewParameter nodes.
10. Named mathematical or physical models (Double Porosity Model, Darcy Flow, diffusion
    kinetics) are PhysicsModel nodes. Connect them with GOVERNED_BY edges from the
    BrewParameter or BrewMethod they describe, and SOURCED_FROM edges to the Expert.
    Use CAUSES when a physical phenomenon (e.g. high flow resistance) produces a
    brewing outcome (e.g. channeling).

OUTPUT FORMAT — respond ONLY with valid JSON, no other text:
{{
  "nodes": [
    {{ "node_type": "...", "name": "...", "properties": {{ ... }} }}
  ],
  "edges": [
    {{
      "source": ["node_type", "node_name"],
      "target": ["node_type", "node_name"],
      "relationship": "...",
      "properties": {{ "confidence": 0.0-1.0, "evidence": "..." }}
    }}
  ]
}}

If nothing worth extracting is in the passage, return: {{"nodes": [], "edges": []}}

{schema_guide}
"""


def extract_from_chunk(
    openai_client: OpenAI,
    chunk: str,
    expert: str,
    schema_guide: str,
    chunk_num: int,
    total_chunks: int,
) -> dict:
    """Send one text chunk to GPT-4o and return parsed nodes + edges."""
    system = _SYSTEM_PROMPT.format(expert=expert, schema_guide=schema_guide)

    print(f"  Chunk {chunk_num}/{total_chunks}  ({len(chunk):,} chars)...", end=" ", flush=True)

    max_retries = 5
    for attempt in range(max_retries):
        try:
            response = openai_client.chat.completions.create(
                model="gpt-4o",
                response_format={"type": "json_object"},
                temperature=0.1,    # low temperature = consistent structured output
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user",   "content": f"Extract knowledge from this passage:\n\n{chunk}"},
                ],
            )
            raw    = response.choices[0].message.content
            parsed = json.loads(raw)
            nodes  = parsed.get("nodes", [])
            edges  = parsed.get("edges", [])
            print(f"{len(nodes)} nodes, {len(edges)} edges")
            return parsed

        except json.JSONDecodeError as e:
            print(f"✗ JSON error: {e}")
            return {"nodes": [], "edges": []}

        except RateLimitError:
            if attempt < max_retries - 1:
                wait = min(5 * 2 ** attempt, 60)   # 5 → 10 → 20 → 40 → 60s
                print(f"⏳ rate limited — retrying in {wait}s...", end=" ", flush=True)
                time.sleep(wait)
            else:
                print(f"✗ rate limit (all {max_retries} retries failed)")
                return {"nodes": [], "edges": []}

        except Exception as e:
            print(f"✗ API error: {e}")
            return {"nodes": [], "edges": []}


# =============================================================================
# DEDUPLICATION
# =============================================================================

def deduplicate_nodes(nodes: list[dict]) -> list[dict]:
    """
    Merge nodes with the same (node_type, name).

    Later occurrences' properties are merged on top of earlier ones — the last
    (typically most complete) mention in the book wins for scalar fields, while
    list fields are union-merged.
    """
    seen: dict[tuple, dict] = {}
    for node in nodes:
        key = (node.get("node_type", ""), node.get("name", ""))
        if key in seen:
            existing_props = seen[key].get("properties", {})
            new_props      = node.get("properties", {})
            merged = {**existing_props}
            for k, v in new_props.items():
                if isinstance(v, list) and isinstance(merged.get(k), list):
                    # Union-merge lists without duplicates
                    merged[k] = list(dict.fromkeys(merged[k] + v))
                else:
                    merged[k] = v
            seen[key]["properties"] = merged
        else:
            seen[key] = dict(node)
    return list(seen.values())


def normalize_edges(edges: list[dict]) -> list[dict]:
    """
    Correct reversed-direction edges emitted by the LLM.

    The extractor occasionally swaps source and target — e.g.
    GrindProfile -PAIRS_WITH-> BrewMethod, when schema.py defines the edge as
    BrewMethod -PAIRS_WITH-> GrindProfile. When the stated direction is invalid
    per the relationship's valid_sources/valid_targets but the flipped direction
    is valid, we flip it in place. Edges that are already valid — or invalid in
    both directions — are left untouched for validate_extracted() to report.
    """
    from schema import RELATIONSHIP_TYPES

    fixed = 0
    for edge in edges:
        rel     = edge.get("relationship")
        src     = edge.get("source")
        tgt     = edge.get("target")
        rel_def = RELATIONSHIP_TYPES.get(rel)
        if not rel_def or not isinstance(src, list) or not isinstance(tgt, list):
            continue

        valid_sources = rel_def.get("valid_sources", [])
        valid_targets = rel_def.get("valid_targets", [])
        if not valid_sources or not valid_targets:
            continue

        src_type, tgt_type = src[0], tgt[0]
        forward_ok = src_type in valid_sources and tgt_type in valid_targets
        flipped_ok = tgt_type in valid_sources and src_type in valid_targets

        if not forward_ok and flipped_ok:
            edge["source"], edge["target"] = tgt, src
            print(f"  ↺ flipped {rel}: {src_type}→{tgt_type}  ⇒  {tgt_type}→{src_type}")
            fixed += 1

    if fixed:
        print(f"  Normalized {fixed} reversed edge(s)")
    return edges


def deduplicate_edges(edges: list[dict]) -> list[dict]:
    """Remove duplicate (source, target, relationship) triples."""
    seen: set[tuple] = set()
    result: list[dict] = []
    for edge in edges:
        key = (
            tuple(edge.get("source", [])),
            tuple(edge.get("target", [])),
            edge.get("relationship", ""),
        )
        if key not in seen:
            seen.add(key)
            result.append(edge)
    return result


# =============================================================================
# EXPERT NODE — ensure the source Expert exists before adding SOURCED_FROM edges
# =============================================================================

def ensure_expert_node(
    supabase_client: Client,
    openai_client:   OpenAI,
    expert: str,
) -> None:
    """
    Ensure an Expert node for `expert` exists in the graph.
    If it doesn't, create a minimal placeholder and upsert it with an embedding.
    The extract_book pipeline will enrich it if the book mentions credentials etc.
    """
    existing = (
        supabase_client.table("knowledge_nodes")
        .select("id, name")
        .eq("node_type", "Expert")
        .eq("name", expert)
        .execute()
        .data
    )
    if existing:
        print(f"  Expert '{expert}' already in graph — id {existing[0]['id'][:8]}...")
        return

    print(f"  Creating placeholder Expert node for '{expert}'...")
    content   = f"Name: {expert}. Type: Expert. full_name: {expert}. credentials: Coffee expert and author."
    embedding = openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=content,
    ).data[0].embedding

    supabase_client.table("knowledge_nodes").upsert(
        {
            "node_type":  "Expert",
            "name":       expert,
            "properties": {
                "full_name":    expert,
                "credentials":  "Coffee expert and author",
                "primary_works": [],
                "organisation": "Independent",
            },
            "embedding": embedding,
        },
        on_conflict="node_type,name",
    ).execute()
    print(f"  ✓ Expert node created for '{expert}'")


# =============================================================================
# VALIDATION
# =============================================================================

def validate_extracted(
    nodes: list[dict],
    edges: list[dict],
) -> tuple[list[dict], list[dict], list[str]]:
    """
    Validate extracted nodes and edges against schema.py.

    Filters out nodes with unknown node_type and edges with unknown
    relationship type, then runs the full schema.validate_graph() for
    BrewingRule contract checks and advisory type-compatibility warnings.

    Returns (valid_nodes, valid_edges, hard_errors).
    """
    from schema import VALID_NODE_TYPE_NAMES, VALID_RELATIONSHIP_NAMES, validate_graph

    # Hard filter: drop unknowns before calling validate_graph
    valid_nodes = [n for n in nodes if n.get("node_type") in VALID_NODE_TYPE_NAMES]
    valid_edges = [e for e in edges if e.get("relationship") in VALID_RELATIONSHIP_NAMES]

    dropped_nodes = len(nodes) - len(valid_nodes)
    dropped_edges = len(edges) - len(valid_edges)
    if dropped_nodes:
        print(f"  Dropped {dropped_nodes} node(s) with unknown node_type")
    if dropped_edges:
        print(f"  Dropped {dropped_edges} edge(s) with unknown relationship")

    # Convert edge format for validate_graph (expects source/target as tuples)
    edge_defs = [
        {
            "source":       tuple(e["source"]),
            "target":       tuple(e["target"]),
            "relationship": e["relationship"],
        }
        for e in valid_edges
        if isinstance(e.get("source"), list) and isinstance(e.get("target"), list)
    ]

    errors, warnings = validate_graph(valid_nodes, edge_defs)

    for w in warnings:
        print(f"  ⚠  {w}")

    return valid_nodes, valid_edges, errors


# =============================================================================
# UPSERT — nodes with embeddings, then edges
# =============================================================================

def upsert_nodes_with_embeddings(
    supabase_client: Client,
    openai_client:   OpenAI,
    nodes: list[dict],
) -> dict[tuple, str]:
    """
    Generate an embedding for every node and upsert to knowledge_nodes.
    Returns a (node_type, name) → supabase_id map for edge resolution.
    """
    id_map: dict[tuple, str] = {}

    for node in nodes:
        node_type = node.get("node_type", "")
        name      = node.get("name", "")

        # Build content string — same logic as ingest.py for consistency
        parts = [f"Name: {name}", f"Type: {node_type}"]
        for k, v in node.get("properties", {}).items():
            val = ", ".join(str(x) for x in v) if isinstance(v, list) else str(v)
            parts.append(f"{k}: {val}")
        content = ". ".join(parts)

        print(f"  Embedding [{node_type}] {name}...", end=" ", flush=True)

        try:
            embedding = openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=content[:8000],   # stay well within token limit
            ).data[0].embedding

            result = supabase_client.table("knowledge_nodes").upsert(
                {
                    "node_type":  node_type,
                    "name":       name,
                    "properties": node.get("properties", {}),
                    "embedding":  embedding,
                },
                on_conflict="node_type,name",
            ).execute()

            if result.data:
                id_map[(node_type, name)] = result.data[0]["id"]
                print("✓")
            else:
                print("✗ (no data returned)")

        except Exception as e:
            print(f"✗ ({e})")

    return id_map


def upsert_edges(
    supabase_client: Client,
    edges: list[dict],
    id_map: dict[tuple, str],
) -> tuple[int, int]:
    """
    Resolve node IDs and upsert all edges.
    Fetches the full node table so edges to pre-existing nodes also resolve.
    Returns (success_count, skipped_count).
    """
    # Build a complete (node_type, name) → id map from the live DB
    all_nodes  = supabase_client.table("knowledge_nodes").select("id, node_type, name").execute().data
    full_map   = {(n["node_type"], n["name"]): n["id"] for n in all_nodes}
    full_map.update(id_map)  # fresh upserts take precedence

    records: list[dict] = []
    skipped: list[str]  = []

    for edge in edges:
        src_key = tuple(edge.get("source", []))
        tgt_key = tuple(edge.get("target", []))
        src_id  = full_map.get(src_key)
        tgt_id  = full_map.get(tgt_key)

        if not src_id or not tgt_id:
            skipped.append(f"{src_key} → {edge.get('relationship')} → {tgt_key}")
            continue

        records.append({
            "source_id":        src_id,
            "target_id":        tgt_id,
            "relationship_type": edge.get("relationship"),
            "properties":       edge.get("properties", {}),
        })

    success = 0
    if records:
        result  = supabase_client.table("knowledge_edges").upsert(
            records, on_conflict="source_id,target_id,relationship_type"
        ).execute()
        success = len(result.data)

    if skipped:
        print(f"  ⚠  Skipped {len(skipped)} edge(s) — referenced node not found:")
        for s in skipped[:5]:
            print(f"     {s}")
        if len(skipped) > 5:
            print(f"     … and {len(skipped) - 5} more")

    return success, len(skipped)


# =============================================================================
# MAIN
# =============================================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract coffee knowledge nodes and edges from a book.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--file",       required=True,       help="Path to PDF or .txt file")
    parser.add_argument("--expert",     required=True,       help='Expert node name, e.g. "Scott Rao"')
    parser.add_argument("--dry-run",    action="store_true", help="Validate only — no DB writes")
    parser.add_argument("--chunk-size", type=int, default=3000,
                        help="Target characters per chunk (default 3000)")
    args = parser.parse_args()

    # ── Env check ─────────────────────────────────────────────────────────────
    missing = [k for k in ("SUPABASE_URL", "SUPABASE_KEY", "OPENAI_API_KEY") if not os.environ.get(k)]
    if missing:
        sys.exit(f"ERROR: Missing env vars: {', '.join(missing)}")

    supabase_client = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])
    openai_client   = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    print("=" * 60)
    print("Coffee MCP — Book Ingestion")
    print(f"  File       : {args.file}")
    print(f"  Expert     : {args.expert}")
    print(f"  Chunk size : {args.chunk_size} words")
    print(f"  Mode       : {'DRY RUN (no DB writes)' if args.dry_run else 'LIVE'}")
    print("=" * 60)

    # ── Load and chunk text ────────────────────────────────────────────────────
    print(f"\nLoading {args.file}...")
    text   = load_text(args.file)
    chunks = chunk_text(text, chunk_size=args.chunk_size)
    print(f"  {len(text):,} chars  →  {len(chunks)} chunks\n")

    # ── Build schema guide once (reused for every chunk) ──────────────────────
    schema_guide = build_schema_guide()

    # ── Ensure Expert node exists in the DB ───────────────────────────────────
    if not args.dry_run:
        print("── EXPERT NODE ──")
        ensure_expert_node(supabase_client, openai_client, args.expert)

    # Keep an Expert node in the local batch so SOURCED_FROM edges resolve
    # even during dry runs and before the DB call above returns an id.
    expert_stub = {
        "node_type":  "Expert",
        "name":       args.expert,
        "properties": {"full_name": args.expert},
    }

    # ── Extract from every chunk ───────────────────────────────────────────────
    print(f"\n── EXTRACTION ({len(chunks)} chunks) ──")
    all_nodes: list[dict] = [expert_stub]
    all_edges: list[dict] = []

    for i, chunk in enumerate(chunks, 1):
        result = extract_from_chunk(
            openai_client, chunk, args.expert, schema_guide, i, len(chunks)
        )
        all_nodes.extend(result.get("nodes", []))
        all_edges.extend(result.get("edges", []))

    raw_node_count = len(all_nodes)
    raw_edge_count = len(all_edges)

    # ── Normalize edge direction (flip reversed source/target) ─────────────────
    all_edges = normalize_edges(all_edges)

    # ── Deduplicate ────────────────────────────────────────────────────────────
    all_nodes = deduplicate_nodes(all_nodes)
    all_edges = deduplicate_edges(all_edges)
    print(
        f"\nAfter deduplication: {len(all_nodes)} nodes "
        f"(from {raw_node_count}), {len(all_edges)} edges (from {raw_edge_count})"
    )

    # ── Validate ──────────────────────────────────────────────────────────────
    print("\n── VALIDATION ──")
    valid_nodes, valid_edges, errors = validate_extracted(all_nodes, all_edges)

    if errors:
        print(f"  ✗ {len(errors)} schema error(s):")
        for err in errors:
            print(f"    {err}")
    else:
        print("  ✓ No schema errors")

    # Node type breakdown
    type_counts = Counter(n["node_type"] for n in valid_nodes)
    print(f"\n  {len(valid_nodes)} valid nodes  |  {len(valid_edges)} valid edges")
    print("  Breakdown:")
    for t, c in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"    {t:25s}  {c}")

    if args.dry_run:
        print("\n── DRY RUN complete — no DB writes. Remove --dry-run to ingest. ──")
        return

    # ── Upsert nodes (with embeddings) ─────────────────────────────────────────
    print(f"\n── UPSERTING {len(valid_nodes)} NODES ──")
    id_map = upsert_nodes_with_embeddings(supabase_client, openai_client, valid_nodes)

    # ── Upsert edges ───────────────────────────────────────────────────────────
    print(f"\n── UPSERTING {len(valid_edges)} EDGES ──")
    edge_ok, edge_skip = upsert_edges(supabase_client, valid_edges, id_map)
    print(f"  {edge_ok} edges written, {edge_skip} skipped")

    print(f"\n✓  Done. {len(id_map)} nodes and {edge_ok} edges written to Supabase.")
    print("   Run `python schema.py` to validate the updated graph.")
    print("   Run `python ingest.py` if you want to refresh ALL embeddings.")


if __name__ == "__main__":
    main()
