import os
from dotenv import load_dotenv
from fastapi import FastAPI
from supabase import create_client, Client
from mcp.server.fastmcp import FastMCP

# Load environment variables from .env file
load_dotenv()

# Initialize Supabase client
supabase_url: str = os.environ.get("SUPABASE_URL")
supabase_key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

# Initialize the MCP server instance
mcp = FastMCP("Coffee Barista MCP", host="0.0.0.0")

@mcp.tool()
def get_recent_shots(limit: int = 5) -> str:
    """
    Fetch the user's most recent espresso and coffee shots from Supabase.
    Use this tool to analyze trends, history, or extraction parameters.
    """
    try:
        response = supabase.table("shots").select("*").order("created_at", desc=True).limit(limit).execute()
        data = response.data
        
        if not data:
            return "No coffee shots found in the database."
        
        result = ["Recent coffee shots:\n"]
        for shot in data:
            result.append(
                f"- Date: {shot.get('created_at')} | Method: {shot.get('brew_method')} | "
                f"Dose: {shot.get('dose')}g | Yield: {shot.get('yield')}g | "
                f"Time: {shot.get('extraction_time')}s | Score: {shot.get('overall_score')}/10"
            )
        
        return "\n".join(result)
        
    except Exception as e:
        return f"Database error: {str(e)}"

@mcp.tool()
def seed_knowledge_graph() -> str:
    """
    Seeds the knowledge_nodes and knowledge_edges Supabase tables with static coffee domain knowledge.
    Uses upsert to safely re-run without creating duplicates.
    Requires SUPABASE_KEY to be set to the service role key (not anon key).
    """
    try:
        from knowledge_graph import NODES, EDGE_DEFINITIONS

        # Upsert all nodes; conflict key is (node_type, name)
        nodes_res = supabase.table("knowledge_nodes").upsert(
            NODES, on_conflict="node_type,name"
        ).execute()
        node_count = len(nodes_res.data)

        # Fetch all nodes to build a (node_type, name) -> id lookup
        all_nodes_res = supabase.table("knowledge_nodes").select("id, node_type, name").execute()
        node_id_map = {(n["node_type"], n["name"]): n["id"] for n in all_nodes_res.data}

        # Resolve edge definitions to concrete source_id / target_id values
        edges = []
        skipped_edges = []
        for edge_def in EDGE_DEFINITIONS:
            src_id = node_id_map.get(edge_def["source"])
            tgt_id = node_id_map.get(edge_def["target"])

            if src_id is None or tgt_id is None:
                skipped_edges.append(f"{edge_def['source']} -> {edge_def['target']}")
                continue

            edges.append({
                "source_id": src_id,
                "target_id": tgt_id,
                "relationship_type": edge_def["relationship"],
                "properties": edge_def["properties"],
            })

        # Upsert edges; conflict key is (source_id, target_id, relationship_type)
        edges_res = supabase.table("knowledge_edges").upsert(
            edges, on_conflict="source_id,target_id,relationship_type"
        ).execute()
        edge_count = len(edges_res.data)

        summary = f"Knowledge graph seeded: {node_count} nodes inserted/updated, {edge_count} edges inserted/updated."
        if skipped_edges:
            summary += f"\nSkipped {len(skipped_edges)} edges (nodes not found): {', '.join(skipped_edges)}"
        return summary

    except Exception as e:
        return f"Error seeding knowledge graph: {str(e)}"


if __name__ == "__main__":
    # Run the server via stdio (standard MCP transport)
    mcp.run()


@mcp.tool()
def analyze_best_value_coffees() -> str:
    """
    Analyzes all coffee beans to find the best Value for Money (VFM).
    Calculates average user scores, price per 100g, and identifies the best brew methods for each bean.
    Use this tool when the user asks for recommendations, the best coffee, or price/value analysis.
    """
    try:
        # 1. Fetch beans and shots from Supabase
        beans_response = supabase.table("beans").select("id, roaster, origin, price_paid, weight_grams").execute()
        shots_response = supabase.table("shots").select("bean_id, overall_score, brew_method").execute()
        
        beans = beans_response.data
        shots = [s for s in shots_response.data if s.get("overall_score") is not None and s.get("bean_id") is not None]

        if not beans or not shots:
            return "Not enough data to perform VFM analysis."

        # 2. Aggregate shots by bean_id
        bean_stats = {}
        for shot in shots:
            b_id = shot["bean_id"]
            score = shot["overall_score"]
            method = shot["brew_method"]

            if b_id not in bean_stats:
                bean_stats[b_id] = {"scores": [], "methods": {}}
            
            bean_stats[b_id]["scores"].append(score)
            
            if method not in bean_stats[b_id]["methods"]:
                bean_stats[b_id]["methods"][method] = []
            bean_stats[b_id]["methods"][method].append(score)

        # 3. Calculate metrics and format the report
        result = ["☕ Coffee Value For Money (VFM) & Brew Analysis:\n"]
        
        for bean in beans:
            b_id = bean.get("id")
            stats = bean_stats.get(b_id)
            
            if not stats:
                continue # Skip beans with no logged shots

            avg_score = sum(stats["scores"]) / len(stats["scores"])
            
            # Calculate the most successful brew method
            method_avgs = {m: sum(s)/len(s) for m, s in stats["methods"].items()}
            best_method = max(method_avgs, key=method_avgs.get)

            price = bean.get("price_paid")
            weight = bean.get("weight_grams")
            
            # Calculate VFM if price and weight exist
            if price and weight and float(weight) > 0:
                price_per_100g = (float(price) / float(weight)) * 100
                vfm_index = avg_score / price_per_100g if price_per_100g > 0 else 0
                cost_str = f"${price_per_100g:.2f} per 100g | VFM Index: {vfm_index:.2f}"
            else:
                cost_str = "Price/Weight data missing"

            result.append(
                f"🔹 {bean.get('roaster')} - {bean.get('origin')}\n"
                f"   • Overall Score: {avg_score:.1f}/10 (based on {len(stats['scores'])} shots)\n"
                f"   • Value: {cost_str}\n"
                f"   • Best Method: {best_method} (Avg: {method_avgs[best_method]:.1f}/10)\n"
            )

        return "\n".join(result)

    except Exception as e:
        return f"Error analyzing beans: {str(e)}"


# ---------------------------------------------------------------------------
# ASGI app — used by uvicorn for cloud / SSE deployment:
#   uvicorn server:app --host 0.0.0.0 --port 8000
#
# All MCP tools are registered on `mcp` by this point in the file, so the
# SSE app picks them up correctly.  The stdio entrypoint (`python server.py`)
# is preserved by the __main__ guard above.
# ---------------------------------------------------------------------------
app = FastAPI(title="Coffee Barista MCP Server")


@app.get("/health")
def health():
    return {"status": "ok", "server": "Coffee Barista MCP"}


# Mount the MCP SSE transport — exposes GET /sse and POST /messages/
app.mount("/", mcp.sse_app())