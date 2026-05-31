import os
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

mcp = FastMCP("Coffee Barista MCP", host="0.0.0.0")


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


def _extract_mentioned_nodes(query: str) -> list[dict]:
    all_nodes = supabase.table("knowledge_nodes").select("id, node_type, name, properties").execute().data
    q = query.lower()
    return [n for n in all_nodes if n["name"].lower() in q]


def _enrich_node(node: dict, similarity: float | None = None) -> str:
    sim_tag = f"  (similarity: {similarity:.4f})" if similarity is not None else ""
    lines = [f"  [{node.get('node_type','?')}] {node.get('name','?')}{sim_tag}"]
    props = node.get("properties") or {}
    for k, v in list(props.items())[:4]:
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

def _unified_search(query: str) -> str:
    """Entity extraction + vector search + graph enrichment. Returns formatted string."""
    sections: list[str] = []
    seen_ids: set[str] = set()

    mentioned   = _extract_mentioned_nodes(query)
    embedding   = _embed(query)
    vector_hits = _vector_search_raw(embedding, threshold=0.2, count=5)
    high_conf   = [r for r in vector_hits if (r.get("similarity") or 0) >= 0.6]
    low_conf    = [r for r in vector_hits if 0.2 <= (r.get("similarity") or 0) < 0.6]

    sections.append(
        f"  {len(mentioned)} entity mention(s)  |  "
        f"{len(vector_hits)} vector hit(s)  |  "
        f"{len(high_conf)} high-confidence (≥ 0.6)"
    )

    enrich_budget = 3

    if mentioned:
        sections.append("── IDENTIFIED ENTITIES ──")
        for node in mentioned[:enrich_budget]:
            if node["id"] not in seen_ids:
                seen_ids.add(node["id"])
                sections.append(_enrich_node(node))
                sections.append("")
                enrich_budget -= 1

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


def _classify_intent(query: str) -> str:
    """
    Keyword-based intent classification.
    Returns one of: 'recommendation' | 'brewing' | 'knowledge'
    """
    q = query.lower()
    if any(w in q for w in [
        "recommend", "suggest", "best", "which bean", "what bean",
        "worth", "value", "vfm", "try next", "should i buy", "what should i try",
    ]):
        return "recommendation"
    if any(w in q for w in [
        "how", "brew", "make", "grind", "temperature", "temp",
        "ratio", "dose", "pour", "steep", "extract", "pull", "shot",
        "recipe", "technique", "prepare",
    ]):
        return "brewing"
    return "knowledge"


# =============================================================================
# PUBLIC MCP TOOLS — the 4-tool semantic layer surface
# =============================================================================

@mcp.tool()
def seed_knowledge_graph() -> str:
    """
    ADMIN — Seeds the knowledge_nodes and knowledge_edges Supabase tables with
    the full static coffee domain knowledge graph (60 nodes, 89 edges).
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

    2. INTENT CLASSIFICATION — Keyword analysis determines which enrichment
       layer to activate on top of the base retrieval:
         • "brewing" intent  → also fetches BrewingRules (grind, temp, ratio,
           PID requirements, no-PID workarounds) for any brew method mentioned.
         • "recommendation" intent → also runs the VFM analysis across all
           beans the user has logged shots against.
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

    Args:
        query: Any natural-language coffee question. Full sentences, keywords,
               flavour descriptions, and abstract concepts all work.
    """
    try:
        parts: list[str] = []

        # 1. User context — always first
        parts.append(_get_user_context())

        # 2. Classify intent
        intent = _classify_intent(query)

        # 3. Unified retrieval (entity + vector + graph enrichment)
        retrieval = _unified_search(query)
        parts.append(f"── KNOWLEDGE RETRIEVAL ──\n{retrieval}")

        # 4. Intent-specific enrichment
        if intent == "brewing":
            brew_methods = [n for n in _extract_mentioned_nodes(query) if n["node_type"] == "BrewMethod"]
            if brew_methods:
                rules_block = "\n\n".join(_get_brewing_rules_for_method(m["name"]) for m in brew_methods[:2])
                parts.append(f"── BREWING RULES ──\n{rules_block}")

        elif intent == "recommendation":
            parts.append(f"── VALUE FOR MONEY ANALYSIS ──\n{_analyze_best_value_coffees()}")

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
        lines = [f"Shot logged. ID: {shot.get('id')}"]
        lines.append(f"  {brew_method} | {dose}g → {yield_g}g | {extraction_time}s | {overall_score}/10")

        # Graph-grounded feedback
        brew_ratio = round(yield_g / dose, 2) if dose > 0 else 0
        if brew_method == "Espresso":
            if extraction_time < 25:
                lines.append("Graph insight: Shot ran fast (<25s). Grind finer or increase dose to slow extraction.")
            elif extraction_time > 35:
                lines.append("Graph insight: Shot ran slow (>35s). Grind coarser or reduce dose.")
            else:
                lines.append("Graph insight: Extraction time within optimal 25-35s window.")
            if brew_ratio < 1.8:
                lines.append(f"Graph insight: Ratio {brew_ratio:.2f} is below the 1:2 target — consider pulling longer.")
            elif brew_ratio > 2.5:
                lines.append(f"Graph insight: Ratio {brew_ratio:.2f} is above 1:2.5 — shot may be dilute.")
        elif brew_method in ("V60", "Chemex"):
            if not (15 <= brew_ratio <= 17):
                lines.append(f"Graph insight: Ratio {brew_ratio:.2f} is outside the Golden Ratio window of 1:15-1:17.")
            else:
                lines.append(f"Graph insight: Ratio {brew_ratio:.2f} is within the Golden Ratio range.")

        return "\n".join(lines)

    except Exception as e:
        return f"Error logging shot: {str(e)}"


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
