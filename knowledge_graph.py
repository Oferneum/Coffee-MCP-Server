# Strictly typed coffee knowledge graph.
# Valid node_type and relationship_type values are defined in schema.py.
# Run `python schema.py` to validate this file against the schema.

NODES = [

    # =========================================================================
    # ORIGINS (8)
    # =========================================================================
    {
        "node_type": "Origin",
        "name": "Ethiopia",
        "properties": {
            "continent": "Africa",
            "altitude_range_m": "1500-2200",
            "common_processes": ["Washed", "Natural"],
            "coffee_species": "Arabica (heirloom landraces)"
        }
    },
    {
        "node_type": "Origin",
        "name": "Colombia",
        "properties": {
            "continent": "South America",
            "altitude_range_m": "1200-2000",
            "common_processes": ["Washed"],
            "coffee_species": "Arabica (Castillo, Caturra)"
        }
    },
    {
        "node_type": "Origin",
        "name": "Brazil",
        "properties": {
            "continent": "South America",
            "altitude_range_m": "800-1200",
            "common_processes": ["Natural", "Pulped Natural"],
            "coffee_species": "Arabica, Robusta"
        }
    },
    {
        "node_type": "Origin",
        "name": "Kenya",
        "properties": {
            "continent": "Africa",
            "altitude_range_m": "1400-2000",
            "common_processes": ["Washed (Double Fermentation)"],
            "coffee_species": "Arabica (SL28, SL34, Ruiru 11)"
        }
    },
    {
        "node_type": "Origin",
        "name": "Guatemala",
        "properties": {
            "continent": "Central America",
            "altitude_range_m": "1200-1800",
            "common_processes": ["Washed", "Natural"],
            "coffee_species": "Arabica (Bourbon, Catuai)"
        }
    },
    {
        "node_type": "Origin",
        "name": "Costa Rica",
        "properties": {
            "continent": "Central America",
            "altitude_range_m": "1200-1900",
            "common_processes": ["Washed", "Honey"],
            "coffee_species": "Arabica (Catuai, Villa Sarchi)"
        }
    },
    {
        "node_type": "Origin",
        "name": "Indonesia",
        "properties": {
            "continent": "Asia",
            "altitude_range_m": "1000-1700",
            "common_processes": ["Wet-Hulled"],
            "coffee_species": "Arabica, Robusta"
        }
    },
    {
        "node_type": "Origin",
        "name": "Yemen",
        "properties": {
            "continent": "Middle East",
            "altitude_range_m": "1500-2500",
            "common_processes": ["Natural"],
            "coffee_species": "Arabica (heirloom)"
        }
    },

    # =========================================================================
    # PROCESS METHODS (4)
    # =========================================================================
    {
        "node_type": "ProcessMethod",
        "name": "Washed",
        "properties": {
            "also_known_as": "Wet Process",
            "description": "Fruit pulp removed before drying; mucilage removed by fermentation in water tanks",
            "flavor_impact": "Clean, high clarity, terroir-forward, bright acidity",
            "water_usage": "High",
            "body_impact": "Light to medium"
        }
    },
    {
        "node_type": "ProcessMethod",
        "name": "Natural",
        "properties": {
            "also_known_as": "Dry Process",
            "description": "Whole cherry dried intact on raised beds or patios for 3-6 weeks",
            "flavor_impact": "Fruity, winey, heavy body, complex fermentation notes",
            "water_usage": "Minimal",
            "body_impact": "Full"
        }
    },
    {
        "node_type": "ProcessMethod",
        "name": "Honey",
        "properties": {
            "also_known_as": "Pulped Natural",
            "description": "Pulp removed but mucilage left on bean during drying; variants from Yellow to Black Honey",
            "flavor_impact": "Stone fruit sweetness, caramel, medium-full body",
            "water_usage": "Low to medium",
            "body_impact": "Medium to full",
            "variants": ["Yellow Honey", "Red Honey", "Black Honey"]
        }
    },
    {
        "node_type": "ProcessMethod",
        "name": "Anaerobic",
        "properties": {
            "also_known_as": "Anaerobic Fermentation",
            "description": "Whole cherries or depulped beans fermented in sealed, oxygen-free tanks",
            "flavor_impact": "Intense tropical fruit, lactic acidity, winey, complex",
            "water_usage": "Low",
            "body_impact": "Heavy",
            "fermentation_duration_hours": "24-200"
        }
    },

    # =========================================================================
    # ROAST LEVELS (3)
    # =========================================================================
    {
        "node_type": "RoastLevel",
        "name": "Light",
        "properties": {
            "internal_temp_c": "196-205",
            "development_stage": "First crack reached; not past",
            "oil_on_surface": False,
            "acidity": "High",
            "body": "Light",
            "suggested_water_temp_c": "94-96",
            "origin_expression": "Maximum — terroir and process flavors dominate"
        }
    },
    {
        "node_type": "RoastLevel",
        "name": "Medium",
        "properties": {
            "internal_temp_c": "210-220",
            "development_stage": "Past first crack, before second crack",
            "oil_on_surface": False,
            "acidity": "Medium",
            "body": "Medium",
            "suggested_water_temp_c": "92-94",
            "origin_expression": "Balanced — origin and roast character share the cup"
        }
    },
    {
        "node_type": "RoastLevel",
        "name": "Dark",
        "properties": {
            "internal_temp_c": "230-245",
            "development_stage": "Past second crack",
            "oil_on_surface": True,
            "acidity": "Very low",
            "body": "Heavy",
            "suggested_water_temp_c": "88-92",
            "origin_expression": "Minimal — roast character dominates"
        }
    },

    # =========================================================================
    # FLAVOR NOTES (19 — SCA Taster's Flavor Wheel)
    # =========================================================================
    {
        "node_type": "FlavorNote",
        "name": "Blueberry",
        "properties": {"sca_category": "Fruity > Berry", "taste_profile": "Sweet, jammy, slightly tart"}
    },
    {
        "node_type": "FlavorNote",
        "name": "Raspberry",
        "properties": {"sca_category": "Fruity > Berry", "taste_profile": "Bright, tart, red fruit"}
    },
    {
        "node_type": "FlavorNote",
        "name": "Blackcurrant",
        "properties": {"sca_category": "Fruity > Berry", "taste_profile": "Bold, dark berry, slightly tannic"}
    },
    {
        "node_type": "FlavorNote",
        "name": "Cherry",
        "properties": {"sca_category": "Fruity > Other Fruit", "taste_profile": "Sweet-tart, red stone fruit"}
    },
    {
        "node_type": "FlavorNote",
        "name": "Peach",
        "properties": {"sca_category": "Fruity > Other Fruit", "taste_profile": "Sweet, delicate, stone fruit"}
    },
    {
        "node_type": "FlavorNote",
        "name": "Lemon",
        "properties": {"sca_category": "Fruity > Citrus Fruit", "taste_profile": "Bright, sharp, citric acidity"}
    },
    {
        "node_type": "FlavorNote",
        "name": "Orange",
        "properties": {"sca_category": "Fruity > Citrus Fruit", "taste_profile": "Mild citrus, slightly sweet"}
    },
    {
        "node_type": "FlavorNote",
        "name": "Jasmine",
        "properties": {"sca_category": "Floral", "taste_profile": "Delicate, perfumed, aromatic"}
    },
    {
        "node_type": "FlavorNote",
        "name": "Rose",
        "properties": {"sca_category": "Floral", "taste_profile": "Soft, sweet floral, fragrant"}
    },
    {
        "node_type": "FlavorNote",
        "name": "Brown Sugar",
        "properties": {"sca_category": "Sweet", "taste_profile": "Molasses, cane sugar, mild sweetness"}
    },
    {
        "node_type": "FlavorNote",
        "name": "Caramel",
        "properties": {"sca_category": "Sweet > Caramelized", "taste_profile": "Sweet, buttery, toffee-like"}
    },
    {
        "node_type": "FlavorNote",
        "name": "Honey",
        "properties": {"sca_category": "Sweet", "taste_profile": "Floral sweetness, viscous mouthfeel"}
    },
    {
        "node_type": "FlavorNote",
        "name": "Dark Chocolate",
        "properties": {"sca_category": "Nutty/Cocoa > Cocoa", "taste_profile": "Rich, bittersweet cocoa, roasty"}
    },
    {
        "node_type": "FlavorNote",
        "name": "Milk Chocolate",
        "properties": {"sca_category": "Nutty/Cocoa > Cocoa", "taste_profile": "Creamy, sweet, mild cocoa"}
    },
    {
        "node_type": "FlavorNote",
        "name": "Hazelnut",
        "properties": {"sca_category": "Nutty/Cocoa > Nutty", "taste_profile": "Roasted nut, slightly sweet"}
    },
    {
        "node_type": "FlavorNote",
        "name": "Almond",
        "properties": {"sca_category": "Nutty/Cocoa > Nutty", "taste_profile": "Mild nut, slightly bitter finish"}
    },
    {
        "node_type": "FlavorNote",
        "name": "Cinnamon",
        "properties": {"sca_category": "Spices > Brown Spice", "taste_profile": "Warm, sweet spice"}
    },
    {
        "node_type": "FlavorNote",
        "name": "Tobacco",
        "properties": {"sca_category": "Roasted", "taste_profile": "Dry, woody, smoky undertone"}
    },
    {
        "node_type": "FlavorNote",
        "name": "Earthy",
        "properties": {"sca_category": "Green/Vegetative > Musty/Earthy", "taste_profile": "Forest floor, mushroom, humus"}
    },

    # =========================================================================
    # BREW METHODS (6)
    # =========================================================================
    {
        "node_type": "BrewMethod",
        "name": "Espresso",
        "properties": {
            "pressure_bar": 9,
            "water_temp_c": "88-96 (roast-dependent)",
            "extraction_time_s": "25-35",
            "dose_g": "18-20",
            "yield_g": "36-40",
            "tds_percent": "8-12",
            "filter_type": "Portafilter basket"
        }
    },
    {
        "node_type": "BrewMethod",
        "name": "V60",
        "properties": {
            "water_temp_c": "92-96 (roast-dependent)",
            "brew_ratio": "1:15-1:17",
            "total_time_min": "3-4",
            "filter_type": "Paper (V60 01/02)",
            "requires_bloom": True
        }
    },
    {
        "node_type": "BrewMethod",
        "name": "Chemex",
        "properties": {
            "water_temp_c": "92-96 (roast-dependent)",
            "brew_ratio": "1:15-1:17",
            "total_time_min": "4-5",
            "filter_type": "Bonded paper (thick)",
            "requires_bloom": True
        }
    },
    {
        "node_type": "BrewMethod",
        "name": "French Press",
        "properties": {
            "water_temp_c": 94,
            "brew_ratio": "1:15",
            "steep_time_min": 4,
            "filter_type": "Metal mesh plunger",
            "requires_bloom": False
        }
    },
    {
        "node_type": "BrewMethod",
        "name": "AeroPress",
        "properties": {
            "water_temp_c": "80-96 (technique-dependent)",
            "brew_ratio": "1:6-1:17",
            "total_time_s": "60-120",
            "filter_type": "Paper or metal",
            "versatility": "Very high"
        }
    },
    {
        "node_type": "BrewMethod",
        "name": "Cold Brew",
        "properties": {
            "water_temp_c": "4-20",
            "brew_ratio": "1:8 (concentrate)",
            "steep_time_hours": "12-24",
            "filter_type": "Paper or cloth",
            "requires_bloom": False
        }
    },

    # =========================================================================
    # BREW PARAMETERS
    # =========================================================================
    {
        "node_type": "BrewParameter",
        "name": "Water Temperature",
        "properties": {
            "unit": "°C",
            "typical_range": "80-96",
            "primary_effect": "Controls extraction rate; higher temp increases solubility of flavor compounds"
        }
    },
    {
        "node_type": "BrewParameter",
        "name": "Extraction Time",
        "properties": {
            "unit": "seconds",
            "typical_range": "25-35 (espresso), 180-300 (filter)",
            "primary_effect": "Determines total dissolved solids; too short = under-extraction, too long = over-extraction"
        }
    },
    {
        "node_type": "BrewParameter",
        "name": "Brew Ratio",
        "properties": {
            "unit": "g coffee : g water",
            "typical_range": "1:2 (espresso) to 1:17 (filter)",
            "primary_effect": "Sets concentration and perceived strength"
        }
    },
    {
        "node_type": "BrewParameter",
        "name": "Grind Size",
        "properties": {
            "unit": "microns",
            "typical_range": "200-1200",
            "primary_effect": "Controls surface area exposed to water; finer = faster extraction, coarser = slower"
        }
    },
    {
        "node_type": "BrewParameter",
        "name": "Bloom Time",
        "properties": {
            "unit": "seconds",
            "typical_range": "30-45",
            "primary_effect": "Pre-infusion degasses CO2, allowing even water penetration through the coffee bed"
        }
    },
    {
        "node_type": "BrewParameter",
        "name": "Yield Ratio",
        "properties": {
            "unit": "ratio (dose:yield)",
            "typical_range": "1:2 to 1:2.5",
            "primary_effect": "Directly controls espresso concentration and flavor intensity"
        }
    },

    # =========================================================================
    # EQUIPMENT TYPES (4)
    # =========================================================================
    {
        "node_type": "EquipmentType",
        "name": "PID Espresso Machine",
        "properties": {
            "temperature_control": "PID (Proportional-Integral-Derivative) closed-loop",
            "temp_stability_variance_c": "±0.1-0.3",
            "use_case": "Precision espresso; critical for light roast extraction",
            "price_range_usd": "600-5000+"
        }
    },
    {
        "node_type": "EquipmentType",
        "name": "Non-PID Espresso Machine",
        "properties": {
            "temperature_control": "Thermostat (on/off switching)",
            "temp_stability_variance_c": "±2-5",
            "use_case": "Entry-level espresso; temperature surfing technique required",
            "price_range_usd": "150-600"
        }
    },
    {
        "node_type": "EquipmentType",
        "name": "Flat Burr Grinder",
        "properties": {
            "burr_geometry": "Two parallel flat rings",
            "grind_distribution": "Unimodal — narrow, uniform particle band",
            "flavor_profile": "High clarity and brightness; preferred for filter and light roast espresso",
            "retention_g": "Low to medium",
            "price_range_usd": "200-3000+"
        }
    },
    {
        "node_type": "EquipmentType",
        "name": "Conical Burr Grinder",
        "properties": {
            "burr_geometry": "Inner cone rotating inside outer ring",
            "grind_distribution": "Bimodal — two distinct particle size populations",
            "flavor_profile": "Sweetness, body, and complexity; preferred for traditional espresso",
            "retention_g": "Low",
            "price_range_usd": "50-2000+"
        }
    },

    # =========================================================================
    # GRIND PROFILES (2)
    # =========================================================================
    {
        "node_type": "GrindProfile",
        "name": "Unimodal",
        "properties": {
            "distribution_shape": "Single peak — narrow, uniform particle size band",
            "primary_benefit": "Predictable, even extraction; high cup clarity",
            "common_grinders": ["Flat burr grinders", "High-precision espresso grinders"],
            "best_for": ["Filter methods", "Light roast espresso", "Competition brewing"]
        }
    },
    {
        "node_type": "GrindProfile",
        "name": "Bimodal",
        "properties": {
            "distribution_shape": "Two peaks — mix of fine 'fines' and coarser particles",
            "primary_benefit": "Fines accelerate extraction onset; coarser particles extend flavor development",
            "common_grinders": ["Conical burr grinders", "Most home grinders"],
            "best_for": ["Traditional espresso", "Immersion methods", "Dark roast brewing"]
        }
    },

    # =========================================================================
    # =========================================================================
    # CULTIVARS (5)
    # Why separate from Origin: Gesha grown in Ethiopia vs. Panama tastes
    # different because of terroir, but it's the same genetic cultivar.
    # Keeping cultivar as its own type lets us model that distinction with
    # GROWN_IN edges rather than duplicating properties on Origin nodes.
    # =========================================================================
    {
        "node_type": "Cultivar",
        "name": "Gesha",
        "properties": {
            "species": "Arabica",
            "genetic_lineage": "Ethiopian heirloom, discovered in Gesha village, Kaffa region",
            "cup_profile": "Intensely floral, jasmine, bergamot, stone fruit, tea-like clarity",
            "typical_origins": ["Ethiopia", "Panama", "Colombia"],
            "yield": "Very low — contributes to premium pricing",
            "altitude_preference_m": "1700-2200"
        }
    },
    {
        "node_type": "Cultivar",
        "name": "Bourbon",
        "properties": {
            "species": "Arabica",
            "genetic_lineage": "Mutation of Typica, first cultivated on Réunion island (formerly Bourbon)",
            "cup_profile": "Complex sweetness, red fruit, caramel, well-balanced acidity",
            "typical_origins": ["Colombia", "Guatemala", "El Salvador", "Brazil"],
            "yield": "Medium",
            "altitude_preference_m": "1000-2000",
            "variants": ["Red Bourbon", "Yellow Bourbon", "Orange Bourbon", "Pink Bourbon"]
        }
    },
    {
        "node_type": "Cultivar",
        "name": "Typica",
        "properties": {
            "species": "Arabica",
            "genetic_lineage": "One of the oldest Arabica cultivars; ancestral lineage for most modern varieties",
            "cup_profile": "Clean, classic, mild sweetness, low acidity, delicate",
            "typical_origins": ["Jamaica", "Hawaii", "Peru", "Papua New Guinea"],
            "yield": "Low — susceptible to disease",
            "altitude_preference_m": "1000-1800"
        }
    },
    {
        "node_type": "Cultivar",
        "name": "SL28",
        "properties": {
            "species": "Arabica",
            "genetic_lineage": "Selected by Scott Laboratories in Kenya in the 1930s from Tanganyika Drought Resistant",
            "cup_profile": "Blackcurrant, bold acidity, winey complexity, full body",
            "typical_origins": ["Kenya"],
            "yield": "Medium",
            "altitude_preference_m": "1500-2100",
            "notes": "The cultivar most responsible for Kenya's distinctive cup profile"
        }
    },
    {
        "node_type": "Cultivar",
        "name": "Catuai",
        "properties": {
            "species": "Arabica",
            "genetic_lineage": "Hybrid of Mundo Novo x Caturra, developed in Brazil in the 1950s",
            "cup_profile": "Mild, sweet, low acidity, chocolate, nuts",
            "typical_origins": ["Brazil", "Colombia", "Central America"],
            "yield": "High — one of the most widely planted Arabica varieties",
            "altitude_preference_m": "800-1500",
            "variants": ["Red Catuai", "Yellow Catuai"]
        }
    },

    # =========================================================================
    # REGIONS (5)
    # Why separate from Origin: Origin is country-level. Region adds the
    # sub-national specificity that specialty coffee buyers actually use.
    # Each Region gets a SUB_REGION_OF edge to its parent Origin.
    # =========================================================================
    {
        "node_type": "Region",
        "name": "Yirgacheffe",
        "properties": {
            "parent_origin": "Ethiopia",
            "altitude_range_m": "1700-2200",
            "cup_profile": "The global reference for washed floral coffee: jasmine, bergamot, lemon, tea-like body",
            "dominant_process": "Washed",
            "primary_cultivars": ["Ethiopian heirlooms"],
            "notable_sub_zones": ["Kochere", "Gedeb", "Aricha"]
        }
    },
    {
        "node_type": "Region",
        "name": "Sidama",
        "properties": {
            "parent_origin": "Ethiopia",
            "altitude_range_m": "1500-2200",
            "cup_profile": "Blueberry, stone fruit, mild chocolate — slightly earthier and fuller than Yirgacheffe",
            "dominant_process": "Both Washed and Natural",
            "primary_cultivars": ["Ethiopian heirlooms"],
            "notable_sub_zones": ["Bensa", "Arbegona", "Shantawene"]
        }
    },
    {
        "node_type": "Region",
        "name": "Huila",
        "properties": {
            "parent_origin": "Colombia",
            "altitude_range_m": "1500-2000",
            "cup_profile": "Complex, bright acidity, tropical fruit, caramel, excellent sweetness",
            "dominant_process": "Washed",
            "primary_cultivars": ["Castillo", "Colombia", "Caturra"],
            "notes": "One of Colombia's most prized departments for specialty production"
        }
    },
    {
        "node_type": "Region",
        "name": "Cerrado",
        "properties": {
            "parent_origin": "Brazil",
            "altitude_range_m": "800-1100",
            "cup_profile": "Chocolate, nuts, low acidity, heavy body — classic Brazilian espresso base",
            "dominant_process": "Natural, Pulped Natural",
            "primary_cultivars": ["Catuai", "Mundo Novo"],
            "notes": "First Brazilian region to receive a geographical indication (GI)"
        }
    },
    {
        "node_type": "Region",
        "name": "Antigua",
        "properties": {
            "parent_origin": "Guatemala",
            "altitude_range_m": "1500-1700",
            "cup_profile": "Full body, dark chocolate, brown sugar, mild fruit, volcanic mineral notes",
            "dominant_process": "Washed",
            "primary_cultivars": ["Bourbon", "Typica", "Caturra"],
            "notes": "Surrounded by three volcanoes; volcanic soil contributes mineral complexity"
        }
    },

    # =========================================================================
    # DEFECTS (5)
    # Why model defects as nodes: The diagnosis engine needs to traverse
    # CAUSES and PREVENTS edges. If defects are only strings in properties,
    # the graph cannot reason about them structurally.
    # =========================================================================
    {
        "node_type": "Defect",
        "name": "Channeling",
        "properties": {
            "stage": "Brewing",
            "sensory_description": "Bitter, uneven, one-dimensional — water finds the path of least resistance, leaving dry pockets under-extracted and wet pockets over-extracted simultaneously",
            "primary_cause": "Uneven coffee bed: clumping, voids, or poor distribution before tamping",
            "severity": "High — renders shot unpredictable mid-pull",
            "corrective_action": "Apply WDT before tamping; ensure level distribution; check grind consistency"
        }
    },
    {
        "node_type": "Defect",
        "name": "Baked",
        "properties": {
            "stage": "Roasting",
            "sensory_description": "Flat, cardboard, bread-like, hollow sweetness — developed but no complexity or brightness",
            "primary_cause": "Roast development too slow; bean temperature stalls during development phase",
            "severity": "Medium — cannot be corrected in brewing; is a roast defect",
            "corrective_action": "Roaster must increase rate of rise during development; unfixable by barista"
        }
    },
    {
        "node_type": "Defect",
        "name": "Sour Ferment",
        "properties": {
            "stage": "Processing",
            "sensory_description": "Vinegar, acetic, sharp unpleasant sourness — distinct from clean citric acidity",
            "primary_cause": "Over-fermentation during wet processing: too long in fermentation tank or contaminated water",
            "severity": "High — a processing defect in the green bean; unfixable in roasting or brewing",
            "corrective_action": "Select beans from producers with controlled fermentation times and clean water"
        }
    },
    {
        "node_type": "Defect",
        "name": "Astringency",
        "properties": {
            "stage": "Brewing",
            "sensory_description": "Drying, gripping, tannin-like mouthfeel — leaves inside of mouth feeling parched and rough",
            "primary_cause": "Over-extraction OR channeling creating locally over-extracted pockets",
            "severity": "Medium — reduces cup quality significantly; partially correctable",
            "corrective_action": "Coarsen grind, reduce extraction time, lower water temperature, or fix puck prep"
        }
    },
    {
        "node_type": "Defect",
        "name": "Grassy",
        "properties": {
            "stage": "Roasting",
            "sensory_description": "Raw, green, fresh-cut grass, hay — the coffee tastes underdeveloped",
            "primary_cause": "Under-roasted: insufficient internal bean temperature during development phase",
            "severity": "Medium — a roast defect; partially masked by higher brew temperature",
            "corrective_action": "Brew at 94-96°C to extract more from dense under-developed cells; sourcing fix is better roasted coffee"
        }
    },

    # =========================================================================
    # BREWING TECHNIQUES (5)
    # Why separate from BrewMethod: Espresso is a method. WDT is something
    # you do inside that method. Techniques REFINE methods (not methods
    # themselves) and PREVENT defects — relationships BrewMethod can't have.
    # =========================================================================
    {
        "node_type": "BrewingTechnique",
        "name": "WDT",
        "properties": {
            "full_name": "Weiss Distribution Technique",
            "purpose": "Break up clumps and evenly distribute espresso grounds in the portafilter basket before tamping, preventing channeling",
            "applies_to_methods": ["Espresso"],
            "difficulty": "Low",
            "equipment_required": "WDT tool (thin needles ~0.3-0.4mm) or repurposed acupuncture needles",
            "time_added_s": 10
        }
    },
    {
        "node_type": "BrewingTechnique",
        "name": "Rao Spin",
        "properties": {
            "full_name": "Rao Spinning Technique",
            "purpose": "Swirl the espresso cup immediately after the pull to integrate crema and body for a uniform, sweeter cup",
            "applies_to_methods": ["Espresso"],
            "difficulty": "Very low",
            "equipment_required": "None beyond the espresso cup",
            "time_added_s": 3
        }
    },
    {
        "node_type": "BrewingTechnique",
        "name": "Bypass Brewing",
        "properties": {
            "full_name": "Bypass Dilution Brewing",
            "purpose": "Brew at higher concentration (1:10), then dilute with hot water to target TDS. More even extraction due to denser bed",
            "applies_to_methods": ["V60", "Chemex", "AeroPress"],
            "difficulty": "Low",
            "equipment_required": "Digital scale, second vessel for dilution water",
            "time_added_s": 30
        }
    },
    {
        "node_type": "BrewingTechnique",
        "name": "Japanese Ice Method",
        "properties": {
            "full_name": "Japanese Iced Coffee / Flash Brew",
            "purpose": "Brew hot coffee directly onto ice for instant chilling. Preserves aromatics lost in cold brew's slow cold steep",
            "applies_to_methods": ["V60", "Chemex"],
            "difficulty": "Low — adjust brew ratio (brew at 1:10) to account for ice melt",
            "equipment_required": "Ice, adjusted brew recipe",
            "time_added_s": 0
        }
    },
    {
        "node_type": "BrewingTechnique",
        "name": "Blooming AeroPress",
        "properties": {
            "full_name": "Blooming AeroPress Method",
            "purpose": "Allow 30-45s pre-infusion (bloom) before adding remaining water, degassing CO2 for more even extraction",
            "applies_to_methods": ["AeroPress"],
            "difficulty": "Low",
            "equipment_required": "Standard AeroPress",
            "time_added_s": 40
        }
    },

    # =========================================================================
    # SENSORY DESCRIPTORS (4)
    # Why add these: Books discuss chemistry directly. When a source says
    # 'chlorogenic acids cause astringency' that's a CAUSES edge.
    # Without SensoryDescriptor nodes, that knowledge has nowhere to live.
    # =========================================================================
    {
        "node_type": "SensoryDescriptor",
        "name": "Malic Acid",
        "properties": {
            "chemical_name": "2-hydroxysuccinic acid",
            "chemical_class": "Organic acid",
            "perception": "Tart, green apple, lemon — a clean mid-range acidity",
            "concentration_in_coffee_ppm": "Moderate (150-300mg/L in brewed coffee)",
            "affected_by_roast": "Partially degrades; highest in light roasts and washed coffees",
            "primary_sources": ["Ethiopian washed", "Kenyan", "Colombian high-altitude"]
        }
    },
    {
        "node_type": "SensoryDescriptor",
        "name": "Citric Acid",
        "properties": {
            "chemical_name": "2-hydroxypropane-1,2,3-tricarboxylic acid",
            "chemical_class": "Organic acid",
            "perception": "Bright, clean orange/lemon citrus — the most common coffee acid",
            "concentration_in_coffee_ppm": "High (200-500mg/L in brewed coffee)",
            "affected_by_roast": "Degrades significantly with roast development; dominant in light roasts",
            "primary_sources": ["Most high-altitude washed Arabica"]
        }
    },
    {
        "node_type": "SensoryDescriptor",
        "name": "Phosphoric Acid",
        "properties": {
            "chemical_name": "Orthophosphoric acid",
            "chemical_class": "Inorganic acid",
            "perception": "Very clean, transparent brightness without specific citrus character",
            "concentration_in_coffee_ppm": "Low (traces, but perceptually significant)",
            "affected_by_roast": "Relatively stable through light-medium roasting",
            "primary_sources": ["Washed Ethiopian high-altitude", "Some Kenyan AA"]
        }
    },
    {
        "node_type": "SensoryDescriptor",
        "name": "Chlorogenic Acid",
        "properties": {
            "chemical_name": "3-O-caffeoylquinic acid (primary isomer)",
            "chemical_class": "Polyphenol",
            "perception": "Astringent, dry, slightly bitter at high concentrations",
            "concentration_in_coffee_ppm": "Very high in green coffee (6-10% dry weight); reduces 50-70% by medium roast",
            "affected_by_roast": "Degrades substantially — nearly absent in dark roasts",
            "primary_sources": ["All coffees — highest in under-roasted or light roasts"]
        }
    },

    # =========================================================================
    # EXPERTS (4)
    # Why model experts as nodes: When books disagree, CONFLICTS_WITH edges
    # between BrewingRules need SOURCED_FROM edges to say *who* holds each
    # position. Without Expert nodes, conflicting claims collapse into one truth.
    # =========================================================================
    {
        "node_type": "Expert",
        "name": "Scott Rao",
        "properties": {
            "full_name": "Scott Rao",
            "credentials": "Coffee consultant, roaster, barista trainer",
            "primary_works": ["The Professional Barista's Handbook (2008)", "The Coffee Roaster's Companion (2014)"],
            "organisation": "Independent",
            "known_for": "Quantitative approach to espresso and roasting; popularised WDT, Rao Spin, extraction yield measurement"
        }
    },
    {
        "node_type": "Expert",
        "name": "James Hoffmann",
        "properties": {
            "full_name": "James Hoffmann",
            "credentials": "2007 World Barista Champion, author, coffee educator",
            "primary_works": ["The World Atlas of Coffee (2014)", "How to Make the Best Coffee in Your Home (2022)"],
            "organisation": "Square Mile Coffee Roasters (co-founder)",
            "known_for": "Accessible coffee education, bypass dilution, French press no-stir method"
        }
    },
    {
        "node_type": "Expert",
        "name": "SCA",
        "properties": {
            "full_name": "Specialty Coffee Association",
            "credentials": "Global trade body defining specialty coffee standards",
            "primary_works": ["SCA Brewing Standards", "SCA Cupping Protocols", "Coffee Taster's Flavor Wheel"],
            "organisation": "Non-profit trade association",
            "known_for": "Golden Cup Standard (1:15-1:17, 90-96°C), grading standards, barista skills curriculum"
        }
    },
    {
        "node_type": "Expert",
        "name": "World Barista Championship",
        "properties": {
            "full_name": "World Barista Championship",
            "credentials": "Annual global competition judged by certified SCA judges",
            "primary_works": ["WBC Rules and Regulations (updated annually)", "WBC Scoresheet"],
            "organisation": "World Coffee Events / SCA",
            "known_for": "Competition-level espresso standards: 1:2 dose-to-yield, 25-35s extraction window"
        }
    },

    # =========================================================================
    # ADDITIONAL BREWING RULE — demonstrates CONFLICTS_WITH
    # Bypass Dilution conflicts with Golden Ratio not because one is wrong,
    # but because they represent different philosophies. Modelling the conflict
    # is more honest than silently picking one.
    # =========================================================================
    {
        "node_type": "BrewingRule",
        "name": "Bypass Dilution for Clarity",
        "properties": {
            "description": "Brew filter coffee at 1:8-1:10 concentration, then add hot water to reach target strength (1:14-1:17). The denser brew bed extracts more evenly; dilution achieves target TDS without over-extracting outer grounds.",
            "dictates": {
                "parameter": "brew_ratio",
                "direction": "concentrate_then_dilute",
                "value_range": "1:8-1:10 brew, dilute to 1:14-1:17",
                "unit": "g coffee per g water"
            },
            "pid_specificity": {
                "requires_pid": None,
                "reason": "Bypass dilution is ratio and volume management; independent of temperature precision equipment.",
                "non_pid_alternative": "Boil a second kettle for dilution water. Weigh both brew output and added dilution water on a 0.1g scale to hit your target TDS."
            },
            "confidence": 0.82,
            "evidence": "James Hoffmann — The World Atlas of Coffee; YouTube: The Bypass Method"
        }
    },

    # BREWING RULES (8)
    # Each rule MUST carry: description, dictates, pid_specificity, confidence, evidence
    # non_pid_alternative MUST be an actionable workaround — never a restriction
    # =========================================================================
    {
        "node_type": "BrewingRule",
        "name": "High Temp for Light Roast",
        "properties": {
            "description": "Light roasts have denser cell structure and require higher water temperature to achieve full extraction of floral and fruit compounds.",
            "dictates": {
                "parameter": "water_temperature",
                "direction": "increase",
                "value_range": "94-96",
                "unit": "°C"
            },
            "pid_specificity": {
                "requires_pid": True,
                "reason": "A 2°C variance at this temperature range meaningfully shifts extraction; temperatures below 94°C leave floral and citric acids under-extracted.",
                "non_pid_alternative": "Temperature surf: run a full group-head flush for 6-8 seconds immediately before pulling to push temp to its upper idle peak, then pull without delay."
            },
            "confidence": 0.93,
            "evidence": "SCA Extraction Fundamentals; Rao — The Professional Barista's Handbook"
        }
    },
    {
        "node_type": "BrewingRule",
        "name": "Lower Temp for Dark Roast",
        "properties": {
            "description": "Dark roasts have porous, fragile cell structure and extract rapidly; lower water temperature prevents bitter and acrid over-extraction.",
            "dictates": {
                "parameter": "water_temperature",
                "direction": "decrease",
                "value_range": "88-92",
                "unit": "°C"
            },
            "pid_specificity": {
                "requires_pid": True,
                "reason": "Over-shooting by 2°C on a dark espresso elevates bitter phenolic extraction noticeably.",
                "non_pid_alternative": "Temperature surf: allow the machine to idle 25-35 seconds after the boiler cycling light extinguishes before pulling the shot."
            },
            "confidence": 0.91,
            "evidence": "Rao — The Professional Barista's Handbook; World Barista Championship training materials"
        }
    },
    {
        "node_type": "BrewingRule",
        "name": "Espresso Extraction Window",
        "properties": {
            "description": "Espresso should extract within 25-35 seconds at 9 bar for balanced sweetness, acidity, and body.",
            "dictates": {
                "parameter": "extraction_time",
                "direction": "target_range",
                "value_range": "25-35",
                "unit": "seconds"
            },
            "pid_specificity": {
                "requires_pid": False,
                "reason": "Shot timing is controlled by grind size and dose weight, not by temperature precision.",
                "non_pid_alternative": "Adjust grind one click coarser if the shot runs under 25s; one click finer if over 35s. Re-pull a fresh shot after each single adjustment."
            },
            "confidence": 0.95,
            "evidence": "SCA Specialty Coffee Barista Skills; World Barista Championship judging criteria"
        }
    },
    {
        "node_type": "BrewingRule",
        "name": "Golden Ratio",
        "properties": {
            "description": "Use 1g of coffee per 15-17g of water for filter brewing to hit the SCA Golden Cup TDS corridor of 1.15-1.45%.",
            "dictates": {
                "parameter": "brew_ratio",
                "direction": "target_range",
                "value_range": "1:15 to 1:17",
                "unit": "g coffee per g water"
            },
            "pid_specificity": {
                "requires_pid": None,
                "reason": "Brew ratio is a measurement of mass, fully independent of temperature control equipment.",
                "non_pid_alternative": "Weigh every dose and total brew yield on a 0.1g-precision scale; a 1g water variance shifts TDS by roughly 0.05%, which is perceptible."
            },
            "confidence": 0.96,
            "evidence": "SCA Brewing Control Chart — Golden Cup Standard"
        }
    },
    {
        "node_type": "BrewingRule",
        "name": "Bloom Pre-Infusion",
        "properties": {
            "description": "Pre-wet grounds with 2x the coffee dose weight in water and wait 30-45 seconds to degas CO2 before the main pour, ensuring even water penetration.",
            "dictates": {
                "parameter": "bloom_time",
                "direction": "target_range",
                "value_range": "30-45",
                "unit": "seconds"
            },
            "pid_specificity": {
                "requires_pid": False,
                "reason": "Bloom timing is a stopwatch technique independent of temperature control equipment.",
                "non_pid_alternative": "Start a phone timer the moment you finish the bloom pour; use the visual cue of the slurry settling and bubbling slowing as a secondary signal alongside the timer."
            },
            "confidence": 0.93,
            "evidence": "Perger — Barista Hustle: Water and Coffee; SCA Brewing Fundamentals"
        }
    },
    {
        "node_type": "BrewingRule",
        "name": "Coarse Grind for Immersion",
        "properties": {
            "description": "Immersion brew methods steep grounds in water for several minutes; a coarse grind slows extraction rate to prevent bitterness and over-extraction.",
            "dictates": {
                "parameter": "grind_size",
                "direction": "increase",
                "value_range": "800-1200",
                "unit": "microns"
            },
            "pid_specificity": {
                "requires_pid": None,
                "reason": "Grind size is a physical, mechanical adjustment that does not interact with temperature control hardware.",
                "non_pid_alternative": "Rub grounds between thumb and forefinger: they should feel like coarse sea salt or rough sand. Adjust the grinder in 2-click increments until the texture matches."
            },
            "confidence": 0.91,
            "evidence": "SCA French Press and Immersion Brewing curriculum"
        }
    },
    {
        "node_type": "BrewingRule",
        "name": "Fine Grind for Pressure",
        "properties": {
            "description": "Pressure-based methods require fine grind to build hydraulic resistance and achieve target extraction in a short 25-35 second window.",
            "dictates": {
                "parameter": "grind_size",
                "direction": "decrease",
                "value_range": "200-400",
                "unit": "microns"
            },
            "pid_specificity": {
                "requires_pid": None,
                "reason": "Grind fineness is set on the grinder and is independent of boiler temperature control.",
                "non_pid_alternative": "Dial in by shot time and flow: aim for a thin, honey-like pour beginning at 5-8s and reaching target yield at 30s. Adjust one step at a time and pull a fresh dose to verify."
            },
            "confidence": 0.95,
            "evidence": "SCA Barista Skills — Espresso Extraction Science"
        }
    },
    {
        "node_type": "BrewingRule",
        "name": "Espresso Dose-to-Yield Ratio",
        "properties": {
            "description": "Pull espresso to a 1:2 dose-to-yield ratio (e.g., 18g dose → 36g liquid yield) for a balanced ristretto-to-lungo spectrum.",
            "dictates": {
                "parameter": "yield_ratio",
                "direction": "target_range",
                "value_range": "1:1.8 to 1:2.5",
                "unit": "g dose per g yield"
            },
            "pid_specificity": {
                "requires_pid": False,
                "reason": "Dose and yield are controlled entirely by scale weight and shot timing.",
                "non_pid_alternative": "Tare a scale under the cup before the shot; stop by pressing the brew button when the yield weight hits target, or watch for the crema colour to transition from dark amber to pale blonde."
            },
            "confidence": 0.94,
            "evidence": "World Barista Championship scoring framework; SCA Espresso Standards"
        }
    },
]

# =========================================================================
# EDGE DEFINITIONS
# source/target are (node_type, name) tuples; seed_knowledge_graph() resolves them to IDs.
# relationship must be from the approved list.
# =========================================================================
EDGE_DEFINITIONS = [

    # --- Origins -> FlavorNotes (TYPICAL_FLAVOR) ---
    {"source": ("Origin", "Ethiopia"), "target": ("FlavorNote", "Blueberry"), "relationship": "TYPICAL_FLAVOR",
     "properties": {"source": "SCA Flavor Wheel", "confidence": 0.95, "evidence": "Documented across Ethiopian naturals; Yirgacheffe naturals are the reference cup"}},
    {"source": ("Origin", "Ethiopia"), "target": ("FlavorNote", "Jasmine"), "relationship": "TYPICAL_FLAVOR",
     "properties": {"source": "SCA Flavor Wheel", "confidence": 0.92, "evidence": "Hallmark of washed Yirgacheffe; high-altitude varietals"}},
    {"source": ("Origin", "Ethiopia"), "target": ("FlavorNote", "Lemon"), "relationship": "TYPICAL_FLAVOR",
     "properties": {"source": "SCA Flavor Wheel", "confidence": 0.87, "evidence": "Citric acid brightness in washed Sidama and Yirgacheffe profiles"}},
    {"source": ("Origin", "Colombia"), "target": ("FlavorNote", "Caramel"), "relationship": "TYPICAL_FLAVOR",
     "properties": {"source": "SCA Flavor Wheel", "confidence": 0.89, "evidence": "Signature sweetness of Colombian washed Castillo and Caturra"}},
    {"source": ("Origin", "Colombia"), "target": ("FlavorNote", "Orange"), "relationship": "TYPICAL_FLAVOR",
     "properties": {"source": "SCA Flavor Wheel", "confidence": 0.84, "evidence": "Mild citric acidity common in Colombian washed profiles"}},
    {"source": ("Origin", "Colombia"), "target": ("FlavorNote", "Milk Chocolate"), "relationship": "TYPICAL_FLAVOR",
     "properties": {"source": "SCA Flavor Wheel", "confidence": 0.86, "evidence": "Classic creamy cocoa note in Colombian medium roasts"}},
    {"source": ("Origin", "Brazil"), "target": ("FlavorNote", "Dark Chocolate"), "relationship": "TYPICAL_FLAVOR",
     "properties": {"source": "SCA Flavor Wheel", "confidence": 0.93, "evidence": "Defining characteristic of Brazilian natural Arabica"}},
    {"source": ("Origin", "Brazil"), "target": ("FlavorNote", "Hazelnut"), "relationship": "TYPICAL_FLAVOR",
     "properties": {"source": "SCA Flavor Wheel", "confidence": 0.90, "evidence": "Very common in Brazilian yellow bourbon and mundo novo"}},
    {"source": ("Origin", "Brazil"), "target": ("FlavorNote", "Brown Sugar"), "relationship": "TYPICAL_FLAVOR",
     "properties": {"source": "SCA Flavor Wheel", "confidence": 0.88, "evidence": "Low-acid sweetness characteristic of Brazilian pulped naturals"}},
    {"source": ("Origin", "Kenya"), "target": ("FlavorNote", "Blackcurrant"), "relationship": "TYPICAL_FLAVOR",
     "properties": {"source": "SCA Flavor Wheel", "confidence": 0.94, "evidence": "Distinctive SL28/SL34 marker; double-fermentation accentuates this note"}},
    {"source": ("Origin", "Kenya"), "target": ("FlavorNote", "Raspberry"), "relationship": "TYPICAL_FLAVOR",
     "properties": {"source": "SCA Flavor Wheel", "confidence": 0.88, "evidence": "Bright red berry acidity common in washed Kenyan AA and AB grades"}},
    {"source": ("Origin", "Kenya"), "target": ("FlavorNote", "Lemon"), "relationship": "TYPICAL_FLAVOR",
     "properties": {"source": "SCA Flavor Wheel", "confidence": 0.85, "evidence": "Crisp citric acidity from Kenya's double-washed process"}},
    {"source": ("Origin", "Guatemala"), "target": ("FlavorNote", "Dark Chocolate"), "relationship": "TYPICAL_FLAVOR",
     "properties": {"source": "SCA Flavor Wheel", "confidence": 0.88, "evidence": "Classic Antigua and Huehuetenango profile"}},
    {"source": ("Origin", "Guatemala"), "target": ("FlavorNote", "Brown Sugar"), "relationship": "TYPICAL_FLAVOR",
     "properties": {"source": "SCA Flavor Wheel", "confidence": 0.85, "evidence": "Characteristic molasses-like sweetness in Guatemalan Bourbon"}},
    {"source": ("Origin", "Costa Rica"), "target": ("FlavorNote", "Peach"), "relationship": "TYPICAL_FLAVOR",
     "properties": {"source": "SCA Flavor Wheel", "confidence": 0.86, "evidence": "Stone fruit sweetness in Costa Rican honey-processed Catuai"}},
    {"source": ("Origin", "Costa Rica"), "target": ("FlavorNote", "Honey"), "relationship": "TYPICAL_FLAVOR",
     "properties": {"source": "SCA Flavor Wheel", "confidence": 0.84, "evidence": "Honey processing preserves mucilage sugars; clean sweetness in the cup"}},
    {"source": ("Origin", "Indonesia"), "target": ("FlavorNote", "Earthy"), "relationship": "TYPICAL_FLAVOR",
     "properties": {"source": "SCA Flavor Wheel", "confidence": 0.93, "evidence": "Defining characteristic of wet-hulled Sumatran Mandheling and Lintong"}},
    {"source": ("Origin", "Indonesia"), "target": ("FlavorNote", "Dark Chocolate"), "relationship": "TYPICAL_FLAVOR",
     "properties": {"source": "SCA Flavor Wheel", "confidence": 0.82, "evidence": "Dark cocoa notes common in Sulawesi Toraja at medium roast"}},
    {"source": ("Origin", "Yemen"), "target": ("FlavorNote", "Cherry"), "relationship": "TYPICAL_FLAVOR",
     "properties": {"source": "SCA Flavor Wheel", "confidence": 0.88, "evidence": "Dried cherry notes in Yemeni natural Mocha-type heirlooms"}},
    {"source": ("Origin", "Yemen"), "target": ("FlavorNote", "Cinnamon"), "relationship": "TYPICAL_FLAVOR",
     "properties": {"source": "SCA Flavor Wheel", "confidence": 0.85, "evidence": "Spice-forward profiles in Yemeni Haraazi and Mattari"}},

    # --- ProcessMethods -> FlavorNotes (PRODUCES_FLAVOR) ---
    {"source": ("ProcessMethod", "Natural"), "target": ("FlavorNote", "Blueberry"), "relationship": "PRODUCES_FLAVOR",
     "properties": {"source": "Processing Science", "confidence": 0.91, "evidence": "Yeast fermentation of intact cherry produces ethyl esters that read as blueberry"}},
    {"source": ("ProcessMethod", "Natural"), "target": ("FlavorNote", "Dark Chocolate"), "relationship": "PRODUCES_FLAVOR",
     "properties": {"source": "Processing Science", "confidence": 0.86, "evidence": "Extended drying develops pyrazines and furans associated with chocolate"}},
    {"source": ("ProcessMethod", "Natural"), "target": ("FlavorNote", "Cherry"), "relationship": "PRODUCES_FLAVOR",
     "properties": {"source": "Processing Science", "confidence": 0.89, "evidence": "Fermentation of cherry pulp infuses dried stone fruit compounds into the bean"}},
    {"source": ("ProcessMethod", "Washed"), "target": ("FlavorNote", "Jasmine"), "relationship": "PRODUCES_FLAVOR",
     "properties": {"source": "Processing Science", "confidence": 0.82, "evidence": "Clean, mucilage-free drying preserves volatile floral aromatics"}},
    {"source": ("ProcessMethod", "Washed"), "target": ("FlavorNote", "Lemon"), "relationship": "PRODUCES_FLAVOR",
     "properties": {"source": "Processing Science", "confidence": 0.87, "evidence": "Fermentation tank wash highlights origin-specific citric and malic acids"}},
    {"source": ("ProcessMethod", "Honey"), "target": ("FlavorNote", "Peach"), "relationship": "PRODUCES_FLAVOR",
     "properties": {"source": "Processing Science", "confidence": 0.89, "evidence": "Partial mucilage during drying develops lactone compounds that read as stone fruit"}},
    {"source": ("ProcessMethod", "Honey"), "target": ("FlavorNote", "Caramel"), "relationship": "PRODUCES_FLAVOR",
     "properties": {"source": "Processing Science", "confidence": 0.87, "evidence": "Mucilage sugar oxidation during slow drying produces caramelized sweetness"}},
    {"source": ("ProcessMethod", "Anaerobic"), "target": ("FlavorNote", "Cherry"), "relationship": "PRODUCES_FLAVOR",
     "properties": {"source": "Processing Science", "confidence": 0.90, "evidence": "Anaerobic lactic fermentation produces malic acid and cherry-like esters"}},
    {"source": ("ProcessMethod", "Anaerobic"), "target": ("FlavorNote", "Raspberry"), "relationship": "PRODUCES_FLAVOR",
     "properties": {"source": "Processing Science", "confidence": 0.88, "evidence": "Controlled anaerobic fermentation produces raspberry ketone-adjacent compounds"}},

    # --- RoastLevels -> FlavorNotes (ENHANCES, PRODUCES, SUPPRESSES) ---
    {"source": ("RoastLevel", "Light"), "target": ("FlavorNote", "Jasmine"), "relationship": "ENHANCES",
     "properties": {"source": "Roasting Science", "confidence": 0.91, "evidence": "Light development preserves linalool and other floral volatile compounds"}},
    {"source": ("RoastLevel", "Light"), "target": ("FlavorNote", "Blueberry"), "relationship": "ENHANCES",
     "properties": {"source": "Roasting Science", "confidence": 0.89, "evidence": "Minimal Maillard masking allows natural berry esters to dominate"}},
    {"source": ("RoastLevel", "Light"), "target": ("FlavorNote", "Lemon"), "relationship": "ENHANCES",
     "properties": {"source": "Roasting Science", "confidence": 0.88, "evidence": "High chlorogenic acid preservation maintains citric brightness"}},
    {"source": ("RoastLevel", "Medium"), "target": ("FlavorNote", "Caramel"), "relationship": "ENHANCES",
     "properties": {"source": "Roasting Science", "confidence": 0.90, "evidence": "Maillard reaction peaks in medium development, converting sugars to caramel compounds"}},
    {"source": ("RoastLevel", "Medium"), "target": ("FlavorNote", "Milk Chocolate"), "relationship": "ENHANCES",
     "properties": {"source": "Roasting Science", "confidence": 0.88, "evidence": "Medium roast develops cocoa-adjacent pyrazines without bitter phenolic dominance"}},
    {"source": ("RoastLevel", "Medium"), "target": ("FlavorNote", "Brown Sugar"), "relationship": "PRODUCES",
     "properties": {"source": "Roasting Science", "confidence": 0.89, "evidence": "Sucrose degradation at 210-220°C produces furfural and hydroxymethylfurfural (HMF)"}},
    {"source": ("RoastLevel", "Dark"), "target": ("FlavorNote", "Dark Chocolate"), "relationship": "PRODUCES",
     "properties": {"source": "Roasting Science", "confidence": 0.90, "evidence": "Extended Maillard and Strecker degradation builds bitter bittersweet chocolate notes"}},
    {"source": ("RoastLevel", "Dark"), "target": ("FlavorNote", "Tobacco"), "relationship": "PRODUCES",
     "properties": {"source": "Roasting Science", "confidence": 0.88, "evidence": "Pyrolysis of chlorogenic acids and cellulose produces tobacco-like phenolics"}},
    {"source": ("RoastLevel", "Dark"), "target": ("FlavorNote", "Jasmine"), "relationship": "SUPPRESSES",
     "properties": {"source": "Roasting Science", "confidence": 0.92, "evidence": "High-temp pyrolysis destroys linalool and delicate volatile floral esters"}},
    {"source": ("RoastLevel", "Dark"), "target": ("FlavorNote", "Blueberry"), "relationship": "SUPPRESSES",
     "properties": {"source": "Roasting Science", "confidence": 0.91, "evidence": "Extended roast time vaporises light fruit esters before second crack"}},
    {"source": ("RoastLevel", "Dark"), "target": ("FlavorNote", "Lemon"), "relationship": "SUPPRESSES",
     "properties": {"source": "Roasting Science", "confidence": 0.93, "evidence": "Chlorogenic acids fully degrade at dark roast temperatures, eliminating citric brightness"}},
    {"source": ("RoastLevel", "Medium"), "target": ("FlavorNote", "Rose"), "relationship": "SUPPRESSES",
     "properties": {"source": "Roasting Science", "confidence": 0.78, "evidence": "Roast development progressively reduces the most delicate rose-geraniol volatiles"}},

    # --- BrewMethods -> FlavorNotes (EMPHASIZES) ---
    {"source": ("BrewMethod", "V60"), "target": ("FlavorNote", "Jasmine"), "relationship": "EMPHASIZES",
     "properties": {"source": "Brewing Science", "confidence": 0.88, "evidence": "Paper filtration and controlled pour rate highlight delicate aromatics"}},
    {"source": ("BrewMethod", "V60"), "target": ("FlavorNote", "Lemon"), "relationship": "EMPHASIZES",
     "properties": {"source": "Brewing Science", "confidence": 0.87, "evidence": "High extraction clarity makes citric acidity the dominant taste sensation"}},
    {"source": ("BrewMethod", "Espresso"), "target": ("FlavorNote", "Dark Chocolate"), "relationship": "EMPHASIZES",
     "properties": {"source": "Brewing Science", "confidence": 0.91, "evidence": "9-bar pressure concentrates cocoa-linked volatile compounds in the crema"}},
    {"source": ("BrewMethod", "Espresso"), "target": ("FlavorNote", "Caramel"), "relationship": "EMPHASIZES",
     "properties": {"source": "Brewing Science", "confidence": 0.89, "evidence": "High TDS concentration amplifies sweetness perception from caramelized sugars"}},
    {"source": ("BrewMethod", "French Press"), "target": ("FlavorNote", "Earthy"), "relationship": "EMPHASIZES",
     "properties": {"source": "Brewing Science", "confidence": 0.85, "evidence": "Metal mesh allows coffee oils and fine particles into cup, adding body and earthy undertones"}},
    {"source": ("BrewMethod", "French Press"), "target": ("FlavorNote", "Dark Chocolate"), "relationship": "EMPHASIZES",
     "properties": {"source": "Brewing Science", "confidence": 0.84, "evidence": "Full immersion and oil retention enhance heavy cocoa mouthfeel"}},
    {"source": ("BrewMethod", "Cold Brew"), "target": ("FlavorNote", "Dark Chocolate"), "relationship": "EMPHASIZES",
     "properties": {"source": "Brewing Science", "confidence": 0.87, "evidence": "Cold extraction selectively extracts lipids and cocoa-adjacent compounds over acids"}},
    {"source": ("BrewMethod", "Chemex"), "target": ("FlavorNote", "Lemon"), "relationship": "EMPHASIZES",
     "properties": {"source": "Brewing Science", "confidence": 0.86, "evidence": "Thick bonded paper removes oils and fines, producing a very clean acidic cup"}},

    # --- RoastLevels -> BrewParameters (SUGGESTS_TEMP) ---
    {"source": ("RoastLevel", "Light"), "target": ("BrewParameter", "Water Temperature"), "relationship": "SUGGESTS_TEMP",
     "properties": {"source": "SCA Extraction Fundamentals", "confidence": 0.93, "evidence": "Denser cell structure requires 94-96°C for adequate solubility"}},
    {"source": ("RoastLevel", "Medium"), "target": ("BrewParameter", "Water Temperature"), "relationship": "SUGGESTS_TEMP",
     "properties": {"source": "SCA Extraction Fundamentals", "confidence": 0.91, "evidence": "Balanced cell porosity targets 92-94°C for optimal extraction window"}},
    {"source": ("RoastLevel", "Dark"), "target": ("BrewParameter", "Water Temperature"), "relationship": "SUGGESTS_TEMP",
     "properties": {"source": "SCA Extraction Fundamentals", "confidence": 0.91, "evidence": "Porous dark roast cells extract rapidly; 88-92°C prevents bitter over-extraction"}},

    # --- BrewingRules -> BrewParameters (DICTATES) ---
    {"source": ("BrewingRule", "High Temp for Light Roast"), "target": ("BrewParameter", "Water Temperature"), "relationship": "DICTATES",
     "properties": {"source": "Rule derivation", "confidence": 0.93, "evidence": "Rule explicitly targets water_temperature parameter"}},
    {"source": ("BrewingRule", "Lower Temp for Dark Roast"), "target": ("BrewParameter", "Water Temperature"), "relationship": "DICTATES",
     "properties": {"source": "Rule derivation", "confidence": 0.91, "evidence": "Rule explicitly targets water_temperature parameter"}},
    {"source": ("BrewingRule", "Espresso Extraction Window"), "target": ("BrewParameter", "Extraction Time"), "relationship": "DICTATES",
     "properties": {"source": "Rule derivation", "confidence": 0.95, "evidence": "Rule explicitly targets extraction_time parameter"}},
    {"source": ("BrewingRule", "Golden Ratio"), "target": ("BrewParameter", "Brew Ratio"), "relationship": "DICTATES",
     "properties": {"source": "Rule derivation", "confidence": 0.96, "evidence": "Rule explicitly targets brew_ratio parameter"}},
    {"source": ("BrewingRule", "Bloom Pre-Infusion"), "target": ("BrewParameter", "Bloom Time"), "relationship": "DICTATES",
     "properties": {"source": "Rule derivation", "confidence": 0.93, "evidence": "Rule explicitly targets bloom_time parameter"}},
    {"source": ("BrewingRule", "Coarse Grind for Immersion"), "target": ("BrewParameter", "Grind Size"), "relationship": "DICTATES",
     "properties": {"source": "Rule derivation", "confidence": 0.91, "evidence": "Rule explicitly targets grind_size parameter"}},
    {"source": ("BrewingRule", "Fine Grind for Pressure"), "target": ("BrewParameter", "Grind Size"), "relationship": "DICTATES",
     "properties": {"source": "Rule derivation", "confidence": 0.95, "evidence": "Rule explicitly targets grind_size parameter"}},
    {"source": ("BrewingRule", "Espresso Dose-to-Yield Ratio"), "target": ("BrewParameter", "Yield Ratio"), "relationship": "DICTATES",
     "properties": {"source": "Rule derivation", "confidence": 0.94, "evidence": "Rule explicitly targets yield_ratio parameter"}},

    # --- BrewingRules -> BrewMethods (APPLIES_TO) ---
    {"source": ("BrewingRule", "High Temp for Light Roast"), "target": ("BrewMethod", "V60"), "relationship": "APPLIES_TO",
     "properties": {"source": "SCA Brewing Standards", "confidence": 0.93, "evidence": "V60 is the primary filter method for light roast; temp control is critical"}},
    {"source": ("BrewingRule", "High Temp for Light Roast"), "target": ("BrewMethod", "Chemex"), "relationship": "APPLIES_TO",
     "properties": {"source": "SCA Brewing Standards", "confidence": 0.91, "evidence": "Chemex brews light roast with high clarity; temperature accuracy matters"}},
    {"source": ("BrewingRule", "High Temp for Light Roast"), "target": ("BrewMethod", "AeroPress"), "relationship": "APPLIES_TO",
     "properties": {"source": "SCA Brewing Standards", "confidence": 0.87, "evidence": "AeroPress light roast recipes commonly target 94-96°C for full extraction"}},
    {"source": ("BrewingRule", "Lower Temp for Dark Roast"), "target": ("BrewMethod", "Espresso"), "relationship": "APPLIES_TO",
     "properties": {"source": "SCA Brewing Standards", "confidence": 0.92, "evidence": "Dark roast espresso must be pulled at lower temperature to avoid acrid bitterness"}},
    {"source": ("BrewingRule", "Lower Temp for Dark Roast"), "target": ("BrewMethod", "French Press"), "relationship": "APPLIES_TO",
     "properties": {"source": "SCA Brewing Standards", "confidence": 0.86, "evidence": "Dark roast immersion also benefits from cooler water to limit over-extraction"}},
    {"source": ("BrewingRule", "Espresso Extraction Window"), "target": ("BrewMethod", "Espresso"), "relationship": "APPLIES_TO",
     "properties": {"source": "SCA Espresso Standards", "confidence": 1.0, "evidence": "This rule is exclusively defined for espresso"}},
    {"source": ("BrewingRule", "Espresso Dose-to-Yield Ratio"), "target": ("BrewMethod", "Espresso"), "relationship": "APPLIES_TO",
     "properties": {"source": "WBC Scoring Framework", "confidence": 0.95, "evidence": "Yield ratio is a core espresso parameter with no equivalent in filter methods"}},
    {"source": ("BrewingRule", "Golden Ratio"), "target": ("BrewMethod", "V60"), "relationship": "APPLIES_TO",
     "properties": {"source": "SCA Golden Cup", "confidence": 0.97, "evidence": "V60 is the canonical filter method for the SCA golden cup standard"}},
    {"source": ("BrewingRule", "Golden Ratio"), "target": ("BrewMethod", "Chemex"), "relationship": "APPLIES_TO",
     "properties": {"source": "SCA Golden Cup", "confidence": 0.96, "evidence": "Chemex follows the same filter brew ratio guidelines"}},
    {"source": ("BrewingRule", "Golden Ratio"), "target": ("BrewMethod", "French Press"), "relationship": "APPLIES_TO",
     "properties": {"source": "SCA Golden Cup", "confidence": 0.93, "evidence": "French press ratio typically targets 1:15 within the golden range"}},
    {"source": ("BrewingRule", "Golden Ratio"), "target": ("BrewMethod", "AeroPress"), "relationship": "APPLIES_TO",
     "properties": {"source": "SCA Golden Cup", "confidence": 0.88, "evidence": "AeroPress recipes often start at 1:15 ratio as a baseline"}},
    {"source": ("BrewingRule", "Bloom Pre-Infusion"), "target": ("BrewMethod", "V60"), "relationship": "APPLIES_TO",
     "properties": {"source": "Barista Hustle", "confidence": 0.98, "evidence": "Bloom is standard and essential practice in V60 brewing"}},
    {"source": ("BrewingRule", "Bloom Pre-Infusion"), "target": ("BrewMethod", "Chemex"), "relationship": "APPLIES_TO",
     "properties": {"source": "Barista Hustle", "confidence": 0.97, "evidence": "Bloom technique is equally critical for Chemex due to its thick filter"}},
    {"source": ("BrewingRule", "Fine Grind for Pressure"), "target": ("BrewMethod", "Espresso"), "relationship": "APPLIES_TO",
     "properties": {"source": "Espresso Science", "confidence": 0.97, "evidence": "Espresso requires fine grind to achieve 9-bar resistance in 25-35s"}},
    {"source": ("BrewingRule", "Coarse Grind for Immersion"), "target": ("BrewMethod", "French Press"), "relationship": "APPLIES_TO",
     "properties": {"source": "Immersion Brewing", "confidence": 0.93, "evidence": "French Press 4-minute steep requires coarse grind to avoid bitterness"}},
    {"source": ("BrewingRule", "Coarse Grind for Immersion"), "target": ("BrewMethod", "Cold Brew"), "relationship": "APPLIES_TO",
     "properties": {"source": "Immersion Brewing", "confidence": 0.94, "evidence": "Cold Brew 12-24h steep requires extra coarse grind to prevent over-extraction"}},

    # --- EquipmentTypes -> GrindProfiles (PRODUCES) ---
    {"source": ("EquipmentType", "Flat Burr Grinder"), "target": ("GrindProfile", "Unimodal"), "relationship": "PRODUCES",
     "properties": {"source": "Grinder Engineering", "confidence": 0.88, "evidence": "Flat burr geometry shears particles to a narrow, single-peak distribution"}},
    {"source": ("EquipmentType", "Conical Burr Grinder"), "target": ("GrindProfile", "Bimodal"), "relationship": "PRODUCES",
     "properties": {"source": "Grinder Engineering", "confidence": 0.86, "evidence": "Conical burr crushing action produces coarse particles with a secondary fine population"}},

    # --- EquipmentTypes -> BrewMethods (PAIRS_WITH) ---
    {"source": ("EquipmentType", "PID Espresso Machine"), "target": ("BrewMethod", "Espresso"), "relationship": "PAIRS_WITH",
     "properties": {"source": "Equipment Guide", "confidence": 1.0, "evidence": "PID machine is the primary vessel for espresso; temperature precision is its core advantage"}},
    {"source": ("EquipmentType", "Non-PID Espresso Machine"), "target": ("BrewMethod", "Espresso"), "relationship": "PAIRS_WITH",
     "properties": {"source": "Equipment Guide", "confidence": 0.90, "evidence": "Non-PID machines brew espresso successfully with temperature surfing technique"}},

    # --- BrewMethods -> GrindProfiles (PAIRS_WITH) ---
    {"source": ("BrewMethod", "Espresso"), "target": ("GrindProfile", "Bimodal"), "relationship": "PAIRS_WITH",
     "properties": {"source": "Espresso Puck Science", "confidence": 0.84, "evidence": "Bimodal fines fill puck voids, increasing resistance and extraction evenness in traditional espresso"}},
    {"source": ("BrewMethod", "V60"), "target": ("GrindProfile", "Unimodal"), "relationship": "PAIRS_WITH",
     "properties": {"source": "Filter Brewing Science", "confidence": 0.87, "evidence": "Unimodal distribution produces even flow rate through the V60 bed and high cup clarity"}},
    {"source": ("BrewMethod", "Chemex"), "target": ("GrindProfile", "Unimodal"), "relationship": "PAIRS_WITH",
     "properties": {"source": "Filter Brewing Science", "confidence": 0.86, "evidence": "Chemex thick filter already slows flow; unimodal grind prevents clogging and ensures even extraction"}},
    {"source": ("BrewMethod", "Cold Brew"), "target": ("GrindProfile", "Unimodal"), "relationship": "PAIRS_WITH",
     "properties": {"source": "Cold Brew Science", "confidence": 0.80, "evidence": "Uniform particle size ensures consistent slow extraction across the long cold-steep window"}},

    # --- Origins -> BrewMethods (PAIRS_WITH) ---
    {"source": ("Origin", "Ethiopia"), "target": ("BrewMethod", "V60"), "relationship": "PAIRS_WITH",
     "properties": {"source": "Specialty Coffee Curation", "confidence": 0.91, "evidence": "V60 high clarity expresses Ethiopian floral and berry notes without masking"}},
    {"source": ("Origin", "Brazil"), "target": ("BrewMethod", "Espresso"), "relationship": "PAIRS_WITH",
     "properties": {"source": "Specialty Coffee Curation", "confidence": 0.90, "evidence": "Brazilian low-acid naturals are the classic espresso base bean for body and chocolate"}},
    {"source": ("Origin", "Kenya"), "target": ("BrewMethod", "V60"), "relationship": "PAIRS_WITH",
     "properties": {"source": "Specialty Coffee Curation", "confidence": 0.89, "evidence": "Kenyan bright acidity and blackcurrant notes shine in high-clarity pour over"}},
    {"source": ("Origin", "Indonesia"), "target": ("BrewMethod", "French Press"), "relationship": "PAIRS_WITH",
     "properties": {"source": "Specialty Coffee Curation", "confidence": 0.87, "evidence": "French Press full-immersion and metal filter complement Indonesian earthy, full-body profile"}},
    {"source": ("Origin", "Colombia"), "target": ("BrewMethod", "AeroPress"), "relationship": "PAIRS_WITH",
     "properties": {"source": "Specialty Coffee Curation", "confidence": 0.85, "evidence": "Colombian balanced profile adapts well to AeroPress versatility across ratios and temps"}},

    # =========================================================================
    # NEW EDGES — using the 8 new relationship types
    # =========================================================================

    # --- SUB_REGION_OF: geographic hierarchy ---
    # Every Region must have exactly one SUB_REGION_OF edge to its parent.
    # This enables queries like "what regions are within Ethiopia?" by
    # traversing inbound SUB_REGION_OF edges on the Origin node.
    {"source": ("Region", "Yirgacheffe"), "target": ("Origin", "Ethiopia"), "relationship": "SUB_REGION_OF",
     "properties": {"source": "World Atlas of Coffee", "confidence": 0.99, "evidence": "Yirgacheffe is a woreda within the SNNPR of Ethiopia"}},
    {"source": ("Region", "Sidama"), "target": ("Origin", "Ethiopia"), "relationship": "SUB_REGION_OF",
     "properties": {"source": "World Atlas of Coffee", "confidence": 0.99, "evidence": "Sidama is a regional state in southern Ethiopia"}},
    {"source": ("Region", "Huila"), "target": ("Origin", "Colombia"), "relationship": "SUB_REGION_OF",
     "properties": {"source": "World Atlas of Coffee", "confidence": 0.99, "evidence": "Huila is a department in the Andean coffee region of Colombia"}},
    {"source": ("Region", "Cerrado"), "target": ("Origin", "Brazil"), "relationship": "SUB_REGION_OF",
     "properties": {"source": "World Atlas of Coffee", "confidence": 0.99, "evidence": "Cerrado Mineiro is a defined coffee-producing region in Minas Gerais, Brazil"}},
    {"source": ("Region", "Antigua"), "target": ("Origin", "Guatemala"), "relationship": "SUB_REGION_OF",
     "properties": {"source": "World Atlas of Coffee", "confidence": 0.99, "evidence": "Antigua is a coffee-producing region in Sacatepéquez department, Guatemala"}},

    # --- GROWN_IN: cultivar geography ---
    # One cultivar can have multiple GROWN_IN edges. The cup profile differs
    # per terroir — that nuance lives in the edge properties, not the Cultivar node.
    {"source": ("Cultivar", "Gesha"), "target": ("Origin", "Ethiopia"), "relationship": "GROWN_IN",
     "properties": {"source": "Scott Rao — Coffee Roaster's Companion", "confidence": 0.97, "evidence": "Gesha originated in the Gesha village, Kaffa zone, Ethiopia"}},
    {"source": ("Cultivar", "SL28"), "target": ("Origin", "Kenya"), "relationship": "GROWN_IN",
     "properties": {"source": "World Atlas of Coffee", "confidence": 0.98, "evidence": "SL28 is almost exclusively grown in Kenya; occasionally in other East African origins"}},
    {"source": ("Cultivar", "Bourbon"), "target": ("Origin", "Colombia"), "relationship": "GROWN_IN",
     "properties": {"source": "World Atlas of Coffee", "confidence": 0.92, "evidence": "Bourbon is widely cultivated across Colombian coffee farms alongside Castillo and Caturra"}},
    {"source": ("Cultivar", "Bourbon"), "target": ("Origin", "Guatemala"), "relationship": "GROWN_IN",
     "properties": {"source": "World Atlas of Coffee", "confidence": 0.93, "evidence": "Bourbon and Typica are the historic cultivars of Guatemalan specialty coffee"}},
    {"source": ("Cultivar", "Catuai"), "target": ("Origin", "Brazil"), "relationship": "GROWN_IN",
     "properties": {"source": "World Atlas of Coffee", "confidence": 0.96, "evidence": "Catuai is the dominant cultivar planted across most Brazilian coffee-growing regions"}},

    # --- TYPICAL_FLAVOR from Cultivars and Regions ---
    # These are more specific than Origin → TYPICAL_FLAVOR because they pin
    # the flavor to a specific genetic line or terroir, not the whole country.
    {"source": ("Cultivar", "Gesha"), "target": ("FlavorNote", "Jasmine"), "relationship": "TYPICAL_FLAVOR",
     "properties": {"source": "SCA Flavor Wheel / Competition records", "confidence": 0.96, "evidence": "Jasmine aroma is the single most cited characteristic of Gesha in cupping notes globally"}},
    {"source": ("Cultivar", "Gesha"), "target": ("FlavorNote", "Rose"), "relationship": "TYPICAL_FLAVOR",
     "properties": {"source": "SCA Flavor Wheel", "confidence": 0.88, "evidence": "Rose is frequently noted alongside jasmine in Gesha — both are linalool-driven floral aromatics"}},
    {"source": ("Cultivar", "SL28"), "target": ("FlavorNote", "Blackcurrant"), "relationship": "TYPICAL_FLAVOR",
     "properties": {"source": "World Atlas of Coffee", "confidence": 0.95, "evidence": "Blackcurrant is considered the signature taste marker of SL28 across all Kenyan growing regions"}},
    {"source": ("Region", "Yirgacheffe"), "target": ("FlavorNote", "Jasmine"), "relationship": "TYPICAL_FLAVOR",
     "properties": {"source": "World Atlas of Coffee", "confidence": 0.94, "evidence": "Washed Yirgacheffe is the global reference for jasmine-forward coffee"}},
    {"source": ("Region", "Yirgacheffe"), "target": ("FlavorNote", "Lemon"), "relationship": "TYPICAL_FLAVOR",
     "properties": {"source": "World Atlas of Coffee", "confidence": 0.91, "evidence": "High citric acid expression is characteristic of high-altitude Yirgacheffe washed lots"}},
    {"source": ("Region", "Sidama"), "target": ("FlavorNote", "Blueberry"), "relationship": "TYPICAL_FLAVOR",
     "properties": {"source": "World Atlas of Coffee", "confidence": 0.88, "evidence": "Sidama naturals are known for jammy blueberry notes, often compared to Yirgacheffe but heavier"}},
    {"source": ("Region", "Huila"), "target": ("FlavorNote", "Caramel"), "relationship": "TYPICAL_FLAVOR",
     "properties": {"source": "World Atlas of Coffee", "confidence": 0.87, "evidence": "Huila washed coffees consistently show clean caramel sweetness with tropical fruit undertones"}},

    # --- CAUSES: defect cascade and chemistry-to-defect ---
    # These edges are what the diagnosis engine traverses when a shot tastes wrong.
    # Channeling → Astringency: channeling creates over-extracted pockets
    # that read as astringent dryness.
    {"source": ("Defect", "Channeling"), "target": ("Defect", "Astringency"), "relationship": "CAUSES",
     "properties": {"source": "Scott Rao — The Professional Barista's Handbook", "confidence": 0.91, "evidence": "Channeling produces locally over-extracted streams; the phenolic compounds in those areas register as astringency"}},
    # Chlorogenic Acid → Astringency: the chemistry underpinning why under-roasted
    # or very light roast coffees can taste harsh.
    {"source": ("SensoryDescriptor", "Chlorogenic Acid"), "target": ("Defect", "Astringency"), "relationship": "CAUSES",
     "properties": {"source": "Rao — Coffee Roaster's Companion; SCA Research", "confidence": 0.88, "evidence": "Chlorogenic acids at high concentrations (under-roasted coffee) bind salivary proteins, causing the dry astringent mouthfeel"}},
    # Sour Ferment → Earthy: fermentation-gone-wrong introduces microbial
    # compounds that often read as earthy or musty rather than clean fruit.
    {"source": ("Defect", "Sour Ferment"), "target": ("FlavorNote", "Earthy"), "relationship": "CAUSES",
     "properties": {"source": "SCA Green Coffee Processing Module", "confidence": 0.78, "evidence": "Over-fermentation introduces Bacillus and mould compounds that often co-present as earthy mustiness alongside the vinegar note"}},

    # --- PREVENTS: technique/rule → defect mitigation ---
    # WDT is the primary mechanical fix for channeling.
    # Bloom Pre-Infusion prevents Grassy by ensuring the full brew water
    # contacts the grounds (un-bloomed brews often taste flat or raw).
    {"source": ("BrewingTechnique", "WDT"), "target": ("Defect", "Channeling"), "relationship": "PREVENTS",
     "properties": {"source": "Scott Rao — The Professional Barista's Handbook", "confidence": 0.93, "evidence": "WDT physically disrupts clumps that create preferential flow paths; the most widely recommended channeling prevention technique"}},
    {"source": ("BrewingRule", "Bloom Pre-Infusion"), "target": ("Defect", "Grassy"), "relationship": "PREVENTS",
     "properties": {"source": "SCA Brewing Standards; Barista Hustle", "confidence": 0.80, "evidence": "Proper bloom fully wets the coffee bed; skipping bloom in fresh coffee causes CO2 pockets that result in uneven, under-extracted (grassy) patches"}},

    # --- REFINES: technique → method ---
    # REFINES is directional: the technique is a specialisation that improves
    # the method. The method still works without the technique — the technique
    # just makes it better.
    {"source": ("BrewingTechnique", "WDT"), "target": ("BrewMethod", "Espresso"), "relationship": "REFINES",
     "properties": {"source": "Scott Rao — The Professional Barista's Handbook", "confidence": 0.94, "evidence": "WDT is an espresso-specific puck prep step that improves consistency by preventing channeling"}},
    {"source": ("BrewingTechnique", "Rao Spin"), "target": ("BrewMethod", "Espresso"), "relationship": "REFINES",
     "properties": {"source": "Scott Rao", "confidence": 0.85, "evidence": "Post-pull cup agitation integrates crema stratification, producing a more uniform sweetness-forward flavour"}},
    {"source": ("BrewingTechnique", "Japanese Ice Method"), "target": ("BrewMethod", "V60"), "relationship": "REFINES",
     "properties": {"source": "James Hoffmann — World Atlas of Coffee", "confidence": 0.88, "evidence": "Flash-chilling onto ice preserves volatile aromatics while achieving cold serving temp; V60 is the most common vessel for this technique"}},
    {"source": ("BrewingTechnique", "Bypass Brewing"), "target": ("BrewMethod", "V60"), "relationship": "REFINES",
     "properties": {"source": "James Hoffmann", "confidence": 0.83, "evidence": "Bypass dilution applied to V60 improves extraction evenness at the expense of slightly more complexity versus direct-ratio brewing"}},
    {"source": ("BrewingTechnique", "Blooming AeroPress"), "target": ("BrewMethod", "AeroPress"), "relationship": "REFINES",
     "properties": {"source": "World AeroPress Championship community recipes", "confidence": 0.87, "evidence": "Adding a bloom phase to AeroPress degasses CO2, improving even extraction across the puck"}},

    # --- SOURCED_FROM: provenance tracking ---
    # Every rule or technique from a book gets a SOURCED_FROM edge.
    # This is what lets the system say 'according to Scott Rao...' rather than
    # presenting all knowledge as equally authoritative.
    {"source": ("BrewingTechnique", "WDT"), "target": ("Expert", "Scott Rao"), "relationship": "SOURCED_FROM",
     "properties": {"source": "attribution", "confidence": 0.95, "evidence": "Scott Rao popularised and named WDT in the specialty community"}},
    {"source": ("BrewingTechnique", "Rao Spin"), "target": ("Expert", "Scott Rao"), "relationship": "SOURCED_FROM",
     "properties": {"source": "attribution", "confidence": 0.99, "evidence": "Rao Spin is named directly after Scott Rao who described and promoted the technique"}},
    {"source": ("BrewingTechnique", "Bypass Brewing"), "target": ("Expert", "James Hoffmann"), "relationship": "SOURCED_FROM",
     "properties": {"source": "attribution", "confidence": 0.90, "evidence": "James Hoffmann is the most prominent advocate of bypass dilution for filter clarity"}},
    {"source": ("BrewingRule", "Bypass Dilution for Clarity"), "target": ("Expert", "James Hoffmann"), "relationship": "SOURCED_FROM",
     "properties": {"source": "attribution", "confidence": 0.90, "evidence": "The bypass dilution rule is sourced from Hoffmann's published methodology"}},
    {"source": ("BrewingRule", "High Temp for Light Roast"), "target": ("Expert", "SCA"), "relationship": "SOURCED_FROM",
     "properties": {"source": "attribution", "confidence": 0.93, "evidence": "SCA Brewing Standards specify 90-96°C as the target range for filter brewing, with higher end recommended for light roasts"}},
    {"source": ("BrewingRule", "Espresso Extraction Window"), "target": ("Expert", "World Barista Championship"), "relationship": "SOURCED_FROM",
     "properties": {"source": "attribution", "confidence": 0.97, "evidence": "WBC judging criteria define 25-35s as the acceptable espresso extraction window"}},

    # --- CONFLICTS_WITH: honest disagreement ---
    # Bypass Dilution for Clarity vs. Golden Ratio is a genuine philosophical
    # conflict: brew-to-target TDS directly (Golden Ratio) vs.
    # brew-strong-then-dilute (Bypass). Both produce good coffee.
    # Recording the conflict lets the system present both options rather than
    # arbitrarily picking one as 'correct'.
    {"source": ("BrewingRule", "Bypass Dilution for Clarity"), "target": ("BrewingRule", "Golden Ratio"), "relationship": "CONFLICTS_WITH",
     "properties": {"source": "comparative analysis", "confidence": 0.80,
                    "evidence": "Golden Ratio brews directly to target ratio (1:15-1:17). Bypass Dilution brews at 1:8-1:10 then dilutes. Both reach similar TDS but via different processes, producing different extraction dynamics and flavour profiles."}},

    # --- MANIFESTS_AS: chemistry → perception ---
    # These edges are what allow the system to answer 'why does this coffee
    # taste like lemon?' with a traceable chemical explanation.
    {"source": ("SensoryDescriptor", "Malic Acid"), "target": ("FlavorNote", "Lemon"), "relationship": "MANIFESTS_AS",
     "properties": {"source": "SCA Sensory Lexicon; Rao — Coffee Roaster's Companion", "confidence": 0.88, "evidence": "Malic acid is the primary contributor to tart apple-lemon acidity in washed high-altitude coffees"}},
    {"source": ("SensoryDescriptor", "Citric Acid"), "target": ("FlavorNote", "Orange"), "relationship": "MANIFESTS_AS",
     "properties": {"source": "SCA Sensory Lexicon", "confidence": 0.91, "evidence": "Citric acid produces the clean orange-citrus brightness that is the most common perceived acidity type in Arabica"}},
    {"source": ("SensoryDescriptor", "Phosphoric Acid"), "target": ("FlavorNote", "Lemon"), "relationship": "MANIFESTS_AS",
     "properties": {"source": "SCA Research; Maxwell Colonna-Dashwood — Water for Coffee", "confidence": 0.82, "evidence": "Phosphoric acid contributes a very clean, transparent acidity that presents as bright lemon or citrus clarity without specific fruit character"}},
    {"source": ("SensoryDescriptor", "Chlorogenic Acid"), "target": ("FlavorNote", "Earthy"), "relationship": "MANIFESTS_AS",
     "properties": {"source": "Rao — Coffee Roaster's Companion", "confidence": 0.75, "evidence": "At high concentrations (very light or under-roasted coffees), chlorogenic acids contribute a green, earthy astringency alongside their bitterness"}},
]
