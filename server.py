import os
from dotenv import load_dotenv
from fastapi import FastAPI
from openai import OpenAI
from supabase import create_client, Client
from mcp.server.fastmcp import FastMCP

# Load environment variables from .env file
load_dotenv()

# Initialize Supabase client
supabase_url: str = os.environ.get("SUPABASE_URL")
supabase_key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

# Initialize OpenAI client (OPENAI_API_KEY read from environment)
openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

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
# GRAPH-RAG TOOLS
# ---------------------------------------------------------------------------

@mcp.tool()
def search_nodes(keyword: str, node_type: str = "") -> str:
    """
    ENTITY RESOLUTION — Use this as your FIRST call whenever you need to look
    up a concept in the knowledge graph but only have a partial, approximate,
    or user-supplied name (e.g. "ethiopian", "v60", "french").

    Performs a case-insensitive partial match (ilike) on the `name` column.
    Optionally filters to a single node_type so you can narrow results.

    WHEN TO USE:
    - User mentions "Ethiopian coffee" → search_nodes("ethiopia") to confirm
      the exact node name and ID before any traversal.
    - You want every available FlavorNote → search_nodes("", "FlavorNote").
    - You are unsure whether a concept exists in the graph at all.

    RETURNS: Matching nodes with id, node_type, name, and full properties.

    MULTI-HOP PATTERN:
    Step 1 → search_nodes("ethiopia")          — resolve the exact name
    Step 2 → get_node_connections("Ethiopia")  — see all 1-hop neighbours
    Step 3 → traverse_by_relationship(...)     — follow a specific edge type

    Valid node_type values (case-sensitive, leave blank for all types):
      Origin, ProcessMethod, RoastLevel, FlavorNote, BrewMethod,
      BrewingRule, BrewParameter, EquipmentType, GrindProfile

    Args:
        keyword:   Partial or full name to search for. Case-insensitive.
                   Pass an empty string to list all nodes of a given type.
        node_type: Optional exact node_type filter. Leave empty to search
                   across all node types.
    """
    try:
        query = supabase.table("knowledge_nodes").select("id, node_type, name, properties")
        if keyword:
            query = query.ilike("name", f"%{keyword}%")
        if node_type:
            query = query.eq("node_type", node_type)
        resp = query.order("node_type").execute()

        if not resp.data:
            suffix = f" with node_type='{node_type}'" if node_type else ""
            return f"No nodes found matching '{keyword}'{suffix}."

        lines = [f"Found {len(resp.data)} node(s):\n"]
        for n in resp.data:
            lines.append(f"  [{n['node_type']}] {n['name']}")
            lines.append(f"    id: {n['id']}")
            for k, v in n["properties"].items():
                lines.append(f"    {k}: {v}")
            lines.append("")
        return "\n".join(lines)
    except Exception as e:
        return f"Error searching nodes: {str(e)}"


@mcp.tool()
def get_node_connections(node_name: str) -> str:
    """
    LOCAL NEIGHBOURHOOD — Returns ALL edges connected to a node (outbound AND
    inbound), giving the LLM a complete 1-hop view of a concept's relationships.

    Resolves the node by exact name first, then falls back to a partial match.
    For each edge the relationship type, direction, connected node type/name,
    and confidence score are returned.

    WHEN TO USE:
    - You know a node name and want to explore everything it connects to before
      deciding which edge type to follow.
    - Starting-point survey before narrowing with traverse_by_relationship().
    - Understanding the full context of a concept in one call.

    RETURNS: Outbound edges (→) and inbound edges (←) with relationship types,
    neighbour node types/names, and per-edge confidence scores.

    MULTI-HOP PATTERN:
    1. search_nodes("v60")           → confirm exact name "V60"
    2. get_node_connections("V60")   → see all connections
    3. traverse_by_relationship("V60", "EMPHASIZES") → drill into flavour notes

    Args:
        node_name: Exact or approximate name of the node to inspect.
    """
    try:
        candidates = supabase.table("knowledge_nodes").select("id, node_type, name").eq("name", node_name).execute().data
        if not candidates:
            candidates = supabase.table("knowledge_nodes").select("id, node_type, name").ilike("name", f"%{node_name}%").execute().data
        if not candidates:
            return f"No node found matching '{node_name}'."
        if len(candidates) > 1:
            names = ", ".join(f"{c['node_type']}:{c['name']}" for c in candidates)
            return f"Multiple nodes match '{node_name}': {names}. Please be more specific."

        node = candidates[0]
        node_id = node["id"]

        out_resp = supabase.table("knowledge_edges").select("target_id, relationship_type, properties").eq("source_id", node_id).execute()
        in_resp  = supabase.table("knowledge_edges").select("source_id, relationship_type, properties").eq("target_id", node_id).execute()

        neighbor_ids = [e["target_id"] for e in out_resp.data] + [e["source_id"] for e in in_resp.data]
        if not neighbor_ids:
            return f"Node '{node['name']}' ({node['node_type']}) exists but has no edges."

        nb_map = {n["id"]: n for n in supabase.table("knowledge_nodes").select("id, node_type, name").in_("id", neighbor_ids).execute().data}

        lines = [f"Connections for [{node['node_type']}] {node['name']}:\n"]

        if out_resp.data:
            lines.append(f"  OUTBOUND ({len(out_resp.data)} edge(s)):")
            for e in out_resp.data:
                nb = nb_map.get(e["target_id"], {})
                lines.append(f"    → {e['relationship_type']} → [{nb.get('node_type','?')}] {nb.get('name','?')}  (confidence: {e['properties'].get('confidence','?')})")

        if in_resp.data:
            lines.append(f"\n  INBOUND ({len(in_resp.data)} edge(s)):")
            for e in in_resp.data:
                nb = nb_map.get(e["source_id"], {})
                lines.append(f"    ← {e['relationship_type']} ← [{nb.get('node_type','?')}] {nb.get('name','?')}  (confidence: {e['properties'].get('confidence','?')})")

        return "\n".join(lines)
    except Exception as e:
        return f"Error getting connections for '{node_name}': {str(e)}"


@mcp.tool()
def traverse_by_relationship(node_name: str, relationship_type: str, direction: str = "outbound") -> str:
    """
    TYPED TRAVERSAL — Follows a single, specific relationship type from a node,
    returning only the nodes reachable via that edge. More focused than
    get_node_connections() when you already know which relationship to explore.

    Direction "inbound" enables powerful reverse queries: instead of "what does
    Ethiopia connect to via TYPICAL_FLAVOR?", ask "which Origins connect to
    Blueberry via TYPICAL_FLAVOR?" by passing direction="inbound" on Blueberry.

    WHEN TO USE:
    - Get all FlavorNotes for an Origin: traverse_by_relationship("Ethiopia", "TYPICAL_FLAVOR")
    - Get all BrewMethods a rule applies to: traverse_by_relationship("Golden Ratio", "APPLIES_TO")
    - Reverse — which rules apply to V60?: traverse_by_relationship("V60", "APPLIES_TO", "inbound")
    - Which roast levels suppress Jasmine?: traverse_by_relationship("Jasmine", "SUPPRESSES", "inbound")

    Valid relationship_type values (case-sensitive):
      TYPICAL_FLAVOR, PRODUCES_FLAVOR, EMPHASIZES, ENHANCES, DICTATES,
      APPLIES_TO, SUGGESTS_TEMP, PRODUCES, SUPPRESSES, PAIRS_WITH

    RETURNS: Each reachable node with its type, name, top properties, and the
    edge confidence + evidence backing the relationship.

    Args:
        node_name:         Exact or approximate starting node name.
        relationship_type: Edge type to follow (case-sensitive).
        direction:         "outbound" (default) to follow edges leaving the node;
                           "inbound" to follow edges arriving at the node.
    """
    try:
        candidates = supabase.table("knowledge_nodes").select("id, node_type, name").eq("name", node_name).execute().data
        if not candidates:
            candidates = supabase.table("knowledge_nodes").select("id, node_type, name").ilike("name", f"%{node_name}%").execute().data
        if not candidates:
            return f"No node found matching '{node_name}'."
        if len(candidates) > 1:
            names = ", ".join(f"{c['node_type']}:{c['name']}" for c in candidates)
            return f"Multiple nodes match '{node_name}': {names}. Please be more specific."

        node = candidates[0]
        node_id = node["id"]

        if direction == "outbound":
            edges_resp = supabase.table("knowledge_edges").select("target_id, properties").eq("source_id", node_id).eq("relationship_type", relationship_type).execute()
            nb_id_field = "target_id"
        else:
            edges_resp = supabase.table("knowledge_edges").select("source_id, properties").eq("target_id", node_id).eq("relationship_type", relationship_type).execute()
            nb_id_field = "source_id"

        if not edges_resp.data:
            return f"No {direction} '{relationship_type}' edges found from '{node['name']}'."

        nb_ids = [e[nb_id_field] for e in edges_resp.data]
        nb_map = {n["id"]: n for n in supabase.table("knowledge_nodes").select("id, node_type, name, properties").in_("id", nb_ids).execute().data}

        arrow = "→" if direction == "outbound" else "←"
        lines = [f"[{node['node_type']}] {node['name']}  {arrow} {relationship_type} ({direction}) {arrow}  {len(edges_resp.data)} node(s):\n"]

        for e in edges_resp.data:
            nb = nb_map.get(e[nb_id_field], {})
            props = e["properties"]
            lines.append(f"  [{nb.get('node_type','?')}] {nb.get('name','?')}")
            lines.append(f"    confidence : {props.get('confidence','?')}")
            lines.append(f"    evidence   : {props.get('evidence','?')}")
            for k, v in list((nb.get("properties") or {}).items())[:3]:
                lines.append(f"    {k}: {v}")
            lines.append("")

        return "\n".join(lines)
    except Exception as e:
        return f"Error traversing '{node_name}' via '{relationship_type}': {str(e)}"


@mcp.tool()
def cross_reference_nodes(node_a: str, node_b: str) -> str:
    """
    INTERSECTION ANALYSIS — Examines the relationship between two nodes by
    checking (1) any direct edges between them and (2) all nodes they share as
    mutual 1-hop neighbours (bridge concepts).

    This is the go-to tool for answering comparative or compatibility questions.
    It lets the LLM draw evidence-backed inferences without hallucinating
    connections that don't exist in the graph.

    WHEN TO USE:
    - "Is Ethiopian coffee good for espresso?" → cross_reference_nodes("Ethiopia", "Espresso")
    - "How does Natural processing relate to Blueberry?" → cross_reference_nodes("Natural", "Blueberry")
    - "Does a Flat Burr Grinder affect V60 quality?" → cross_reference_nodes("Flat Burr Grinder", "V60")
    - Any time the user asks about the relationship between two specific concepts.

    RETURNS:
    - Direct edges (if any) with relationship type, confidence, and evidence.
    - Shared neighbour nodes — the bridge concepts that link the two nodes
      indirectly through the graph.

    MULTI-HOP TIP: If no shared neighbours are found, call find_paths() to
    search for a longer connection chain (2-3 hops).

    Args:
        node_a: Name of the first node (exact or approximate).
        node_b: Name of the second node (exact or approximate).
    """
    try:
        def resolve(name):
            r = supabase.table("knowledge_nodes").select("id, node_type, name").eq("name", name).execute().data
            if not r:
                r = supabase.table("knowledge_nodes").select("id, node_type, name").ilike("name", f"%{name}%").execute().data
            return r

        na_list, nb_list = resolve(node_a), resolve(node_b)
        if not na_list:
            return f"Node '{node_a}' not found."
        if not nb_list:
            return f"Node '{node_b}' not found."
        if len(na_list) > 1:
            return f"'{node_a}' is ambiguous: {', '.join(n['name'] for n in na_list)}. Be more specific."
        if len(nb_list) > 1:
            return f"'{node_b}' is ambiguous: {', '.join(n['name'] for n in nb_list)}. Be more specific."

        na, nb = na_list[0], nb_list[0]
        id_a, id_b = na["id"], nb["id"]

        lines = [f"Cross-reference: [{na['node_type']}] {na['name']}  ×  [{nb['node_type']}] {nb['name']}\n"]

        # Direct edges
        ab = supabase.table("knowledge_edges").select("relationship_type, properties").eq("source_id", id_a).eq("target_id", id_b).execute().data
        ba = supabase.table("knowledge_edges").select("relationship_type, properties").eq("source_id", id_b).eq("target_id", id_a).execute().data

        if ab or ba:
            lines.append("DIRECT EDGES:")
            for e in ab:
                lines.append(f"  {na['name']} → {e['relationship_type']} → {nb['name']}  (confidence: {e['properties'].get('confidence','?')})")
                lines.append(f"  evidence: {e['properties'].get('evidence','?')}")
            for e in ba:
                lines.append(f"  {nb['name']} → {e['relationship_type']} → {na['name']}  (confidence: {e['properties'].get('confidence','?')})")
                lines.append(f"  evidence: {e['properties'].get('evidence','?')}")
        else:
            lines.append("DIRECT EDGES: None — these nodes are not directly connected.")

        # Shared neighbours
        def neighbor_ids(nid):
            out = {e["target_id"] for e in supabase.table("knowledge_edges").select("target_id").eq("source_id", nid).execute().data}
            inc = {e["source_id"] for e in supabase.table("knowledge_edges").select("source_id").eq("target_id", nid).execute().data}
            return out | inc

        shared = list((neighbor_ids(id_a) & neighbor_ids(id_b)) - {id_a, id_b})
        lines.append(f"\nSHARED NEIGHBOURS ({len(shared)} bridge node(s)):")
        if shared:
            shared_nodes = supabase.table("knowledge_nodes").select("node_type, name").in_("id", shared).execute().data
            for sn in shared_nodes:
                lines.append(f"  [{sn['node_type']}] {sn['name']}")
        else:
            lines.append("  None within 1 hop. Call find_paths() to search deeper.")

        return "\n".join(lines)
    except Exception as e:
        return f"Error cross-referencing '{node_a}' and '{node_b}': {str(e)}"


@mcp.tool()
def get_nodes_by_type(node_type: str) -> str:
    """
    TYPE ENUMERATION — Returns every node of a given type, giving the LLM a
    full inventory of available concepts in a category before making any
    recommendation. Always call this before recommending a specific node name
    to confirm it actually exists in the graph.

    WHEN TO USE:
    - "What origins do you support?" → get_nodes_by_type("Origin")
    - "List all brewing rules" → get_nodes_by_type("BrewingRule")
    - "What equipment types exist?" → get_nodes_by_type("EquipmentType")
    - Before any graph traversal that references a type, to avoid hallucinating
      node names that do not exist.

    RETURNS: All nodes of the specified type with name and a key summary
    property tailored per type (cup profile for Origins, SCA category for
    FlavorNotes, dictates summary for BrewingRules, etc.).

    Valid node_type values (case-sensitive):
      Origin, ProcessMethod, RoastLevel, FlavorNote, BrewMethod,
      BrewingRule, BrewParameter, EquipmentType, GrindProfile

    Args:
        node_type: Exact node type name (case-sensitive).
    """
    try:
        resp = supabase.table("knowledge_nodes").select("name, properties").eq("node_type", node_type).order("name").execute()

        if not resp.data:
            valid = "Origin, ProcessMethod, RoastLevel, FlavorNote, BrewMethod, BrewingRule, BrewParameter, EquipmentType, GrindProfile"
            return f"No nodes found for node_type='{node_type}'. Valid types: {valid}"

        lines = [f"All {node_type} nodes ({len(resp.data)} total):\n"]
        for n in resp.data:
            p = n["properties"]
            lines.append(f"  • {n['name']}")
            if node_type == "Origin":
                lines.append(f"    {p.get('cup_profile','')}")
            elif node_type == "BrewingRule":
                d = p.get("dictates", {})
                lines.append(f"    dictates {d.get('parameter','')} → {d.get('direction','')} to {d.get('value_range','')} {d.get('unit','')}")
            elif node_type == "FlavorNote":
                lines.append(f"    {p.get('sca_category','')} — {p.get('taste_profile','')}")
            elif node_type == "BrewMethod":
                lines.append(f"    ratio: {p.get('brew_ratio', p.get('brew_ratio_min','?'))}  |  filter: {p.get('filter_type','?')}")
            elif node_type == "EquipmentType":
                lines.append(f"    {p.get('grind_distribution', p.get('temperature_control',''))}")
            lines.append("")
        return "\n".join(lines)
    except Exception as e:
        return f"Error listing nodes by type '{node_type}': {str(e)}"


@mcp.tool()
def get_brewing_rules_for_method(brew_method_name: str) -> str:
    """
    BREWING INTELLIGENCE — Retrieves every BrewingRule that APPLIES_TO a
    specific brew method, returning the full structured JSONB for each rule:
    which parameter it controls, the target value range, whether a PID
    temperature controller is required, and — critically — the actionable
    barista workaround for users without precision equipment.

    This is the primary tool for generating grounded, actionable brewing advice.
    It surfaces the Neuro-Symbolic layer of the graph: rules derived from
    SCA standards and specialty coffee science, not from LLM training data.

    WHEN TO USE:
    - "How do I brew a great V60?" → get_brewing_rules_for_method("V60")
    - "Give me espresso tips" → get_brewing_rules_for_method("Espresso")
    - "What should I know about French Press?" → get_brewing_rules_for_method("French Press")
    - ALWAYS call this before giving brewing advice so your guidance is
      grounded in the knowledge graph, not hallucinated.

    RETURNS: For each applicable BrewingRule:
      - description, dictates (parameter + value range), pid_specificity
        (requires_pid + reason + non_pid_alternative), confidence, evidence.

    MULTI-HOP PATTERN: Combine with traverse_by_relationship(method, "EMPHASIZES")
    to also surface the FlavorNotes that method highlights — giving a complete
    brewing + flavour profile in just two tool calls.

    Args:
        brew_method_name: Name of the brew method (e.g. "Espresso", "V60",
                          "French Press", "Chemex", "AeroPress", "Cold Brew").
    """
    try:
        candidates = supabase.table("knowledge_nodes").select("id, name").eq("node_type", "BrewMethod").ilike("name", f"%{brew_method_name}%").execute().data
        if not candidates:
            return f"No BrewMethod found matching '{brew_method_name}'."
        if len(candidates) > 1:
            return f"Multiple methods match '{brew_method_name}': {', '.join(c['name'] for c in candidates)}. Be more specific."

        method = candidates[0]

        inbound = supabase.table("knowledge_edges").select("source_id").eq("target_id", method["id"]).eq("relationship_type", "APPLIES_TO").execute().data
        if not inbound:
            return f"No BrewingRules found that apply to '{method['name']}'."

        rule_ids = [e["source_id"] for e in inbound]
        rules = supabase.table("knowledge_nodes").select("name, properties").eq("node_type", "BrewingRule").in_("id", rule_ids).execute().data

        lines = [f"BrewingRules for {method['name']} ({len(rules)} rule(s)):\n"]
        for rule in rules:
            p = rule["properties"]
            d = p.get("dictates", {})
            pid = p.get("pid_specificity", {})
            lines.append(f"  ── {rule['name']} ──")
            lines.append(f"  {p.get('description','')}")
            lines.append(f"  Dictates : {d.get('parameter','')} → {d.get('direction','')} to {d.get('value_range','')} {d.get('unit','')}")
            lines.append(f"  PID required    : {pid.get('requires_pid','?')}")
            if pid.get("requires_pid"):
                lines.append(f"  Reason          : {pid.get('reason','')}")
            lines.append(f"  No-PID workaround: {pid.get('non_pid_alternative','')}")
            lines.append(f"  Confidence: {p.get('confidence','?')}  |  Source: {p.get('evidence','?')}")
            lines.append("")
        return "\n".join(lines)
    except Exception as e:
        return f"Error retrieving brewing rules for '{brew_method_name}': {str(e)}"


@mcp.tool()
def find_paths(start_node: str, end_node: str, max_hops: int = 3) -> str:
    """
    MULTI-HOP PATH FINDING — Discovers how two nodes are connected across the
    knowledge graph, even with no direct edge. Uses BFS over the full graph
    (loaded in-memory — 60 nodes, 89 edges) to find all shortest paths up to
    max_hops steps, returning the complete chain of nodes and relationships.

    This is the most powerful reasoning tool in the suite. It lets the LLM
    construct an explicit, evidence-grounded reasoning chain to explain *why*
    two concepts are related — beyond shallow 1-hop lookups.

    WHEN TO USE:
    - "Why would Ethiopian Natural pair well with French Press?" →
        find_paths("Ethiopia", "French Press")
    - "How does a Conical Burr Grinder relate to Dark Chocolate flavour?" →
        find_paths("Conical Burr Grinder", "Dark Chocolate")
    - When cross_reference_nodes() finds no shared neighbours and you need
      to search deeper than 1 hop.
    - Any time the user asks "why" or "how" two coffee concepts relate.

    RETURNS: Up to 5 shortest paths, each showing the full node-and-edge chain:
      [Origin] Ethiopia → TYPICAL_FLAVOR → [FlavorNote] Blueberry
                        → PRODUCES_FLAVOR ← [ProcessMethod] Natural
                        ...

    Traversal is bidirectional (edges followed in both directions) so the path
    can cross any relationship type in either direction.

    PERFORMANCE: max_hops above 4 is rarely needed and is capped at 4.
    The default of 3 covers virtually all meaningful connections in this graph.

    Args:
        start_node: Name of the starting node (exact or approximate).
        end_node:   Name of the destination node (exact or approximate).
        max_hops:   Maximum edges to traverse. Default 3, capped at 4.
    """
    try:
        from collections import deque
        max_hops = min(int(max_hops), 4)

        def resolve_one(name):
            r = supabase.table("knowledge_nodes").select("id, node_type, name").eq("name", name).execute().data
            if not r:
                r = supabase.table("knowledge_nodes").select("id, node_type, name").ilike("name", f"%{name}%").execute().data
            return r

        starts, ends = resolve_one(start_node), resolve_one(end_node)
        if not starts:
            return f"Start node '{start_node}' not found."
        if not ends:
            return f"End node '{end_node}' not found."
        if len(starts) > 1:
            return f"'{start_node}' is ambiguous: {', '.join(n['name'] for n in starts)}."
        if len(ends) > 1:
            return f"'{end_node}' is ambiguous: {', '.join(n['name'] for n in ends)}."

        start, end = starts[0], ends[0]
        if start["id"] == end["id"]:
            return f"Start and end are the same node: {start['name']}."

        # Load full graph into memory
        node_info = {n["id"]: n for n in supabase.table("knowledge_nodes").select("id, node_type, name").execute().data}
        all_edges  = supabase.table("knowledge_edges").select("source_id, target_id, relationship_type").execute().data

        # Bidirectional adjacency: id → [(neighbour_id, display_label)]
        adj: dict[str, list] = {nid: [] for nid in node_info}
        for e in all_edges:
            s, t, r = e["source_id"], e["target_id"], e["relationship_type"]
            adj[s].append((t, f"→{r}→"))
            adj[t].append((s, f"←{r}←"))

        # BFS — each queue entry: (current_id, path)
        # path = [(node_id, edge_label_used_to_arrive_here), ...]
        queue = deque([(start["id"], [(start["id"], "")])])
        found: list = []

        while queue and len(found) < 5:
            current_id, path = queue.popleft()
            if len(path) - 1 >= max_hops:
                continue
            visited_in_path = {p[0] for p in path}
            for nb_id, label in adj.get(current_id, []):
                if nb_id in visited_in_path:
                    continue
                new_path = path + [(nb_id, label)]
                if nb_id == end["id"]:
                    found.append(new_path)
                    if len(found) >= 5:
                        break
                else:
                    queue.append((nb_id, new_path))

        if not found:
            return (f"No path found between '{start['name']}' and '{end['name']}' "
                    f"within {max_hops} hops.\n"
                    f"Try increasing max_hops, or use cross_reference_nodes() "
                    f"to inspect 1-hop shared neighbours.")

        lines = [
            f"Paths: [{start['node_type']}] {start['name']} → ... → "
            f"[{end['node_type']}] {end['name']}  "
            f"({len(found)} path(s), max_hops={max_hops})\n"
        ]
        for i, path in enumerate(found, 1):
            lines.append(f"  Path {i} ({len(path)-1} hop(s)):")
            for j, (nid, label) in enumerate(path):
                n = node_info.get(nid, {})
                node_label = f"[{n.get('node_type','?')}] {n.get('name','?')}"
                if j == 0:
                    lines.append(f"    {node_label}")
                else:
                    lines.append(f"    {label}")
                    lines.append(f"    {node_label}")
            lines.append("")
        return "\n".join(lines)
    except Exception as e:
        return f"Error finding paths between '{start_node}' and '{end_node}': {str(e)}"


@mcp.tool()
def semantic_search(query: str, match_count: int = 3) -> str:
    """
    SEMANTIC SEARCH — The ultimate fallback tool when you don't know the exact
    node name, relationship type, or even the right category to search in.

    Unlike search_nodes() (which does a text substring match on node names),
    semantic_search() encodes the *meaning* of the query into a 1536-dimension
    vector and finds the knowledge graph nodes whose stored embeddings are most
    semantically similar — regardless of exact wording.

    WHEN TO USE THIS TOOL:
    - Abstract or emotional queries: "something for cold mornings", "cozy",
      "bright and energising", "smooth and low-acid" — these have no exact
      graph node but map strongly to certain origins, roast levels, or methods.
    - Flavour-first queries: "sour", "fruity", "jammy", "stone fruit" — the
      user is describing a taste experience, not a node name.
    - Concept bridging: "What coffee suits a beginner with no fancy equipment?"
      — the answer lives across BrewMethod, EquipmentType, and BrewingRule
      nodes whose embeddings capture that context.
    - When search_nodes() returns nothing useful and you need a broader net.
    - When the user's phrasing is colloquial or imprecise ("Ethiopian-ish",
      "something like V60 but easier").

    HOW IT WORKS:
    Calls the Supabase `match_knowledge_nodes` RPC (pgvector cosine similarity)
    with a match_threshold of 0.2. Results are ranked by similarity score
    (1.0 = identical meaning, 0.0 = unrelated). Scores above 0.5 are strong
    matches; 0.3-0.5 are plausible associations worth investigating.

    MULTI-HOP PATTERN:
    1. semantic_search("fruity and floral light roast") → surfaces "Ethiopia",
       "Jasmine", "Light" as top hits.
    2. get_node_connections("Ethiopia") → explore exact graph relationships.
    3. get_brewing_rules_for_method("V60") → ground the advice in brewing rules.

    RETURNS: Up to `match_count` nodes ranked by semantic similarity, each with
    node_type, name, similarity score, and a properties snippet so you can
    immediately judge relevance and decide which graph tools to call next.

    Args:
        query:       Natural-language description of what you're looking for.
                     Can be a flavour profile, brewing scenario, or abstract concept.
        match_count: Maximum number of results to return (default 3, max sensible
                     value is ~10 — more results dilute relevance quickly).
    """
    try:
        # 1. Embed the query
        response = openai_client.embeddings.create(
            input=query.strip().replace("\n", " "),
            model="text-embedding-3-small",
        )
        embedding = response.data[0].embedding

        # 2. Call the pgvector RPC
        rpc_resp = supabase.rpc(
            "match_knowledge_nodes",
            {
                "query_embedding": embedding,
                "match_threshold":  0.2,
                "match_count":      match_count,
            },
        ).execute()

        results = rpc_resp.data
        if not results:
            return (
                f"No semantic matches found for query: '{query}'.\n"
                f"Try rephrasing, or use search_nodes() for an exact keyword lookup."
            )

        lines = [f"Semantic search for '{query}' — {len(results)} match(es):\n"]
        for i, row in enumerate(results, 1):
            similarity = row.get("similarity", 0)
            props = row.get("properties") or {}

            # Build a short properties snippet (first 3 key-value pairs)
            snippet_parts = []
            for k, v in list(props.items())[:3]:
                if isinstance(v, list):
                    snippet_parts.append(f"{k}: {', '.join(str(x) for x in v)}")
                else:
                    snippet_parts.append(f"{k}: {v}")
            snippet = " | ".join(snippet_parts) if snippet_parts else "(no properties)"

            lines.append(f"  {i}. [{row.get('node_type','?')}] {row.get('name','?')}")
            lines.append(f"     similarity : {similarity:.4f}")
            lines.append(f"     properties : {snippet}")
            lines.append("")

        return "\n".join(lines)

    except Exception as e:
        return f"Error during semantic search: {str(e)}"


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