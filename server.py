import os
import re
import hmac
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse
from collections import Counter
from dotenv import load_dotenv
from fastapi import FastAPI
from openai import OpenAI
from supabase import create_client, Client
from mcp.server.fastmcp import FastMCP

load_dotenv()

supabase_url: str = os.environ.get("SUPABASE_URL")
supabase_key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Bounded pool for background ingestion jobs — caps concurrency, reuses threads.
_ingest_executor = ThreadPoolExecutor(max_workers=4)

mcp = FastMCP("Coffee Barista MCP", host="0.0.0.0")

# Admin gate for research_and_ingest_topic. The MCP server is otherwise
# identity-blind, so authorization rides on headers the *frontend* attaches to
# its MCP transport requests AFTER it authenticates the user with Supabase —
# never on an LLM-supplied argument (which a user or a prompt-injected scraped
# page could forge). Both must be set in the server environment for the tool to
# ever run; if either is unset the tool fails closed.
ADMIN_EMAIL: str = (os.environ.get("ADMIN_EMAIL") or "").strip().lower()
RESEARCH_INGEST_SECRET: str = os.environ.get("RESEARCH_INGEST_SECRET") or ""
_ADMIN_DENIED = "Error: This operation is restricted to system administrators."


# =============================================================================
# PRIVATE HELPERS — plain Python functions, not MCP tools.
# These are the internal plumbing called by the 4 public tools below.
# =============================================================================

# --- Formerly public tools, now internal data-access helpers -----------------

def _get_recent_shots(limit: int = 5) -> str:
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


def _analyze_best_value_coffees() -> str:
    try:
        beans_response = supabase.table("beans").select("id, roaster, origin, price_paid, weight_grams").execute()
        shots_response = supabase.table("shots").select("bean_id, overall_score, brew_method").execute()
        beans = beans_response.data
        shots = [s for s in shots_response.data if s.get("overall_score") is not None and s.get("bean_id") is not None]
        if not beans or not shots:
            return "Not enough data to perform VFM analysis."
        bean_stats: dict = {}
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
        result = ["Value For Money (VFM) & Brew Analysis:\n"]
        for bean in beans:
            b_id = bean.get("id")
            stats = bean_stats.get(b_id)
            if not stats:
                continue
            avg_score = sum(stats["scores"]) / len(stats["scores"])
            method_avgs = {m: sum(s) / len(s) for m, s in stats["methods"].items()}
            best_method = max(method_avgs, key=method_avgs.get)
            price = bean.get("price_paid")
            weight = bean.get("weight_grams")
            if price and weight and float(weight) > 0:
                price_per_100g = (float(price) / float(weight)) * 100
                vfm_index = avg_score / price_per_100g if price_per_100g > 0 else 0
                cost_str = f"${price_per_100g:.2f} per 100g | VFM Index: {vfm_index:.2f}"
            else:
                cost_str = "Price/Weight data missing"
            result.append(
                f"  {bean.get('roaster')} - {bean.get('origin')}\n"
                f"    Overall Score : {avg_score:.1f}/10 ({len(stats['scores'])} shots)\n"
                f"    Value         : {cost_str}\n"
                f"    Best Method   : {best_method} (avg {method_avgs[best_method]:.1f}/10)\n"
            )
        return "\n".join(result)
    except Exception as e:
        return f"Error analyzing beans: {str(e)}"


def _search_nodes(keyword: str, node_type: str = "") -> str:
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


def _get_node_connections(node_name: str) -> str:
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


def _traverse_by_relationship(node_name: str, relationship_type: str, direction: str = "outbound") -> str:
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


def _cross_reference_nodes(node_a: str, node_b: str) -> str:
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
            lines.append("  None within 1 hop.")
        return "\n".join(lines)
    except Exception as e:
        return f"Error cross-referencing '{node_a}' and '{node_b}': {str(e)}"


def _get_nodes_by_type(node_type: str) -> str:
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
            elif node_type == "Cultivar":
                lines.append(f"    {p.get('cup_profile','')}")
                lines.append(f"    origins: {', '.join(p.get('typical_origins', []))}")
            elif node_type == "Region":
                lines.append(f"    parent: {p.get('parent_origin','')}  |  alt: {p.get('altitude_range_m','')}")
                lines.append(f"    {p.get('cup_profile','')}")
            elif node_type == "Defect":
                lines.append(f"    stage: {p.get('stage','')}  |  severity: {p.get('severity','')}")
                lines.append(f"    {p.get('sensory_description','')[:100]}")
            elif node_type == "BrewingTechnique":
                lines.append(f"    {p.get('purpose','')[:100]}")
                lines.append(f"    applies to: {', '.join(p.get('applies_to_methods', []))}")
            elif node_type == "SensoryDescriptor":
                lines.append(f"    {p.get('perception','')}")
                lines.append(f"    class: {p.get('chemical_class','')}")
            elif node_type == "Expert":
                lines.append(f"    {p.get('known_for','')[:100]}")
            lines.append("")
        return "\n".join(lines)
    except Exception as e:
        return f"Error listing nodes by type '{node_type}': {str(e)}"


def _get_brewing_rules_for_method(brew_method_name: str) -> str:
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
            lines.append(f"  PID required     : {pid.get('requires_pid','?')}")
            if pid.get("requires_pid"):
                lines.append(f"  Reason           : {pid.get('reason','')}")
            lines.append(f"  No-PID workaround: {pid.get('non_pid_alternative','')}")
            lines.append(f"  Confidence: {p.get('confidence','?')}  |  Source: {p.get('evidence','?')}")
            lines.append("")
        return "\n".join(lines)
    except Exception as e:
        return f"Error retrieving brewing rules for '{brew_method_name}': {str(e)}"


def _find_paths(start_node: str, end_node: str, max_hops: int = 3) -> str:
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
        node_info = {n["id"]: n for n in supabase.table("knowledge_nodes").select("id, node_type, name").execute().data}
        all_edges  = supabase.table("knowledge_edges").select("source_id, target_id, relationship_type").execute().data
        adj: dict[str, list] = {nid: [] for nid in node_info}
        for e in all_edges:
            s, t, r = e["source_id"], e["target_id"], e["relationship_type"]
            adj[s].append((t, f"→{r}→"))
            adj[t].append((s, f"←{r}←"))
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
                    f"within {max_hops} hops.")
        lines = [f"Paths: [{start['node_type']}] {start['name']} → ... → [{end['node_type']}] {end['name']}  ({len(found)} path(s))\n"]
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


def _semantic_search(query: str, match_count: int = 5) -> str:
    try:
        response = openai_client.embeddings.create(
            input=query.strip().replace("\n", " "),
            model="text-embedding-3-small",
        )
        embedding = response.data[0].embedding
        rpc_resp = supabase.rpc(
            "match_knowledge_nodes",
            {"query_embedding": embedding, "match_threshold": 0.2, "match_count": match_count},
        ).execute()
        results = rpc_resp.data
        if not results:
            return f"No semantic matches found for: '{query}'."
        lines = [f"Semantic search '{query}' — {len(results)} match(es):\n"]
        for i, row in enumerate(results, 1):
            similarity = row.get("similarity", 0)
            props = row.get("properties") or {}
            snippet_parts = []
            for k, v in list(props.items())[:3]:
                snippet_parts.append(f"{k}: {', '.join(str(x) for x in v) if isinstance(v, list) else v}")
            snippet = " | ".join(snippet_parts) if snippet_parts else "(no properties)"
            lines.append(f"  {i}. [{row.get('node_type','?')}] {row.get('name','?')}")
            lines.append(f"     similarity : {similarity:.4f}")
            lines.append(f"     properties : {snippet}")
            lines.append("")
        return "\n".join(lines)
    except Exception as e:
        return f"Error during semantic search: {str(e)}"


# --- Vector + graph enrichment helpers (unchanged) ---------------------------

def _embed(text: str) -> list[float]:
    response = openai_client.embeddings.create(
        input=text.strip().replace("\n", " "),
        model="text-embedding-3-small",
    )
    return response.data[0].embedding


def _vector_search_raw(embedding: list[float], threshold: float = 0.2, count: int = 5) -> list[dict]:
    resp = supabase.rpc("match_knowledge_nodes", {
        "query_embedding": embedding,
        "match_threshold":  threshold,
        "match_count":      count,
    }).execute()
    return resp.data or []




def _enrich_node(node: dict, similarity: float | None = None) -> str:
    sim_tag = f"  (similarity: {similarity:.4f})" if similarity is not None else ""
    lines = [f"  [{node.get('node_type','?')}] {node.get('name','?')}{sim_tag}"]
    props = node.get("properties") or {}
    # Surface _source explicitly so Bean can always cite the origin document.
    if "_source" in props:
        lines.append(f"    source: {props['_source']}")
    for k, v in list(props.items())[:4]:
        if k == "_source":
            continue
        val = ", ".join(str(x) for x in v) if isinstance(v, list) else str(v)
        lines.append(f"    {k}: {val}")
    node_id = node.get("id")
    if not node_id:
        return "\n".join(lines)
    out_edges = supabase.table("knowledge_edges").select("target_id, relationship_type, properties").eq("source_id", node_id).execute().data
    in_edges  = supabase.table("knowledge_edges").select("source_id, relationship_type, properties").eq("target_id", node_id).execute().data
    nb_ids = [e["target_id"] for e in out_edges] + [e["source_id"] for e in in_edges]
    if nb_ids:
        nb_map = {n["id"]: n for n in supabase.table("knowledge_nodes").select("id, node_type, name").in_("id", nb_ids).execute().data}
        if out_edges:
            lines.append("    Connects to:")
            for e in out_edges[:5]:
                nb = nb_map.get(e["target_id"], {})
                conf = e["properties"].get("confidence", "?")
                lines.append(f"      → {e['relationship_type']} → [{nb.get('node_type','?')}] {nb.get('name','?')}  (conf: {conf})")
        if in_edges:
            lines.append("    Referenced by:")
            for e in in_edges[:3]:
                nb = nb_map.get(e["source_id"], {})
                lines.append(f"      ← {e['relationship_type']} ← [{nb.get('node_type','?')}] {nb.get('name','?')}")
    return "\n".join(lines)


# --- Orchestration helpers (new) ---------------------------------------------

def _unified_search(query: str, embedding: list[float]) -> str:
    """Vector search + graph enrichment. Returns formatted string."""
    sections: list[str] = []
    seen_ids: set[str] = set()

    vector_hits = _vector_search_raw(embedding, threshold=0.2, count=5)
    high_conf   = [r for r in vector_hits if (r.get("similarity") or 0) >= 0.6]
    low_conf    = [r for r in vector_hits if 0.2 <= (r.get("similarity") or 0) < 0.6]

    sections.append(
        f"  {len(vector_hits)} vector hit(s)  |  "
        f"{len(high_conf)} high-confidence (≥ 0.6)"
    )

    enrich_budget = 3

    if high_conf and enrich_budget > 0:
        sections.append("── HIGH-CONFIDENCE SEMANTIC MATCHES (similarity ≥ 0.6) ──")
        for r in high_conf:
            if enrich_budget <= 0:
                break
            r_id = r.get("id")
            if r_id and r_id not in seen_ids:
                seen_ids.add(r_id)
                sections.append(_enrich_node(r, similarity=r.get("similarity")))
                sections.append("")
                enrich_budget -= 1

    remaining = [r for r in low_conf if r.get("id") not in seen_ids]
    if remaining:
        sections.append("── SUPPORTING CONTEXT (similarity 0.2–0.6) ──")
        for r in remaining[:3]:
            props = r.get("properties") or {}
            snippet = "  |  ".join(
                f"{k}: {', '.join(str(x) for x in v) if isinstance(v, list) else v}"
                for k, v in list(props.items())[:2]
            )
            sections.append(f"  [{r.get('node_type','?')}] {r.get('name','?')}  (similarity: {r.get('similarity', 0):.4f})")
            if snippet:
                sections.append(f"  {snippet}")
            sections.append("")

    return "\n".join(sections) if sections else "No results found."


def _get_user_context() -> str:
    """
    Derive a user profile from existing shots and beans data.
    Returns a formatted summary block prepended to every ask() response.
    """
    try:
        shots = supabase.table("shots").select(
            "brew_method, overall_score, created_at"
        ).order("created_at", desc=True).limit(30).execute().data

        active_beans = supabase.table("beans").select(
            "roaster, origin, roast_date"
        ).eq("is_active", True).execute().data

        lines = ["── YOUR CONTEXT ──"]

        # Active bean
        if active_beans:
            b = active_beans[0]
            lines.append(f"  Active bean    : {b.get('roaster','')} — {b.get('origin','')}  (roasted: {b.get('roast_date','')})")
        else:
            lines.append("  Active bean    : None set")

        if not shots:
            lines.append("  Shot history   : None yet — log your first shot with log_shot()")
            return "\n".join(lines)

        method_counts: Counter = Counter(s.get("brew_method") for s in shots if s.get("brew_method"))
        method_scores: dict[str, list[float]] = {}
        for s in shots:
            m  = s.get("brew_method")
            sc = s.get("overall_score")
            if m and sc is not None:
                method_scores.setdefault(m, []).append(float(sc))

        top_method  = method_counts.most_common(1)[0][0] if method_counts else "unknown"
        avg_scores  = {m: sum(v) / len(v) for m, v in method_scores.items()}
        best_method = max(avg_scores, key=avg_scores.get) if avg_scores else "unknown"
        overall_avg = sum(avg_scores.values()) / len(avg_scores) if avg_scores else 0.0

        lines.append(f"  Most used      : {top_method} ({method_counts.get(top_method, 0)} shots)")
        lines.append(f"  Best scoring   : {best_method} (avg {avg_scores.get(best_method, 0):.1f}/10)")
        lines.append(f"  Overall avg    : {overall_avg:.1f}/10  across {len(shots)} recent shots")

        return "\n".join(lines)
    except Exception as e:
        return f"── YOUR CONTEXT ──\n  (unavailable: {str(e)})"


# =============================================================================
# DEFECT VOCABULARY — used by both intent classification and graph traversal.
#
# _DEFECT_WORD_MAP  : maps a lowercase query substring to the exact Defect node
#   name stored in knowledge_nodes.  If a user types "channeling" we can look
#   up the "Channeling" node and traverse its CAUSES / PREVENTS edges directly.
#
# _NEGATIVE_SENSORY_WORDS : broader set of negative-taste / problem signals
#   that don't have a 1:1 Defect node but still indicate "something went wrong
#   with my shot".  They trigger the diagnosis intent so the last shot is
#   fetched and diagnosed even when the user doesn't name a brew method.
# =============================================================================

_DEFECT_WORD_MAP: dict[str, str] = {
    "channeling":   "Channeling",
    "baked":        "Baked",
    "sour ferment": "Sour Ferment",
    "astringent":   "Astringency",
    "astringency":  "Astringency",
    "grassy":       "Grassy",
}

_NEGATIVE_SENSORY_WORDS: frozenset[str] = frozenset({
    "sour", "bitter", "harsh", "flat", "hollow", "vinegar", "acetic",
    "papery", "rubbery", "dry", "rough", "off", "wrong", "went wrong",
    "bad shot", "fix my", "help me fix", "diagnose",
    "over-extracted", "under-extracted", "over extracted", "under extracted",
    "why was my", "why did my", "what happened",
})


_VALID_INTENTS: frozenset[str] = frozenset(
    {"recommendation", "diagnosis", "brewing", "knowledge"}
)

_INTENT_ROUTER_SYSTEM_PROMPT = """\
You are an intent router for a coffee assistant. Read the user's message and
classify it into EXACTLY ONE of these four intents. Respond with ONLY the
single lowercase category word — one of:
recommendation | diagnosis | brewing | knowledge
No quotes, no punctuation, no JSON, no explanation. Just the one word.

CATEGORIES

recommendation — The user wants a suggestion about WHICH coffee/bean to buy,
  try, or whether something is worth the money. Value-for-money, "what should I
  try next", "which bean is best", purchasing decisions.
  e.g. "what bean should I buy next?", "is this roaster worth it?",
       "recommend something fruity"

diagnosis — The user is describing a PROBLEM with a coffee they made and wants
  to know what went wrong or how to fix it. Negative taste/quality signals:
  sour, bitter, harsh, astringent, channeling, "my shot was bad",
  "why did it taste off". These need shot history + defect cause/prevention.
  e.g. "why was my espresso so sour?", "my coffee tastes bitter and thin",
       "I keep getting channeling"

brewing — The user wants ACTIONABLE how-to guidance to prepare or improve a brew
  THEY are making: recipes, parameters, dialing in, grind/temp/ratio/dose
  adjustments, techniques to apply. This is "how do I make/brew/adjust X".
  e.g. "how do I brew a V60?", "what grind for espresso?",
       "how should I dial in this bean?", "how to do WDT"

knowledge — The user wants to UNDERSTAND a concept, mechanism, or fact about
  coffee science, origins, processing, or chemistry. Explanatory/educational,
  NOT tied to fixing or making their own cup.
  e.g. "what is extraction yield?", "how is decaf made?",
       "why does light roast taste more acidic?", "what is the Maillard reaction?"

CRITICAL EDGE CASE — "how" questions:
  - "how do I brew / make / adjust <my drink>"     → brewing (actionable, theirs)
  - "how does <X> work" / "how is <X> made"        → knowledge (conceptual)
  "how is decaf made" is knowledge, NOT brewing.
  "how do I make a good espresso" is brewing.

If genuinely ambiguous, prefer the more specific intent in this priority order:
diagnosis > recommendation > brewing > knowledge.
Respond with ONLY the single category word, nothing else."""


def _classify_intent(query: str) -> str:
    """
    Semantic LLM intent router.
    Returns one of: 'recommendation' | 'diagnosis' | 'brewing' | 'knowledge'

    Uses a fast model (gpt-4o-mini) with a strong category-defining system
    prompt to classify the query. This handles paraphrase, typos, and the
    "how to brew" vs "how does X work" distinction that the old substring
    heuristic missed (e.g. "how is decaf made" → knowledge, not brewing).

    For latency the model returns a single bare word (no JSON wrapper), capped
    at a few tokens. Reliability contract: this function ALWAYS returns a valid
    intent. If the API call fails, times out, or returns an unrecognised label,
    it falls back to the deterministic keyword classifier
    (`_classify_intent_keyword`) so `ask()` never receives an invalid value.
    """
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            max_tokens=8,
            messages=[
                {"role": "system", "content": _INTENT_ROUTER_SYSTEM_PROMPT},
                {"role": "user", "content": query},
            ],
        )
        raw = response.choices[0].message.content or ""
        # Normalise: drop stray quotes/punctuation/casing, take the first word.
        tokens = raw.strip().strip('"\'.`').lower().split()
        intent = tokens[0] if tokens else ""
        if intent in _VALID_INTENTS:
            return intent
        # Unrecognised label → deterministic fallback rather than guessing.
        return _classify_intent_keyword(query)
    except Exception:
        # Any API/parse failure must not break routing — degrade gracefully.
        return _classify_intent_keyword(query)


def _classify_intent_keyword(query: str) -> str:
    """
    Deterministic keyword fallback for `_classify_intent`.
    Returns one of: 'recommendation' | 'diagnosis' | 'brewing' | 'knowledge'

    Used only when the LLM router is unavailable. Order matters: diagnosis is
    checked before brewing because many defect queries contain brewing words
    ("shot", "extract") and would otherwise be misrouted; knowledge framing is
    checked before brewing so "what is extraction yield?" doesn't match on the
    word "extract".
    """
    q = query.lower()
    if any(w in q for w in [
        "recommend", "suggest", "best", "which bean", "what bean",
        "worth", "value", "vfm", "try next", "should i buy", "what should i try",
    ]):
        return "recommendation"
    if (any(w in q for w in _DEFECT_WORD_MAP)
            or any(w in q for w in _NEGATIVE_SENSORY_WORDS)):
        return "diagnosis"
    if any(w in q for w in [
        "what is", "what are", "why is", "why does", "why do",
        "explain", "how does", "what does", "tell me about",
        "based on the research", "according to", "what model", "what theory",
    ]):
        return "knowledge"
    if any(w in q for w in [
        "how", "brew", "make", "grind", "temperature", "temp",
        "ratio", "dose", "pour", "steep", "extract", "pull", "shot",
        "recipe", "technique", "prepare",
    ]):
        return "brewing"
    return "knowledge"


# =============================================================================
# DEFECT GRAPH CONTEXT — pure graph traversal, no inference
#
# Reads CAUSES (inbound) and PREVENTS (inbound) edges for any Defect nodes
# matched in the query.  Returns a formatted string block that the LLM uses
# to explain *why* a shot tasted wrong and *what to do* about it.
#
# Architecture note: all thresholds and causal claims live in the graph as
# node properties and edge evidence strings.  This function never hard-codes
# what causes or prevents a defect — it only reads what the graph says.
# =============================================================================

def _get_defect_graph_context(embedding: list[float]) -> str:
    """
    Find Defect nodes via semantic search and return a structured block
    showing what CAUSES each matched defect and what PREVENTS it.
    Caps at 2 defects.
    """
    defect_nodes = [
        n for n in _vector_search_raw(embedding, threshold=0.2, count=10)
        if n["node_type"] == "Defect"
    ][:2]

    if not defect_nodes:
        return ""

    try:
        sections: list[str] = [
            f"── DEFECT GRAPH CONTEXT ({len(defect_nodes)} defect(s) identified) ──"
        ]

        for defect in defect_nodes:
            defect_id = defect["id"]
            p         = defect.get("properties") or {}

            sections.append(f"\n[Defect] {defect['name']}")
            sections.append(f"  Stage    : {p.get('stage', '?')}")
            sections.append(f"  Severity : {p.get('severity', '?')}")
            sections.append(f"  Feels like : {str(p.get('sensory_description', '?'))[:120]}")
            sections.append(f"  Root fix : {p.get('corrective_action', '?')}")

            # ── CAUSES inbound: X → CAUSES → this defect ─────────────────────
            # These are the upstream sources that produce this defect.
            # Could be another Defect (cascades), a SensoryDescriptor (chemistry),
            # or a brewing condition.
            causes_edges = (
                supabase.table("knowledge_edges")
                .select("source_id, properties")
                .eq("target_id", defect_id)
                .eq("relationship_type", "CAUSES")
                .execute()
                .data
            )
            if causes_edges:
                src_ids = [e["source_id"] for e in causes_edges]
                src_map = {
                    n["id"]: n
                    for n in supabase.table("knowledge_nodes")
                    .select("id, node_type, name")
                    .in_("id", src_ids)
                    .execute()
                    .data
                }
                sections.append("  Caused by:")
                for e in causes_edges:
                    src  = src_map.get(e["source_id"], {})
                    conf = e["properties"].get("confidence", "?")
                    evid = str(e["properties"].get("evidence", ""))[:90]
                    sections.append(
                        f"    ← CAUSES ← [{src.get('node_type','?')}] {src.get('name','?')}"
                        f"  (confidence {conf})"
                    )
                    if evid:
                        sections.append(f"      evidence: {evid}")

            # ── PREVENTS inbound: X → PREVENTS → this defect ─────────────────
            # These are the techniques and rules that eliminate this defect
            # when applied correctly.  This is what Bean should recommend.
            prevents_edges = (
                supabase.table("knowledge_edges")
                .select("source_id, properties")
                .eq("target_id", defect_id)
                .eq("relationship_type", "PREVENTS")
                .execute()
                .data
            )
            if prevents_edges:
                prev_ids = [e["source_id"] for e in prevents_edges]
                prev_map = {
                    n["id"]: n
                    for n in supabase.table("knowledge_nodes")
                    .select("id, node_type, name, properties")
                    .in_("id", prev_ids)
                    .execute()
                    .data
                }
                sections.append("  Prevented by:")
                for e in prevents_edges:
                    src  = prev_map.get(e["source_id"], {})
                    conf = e["properties"].get("confidence", "?")
                    sections.append(
                        f"    → PREVENTS ← [{src.get('node_type','?')}] {src.get('name','?')}"
                        f"  (confidence {conf})"
                    )
                    # Surface the technique's purpose so the LLM can paraphrase it
                    if src.get("node_type") == "BrewingTechnique":
                        purpose = str((src.get("properties") or {}).get("purpose", ""))[:100]
                        if purpose:
                            sections.append(f"      purpose: {purpose}")
                    elif src.get("node_type") == "BrewingRule":
                        desc = str((src.get("properties") or {}).get("description", ""))[:100]
                        if desc:
                            sections.append(f"      rule: {desc}")

        return "\n".join(sections)

    except Exception as e:
        return f"── DEFECT GRAPH CONTEXT ──\n  (unavailable: {str(e)})"


# =============================================================================
# DIAGNOSIS ENGINE — rule-based inference over BrewingRule graph nodes
#
# These three helpers form the core of step 3 of the semantic layer.
# The key architectural principle: thresholds live in the graph as BrewingRule
# nodes, not hardcoded in Python. Adding a book adds new rules; the diagnosis
# engine automatically uses them — zero code changes required.
# =============================================================================

def _parse_value_range(value_range: str) -> tuple[float, float] | None:
    """
    Parse a BrewingRule dictates.value_range string into a (min, max) float pair.

    Handles the formats present in the graph:
      "25-35"           → (25.0, 35.0)
      "94-96"           → (94.0, 96.0)
      "1:1.8 to 1:2.5"  → (1.8, 2.5)   — right-side of ratio extracted
      "1:15-1:17"       → (15.0, 17.0)  — right-side of ratio extracted
      "200-400"          → (200.0, 400.0)
      "Fine (200-400…)"  → (200.0, 400.0) — numbers extracted from context

    Returns None when the range is non-numeric or too complex to evaluate
    (e.g. "concentrate_then_dilute").  Callers mark those rules UNCHECKED.
    """
    if not value_range:
        return None

    # Ratio patterns: "1:15 to 1:17" or "1:1.8-1:2.5"
    # Extract the right-hand side of every "1:X" token.
    ratio_parts = re.findall(r'1:(\d+\.?\d*)', value_range)
    if len(ratio_parts) >= 2:
        try:
            lo, hi = float(ratio_parts[0]), float(ratio_parts[-1])
            return (min(lo, hi), max(lo, hi))
        except ValueError:
            pass

    # Parenthesised range: "(200-400 microns)" or "(1.8-2.5 acceptable)"
    paren_match = re.search(r'\((\d+\.?\d*)\s*[-–]\s*(\d+\.?\d*)', value_range)
    if paren_match:
        try:
            return (float(paren_match.group(1)), float(paren_match.group(2)))
        except ValueError:
            pass

    # Simple "X-Y" or "X to Y"
    plain_match = re.search(r'(\d+\.?\d*)\s*(?:[-–]|to)\s*(\d+\.?\d*)', value_range)
    if plain_match:
        try:
            lo, hi = float(plain_match.group(1)), float(plain_match.group(2))
            return (min(lo, hi), max(lo, hi))
        except ValueError:
            pass

    return None


def _corrective_action_from_rule(p: dict, side: str) -> str:
    """Derive a corrective action from the BrewingRule's own properties."""
    if explicit := p.get("corrective_action"):
        return explicit
    dictates  = p.get("dictates", {})
    param     = dictates.get("parameter", "parameter").replace("_", " ")
    val_range = dictates.get("value_range", "target range")
    unit      = dictates.get("unit", "")
    direction = "Increase" if side == "below" else "Decrease"
    target    = f"{val_range} {unit}".strip()
    description = p.get("description", "")
    if description:
        return f"{direction} {param} toward {target}. Rule: {description}"
    return f"{direction} {param} toward {target}"


def _diagnose_shot(shot: dict) -> str:
    """
    Compare a shot record against every BrewingRule that APPLIES_TO its method.

    For each rule whose dictates.direction is "target_range" we compare the
    shot's actual value against the parsed value_range and classify as:
      VIOLATED  — actual is outside range; includes corrective action + evidence
      COMPLIANT — actual is within range
    Rules with directional hints ("increase" / "decrease") are shown as
    CONTEXT — they give calibration guidance without being strict pass/fail.
    Rules whose parameter is not tracked in the shots table (bloom_time,
    grind_size in microns, etc.) are labelled UNCHECKED.

    Violations are sorted by confidence descending so the most evidence-backed
    issues surface first.  All thresholds come from graph BrewingRule nodes —
    adding new rules via book ingestion instantly enriches future diagnoses.
    """
    brew_method = shot.get("brew_method", "")
    if not brew_method:
        return "Cannot diagnose: shot has no brew_method."

    try:
        # ── 1. Resolve BrewMethod node ──────────────────────────────────────
        method_nodes = supabase.table("knowledge_nodes") \
            .select("id, name") \
            .eq("node_type", "BrewMethod") \
            .ilike("name", f"%{brew_method}%").execute().data
        if not method_nodes:
            return f"No BrewMethod node found for '{brew_method}' — cannot run diagnosis."
        method = method_nodes[0]

        # ── 2. Fetch all BrewingRules that APPLY_TO this method ──────────────
        inbound = supabase.table("knowledge_edges") \
            .select("source_id") \
            .eq("target_id", method["id"]) \
            .eq("relationship_type", "APPLIES_TO").execute().data
        if not inbound:
            return f"No BrewingRules found for '{method['name']}' — graph may need seeding."

        rule_ids  = [e["source_id"] for e in inbound]
        rules     = supabase.table("knowledge_nodes") \
            .select("name, properties") \
            .eq("node_type", "BrewingRule") \
            .in_("id", rule_ids).execute().data

        # ── 3. Compute derived shot values ───────────────────────────────────
        dose   = float(shot.get("dose")  or 0)
        yield_g = float(shot.get("yield") or shot.get("yield_g") or 0)
        ratio  = round(yield_g / dose, 3) if dose > 0 else None

        shot_values: dict[str, float | None] = {
            "water_temperature": _safe_float(shot.get("brew_temp")),
            "extraction_time":   _safe_float(shot.get("extraction_time")),
            "brew_ratio":        ratio,
            "yield_ratio":       ratio,   # same computation, different rule names
            "bloom_time":        None,    # not tracked in shots table
            "grind_size":        None,    # stored as setting string, not microns
        }

        # ── 4. Evaluate each rule ────────────────────────────────────────────
        violated:  list[dict] = []
        compliant: list[dict] = []
        context:   list[dict] = []
        unchecked: list[dict] = []

        for rule in rules:
            p        = rule["properties"]
            dictates = p.get("dictates", {})
            param    = dictates.get("parameter", "")
            direction = dictates.get("direction", "")
            val_range = dictates.get("value_range", "")
            unit     = dictates.get("unit", "")
            confidence = float(p.get("confidence", 0.5))
            evidence = p.get("evidence", "")
            pid      = p.get("pid_specificity", {})

            actual = shot_values.get(param)

            # Parameter not tracked in shot data
            if actual is None:
                unchecked.append({
                    "rule":   rule["name"],
                    "reason": f"'{param}' is not recorded in shot data",
                })
                continue

            parsed = _parse_value_range(val_range)

            # Directional guidelines ("increase"/"decrease") → CONTEXT bucket
            if direction in ("increase", "decrease") or parsed is None:
                context.append({
                    "rule":       rule["name"],
                    "param":      param,
                    "actual":     actual,
                    "guidance":   f"{direction} toward {val_range} {unit}".strip(),
                    "confidence": confidence,
                    "evidence":   evidence,
                })
                continue

            # target_range rules → strict VIOLATED / COMPLIANT
            lo, hi = parsed
            if lo <= actual <= hi:
                compliant.append({
                    "rule":       rule["name"],
                    "param":      param,
                    "actual":     actual,
                    "target":     f"{lo}–{hi} {unit}".strip(),
                    "confidence": confidence,
                    "evidence":   evidence,
                })
            else:
                side   = "below" if actual < lo else "above"
                action = _corrective_action_from_rule(p, side)
                violated.append({
                    "rule":        rule["name"],
                    "param":       param,
                    "actual":      actual,
                    "target":      f"{lo}–{hi} {unit}".strip(),
                    "side":        side,
                    "action":      action,
                    "confidence":  confidence,
                    "evidence":    evidence,
                    "requires_pid": pid.get("requires_pid"),
                    "workaround":  pid.get("non_pid_alternative", ""),
                    "description": p.get("description", ""),
                })

        # Sort violations: highest-confidence issues first
        violated.sort(key=lambda x: x["confidence"], reverse=True)

        # ── 5. Format output ─────────────────────────────────────────────────
        header = (
            f"Diagnosis: {method['name']}  |  "
            f"{dose}g → {yield_g}g  |  "
            f"{shot.get('extraction_time')}s  |  "
            f"score {shot.get('overall_score')}/10"
        )
        if ratio:
            header += f"  |  ratio 1:{ratio:.2f}"
        lines = [header, ""]

        if violated:
            lines.append(f"VIOLATED ({len(violated)}):")
            for v in violated:
                lines.append(f"  ✗  {v['rule']}")
                lines.append(f"     {v['param']}: {v['actual']} is {v['side']} target {v['target']}")
                lines.append(f"     Action  : {v['action']}")
                if v.get("requires_pid") and v.get("workaround"):
                    lines.append(f"     No-PID  : {v['workaround']}")
                lines.append(f"     Evidence: {v['evidence']}  (confidence {v['confidence']:.2f})")
                lines.append("")
        else:
            lines.append("No rule violations detected.")
            lines.append("")

        if compliant:
            lines.append(f"COMPLIANT ({len(compliant)}):")
            for c in compliant:
                lines.append(
                    f"  ✓  {c['rule']}: {c['param']} = {c['actual']}  "
                    f"(target {c['target']}, confidence {c['confidence']:.2f})"
                )
            lines.append("")

        if context:
            lines.append(f"CALIBRATION CONTEXT ({len(context)} guideline(s)):")
            for g in context:
                lines.append(f"  ·  {g['rule']}: {g['param']} = {g['actual']} — {g['guidance']}")
            lines.append("")

        if unchecked:
            lines.append(f"UNCHECKED ({len(unchecked)} rule(s) — parameters not in shot data):")
            for u in unchecked:
                lines.append(f"  —  {u['rule']}: {u['reason']}")

        return "\n".join(lines)

    except Exception as e:
        return f"Diagnosis error: {str(e)}"


def _safe_float(value) -> float | None:
    """Convert a value to float, returning None if not possible."""
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


# =============================================================================
# PUBLIC MCP TOOLS — the 4-tool semantic layer surface
# =============================================================================

@mcp.tool()
def seed_knowledge_graph() -> str:
    """
    ADMIN — Seeds the knowledge_nodes and knowledge_edges Supabase tables with
    the static coffee domain knowledge graph defined in knowledge_graph.py.
    Uses upsert — safe to re-run without creating duplicates.
    Requires SUPABASE_KEY to be set to the service role key.
    """
    try:
        from knowledge_graph import NODES, EDGE_DEFINITIONS
        nodes_res = supabase.table("knowledge_nodes").upsert(NODES, on_conflict="node_type,name").execute()
        node_count = len(nodes_res.data)
        all_nodes_res = supabase.table("knowledge_nodes").select("id, node_type, name").execute()
        node_id_map = {(n["node_type"], n["name"]): n["id"] for n in all_nodes_res.data}
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
        edges_res = supabase.table("knowledge_edges").upsert(edges, on_conflict="source_id,target_id,relationship_type").execute()
        edge_count = len(edges_res.data)
        summary = f"Knowledge graph seeded: {node_count} nodes, {edge_count} edges."
        if skipped_edges:
            summary += f"\nSkipped {len(skipped_edges)} edges: {', '.join(skipped_edges)}"
        return summary
    except Exception as e:
        return f"Error seeding knowledge graph: {str(e)}"


@mcp.tool()
def ask(query: str) -> str:
    """
    PRIMARY ENTRY POINT — Use this for every coffee question. It is the only
    tool you need to call for knowledge queries, brewing advice, and general
    exploration of the coffee graph.

    Internally it runs three pipelines and synthesises the results:

    1. USER CONTEXT — Fetches the user's shot history and active bean to
       personalise every response. Their most-used brew method, best-scoring
       method, and overall average score are prepended automatically.

    2. INTENT CLASSIFICATION — Keyword analysis routes to one of four pipelines:
         • "diagnosis" intent  → triggered by defect words ("sour", "bitter",
           "channeling", "astringent", etc.) or negative-sensory signals. Fetches
           the user's most recent shot, runs _diagnose_shot() against the graph,
           and traverses CAUSES/PREVENTS edges for any named Defect nodes.
         • "brewing" intent  → triggered by how/brew/grind/temp/ratio/shot etc.
           Fetches BrewingRules for the named method (or infers method from last
           shot) and appends a full shot diagnosis. PID and no-PID workarounds
           are surfaced from the graph's pid_specificity JSONB blocks.
         • "recommendation" intent → runs VFM analysis across all beans the
           user has logged shots against.
         • "knowledge" intent (default) → base retrieval only.

    3. UNIFIED RETRIEVAL — Runs entity extraction (every graph node name
       checked against the query) plus pgvector semantic search, then enriches
       the top results with their 1-hop graph connections. High-confidence
       semantic hits (similarity ≥ 0.6) get full graph profiles; lower-
       confidence hits appear as supporting context.

    WHEN TO USE A DIFFERENT TOOL INSTEAD:
    - Logging a new shot           → log_shot()
    - Getting personalised picks   → get_recommendations() (more detailed than ask)
    - Re-seeding the graph         → seed_knowledge_graph() (admin only)

    CRITICAL — DO NOT call ask() (or any tool) in these situations:
    • The user asks a simple conversational or factual question you can answer
      from internal knowledge without DB data ("what is a flat white?",
      "who is James Hoffmann?", "what does bloom mean?"). Calling a tool here
      adds latency with no benefit — just answer directly.
    • The user explicitly says "in general", "not from my history", or
      "hypothetically". They are opting out of personalisation — answer from
      your training knowledge without touching the DB.
    • The question is about another person's equipment or workflow entirely
      unrelated to the user's own shots or beans.

    RESPONSE FORMAT — Scientist-to-Barista framework (mandatory for all answers):

    Structure every response in three sections:

    ### [PhysicsModel or root cause] — Why This Happens
    One crisp sentence naming the root cause using its precise scientific term
    (e.g. "diffusion coefficient", "intragranular pore network", "bimodal
    particle distribution"). If a PhysicsModel node was retrieved, name it here.

    ### What To Do
    2–3 bulleted steps. **Bold** the key adjustment on each line.
    End with a one-line physical intuition: describe what is happening inside
    the puck or the cup (e.g. "Imagine water bypassing the dense particle
    core — it tastes every surface, but none of the depth.").

    ### Source
    If a SOURCED_FROM edge is in the retrieval, cite the expert/paper name.
    If not, omit this section entirely — do not fabricate citations.

    Style rules:
    - Never exceed 150 words total.
    - If a technical term appears, pair it immediately with its practical
      implication (e.g. "low diffusion coefficient — flavour compounds are
      locked inside the particle and won't dissolve").
    - Use Markdown headers, bullets, and inline code for settings
      (e.g. `Grind Size: 2 clicks finer`).
    - Never use filler phrases ("it sounds like", "let me know if", "great
      question"). Open directly with the science or the fix.

    Args:
        query: Any natural-language coffee question. Full sentences, keywords,
               flavour descriptions, and abstract concepts all work.
    """
    try:
        parts: list[str] = []

        # 1. Classify intent
        intent = _classify_intent(query)

        # 2. Light style guide — no templates, just the hard constraints.
        #    Bean decides the format; we only enforce plain text and accuracy rules.
        parts.append(
            "── STYLE GUIDE ──\n"
            "Plain text only — the app does not render markdown. "
            "Do not use #, ##, **, *, --, > or any other markdown syntax.\n"
            "Be concise (under 150 words). Write like a knowledgeable friend.\n"
            "CRITICAL: Base your answer EXCLUSIVELY on the retrieved data sections below. "
            "Your pre-trained knowledge is OVERRIDDEN by this data. If the retrieved data "
            "says X causes Y, state that — even if your baseline weights suggest otherwise. "
            "If the retrieved data does not contain enough information to answer, say exactly: "
            "'I don't have specific data on that in my knowledge graph yet.' Do NOT invent, "
            "infer, or fill gaps from pre-trained knowledge.\n"
            "Ground every claim in the retrieved data — use the exact node names "
            "(PhysicsModel, BrewParameter, Defect, etc.) rather than paraphrasing them.\n"
            "If any retrieved node has a 'source:' property, end with: Source: [that value]\n"
            "Never fabricate a citation. If no source is in the data, omit the Source line."
        )

        # 3. User context
        parts.append(_get_user_context())

        # 4. Unified retrieval (vector search + graph enrichment)
        embedding = _embed(query)
        retrieval = _unified_search(query, embedding)
        parts.append(f"── KNOWLEDGE RETRIEVAL ──\n{retrieval}")

        # 4. Intent-specific enrichment
        if intent == "brewing":
            brew_methods = [n for n in _vector_search_raw(embedding, count=10) if n["node_type"] == "BrewMethod"]
            if brew_methods:
                # Named brew method: fetch its rules + diagnose the most recent
                # shot made with that method.  This grounds the answer in the
                # user's actual parameters rather than generic advice.
                rules_block = "\n\n".join(
                    _get_brewing_rules_for_method(m["name"]) for m in brew_methods[:2]
                )
                parts.append(f"── BREWING RULES ──\n{rules_block}")

                recent_shots = (
                    supabase.table("shots")
                    .select("*")
                    .eq("brew_method", brew_methods[0]["name"])
                    .order("created_at", desc=True)
                    .limit(1)
                    .execute()
                    .data
                )
                if recent_shots:
                    diagnosis = _diagnose_shot(recent_shots[0])
                    parts.append(
                        f"── YOUR MOST RECENT {brew_methods[0]['name'].upper()} SHOT ──\n{diagnosis}"
                    )
            else:
                # No brew method named in the query (e.g. "how do I adjust my
                # grind?").  Fall back to the user's most recent shot, infer
                # its method, and run both the rules block and diagnosis against
                # that method.  This keeps the answer personal and concrete even
                # when the user doesn't specify a method.
                fallback = (
                    supabase.table("shots")
                    .select("*")
                    .order("created_at", desc=True)
                    .limit(1)
                    .execute()
                    .data
                )
                if fallback:
                    shot        = fallback[0]
                    method_name = shot.get("brew_method", "")
                    if method_name:
                        rules_block = _get_brewing_rules_for_method(method_name)
                        parts.append(
                            f"── BREWING RULES (inferred from last shot: {method_name}) ──\n{rules_block}"
                        )
                    diagnosis = _diagnose_shot(shot)
                    label = method_name.upper() if method_name else "LAST"
                    parts.append(f"── YOUR MOST RECENT {label} SHOT ──\n{diagnosis}")

        elif intent == "diagnosis":
            # Defect-heavy query ("why was my shot sour?", "I'm getting
            # channeling", "it tasted bitter and harsh").
            #
            # Two-part response:
            #   A. Shot diagnosis  — compare the user's last shot parameters
            #      against every BrewingRule that applies to its method.
            #      Tells the LLM *which rules were violated* and *what to fix*.
            #   B. Defect graph context — traverse CAUSES (what produced this
            #      defect) and PREVENTS (what eliminates it) edges in the graph.
            #      Gives the LLM the causal chain so it can explain *why*, not
            #      just *what*.
            #
            # If the query names a specific brew method, we fetch that method's
            # most recent shot.  Otherwise we fall back to the globally most
            # recent shot and infer its method.

            mentioned_methods = [
                n for n in _vector_search_raw(embedding, count=10)
                if n["node_type"] == "BrewMethod"
            ]
            if mentioned_methods:
                recent_shots = (
                    supabase.table("shots")
                    .select("*")
                    .eq("brew_method", mentioned_methods[0]["name"])
                    .order("created_at", desc=True)
                    .limit(1)
                    .execute()
                    .data
                )
            else:
                recent_shots = (
                    supabase.table("shots")
                    .select("*")
                    .order("created_at", desc=True)
                    .limit(1)
                    .execute()
                    .data
                )

            if recent_shots:
                shot        = recent_shots[0]
                method_name = shot.get("brew_method", "?")
                diagnosis   = _diagnose_shot(shot)
                parts.append(f"── SHOT DIAGNOSIS ({method_name.upper()}) ──\n{diagnosis}")

            # Defect graph traversal — this is what makes the answer
            # neuro-symbolic rather than purely retrieval-based.
            # The LLM should narrate these edges, not re-invent them.
            defect_ctx = _get_defect_graph_context(embedding)
            if defect_ctx:
                parts.append(defect_ctx)

        elif intent == "recommendation":
            parts.append(f"── VALUE FOR MONEY ANALYSIS ──\n{_analyze_best_value_coffees()}")

        # ── Intent-aware format instruction ──────────────────────────────────
        # Plain text only — the app does not render markdown.
        # Each intent gets a format matched to what the question actually is.
        return "\n\n".join(p for p in parts if p.strip())

    except Exception as e:
        return f"Error in ask: {str(e)}"


@mcp.tool()
def log_shot(
    brew_method: str,
    dose: float,
    yield_g: float,
    extraction_time: int,
    overall_score: int,
    brew_temp: float = 93.0,
    grind_setting: str = "",
    has_milk: bool = False,
    bean_id: str = "",
) -> str:
    """
    LOG A SHOT — Record a new coffee shot to the database. Call this whenever
    the user says they just made a coffee, pulled a shot, or wants to track
    a brew.

    After inserting the shot, returns a graph-grounded insight comparing the
    user's parameters against the knowledge graph's BrewingRules for their
    chosen method (e.g. whether extraction time is within the optimal window).

    CRITICAL — DO NOT call this tool in the following situations:
    • The user is asking a theoretical question about brewing parameters ("what
      should my yield be for espresso?"). That is a knowledge question — call
      ask() instead. Only call log_shot() when the user is recording a real
      shot they actually just made.
    • The user has not provided real numbers (dose, yield, time, score). Do not
      guess or invent parameters — ask the user for the missing values first.
    • The user is describing a hypothetical shot ("if I pulled at 1:2.5 ratio,
      what would happen?"). Hypotheticals are not logged — answer from your
      knowledge or call ask() for graph-grounded context.

    Args:
        brew_method:      Brew method used. Common values: "Espresso", "V60",
                          "French Press", "Chemex", "AeroPress", "Cold Brew".
        dose:             Coffee dose in grams (e.g. 18.0).
        yield_g:          Liquid yield in grams (e.g. 36.0).
        extraction_time:  Total brew time in seconds (e.g. 28).
        overall_score:    Your score for this shot, 1–10.
        brew_temp:        Water temperature in °C (default 93.0).
        grind_setting:    Grinder setting used, as a string (e.g. "12", "3.5").
        has_milk:         True if milk or alternative was added (default False).
        bean_id:          UUID of the bean used. Leave empty if unknown.
    """
    try:
        if not 1 <= overall_score <= 10:
            return f"Score must be between 1 and 10. Received: {overall_score}"

        payload: dict = {
            "brew_method":     brew_method,
            "dose":            dose,
            "yield":           yield_g,
            "extraction_time": extraction_time,
            "overall_score":   overall_score,
            "brew_temp":       brew_temp,
            "has_milk":        has_milk,
        }
        if grind_setting:
            payload["grind_setting"] = grind_setting
        if bean_id:
            payload["bean_id"] = bean_id

        resp = supabase.table("shots").insert(payload).execute()
        if not resp.data:
            return "Shot insert returned no data. Check Supabase logs."

        shot = resp.data[0]
        header = f"Shot logged. ID: {shot.get('id')}"

        # Run the graph diagnosis engine against the inserted shot record.
        # Thresholds come entirely from BrewingRule nodes in the knowledge
        # graph — no hardcoded numbers here.
        diagnosis = _diagnose_shot(shot)

        return f"{header}\n\n{diagnosis}"

    except Exception as e:
        return f"Error logging shot: {str(e)}"


@mcp.tool()
def diagnose_shot(shot_id: str, user_id: str = None) -> str:
    """
    Diagnose a specific shot by ID against the BrewingRules in the knowledge
    graph. Skips intent classification, query embedding, and vector search that
    ask() does — much faster when shot_id is already known (e.g. immediately
    after log_shot() returns).

    Returns VIOLATED / COMPLIANT / CONTEXT / UNCHECKED for every rule that
    applies to the shot's brew method, with corrective actions for violations.
    """
    try:
        query = supabase.table("shots").select("*").eq("id", shot_id)
        if user_id:
            query = query.eq("user_id", user_id)
        resp = query.execute()
        if not resp.data:
            return f"No shot found with ID '{shot_id}'."
        return _diagnose_shot(resp.data[0])
    except Exception as e:
        return f"Error: {str(e)}"


@mcp.tool()
def get_recommendations() -> str:
    """
    PERSONALISED RECOMMENDATIONS — Get tailored coffee suggestions grounded
    in both the user's shot history and the knowledge graph.

    Call this when the user asks what they should try next, which bean offers
    the best value, or wants a data-driven suggestion based on their brewing
    history.

    Returns three layers of insight:
    1. USER CONTEXT — current active bean and derived preferences.
    2. VFM ANALYSIS — value-for-money ranking across all beans the user has
       shot against, with average scores, price-per-100g, and best method.
    3. GRAPH PAIRINGS — Origins that the knowledge graph recommends for the
       user's most-used brew method (via PAIRS_WITH edges), so suggestions
       are grounded in structured coffee science rather than generic advice.

    CRITICAL — DO NOT call this tool in the following situations:
    • The user is asking a general theory question ("what beans work well with
      espresso in general?", "what origins are fruity?"). Use your internal
      knowledge or call ask() instead — this tool only knows about beans the
      user has personally logged shots against, not coffee in general.
    • The user is asking about someone else's setup or equipment ("what would
      you recommend for my friend?"). This tool reads the current user's DB
      history only and will return irrelevant personal data.
    • The user explicitly signals they want general advice ("not from my DB",
      "in general", "hypothetically", "ignoring my history"). Respect that
      signal — answer from your internal knowledge without calling any tool.
    • The user has no shot history yet. VFM analysis requires logged shots;
      calling this tool with an empty DB returns meaningless output. Prompt
      the user to log a shot with log_shot() first.
    """
    try:
        parts: list[str] = []

        # 1. User context
        parts.append(_get_user_context())

        # 2. VFM analysis
        parts.append(f"── VALUE FOR MONEY ANALYSIS ──\n{_analyze_best_value_coffees()}")

        # 3. Graph-grounded origin pairings for top method
        shots = supabase.table("shots").select("brew_method").order("created_at", desc=True).limit(30).execute().data
        if shots:
            method_counts: Counter = Counter(s.get("brew_method") for s in shots if s.get("brew_method"))
            top_method = method_counts.most_common(1)[0][0] if method_counts else None

            if top_method:
                method_node = supabase.table("knowledge_nodes").select("id, name").eq("node_type", "BrewMethod").eq("name", top_method).execute().data
                if method_node:
                    method_id = method_node[0]["id"]
                    pairs_edges = supabase.table("knowledge_edges").select("source_id").eq("target_id", method_id).eq("relationship_type", "PAIRS_WITH").execute().data
                    if pairs_edges:
                        origin_ids = [e["source_id"] for e in pairs_edges]
                        origins = supabase.table("knowledge_nodes").select("name, properties").in_("id", origin_ids).eq("node_type", "Origin").execute().data
                        if origins:
                            lines = [f"── ORIGINS THAT PAIR WELL WITH {top_method.upper()} (from knowledge graph) ──"]
                            for o in origins:
                                p = o["properties"]
                                lines.append(f"  • {o['name']}")
                                lines.append(f"    {p.get('cup_profile','')}")
                                lines.append(f"    Common processes: {', '.join(p.get('common_processes', []))}")
                            parts.append("\n".join(lines))

        return "\n\n".join(p for p in parts if p.strip())

    except Exception as e:
        return f"Error getting recommendations: {str(e)}"


@mcp.tool()
def introspect() -> str:
    """
    SCHEMA REGISTRY — Returns a live snapshot of the knowledge graph's ontology.

    Combines static schema definitions from schema.py with live node and edge
    counts from Supabase.  Call this when you need to:

      • Understand what a node type means (e.g. what is a SensoryDescriptor?)
      • Know how many nodes of each type currently exist in the graph
      • Understand which relationship types connect which node types
      • Orient yourself after new books have been ingested (new node types or
        new instances of existing types may have been added)

    This tool is the ontology layer of the semantic stack.  You do not need to
    call it for every query — use it when ask() returns node types or
    relationship types you want to reason about more precisely.

    CRITICAL — DO NOT call this tool in the following situations:
    • The user asks a general coffee question. introspect() returns schema
      metadata (node type counts, relationship definitions) — it contains no
      brewing advice, flavor data, or user history. It will not help answer
      "what is the best grind for V60?" — call ask() for that.
    • Routine queries where you already understand the schema. Calling
      introspect() on every turn is wasteful — only call it when you genuinely
      need to reason about which node types or relationship types exist.
    """
    try:
        from schema import NODE_TYPES, RELATIONSHIP_TYPES

        # ── 1. Live node counts from Supabase ──────────────────────────────────
        # Fetch only the node_type column — no properties, no embeddings.
        # One Supabase call; Counter does the grouping in Python.
        node_rows   = supabase.table("knowledge_nodes").select("node_type").execute().data
        node_counts = Counter(row["node_type"] for row in node_rows)
        total_nodes = sum(node_counts.values())

        # ── 2. Live edge counts from Supabase ──────────────────────────────────
        edge_rows   = supabase.table("knowledge_edges").select("relationship_type").execute().data
        edge_counts = Counter(row["relationship_type"] for row in edge_rows)
        total_edges = sum(edge_counts.values())

        # How many schema-defined types currently have at least one node/edge
        populated_node_types = sum(1 for t in NODE_TYPES if node_counts.get(t, 0) > 0)
        used_rel_types       = sum(1 for r in RELATIONSHIP_TYPES if edge_counts.get(r, 0) > 0)

        lines: list[str] = [
            "── KNOWLEDGE GRAPH SCHEMA REGISTRY ──",
            (
                f"  {total_nodes} nodes  |  {total_edges} edges  "
                f"|  {populated_node_types}/{len(NODE_TYPES)} node types populated  "
                f"|  {used_rel_types}/{len(RELATIONSHIP_TYPES)} relationship types in use"
            ),
        ]

        # ── 3. Node types ───────────────────────────────────────────────────────
        # Sorted: populated types first (by count desc), then unpopulated (schema-
        # defined but not yet ingested — important to surface after book ingestion).
        lines.append("\nNODE TYPES:")
        sorted_node_types = sorted(
            NODE_TYPES.items(),
            key=lambda kv: node_counts.get(kv[0], 0),
            reverse=True,
        )

        for type_name, type_def in sorted_node_types:
            count = node_counts.get(type_name, 0)

            # Truncate the description to the first sentence — the full text is
            # in schema.py for humans; Bean needs the one-liner to reason.
            raw_desc    = type_def.get("description", "")
            first_sent  = raw_desc.split(".")[0].strip() + "."

            key_props   = type_def.get("key_properties", [])
            examples    = type_def.get("example_names", [])[:4]

            # Flag types with zero nodes — they're schema-defined but not yet
            # populated.  This matters after book ingestion adds new types.
            status = f"{count} nodes" if count > 0 else "0 nodes — schema defined, not yet ingested"

            lines.append(f"\n  [{type_name}]  {status}")
            lines.append(f"  {first_sent}")
            if key_props:
                lines.append(f"  Properties : {', '.join(key_props[:6])}")
            if examples:
                lines.append(f"  Examples   : {', '.join(examples)}")

        # ── 4. Relationship types ───────────────────────────────────────────────
        # Sorted: most-used relationships first, then unused ones.
        lines.append("\nRELATIONSHIP TYPES:")
        sorted_rels = sorted(
            RELATIONSHIP_TYPES.items(),
            key=lambda kv: edge_counts.get(kv[0], 0),
            reverse=True,
        )

        for rel_name, rel_def in sorted_rels:
            count   = edge_counts.get(rel_name, 0)
            sources = ", ".join(rel_def.get("valid_sources", []))
            targets = ", ".join(rel_def.get("valid_targets", []))
            example = rel_def.get("example", "")
            status  = f"{count} edges" if count > 0 else "0 edges — defined, not yet used"

            lines.append(f"\n  {rel_name}  ({status})")
            lines.append(f"  {rel_def['description']}")
            lines.append(f"  {sources}  →  {targets}")
            if example:
                lines.append(f"  e.g. {example}")

        return "\n".join(lines)

    except Exception as e:
        return f"Error in introspect: {str(e)}"


# =============================================================================
# RESEARCH AGENT — web search → scrape → LLM extraction → graph injection
# Admin-only. Reuses the schema-aware extraction pipeline from extract_book.py
# so every node/edge conforms to schema.py and all writes are duplicate-safe
# upserts (on_conflict node_type,name and source_id,target_id,relationship_type).
# =============================================================================

from extract_book import (
    build_schema_guide,
    chunk_text,
    extract_from_chunk,
    normalize_node_names,
    normalize_edges,
    deduplicate_nodes,
    deduplicate_edges,
    validate_extracted,
    generate_embeddings,
    ingest_document_rpc,
)


def _request_headers() -> dict:
    """
    Return the HTTP headers attached to the current MCP tool-call request.

    Under the SSE transport the POST that carries a tool invocation propagates
    its Starlette Request into the MCP request context (mcp/server/sse.py →
    lowlevel server), so the frontend's per-session auth headers are readable
    here. Returns {} when no request context is available — callers MUST treat
    an empty result as unauthorized (fail closed).
    """
    try:
        req = mcp.get_context().request_context.request
        if req is None:
            return {}
        # Starlette Headers are case-insensitive; flatten to a lowercase dict.
        return {k.lower(): v for k, v in req.headers.items()}
    except Exception:
        return {}


def _authorize_admin() -> str | None:
    """
    Authorize the caller as the system administrator.

    Trust comes from headers the frontend attaches to its MCP transport request
    AFTER authenticating the user with Supabase — never from an LLM argument.
    Returns None when authorized, or the safe denial string otherwise. Fails
    closed on any missing server config, missing header, secret mismatch, or
    email mismatch. Constant-time comparisons avoid leaking the secret/email.
    """
    if not ADMIN_EMAIL or not RESEARCH_INGEST_SECRET:
        return _ADMIN_DENIED  # server not provisioned for admin ops → deny all

    headers          = _request_headers()
    presented_secret = headers.get("x-research-secret", "")
    presented_email  = headers.get("x-user-email", "").strip().lower()

    secret_ok = hmac.compare_digest(presented_secret, RESEARCH_INGEST_SECRET)
    email_ok  = bool(presented_email) and hmac.compare_digest(presented_email, ADMIN_EMAIL)

    return None if (secret_ok and email_ok) else _ADMIN_DENIED


# Hosts that never yield scrapeable article prose — skip them as candidates.
_NON_ARTICLE_HOSTS = (
    "youtube.com", "youtu.be", "twitter.com", "x.com", "instagram.com",
    "tiktok.com", "facebook.com", "pinterest.com", "reddit.com",
)


def _search_candidate_urls(query: str, max_results: int = 8) -> list[str]:
    """Return candidate article URLs for `query`, best first, sans non-article hosts."""
    try:
        try:
            from ddgs import DDGS                  # maintained successor package
        except ImportError:                        # older deprecated name
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
        print(f"  [research] search error: {e}")
        return []


def _scrape_article(url: str) -> str | None:
    """Download `url` and extract clean main-body text via trafilatura."""
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
        print(f"  [research] scrape error: {e}")
        return None


def _run_research_ingest(query: str, url: str, source_name: str) -> str:
    """
    The heavy pipeline: search → scrape → LLM extraction → graph injection.

    Runs in a background thread (see research_and_ingest_topic) so the MCP tool
    call returns immediately and the chat route never blocks. Returns/​logs a
    human-readable summary; the result is not delivered back to the chat turn
    that started it — progress is observable in the server logs.
    """
    # 1. Resolve candidate URLs (direct url wins; otherwise search the web)
    if url:
        candidates = [url]
    else:
        candidates = _search_candidate_urls(query)
        if not candidates:
            return f"No web results found for '{query}'."

    # 2. Scrape the first candidate that yields enough readable prose
    MIN_WORDS = 150
    text, chosen, tried = None, None, []
    for candidate in candidates:
        scraped = _scrape_article(candidate)
        words = len((scraped or "").split())
        tried.append(f"{candidate} ({words}w)")
        if scraped and words >= MIN_WORDS:
            text, chosen = scraped, candidate
            break
    if not text:
        return ("Could not extract enough readable text from any candidate "
                "(paywalled/JS-rendered/blocked). Tried:\n  - " + "\n  - ".join(tried))

    # 3. Provenance / Expert node name
    domain = urlparse(chosen).netloc.replace("www.", "")
    expert = (source_name or "").strip() or domain or "Web Research"

    # 4. Schema-aware LLM extraction (reuses the book-ingestion pipeline)
    schema_guide = build_schema_guide()
    chunks = chunk_text(text, chunk_size=1200)[:8]   # bound LLM cost per call
    expert_stub = {
        "node_type":  "Expert",
        "name":       expert,
        "properties": {"full_name": expert, "organisation": "Web source", "source_url": chosen},
    }
    all_nodes: list[dict] = [expert_stub]
    all_edges: list[dict] = []
    for i, chunk in enumerate(chunks, 1):
        result = extract_from_chunk(openai_client, chunk, expert, schema_guide, i, len(chunks))
        all_nodes.extend(result.get("nodes", []))
        all_edges.extend(result.get("edges", []))

    # 5. Normalize edge direction → dedup → validate against schema.py
    all_nodes, all_edges = normalize_node_names(all_nodes, all_edges)
    all_edges = normalize_edges(all_edges)
    all_nodes = deduplicate_nodes(all_nodes)
    all_edges = deduplicate_edges(all_edges)
    valid_nodes, valid_edges, errors = validate_extracted(all_nodes, all_edges)
    if errors:
        return "Extraction produced schema errors; nothing was written:\n  - " + "\n  - ".join(errors)
    if len(valid_nodes) <= 1:   # only the Expert stub survived
        return f"No schema-conformant knowledge could be extracted from {chosen}."

    # 6. Generate embeddings then write everything in one atomic transaction
    for node in valid_nodes:
        node.setdefault("properties", {})["_source"] = chosen
    valid_nodes = generate_embeddings(openai_client, valid_nodes)
    nodes_ok, edge_ok, edge_skip = ingest_document_rpc(supabase, valid_nodes, valid_edges)

    breakdown = Counter(n["node_type"] for n in valid_nodes)
    lines = [
        f"✓ Ingested research from: {chosen}",
        f"  Provenance (Expert): {expert}",
        f"  Nodes upserted: {nodes_ok}  |  Edges written: {edge_ok} (skipped {edge_skip})",
        "  Node breakdown: " + ", ".join(f"{t}:{c}" for t, c in sorted(breakdown.items(), key=lambda x: -x[1])),
    ]
    return "\n".join(lines)


def _research_ingest_worker(query: str, url: str, source_name: str) -> None:
    """Thread entry point: run the pipeline and log the outcome (never raises)."""
    label = url or query
    print(f"[research] ▶ background ingest started for: {label}")
    try:
        summary = _run_research_ingest(query, url, source_name)
        print(f"[research] ✓ background ingest finished for {label}:\n{summary}")
    except Exception as e:
        print(f"[research] ✗ background ingest FAILED for {label}: {e!r}")


@mcp.tool()
def research_and_ingest_topic(query: str = "", url: str = "", source_name: str = "") -> str:
    """
    ADMIN-ONLY. Kick off web research on a coffee-science topic and add what it
    learns to the knowledge graph. **Returns immediately** — do NOT wait for a
    completion message.

    Given a search `query` (e.g. "coffee bed channeling causes") or a direct
    article `url`, this finds and scrapes the article, extracts schema-conformant
    nodes (BrewParameter, PhysicsModel, Defect, BrewingRule, …) + edges, and
    upserts them into Supabase with embeddings, with SOURCED_FROM provenance to
    an Expert node named after the source domain (override with `source_name`).
    Upserts are idempotent, so re-running is safe.

    Because scraping + embedding + DB writes take 30–90s, the actual work runs in
    a background thread on the server and this tool returns a one-line
    acknowledgement in milliseconds. As soon as you receive that acknowledgement,
    tell the user the ingestion has started in the background and continue the
    conversation — there is no second result to wait for (outcome is logged
    server-side). This is privileged and restricted to the system administrator.
    """
    # ── Admin gate — abort BEFORE doing anything else ─────────────────────────
    denied = _authorize_admin()
    if denied:
        return denied

    query = (query or "").strip()
    url   = (url or "").strip()
    if not query and not url:
        return "Error: provide either a `query` to search or a direct `url` to ingest."

    # Hand the heavy pipeline to the executor and return at once. The pool
    # keeps running on the (always-on) Railway container; the chat route never
    # blocks on scraping/embedding/DB writes.
    _ingest_executor.submit(_research_ingest_worker, query, url, source_name)

    topic = url or query
    return (f"✓ Started research & ingestion for: {topic}\n"
            "Scraping, extraction and graph upserts are now running in the background "
            "(~30–90s). No need to wait — let the user know the knowledge graph is "
            "updating and carry on; the outcome is logged server-side.")


# =============================================================================
# ASGI app — uvicorn server:app --host 0.0.0.0 --port $PORT
# =============================================================================

if __name__ == "__main__":
    mcp.run()

app = FastAPI(title="Coffee Barista MCP Server")


@app.get("/health")
def health():
    return {"status": "ok", "server": "Coffee Barista MCP"}


app.mount("/", mcp.sse_app())
