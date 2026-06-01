# DIALED — Coffee MCP Server

**DIALED** is a Next.js espresso journal with a Neuro-Symbolic AI assistant named **Bean**, backed by a Python MCP server on Railway and a Supabase pgvector database.

---

## Architecture: Semantic Layer

The server exposes exactly **5 public MCP tools** to the LLM. All internal graph/vector routing is handled server-side.

```
LLM (Bean)
  ├── ask(query)              ← primary entry point for all knowledge queries
  ├── log_shot(...)           ← record a brew; returns graph-grounded diagnosis
  ├── get_recommendations()   ← VFM analysis + graph-paired origin suggestions
  ├── introspect()            ← live schema registry: node types, counts, relationships
  └── seed_knowledge_graph()  ← admin: upsert NODES + EDGE_DEFINITIONS to Supabase
```

The LLM never calls graph or vector functions directly. `ask()` internally runs three pipelines:
1. **User Context** — fetches shot history and active bean from `shots` / `beans` tables
2. **Intent Classification** — keyword routing: `brewing` | `recommendation` | `knowledge`
3. **Unified Retrieval** — entity extraction + pgvector semantic search + 1-hop graph enrichment

---

## Database (Supabase pgvector)

| Table | Purpose |
|---|---|
| `knowledge_nodes` | Graph nodes — `node_type`, `name`, `properties` (JSONB), `embedding` (vector 1536) |
| `knowledge_edges` | Graph edges — `source_id`, `target_id`, `relationship_type`, `properties` (JSONB) |
| `shots` | User shot journal — dose, yield, extraction_time, overall_score, brew_method, etc. |
| `beans` | Bean catalog — roaster, origin, price_paid, weight_grams, is_active |

RPC function `match_knowledge_nodes` powers pgvector similarity search.

---

## Schema (`schema.py`) — Single Source of Truth

**Always edit `schema.py` first** when adding new node types or relationship types. All other files (`knowledge_graph.py`, `extract_book.py`, `server.py`) import from it.

### Node Types (16 total)

| Type | Description |
|---|---|
| `Origin` | Country-level coffee producing nation |
| `Region` | Sub-national growing area with distinct terroir; always has `SUB_REGION_OF` edge |
| `Cultivar` | Specific genetic variety (Arabica/Robusta); more specific than Origin |
| `ProcessMethod` | Post-harvest processing (Washed, Natural, Honey, Anaerobic) |
| `RoastLevel` | Roast development stage (Light, Medium, Dark) |
| `FlavorNote` | SCA Taster's Flavor Wheel tasting note |
| `SensoryDescriptor` | Chemical compound underlying a FlavorNote; bridged by `MANIFESTS_AS` |
| `BrewMethod` | Top-level brewing method (Espresso, V60, French Press, etc.) |
| `BrewingRule` | Parameterised guideline with full JSONB contract (see below) |
| `BrewingTechnique` | Specific technique applied within a method (WDT, Rao Spin, etc.) |
| `BrewParameter` | Measurable variable (Water Temperature, Brew Ratio, etc.) |
| `EquipmentType` | Equipment category (PID vs Non-PID machine, burr grinder types) |
| `GrindProfile` | Particle-size distribution (Unimodal / Bimodal) |
| `Defect` | Negative quality outcome traceable to a cause |
| `Expert` | Knowledge authority for provenance tracking via `SOURCED_FROM` edges |
| `PhysicsModel` | Named mathematical model describing extraction, flow, or grinding mechanics |

### Relationship Types (20 total)

`TYPICAL_FLAVOR`, `PRODUCES_FLAVOR`, `EMPHASIZES`, `ENHANCES`, `SUPPRESSES`, `PRODUCES`, `DICTATES`, `APPLIES_TO`, `SUGGESTS_TEMP`, `PAIRS_WITH`, `SUB_REGION_OF`, `GROWN_IN`, `CAUSES`, `PREVENTS`, `REFINES`, `SOURCED_FROM`, `CONFLICTS_WITH`, `MANIFESTS_AS`, `TRANSFORMS_TO`, `GOVERNED_BY`

### BrewingRule JSONB Contract

Every `BrewingRule` node's `properties` must contain:
```json
{
  "description": "...",
  "dictates":        { "parameter": "", "direction": "", "value_range": "", "unit": "" },
  "pid_specificity": { "requires_pid": true/false/null, "reason": "", "non_pid_alternative": "" },
  "confidence":      0.7–1.0,
  "evidence":        "citation string"
}
```
`non_pid_alternative` must be an **actionable workaround**, never a restriction.

---

## Key Files

| File | Role |
|---|---|
| `schema.py` | Node types, relationship types, `BREWING_RULE_SCHEMA`, `validate_graph()` |
| `knowledge_graph.py` | `NODES` list and `EDGE_DEFINITIONS` list — the static seed data |
| `server.py` | FastAPI + FastMCP server; all 4 public tools + private helpers |
| `ingest.py` | Standalone script — generates OpenAI embeddings and upserts all nodes + edges |
| `extract_book.py` | LLM-guided extraction of nodes/edges from coffee books |

---

## Critical Rules

- **Edit `schema.py` first** when adding new node types or relationship types.
- **Run `python schema.py`** after any change to validate the graph.
- **`non_pid_alternative` must always be an actionable workaround** — never say "you need a PID machine".
- **Never silently overwrite conflicting rules** — add both rules and a `CONFLICTS_WITH` edge.
- **Every `BrewingTechnique`/`BrewingRule` from a book needs a `SOURCED_FROM` edge** to its Expert node.
- **Every `Region` needs a `SUB_REGION_OF` edge** to its parent `Origin`.
- **Embeddings are generated by `ingest.py`** — re-run it after adding nodes to `knowledge_graph.py`.
- The diagnosis engine (`_diagnose_shot`) reads thresholds from `BrewingRule` nodes — adding rules via book ingestion enriches diagnoses automatically with zero code changes.
