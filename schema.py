"""
schema.py — Single source of truth for the Coffee Knowledge Graph schema.

Every valid node type, relationship type, and structural constraint lives here.
All other files import from this module rather than defining their own lists,
so the schema never diverges across ingestion, validation, and retrieval.

Imported by:
  knowledge_graph.py  — validates static graph data at seed time
  extract_book.py     — guides the LLM when extracting nodes/edges from books
  server.py           — will power the introspect() tool (step 4 of semantic layer)

Run directly to validate the full knowledge graph:
  python schema.py
"""

# =============================================================================
# NODE TYPES
# Each entry describes the type, its expected properties, and examples.
# The `key_properties` list is guidance for ingestion — not enforced at DB level.
# The `example_names` list is fed to the LLM during book extraction so it can
# recognise when a concept it's reading about already exists in the graph.
# =============================================================================

NODE_TYPES: dict[str, dict] = {

    # ── Original 9 ────────────────────────────────────────────────────────────

    "Origin": {
        "description": (
            "A country-level coffee producing nation. Use this for country-scale "
            "claims (e.g. 'Ethiopian coffees are floral'). For finer geographic "
            "specificity, use Region."
        ),
        "key_properties": ["continent", "altitude_range_m", "common_processes", "cup_profile", "coffee_species"],
        "example_names": ["Ethiopia", "Colombia", "Brazil", "Kenya", "Guatemala", "Costa Rica", "Indonesia", "Yemen"],
    },

    "ProcessMethod": {
        "description": (
            "A post-harvest processing method applied to coffee cherries before "
            "drying. Determines how much fermentation the bean undergoes and "
            "directly shapes body, sweetness, and fruit character."
        ),
        "key_properties": ["also_known_as", "description", "flavor_impact", "acidity_impact", "body_impact", "water_usage"],
        "example_names": ["Washed", "Natural", "Honey", "Anaerobic", "Wet-Hulled"],
    },

    "RoastLevel": {
        "description": (
            "A roast development stage defined by bean internal temperature and "
            "visual/auditory cues. Determines the balance between origin character "
            "and roast character in the cup."
        ),
        "key_properties": ["internal_temp_c", "first_crack", "oil_on_surface", "acidity", "body", "suggested_water_temp_c"],
        "example_names": ["Light", "Medium-Light", "Medium", "Medium-Dark", "Dark"],
    },

    "FlavorNote": {
        "description": (
            "A consumer-facing tasting note drawn from the SCA Coffee Taster's "
            "Flavor Wheel. Represents perceived flavour, not chemistry — use "
            "SensoryDescriptor for chemical compounds."
        ),
        "key_properties": ["sca_category", "taste_profile"],
        "example_names": [
            "Blueberry", "Raspberry", "Blackcurrant", "Cherry", "Peach",
            "Lemon", "Orange", "Jasmine", "Rose", "Brown Sugar",
            "Caramel", "Honey", "Dark Chocolate", "Milk Chocolate",
            "Hazelnut", "Almond", "Cinnamon", "Tobacco", "Earthy",
        ],
    },

    "BrewMethod": {
        "description": (
            "A top-level brewing method defined by its extraction mechanism "
            "(pressure, immersion, percolation, or cold). Each method has specific "
            "BrewingRules that APPLY_TO it and BrewingTechniques that REFINE it."
        ),
        "key_properties": ["filter_type", "brew_ratio", "water_temp_c", "extraction_time_s"],
        "example_names": ["Espresso", "V60", "French Press", "Chemex", "AeroPress", "Cold Brew", "Moka Pot"],
    },

    "BrewingRule": {
        "description": (
            "A parameterised brewing guideline derived from SCA standards, expert "
            "publications, or empirical research. Every BrewingRule MUST carry the "
            "full JSONB structure: description, dictates, pid_specificity, "
            "confidence, and evidence. See BREWING_RULE_SCHEMA below."
        ),
        "key_properties": ["description", "dictates", "pid_specificity", "confidence", "evidence"],
        "example_names": [
            "Golden Ratio", "Espresso Extraction Window", "High Temp for Light Roast",
            "Lower Temp for Dark Roast", "Bloom Pre-Infusion",
            "Fine Grind for Pressure", "Coarse Grind for Immersion",
            "Espresso Dose-to-Yield Ratio",
        ],
    },

    "BrewParameter": {
        "description": (
            "A measurable variable in the brewing process. BrewingRules DICTATE "
            "target values for BrewParameters. Connecting a rule to a parameter "
            "makes the parameter machine-readable for the diagnosis engine. "
            "Includes water chemistry parameters such as mineral content and TDS."
        ),
        "key_properties": ["unit", "typical_range", "primary_effect"],
        "example_names": [
            "Water Temperature", "Extraction Time", "Brew Ratio", "Grind Size",
            "Bloom Time", "Yield Ratio",
            "Water Magnesium Content", "Water Calcium Content",
            "Water TDS", "Water Sodium Content", "Water Hardness",
        ],
    },

    "EquipmentType": {
        "description": (
            "A category of brewing or grinding equipment. Grinder types shape "
            "the GrindProfile; machine types determine temperature stability. "
            "Used to route brewing advice to the right pid_specificity branch."
        ),
        "key_properties": ["category", "price_range_usd", "grind_distribution", "temperature_control"],
        "example_names": ["PID Espresso Machine", "Non-PID Espresso Machine", "Flat Burr Grinder", "Conical Burr Grinder"],
    },

    "GrindProfile": {
        "description": (
            "The particle-size distribution produced by a grinder. Bimodal "
            "(two peaks) is typical of conical burrs; unimodal (single peak) "
            "is typical of flat burrs. Affects extraction evenness and cup clarity."
        ),
        "key_properties": ["distribution_shape", "primary_benefit", "best_for"],
        "example_names": ["Unimodal", "Bimodal"],
    },

    # ── New 6 ─────────────────────────────────────────────────────────────────

    "Cultivar": {
        "description": (
            "A specific genetic variety of coffee (Arabica or Robusta). More "
            "specific than Origin — the same cultivar can be grown in multiple "
            "origins and produce distinct cup profiles in each terroir. "
            "When a book references a specific variety by name, create a Cultivar "
            "node rather than adding it to an Origin's properties."
        ),
        "key_properties": ["species", "genetic_lineage", "cup_profile", "typical_origins", "yield", "altitude_preference_m"],
        "example_names": ["Gesha", "Bourbon", "Typica", "SL28", "Catuai", "Caturra", "Mundo Novo", "Pacamara", "Wush Wush"],
    },

    "Region": {
        "description": (
            "A sub-national growing area with its own distinct terroir, altitude "
            "band, and cup identity. Always attach a SUB_REGION_OF edge to its "
            "parent Origin. Yirgacheffe and Sidama are both in Ethiopia but taste "
            "very different — that specificity belongs here, not in Origin.properties."
        ),
        "key_properties": ["parent_origin", "altitude_range_m", "cup_profile", "primary_cultivars", "dominant_process"],
        "example_names": ["Yirgacheffe", "Sidama", "Guji", "Huila", "Nariño", "Cerrado", "Sul de Minas", "Antigua", "Huehuetenango"],
    },

    "Defect": {
        "description": (
            "A negative quality outcome in the cup, traceable to a specific cause "
            "in processing, roasting, or brewing. Defects are the targets of "
            "PREVENTS edges (from BrewingTechniques and BrewingRules) and the "
            "sources of CAUSES edges (to FlavorNotes or other Defects). "
            "Modelling defects explicitly lets the diagnosis engine explain *why* "
            "a shot tasted wrong, not just *that* it tasted wrong."
        ),
        "key_properties": ["sensory_description", "primary_cause", "stage", "severity", "corrective_action"],
        "example_names": ["Channeling", "Baked", "Sour Ferment", "Astringency", "Grassy", "Quaker", "Papery", "Rubbery"],
    },

    "BrewingTechnique": {
        "description": (
            "A specific preparation technique applied within or around a BrewMethod "
            "to improve consistency, quality, or flavour clarity. More granular than "
            "BrewMethod — WDT and Rao Spin are both 'Espresso' techniques but are "
            "distinct actions. BrewingTechniques REFINE a BrewMethod and PREVENT "
            "specific Defects."
        ),
        "key_properties": ["purpose", "applies_to_methods", "difficulty", "equipment_required", "time_added_s"],
        "example_names": ["WDT", "Rao Spin", "Bypass Brewing", "Japanese Ice Method", "Blooming AeroPress", "Levelling", "Distribution"],
    },

    "SensoryDescriptor": {
        "description": (
            "A chemical compound or scientific sensory concept that underlies a "
            "perceived FlavorNote. Bridges the chemistry of coffee (what's in the "
            "bean/cup) with the consumer vocabulary (what it tastes like). "
            "Use MANIFESTS_AS to connect a SensoryDescriptor to its FlavorNote(s). "
            "When a book discusses acidity types, roast chemistry, or Maillard "
            "compounds, create SensoryDescriptor nodes rather than adding science "
            "to FlavorNote properties."
        ),
        "key_properties": ["chemical_name", "chemical_class", "perception", "concentration_in_coffee_ppm", "affected_by_roast"],
        "example_names": [
            "Malic Acid", "Citric Acid", "Phosphoric Acid", "Acetic Acid",
            "Chlorogenic Acid", "Sucrose", "Trigonelline", "Caffeine",
            "Linalool", "Geraniol", "Maillard Compounds",
        ],
    },

    "Expert": {
        "description": (
            "A knowledge authority whose claims are tracked for provenance in the "
            "graph. Every BrewingRule, BrewingTechnique, or SensoryDescriptor "
            "extracted from a book should have a SOURCED_FROM edge pointing to the "
            "relevant Expert node. When two experts disagree, model both rules and "
            "add a CONFLICTS_WITH edge — do not silently overwrite one with the other."
        ),
        "key_properties": ["full_name", "credentials", "primary_works", "organisation"],
        "example_names": ["Scott Rao", "James Hoffmann", "SCA", "World Barista Championship", "Tim Wendelboe"],
    },

    "PhysicsModel": {
        "description": (
            "A mathematical or physical model that describes the mechanics of coffee "
            "extraction, grinding, or fluid flow. Use for named models from scientific "
            "literature (Double Porosity Model, Darcy Flow, Diffusion-Limited Extraction) "
            "rather than for qualitative descriptions. BrewParameters and BrewMethods "
            "are GOVERNED_BY the PhysicsModel that predicts their behaviour."
        ),
        "key_properties": [
            "model_type", "governing_equation", "key_variables",
            "predicts", "assumptions", "source_paper",
        ],
        "example_names": [
            "Double Porosity Model", "Darcy Flow Model",
            "Diffusion-Limited Extraction", "Rao Channeling Model",
            "Particle Size Distribution Model",
        ],
    },
}


# =============================================================================
# RELATIONSHIP TYPES
# valid_sources and valid_targets are advisory for ingestion guidance.
# The DB does not enforce them — the validation function below does.
# =============================================================================

RELATIONSHIP_TYPES: dict[str, dict] = {

    # ── Original 10 ───────────────────────────────────────────────────────────

    "TYPICAL_FLAVOR": {
        "description": "An Origin, Region, or Cultivar typically produces this FlavorNote in the cup.",
        "valid_sources": ["Origin", "Region", "Cultivar"],
        "valid_targets": ["FlavorNote"],
        "example": "Origin:Ethiopia → TYPICAL_FLAVOR → FlavorNote:Blueberry",
    },

    "PRODUCES_FLAVOR": {
        "description": "A ProcessMethod produces this FlavorNote through its fermentation or drying chemistry.",
        "valid_sources": ["ProcessMethod"],
        "valid_targets": ["FlavorNote"],
        "example": "ProcessMethod:Natural → PRODUCES_FLAVOR → FlavorNote:Cherry",
    },

    "EMPHASIZES": {
        "description": "A BrewMethod highlights or amplifies this FlavorNote due to its extraction characteristics.",
        "valid_sources": ["BrewMethod"],
        "valid_targets": ["FlavorNote"],
        "example": "BrewMethod:V60 → EMPHASIZES → FlavorNote:Jasmine",
    },

    "ENHANCES": {
        "description": "A RoastLevel preserves or develops this FlavorNote through its thermal progression.",
        "valid_sources": ["RoastLevel"],
        "valid_targets": ["FlavorNote"],
        "example": "RoastLevel:Light → ENHANCES → FlavorNote:Blueberry",
    },

    "DICTATES": {
        "description": "A BrewingRule dictates the target value or direction for this BrewParameter.",
        "valid_sources": ["BrewingRule"],
        "valid_targets": ["BrewParameter"],
        "example": "BrewingRule:Golden Ratio → DICTATES → BrewParameter:Brew Ratio",
    },

    "APPLIES_TO": {
        "description": "A BrewingRule applies to this BrewMethod — its parameter targets are relevant for this method.",
        "valid_sources": ["BrewingRule"],
        "valid_targets": ["BrewMethod"],
        "example": "BrewingRule:Bloom Pre-Infusion → APPLIES_TO → BrewMethod:V60",
    },

    "SUGGESTS_TEMP": {
        "description": "A RoastLevel suggests a target water temperature range for brewing.",
        "valid_sources": ["RoastLevel"],
        "valid_targets": ["BrewParameter"],
        "example": "RoastLevel:Light → SUGGESTS_TEMP → BrewParameter:Water Temperature",
    },

    "PRODUCES": {
        "description": (
            "An EquipmentType or BrewingTechnique produces a GrindProfile; "
            "a RoastLevel directly produces a FlavorNote compound; "
            "a GrindProfile characterises a target BrewParameter value; "
            "a PhysicsModel or BrewParameter produces an observable extraction outcome."
        ),
        "valid_sources": ["EquipmentType", "RoastLevel", "BrewingTechnique", "GrindProfile", "PhysicsModel", "BrewParameter"],
        "valid_targets": ["GrindProfile", "FlavorNote", "BrewParameter", "PhysicsModel"],
        "example": "EquipmentType:Flat Burr Grinder → PRODUCES → GrindProfile:Unimodal",
    },

    "SUPPRESSES": {
        "description": "A RoastLevel destroys or masks this FlavorNote's volatile compounds.",
        "valid_sources": ["RoastLevel"],
        "valid_targets": ["FlavorNote"],
        "example": "RoastLevel:Dark → SUPPRESSES → FlavorNote:Jasmine",
    },

    "PAIRS_WITH": {
        "description": "A BrewMethod, Origin, or RoastLevel pairs well with another concept for complementary reasons.",
        "valid_sources": ["BrewMethod", "Origin", "Region", "Cultivar", "RoastLevel", "EquipmentType"],
        "valid_targets": ["GrindProfile", "BrewMethod", "RoastLevel"],
        "example": "Origin:Ethiopia → PAIRS_WITH → BrewMethod:V60",
    },

    # ── New 8 ─────────────────────────────────────────────────────────────────

    "SUB_REGION_OF": {
        "description": (
            "A Region is a geographically defined sub-area within a parent Origin "
            "(or another Region for nested areas). Always directed child → parent. "
            "Critical for enabling sub-national queries once book knowledge is ingested."
        ),
        "valid_sources": ["Region"],
        "valid_targets": ["Origin", "Region"],
        "example": "Region:Yirgacheffe → SUB_REGION_OF → Origin:Ethiopia",
    },

    "GROWN_IN": {
        "description": (
            "A Cultivar is cultivated in this Origin or Region. One cultivar can "
            "have multiple GROWN_IN edges (Gesha is grown in Ethiopia AND Panama). "
            "The cup profile differs by terroir — model that difference in the edge "
            "properties, not by creating duplicate Cultivar nodes."
        ),
        "valid_sources": ["Cultivar"],
        "valid_targets": ["Origin", "Region"],
        "example": "Cultivar:SL28 → GROWN_IN → Origin:Kenya",
    },

    "CAUSES": {
        "description": (
            "A Defect, SensoryDescriptor, BrewParameter out of range, BrewingRule "
            "violation, or PhysicsModel phenomenon causes this Defect, FlavorNote, "
            "BrewParameter deviation, or PhysicsModel outcome. Use for defect cascade "
            "chains, chemistry-to-defect links, rule-violation-to-defect links, and "
            "physical-force-to-outcome links. Primary edge type for the diagnosis engine."
        ),
        "valid_sources": ["Defect", "SensoryDescriptor", "BrewParameter", "PhysicsModel", "BrewingRule"],
        "valid_targets": ["Defect", "FlavorNote", "PhysicsModel", "BrewParameter"],
        "example": "Defect:Channeling → CAUSES → Defect:Astringency",
    },

    "PREVENTS": {
        "description": (
            "A BrewingTechnique or BrewingRule actively prevents this Defect "
            "when applied correctly. The inverse of CAUSES — used by the diagnosis "
            "engine to recommend corrective techniques when a defect is detected."
        ),
        "valid_sources": ["BrewingTechnique", "BrewingRule"],
        "valid_targets": ["Defect"],
        "example": "BrewingTechnique:WDT → PREVENTS → Defect:Channeling",
    },

    "REFINES": {
        "description": (
            "A BrewingTechnique refines, enhances, or is a specialised variant of "
            "a BrewMethod. Distinct from APPLIES_TO (which is for BrewingRules). "
            "A BrewMethod may have many REFINES-inbound edges from different techniques "
            "that each improve a different aspect of the brew."
        ),
        "valid_sources": ["BrewingTechnique"],
        "valid_targets": ["BrewMethod"],
        "example": "BrewingTechnique:WDT → REFINES → BrewMethod:Espresso",
    },

    "SOURCED_FROM": {
        "description": (
            "The knowledge claim in this node is attributed to a specific Expert or "
            "publication. Add this edge to every BrewingRule and BrewingTechnique "
            "extracted from a book. When the same claim appears in multiple sources, "
            "add multiple SOURCED_FROM edges — higher agreement across experts "
            "raises effective confidence."
        ),
        "valid_sources": ["BrewingRule", "BrewingTechnique", "Defect", "SensoryDescriptor", "Cultivar", "PhysicsModel"],
        "valid_targets": ["Expert"],
        "example": "BrewingTechnique:WDT → SOURCED_FROM → Expert:Scott Rao",
    },

    "CONFLICTS_WITH": {
        "description": (
            "Two BrewingRules make contradictory claims about the same parameter. "
            "Do NOT silently overwrite one rule with another when ingesting a new "
            "book. Instead, keep both rules and add a CONFLICTS_WITH edge so the "
            "system can surface the disagreement rather than hiding it. "
            "The edge properties should explain the nature of the conflict."
        ),
        "valid_sources": ["BrewingRule"],
        "valid_targets": ["BrewingRule"],
        "example": "BrewingRule:Bypass Dilution for Clarity → CONFLICTS_WITH → BrewingRule:Golden Ratio",
    },

    "MANIFESTS_AS": {
        "description": (
            "A SensoryDescriptor (chemical compound) manifests as a perceived "
            "FlavorNote in the cup at typical coffee concentrations. Bridges the "
            "scientific layer (chemistry) to the consumer layer (tasting notes). "
            "One compound can manifest as multiple FlavorNotes; one FlavorNote can "
            "be caused by multiple compounds."
        ),
        "valid_sources": ["SensoryDescriptor"],
        "valid_targets": ["FlavorNote"],
        "example": "SensoryDescriptor:Malic Acid → MANIFESTS_AS → FlavorNote:Lemon",
    },

    "TRANSFORMS_TO": {
        "description": (
            "A SensoryDescriptor degrades, hydrolyses, or oxidises into another "
            "SensoryDescriptor through roasting or brewing chemistry. Use this — "
            "not CAUSES — for compound-to-compound transformation chains "
            "(e.g. chlorogenic acid hydrolyses to quinic acid + caffeic acid at "
            "high roast temperatures). CAUSES is reserved for chemistry-to-defect "
            "or defect-to-defect links."
        ),
        "valid_sources": ["SensoryDescriptor"],
        "valid_targets": ["SensoryDescriptor"],
        "example": "SensoryDescriptor:Chlorogenic Acid → TRANSFORMS_TO → SensoryDescriptor:Quinic Acid",
    },

    "GOVERNED_BY": {
        "description": (
            "Links a physical phenomenon to the model that explains it, or a model "
            "to the parameter it predicts. Two valid directions: "
            "(1) BrewParameter/BrewMethod/GrindProfile → GOVERNED_BY → PhysicsModel "
            "('flow rate obeys Darcy's law'); "
            "(2) PhysicsModel → GOVERNED_BY → BrewParameter "
            "('the Double Porosity Model governs extraction yield'). "
            "Use whichever direction the source text implies."
        ),
        "valid_sources": ["BrewMethod", "BrewParameter", "GrindProfile", "BrewingTechnique", "PhysicsModel"],
        "valid_targets": ["PhysicsModel", "BrewParameter", "BrewMethod"],
        "example": "BrewParameter:Flow Rate → GOVERNED_BY → PhysicsModel:Darcy Flow Model",
    },
}


# =============================================================================
# BREWING RULE JSONB CONTRACT
# Every BrewingRule node's `properties` field MUST contain all of these keys.
# The pid_specificity.non_pid_alternative MUST be an actionable workaround,
# never a restriction or discouragement.
# =============================================================================

BREWING_RULE_SCHEMA = {
    "required_top_keys":      {"description", "dictates", "pid_specificity", "confidence", "evidence"},
    "required_dictates_keys": {"parameter", "direction", "value_range", "unit"},
    "required_pid_keys":      {"requires_pid", "reason", "non_pid_alternative"},
    "confidence_range":       (0.7, 1.0),
}

# Derived sets for fast import in knowledge_graph.py and extract_book.py
VALID_NODE_TYPE_NAMES      = set(NODE_TYPES.keys())
VALID_RELATIONSHIP_NAMES   = set(RELATIONSHIP_TYPES.keys())


# =============================================================================
# VALIDATION
# =============================================================================

def validate_graph(nodes: list[dict], edge_definitions: list[dict]) -> tuple[list[str], list[str]]:
    """
    Validate a NODES + EDGE_DEFINITIONS pair against the schema.
    Returns (errors, warnings). Errors block seeding; warnings are advisory.
    """
    errors: list[str]   = []
    warnings: list[str] = []

    # ── Node validation ───────────────────────────────────────────────────────
    for n in nodes:
        nt   = n.get("node_type", "")
        name = n.get("name", "?")

        if nt not in VALID_NODE_TYPE_NAMES:
            errors.append(f"[node] Invalid node_type '{nt}' on node '{name}'")

        if nt == "BrewingRule":
            p = n.get("properties", {})
            for key in BREWING_RULE_SCHEMA["required_top_keys"]:
                if key not in p:
                    errors.append(f"[BrewingRule '{name}'] Missing required property key: '{key}'")
                    continue
            if "dictates" in p:
                for key in BREWING_RULE_SCHEMA["required_dictates_keys"]:
                    if key not in p["dictates"]:
                        errors.append(f"[BrewingRule '{name}'] dictates missing key: '{key}'")
            if "pid_specificity" in p:
                for key in BREWING_RULE_SCHEMA["required_pid_keys"]:
                    if key not in p["pid_specificity"]:
                        errors.append(f"[BrewingRule '{name}'] pid_specificity missing key: '{key}'")
            if "confidence" in p:
                lo, hi = BREWING_RULE_SCHEMA["confidence_range"]
                if not (lo <= float(p["confidence"]) <= hi):
                    warnings.append(f"[BrewingRule '{name}'] confidence {p['confidence']} outside recommended {lo}–{hi}")

    # ── Edge validation ───────────────────────────────────────────────────────
    node_map: dict[tuple, str] = {(n["node_type"], n["name"]): n["node_type"] for n in nodes}

    for e in edge_definitions:
        src_key = e.get("source")
        tgt_key = e.get("target")
        rel     = e.get("relationship", "")

        if rel not in VALID_RELATIONSHIP_NAMES:
            errors.append(f"[edge] Invalid relationship '{rel}': {src_key} → {tgt_key}")

        if src_key and src_key not in node_map:
            warnings.append(f"[edge] Source node not in graph: {src_key}")
        if tgt_key and tgt_key not in node_map:
            warnings.append(f"[edge] Target node not in graph: {tgt_key}")

        # Advisory type-compatibility check
        if rel in RELATIONSHIP_TYPES and src_key and tgt_key:
            rt        = RELATIONSHIP_TYPES[rel]
            src_type  = node_map.get(src_key, "")
            tgt_type  = node_map.get(tgt_key, "")
            if src_type and src_type not in rt["valid_sources"]:
                warnings.append(
                    f"[edge] '{src_type}' is not a typical source for '{rel}' "
                    f"(valid: {rt['valid_sources']}): {src_key} → {tgt_key}"
                )
            if tgt_type and tgt_type not in rt["valid_targets"]:
                warnings.append(
                    f"[edge] '{tgt_type}' is not a typical target for '{rel}' "
                    f"(valid: {rt['valid_targets']}): {src_key} → {tgt_key}"
                )

    return errors, warnings


# =============================================================================
# CLI — run `python schema.py` to validate the full knowledge graph
# =============================================================================

if __name__ == "__main__":
    from knowledge_graph import NODES, EDGE_DEFINITIONS
    from collections import Counter

    errors, warnings = validate_graph(NODES, EDGE_DEFINITIONS)

    type_counts = Counter(n["node_type"] for n in NODES)
    rel_counts  = Counter(e["relationship"] for e in EDGE_DEFINITIONS)

    print("=" * 60)
    print("Coffee Knowledge Graph — Schema Validation")
    print("=" * 60)

    if errors:
        print(f"\n✗ {len(errors)} ERROR(S):")
        for err in errors:
            print(f"  {err}")
    else:
        print("\n✓ No errors")

    if warnings:
        print(f"\n⚠  {len(warnings)} WARNING(S):")
        for w in warnings:
            print(f"  {w}")
    else:
        print("✓ No warnings")

    print(f"\nNode counts ({len(NODES)} total):")
    for t in sorted(VALID_NODE_TYPE_NAMES):
        count = type_counts.get(t, 0)
        bar   = "█" * count
        print(f"  {t:22s} {count:3d}  {bar}")

    print(f"\nRelationship counts ({len(EDGE_DEFINITIONS)} total):")
    for r in sorted(VALID_RELATIONSHIP_NAMES):
        count = rel_counts.get(r, 0)
        bar   = "█" * count
        print(f"  {r:22s} {count:3d}  {bar}")

    missing_rels = VALID_RELATIONSHIP_NAMES - set(rel_counts.keys())
    if missing_rels:
        print(f"\n⚠  Relationship types defined in schema but not yet used:")
        for r in sorted(missing_rels):
            print(f"  {r}")
