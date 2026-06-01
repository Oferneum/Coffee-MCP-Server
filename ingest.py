"""
ingest.py — Standalone vector embedding ingestion script.

Reads SUPABASE_URL, SUPABASE_KEY (service role), and OPENAI_API_KEY from the
environment (or .env file), generates an embedding for a node's content using
OpenAI text-embedding-3-small, and upserts the node — including its embedding
vector — into the knowledge_nodes table's `embedding` column (pgvector).

Usage:
    python ingest.py
"""

import os
import sys

from dotenv import load_dotenv
from openai import OpenAI
from supabase import create_client, Client

load_dotenv()

# ---------------------------------------------------------------------------
# Client initialisation — fail fast with clear messages if env vars missing
# ---------------------------------------------------------------------------
_required = {"SUPABASE_URL", "SUPABASE_KEY", "OPENAI_API_KEY"}
_missing  = [k for k in _required if not os.environ.get(k)]
if _missing:
    sys.exit(f"ERROR: Missing required environment variable(s): {', '.join(_missing)}\n"
             f"Add them to your .env file and re-run.")

supabase: Client = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])
openai_client    = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

EMBEDDING_MODEL = "text-embedding-3-small"


# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------

def get_embedding(text: str) -> list[float]:
    """Return a 1536-dim embedding vector for `text` using text-embedding-3-small."""
    response = openai_client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text.strip().replace("\n", " "),
    )
    return response.data[0].embedding


def build_content_string(node: dict) -> str:
    """
    Flatten a node dict into a single plain-text string suitable for embedding.

    The content string deliberately includes the name, type, and every
    human-readable value from `properties` so the embedding captures the full
    semantic meaning of the node.
    """
    parts = [
        f"Name: {node['name']}",
        f"Type: {node['node_type']}",
    ]
    for key, value in node.get("properties", {}).items():
        if isinstance(value, list):
            parts.append(f"{key}: {', '.join(str(v) for v in value)}")
        else:
            parts.append(f"{key}: {value}")
    return ". ".join(parts)


def upsert_node_with_embedding(node: dict) -> dict:
    """
    Generate an embedding for `node` and upsert the record into knowledge_nodes.

    The `embedding` column must be a pgvector column (vector(1536)) in Supabase.
    Conflict resolution is on (node_type, name) — matching the existing schema.

    Returns the upserted record from Supabase.
    """
    content = build_content_string(node)
    print(f"  Generating embedding for: {node['node_type']} / {node['name']}")
    print(f"  Content string: {content[:120]}...")

    embedding = get_embedding(content)
    print(f"  Embedding dimensions: {len(embedding)}")

    payload = {
        "node_type":  node["node_type"],
        "name":       node["name"],
        "properties": node["properties"],
        "embedding":  embedding,
    }

    response = supabase.table("knowledge_nodes").upsert(
        payload,
        on_conflict="node_type,name",
    ).execute()

    return response.data[0] if response.data else {}


# ---------------------------------------------------------------------------
# Main — ingest all nodes from knowledge_graph.py with embeddings, then seed edges
# ---------------------------------------------------------------------------

def main():
    from knowledge_graph import NODES, EDGE_DEFINITIONS

    print("=" * 60)
    print("Coffee MCP — Full Knowledge Graph Ingestion")
    print("=" * 60)
    print(f"\nNodes to ingest : {len(NODES)}")
    print(f"Edges to seed   : {len(EDGE_DEFINITIONS)}")

    # ── 1. Upsert every node with its embedding ──────────────────────────────
    print("\n── NODES ──")
    success, failed = 0, 0
    for node in NODES:
        try:
            result = upsert_node_with_embedding(node)
            if result:
                print(f"  ✓  [{node['node_type']}] {node['name']}")
                success += 1
            else:
                print(f"  ✗  [{node['node_type']}] {node['name']} — no data returned")
                failed += 1
        except Exception as e:
            print(f"  ✗  [{node['node_type']}] {node['name']} — {e}")
            failed += 1

    print(f"\nNodes: {success} succeeded, {failed} failed")

    # ── 2. Resolve node IDs and upsert all edges ─────────────────────────────
    print("\n── EDGES ──")
    all_nodes_resp = supabase.table("knowledge_nodes").select("id, node_type, name").execute()
    node_id_map = {(n["node_type"], n["name"]): n["id"] for n in all_nodes_resp.data}

    edges, skipped = [], []
    for edge_def in EDGE_DEFINITIONS:
        src_id = node_id_map.get(edge_def["source"])
        tgt_id = node_id_map.get(edge_def["target"])
        if src_id is None or tgt_id is None:
            skipped.append(f"{edge_def['source']} → {edge_def['target']}")
            continue
        edges.append({
            "source_id":        src_id,
            "target_id":        tgt_id,
            "relationship_type": edge_def["relationship"],
            "properties":       edge_def["properties"],
        })

    if edges:
        edges_resp = supabase.table("knowledge_edges").upsert(
            edges, on_conflict="source_id,target_id,relationship_type"
        ).execute()
        print(f"  ✓  {len(edges_resp.data)} edge(s) upserted")
    if skipped:
        print(f"  ✗  {len(skipped)} edge(s) skipped (missing node):")
        for s in skipped:
            print(f"       {s}")

    print("\nDone.")


if __name__ == "__main__":
    main()
