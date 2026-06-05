# DIALED — Coffee MCP Server

A Python MCP server powering **Bean**, the neuro-symbolic AI assistant inside the DIALED espresso journal. Bean reasons over a live knowledge graph of coffee science, brewing rules, extraction physics, and defect chains to give home baristas expert-level, evidence-backed advice.

Deployed on Railway. Connected to a Supabase pgvector database.

---

## Architecture

The server exposes 5 public MCP tools. All graph traversal and vector retrieval happens server-side — the LLM never queries the DB directly.

```
LLM (Bean)
  ├── ask(query)              ← primary entry point for all knowledge queries
  ├── log_shot(...)           ← record a brew; returns graph-grounded diagnosis
  ├── get_recommendations()   ← VFM analysis + graph-paired origin suggestions
  ├── introspect()            ← live schema registry: node types, counts, relationships
  └── seed_knowledge_graph()  ← admin: upsert NODES + EDGE_DEFINITIONS to Supabase
```

`ask()` runs three pipelines internally:
1. **User Context** — shot history and active bean from `shots` / `beans` tables
2. **Intent Classification** — keyword routing: `brewing` | `diagnosis` | `recommendation` | `knowledge`
3. **Unified Retrieval** — entity extraction + pgvector semantic search + 1-hop graph enrichment

---

## Knowledge Graph

**292 nodes · 374 edges** — sourced from peer-reviewed papers and expert publications.

### Node types (16)

| Type | Count | Description |
|---|---|---|
| `BrewingRule` | 85 | Parameterised guideline with full JSONB contract |
| `PhysicsModel` | 38 | Named mathematical model (Double Porosity, Darcy Flow, etc.) |
| `BrewParameter` | 35 | Measurable extraction variable |
| `FlavorNote` | 22 | SCA Flavor Wheel tasting note |
| `SensoryDescriptor` | 20 | Chemical compound underlying a flavor note |
| `Defect` | 15 | Negative quality outcome traceable to a cause |
| `BrewingTechnique` | 14 | Specific preparation technique (WDT, Rao Spin, etc.) |
| `Expert` | 11 | Knowledge authority for provenance tracking |
| `Origin` | 11 | Country-level coffee producing nation |
| `Cultivar` | 8 | Specific genetic variety |
| `BrewMethod` | 7 | Top-level brewing method |
| `Region` | 7 | Sub-national growing area |
| `GrindProfile` | 6 | Particle-size distribution |
| `EquipmentType` | 5 | Equipment category |
| `ProcessMethod` | 4 | Post-harvest processing method |
| `RoastLevel` | 4 | Roast development stage |

### Relationship types (20)

`TYPICAL_FLAVOR` · `PRODUCES_FLAVOR` · `EMPHASIZES` · `ENHANCES` · `SUPPRESSES` · `PRODUCES` · `DICTATES` · `APPLIES_TO` · `SUGGESTS_TEMP` · `PAIRS_WITH` · `SUB_REGION_OF` · `GROWN_IN` · `CAUSES` · `PREVENTS` · `REFINES` · `SOURCED_FROM` · `CONFLICTS_WITH` · `MANIFESTS_AS` · `TRANSFORMS_TO` · `GOVERNED_BY`

### Ingested sources

| Expert | Source |
|---|---|
| Scott Rao | Espresso Extraction: Measurement and Mastery |
| Michael I. Cameron, et al. | Systematically Improving Espresso (2020) |
| Kevin M. Moroney, et al. | Espresso Extraction Model |
| Uman et al. | Particle Distribution and Grinding |
| Christopher H. Hendon, et al. | The Role of Dissolved Cations in Coffee Extraction |
| Jonathan Gagné | More Even Espresso Extractions; The Effects of Varieties, Origin and Processing |
| Socratic Coffee | Exploring the Impact of Particles on Espresso Extraction |
| SCA | Protocols & Best Practices; Coffee Brewing Handbook |

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

## Key Files

| File | Role |
|---|---|
| `schema.py` | Node types, relationship types, `BREWING_RULE_SCHEMA`, `validate_graph()` |
| `knowledge_graph.py` | Static seed data — `NODES` and `EDGE_DEFINITIONS` |
| `server.py` | FastAPI + FastMCP server; all 5 public tools + private helpers |
| `ingest.py` | Generates OpenAI embeddings and upserts all seed nodes + edges |
| `extract_book.py` | LLM-guided extraction of nodes/edges from coffee books and articles |
| `sources/` | PDF library — all ingested source documents |

---

## Adding New Knowledge

Drop a PDF into `sources/` and run:

```bash
python extract_book.py --file "sources/your-article.pdf" --expert "Author Name" --chunk-size 1500
```

Use `--dry-run` to validate extraction without writing to the DB.

---

## Local Development

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add SUPABASE_URL, SUPABASE_KEY, OPENAI_API_KEY
uvicorn server:app --host 0.0.0.0 --port 8000 --reload
```

Validate the graph schema at any time:

```bash
python schema.py
```
