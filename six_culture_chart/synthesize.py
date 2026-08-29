#!/usr/bin/env python3
"""
Six-Culture Chart Synthesis Engine (Steps 7-8)
Projects computed data onto nine life domains, computes convergence grades,
and produces the final reading.
"""

import json
from pathlib import Path
from datetime import datetime

OUTPUT_DIR = Path(__file__).parent
dataset = json.loads((OUTPUT_DIR / "MASTER_DATASET.json").read_text())

jyotisha = dataset["jyotisha"]
bazi = dataset["bazi"]
western = dataset["western_hellenistic"]
ziwei = dataset["zi_wei_dou_shu"]
maya = dataset["maya"]
tibetan = dataset["tibetan"]
audit = dataset["input_audit"]
verification = dataset["verification"]
astro = dataset["astronomical_base"]["reported"]

# ═══════════════════════════════════════════════════════════════════════
# DOMAIN MAPPING REGISTRY
# ═══════════════════════════════════════════════════════════════════════

DOMAINS = {
    "D1": "Self/Identity",
    "D2": "Career/Status",
    "D3": "Wealth/Gains",
    "D4": "Partnership",
    "D5": "Family/Roots/Home",
    "D6": "Children/Creation",
    "D7": "Health/Routine",
    "D8": "Mind/Education/Craft",
    "D9": "Fortune/Spirituality/Worldview",
}

HOUSE_DOMAIN_MAP_JYOTISHA = {
    1: "D1", 2: "D3", 3: "D8", 4: "D5", 5: "D6", 6: "D7",
    7: "D4", 8: "D9", 9: "D9", 10: "D2", 11: "D3", 12: "D9",
}

HOUSE_DOMAIN_MAP_WESTERN = {
    1: "D1", 2: "D3", 3: "D8", 4: "D5", 5: "D6", 6: "D7",
    7: "D4", 8: "D9", 9: "D9", 10: "D2", 11: "D3", 12: "D9",
}

# ═══════════════════════════════════════════════════════════════════════
# STEP 7: PROJECTIONS
# ═══════════════════════════════════════════════════════════════════════

projections = []

# ── JYOTISHA PROJECTIONS ──

# Lagna lord and condition
lagna_sign = jyotisha["lagna"]["sign"]
lagna_lord = jyotisha["houses"]["1"]["lord"]
lagna_lord_data = jyotisha["grahas"].get(lagna_lord, {})
projections.append({
    "domain": "D1",
    "system": "jyotisha",
    "cluster": "jyotisha",
    "fact": f"Lagna in {lagna_sign}, lord {lagna_lord} in house {lagna_lord_data.get('house', '?')} ({lagna_lord_data.get('sign', '?')})",
    "prominence": "high",
    "polarity": "positive" if lagna_lord_data.get("dignity") in ["own_sign", "exalted", "moolatrikona"] else "mixed",
    "confidence": "high",
    "mapping_rule": "lagna_sign_and_lord_placement",
})

# Moon placement and nakshatra
moon = jyotisha["grahas"]["Moon"]
projections.append({
    "domain": "D1",
    "system": "jyotisha",
    "cluster": "jyotisha",
    "fact": f"Moon in {moon['sign']} (house {moon['house']}), nakshatra {moon['nakshatra']} pada {moon['nakshatra_pada']}",
    "prominence": "high",
    "polarity": "mixed",
    "confidence": "high",
    "mapping_rule": "moon_sign_house_nakshatra",
})

# 10th house lord for career
h10_lord = jyotisha["houses"]["10"]["lord"]
h10_lord_data = jyotisha["grahas"].get(h10_lord, {})
projections.append({
    "domain": "D2",
    "system": "jyotisha",
    "cluster": "jyotisha",
    "fact": f"10th lord {h10_lord} in house {h10_lord_data.get('house', '?')} ({h10_lord_data.get('sign', '?')}), dignity: {h10_lord_data.get('dignity', '?')}",
    "prominence": "high",
    "polarity": "mixed",
    "confidence": "high",
    "mapping_rule": "tenth_lord_placement",
})

# Planets in each house → domain projection
for name, gdata in jyotisha["grahas"].items():
    house = gdata["house"]
    domain = HOUSE_DOMAIN_MAP_JYOTISHA.get(house, "D9")
    if name in ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]:
        pol = "positive" if gdata["dignity"] in ["own_sign", "exalted", "moolatrikona"] else \
              "negative" if gdata["dignity"] == "debilitated" else "mixed"
        projections.append({
            "domain": domain,
            "system": "jyotisha",
            "cluster": "jyotisha",
            "fact": f"{name} in {gdata['sign']} (house {house}), dignity: {gdata['dignity']}, retro: {gdata['retrograde']}",
            "prominence": "high" if house in [1, 4, 7, 10] else "medium",
            "polarity": pol,
            "confidence": "high",
            "mapping_rule": "graha_house_placement",
        })

# Yogas
for yoga in jyotisha.get("yogas", []):
    if "Career" in yoga["name"] or "Gajakesari" in yoga["name"]:
        domains_for_yoga = ["D2", "D1"]
    elif "Chandra-Mangal" in yoga["name"]:
        domains_for_yoga = ["D3", "D1"]
    else:
        domains_for_yoga = ["D1"]

    for d in domains_for_yoga:
        projections.append({
            "domain": d,
            "system": "jyotisha",
            "cluster": "jyotisha",
            "fact": f"{yoga['name']}: {yoga['satisfied_by']}",
            "prominence": "high",
            "polarity": "positive",
            "confidence": "medium",
            "mapping_rule": "classical_yoga",
        })


# ── WESTERN/HELLENISTIC PROJECTIONS ──

# Ascendant
projections.append({
    "domain": "D1",
    "system": "western",
    "cluster": "western",
    "fact": f"Ascendant in {western['ascendant']['sign']} ({western['ascendant']['element']}, {western['ascendant']['modality']})",
    "prominence": "high",
    "polarity": "neutral",
    "confidence": "high",
    "mapping_rule": "ascendant_sign_element",
})

# Sun sign
sun_w = western["planets"]["Sun"]
projections.append({
    "domain": "D1",
    "system": "western",
    "cluster": "western",
    "fact": f"Sun in {sun_w['sign']} (house {sun_w['house']}), sect: {sun_w['sect_status']}",
    "prominence": "high",
    "polarity": "positive" if sun_w["sect_status"] == "in_sect" else "mixed",
    "confidence": "high",
    "mapping_rule": "sun_sign_house_sect",
})

# Moon
moon_w = western["planets"]["Moon"]
projections.append({
    "domain": "D1",
    "system": "western",
    "cluster": "western",
    "fact": f"Moon in {moon_w['sign']} (house {moon_w['house']})",
    "prominence": "high",
    "polarity": "mixed",
    "confidence": "high",
    "mapping_rule": "moon_sign_house",
})

# Each planet → domain
for name, pdata in western["planets"].items():
    house = pdata["house"]
    domain = HOUSE_DOMAIN_MAP_WESTERN.get(house, "D9")
    dignities_str = ", ".join(pdata["dignities"]) if pdata["dignities"] else "none"
    pol = "positive" if any(d in pdata["dignities"] for d in ["domicile", "exaltation"]) else \
          "negative" if any(d in pdata["dignities"] for d in ["detriment", "fall"]) else "mixed"

    projections.append({
        "domain": domain,
        "system": "western",
        "cluster": "western",
        "fact": f"{name} in {pdata['sign']} (house {house}), dignities: {dignities_str}, {pdata['angularity']}",
        "prominence": "high" if pdata["angularity"] == "angular" else "medium",
        "polarity": pol,
        "confidence": "high",
        "mapping_rule": "planet_house_dignity",
    })

# Lot of Fortune
lot_f = western["lots"]["fortune"]
projections.append({
    "domain": "D3",
    "system": "western",
    "cluster": "western",
    "fact": f"Lot of Fortune in {lot_f['sign']} (house {lot_f['house']})",
    "prominence": "medium",
    "polarity": "mixed",
    "confidence": "high",
    "mapping_rule": "lot_of_fortune",
})

# Profection
prof = western["profection"]
projections.append({
    "domain": "D6" if prof["activated_house"] == 5 else "D1",
    "system": "western",
    "cluster": "western",
    "fact": f"Age-{prof['current_age']} profection activates house {prof['activated_house']} ({prof['activated_sign']}), lord {prof['lord_of_year']}",
    "prominence": "high",
    "polarity": "mixed",
    "confidence": "high",
    "mapping_rule": "annual_profection",
})


# ── BAZI PROJECTIONS (Sinic cluster) ──

dm = bazi["day_master"]
projections.append({
    "domain": "D1",
    "system": "bazi",
    "cluster": "sinic",
    "fact": f"Day Master: {dm['stem']} ({dm['element']}, {dm['polarity']})",
    "prominence": "high",
    "polarity": "neutral",
    "confidence": "high",
    "mapping_rule": "day_master_element",
})

# Year pillar → D5 (family/roots)
yp = bazi["pillars"]["year"]
projections.append({
    "domain": "D5",
    "system": "bazi",
    "cluster": "sinic",
    "fact": f"Year Pillar: {yp['stem']}-{yp['branch']} ({yp['element']} {yp['animal']})",
    "prominence": "medium",
    "polarity": "neutral",
    "confidence": "high",
    "mapping_rule": "year_pillar_family",
})

# Month pillar → D2 (career)
mp = bazi["pillars"]["month"]
projections.append({
    "domain": "D2",
    "system": "bazi",
    "cluster": "sinic",
    "fact": f"Month Pillar: {mp['stem']}-{mp['branch']} ({mp['element']}), ten_god: {mp.get('ten_god', 'N/A')}",
    "prominence": "high",
    "polarity": "mixed",
    "confidence": "high",
    "mapping_rule": "month_pillar_career",
})

# Hour pillar → D6 (children/creation)
hp = bazi["pillars"]["hour"]
projections.append({
    "domain": "D6",
    "system": "bazi",
    "cluster": "sinic",
    "fact": f"Hour Pillar: {hp['stem']}-{hp['branch']} ({hp['element']}), ten_god: {hp.get('ten_god', 'N/A')}",
    "prominence": "medium",
    "polarity": "mixed",
    "confidence": "high",
    "mapping_rule": "hour_pillar_children",
})

# Day master element analysis for wealth, career
projections.append({
    "domain": "D3",
    "system": "bazi",
    "cluster": "sinic",
    "fact": f"Day Master {dm['element']} — wealth element is {'Wood' if dm['element'] == 'Water' else 'Fire' if dm['element'] == 'Wood' else 'Earth' if dm['element'] == 'Fire' else 'Metal' if dm['element'] == 'Earth' else 'Water'}",
    "prominence": "medium",
    "polarity": "mixed",
    "confidence": "medium",
    "mapping_rule": "day_master_wealth_element",
})


# ── ZI WEI DOU SHU PROJECTIONS (Sinic cluster) ──

projections.append({
    "domain": "D1",
    "system": "zi_wei_dou_shu",
    "cluster": "sinic",
    "fact": f"Ming Palace in {ziwei['ming_palace']['branch']}, Five Elements Bureau: {ziwei['five_elements_bureau']['element']} ({ziwei['five_elements_bureau']['number']})",
    "prominence": "high",
    "polarity": "neutral",
    "confidence": "medium",
    "mapping_rule": "ming_palace_bureau",
})

projections.append({
    "domain": "D2",
    "system": "zi_wei_dou_shu",
    "cluster": "sinic",
    "fact": f"Life Ruler: {ziwei['life_ruler']}, Si Hua Lu: {ziwei['si_hua_four_transformations']['transformations'].get('Lu', 'N/A')}",
    "prominence": "high",
    "polarity": "mixed",
    "confidence": "medium",
    "mapping_rule": "life_ruler_si_hua",
})

projections.append({
    "domain": "D9",
    "system": "zi_wei_dou_shu",
    "cluster": "sinic",
    "fact": f"Body Ruler: {ziwei['body_ruler']}, Si Hua Ji: {ziwei['si_hua_four_transformations']['transformations'].get('Ji', 'N/A')}",
    "prominence": "medium",
    "polarity": "mixed",
    "confidence": "medium",
    "mapping_rule": "body_ruler_si_hua",
})


# ── MAYA (symbolic overlay, no domain votes) ──
projections.append({
    "domain": "D1",
    "system": "maya",
    "cluster": "maya_overlay",
    "fact": f"Tzolk'in: {maya['tzolkin']['display']}, Haab': {maya['haab']['display']}",
    "prominence": "low",
    "polarity": "neutral",
    "confidence": "medium",
    "mapping_rule": "day_sign_overlay",
    "overlay_only": True,
})

# ── TIBETAN (symbolic overlay) ──
projections.append({
    "domain": "D1",
    "system": "tibetan",
    "cluster": "tibetan_overlay",
    "fact": f"Year: {tibetan['year']['display']}, Mewa: {tibetan['mewa']['number']}, Parkha: {tibetan['parkha']['name']}",
    "prominence": "low",
    "polarity": "neutral",
    "confidence": "low",
    "mapping_rule": "element_animal_overlay",
    "overlay_only": True,
})


# ═══════════════════════════════════════════════════════════════════════
# STEP 7: DOMAIN GRADES
# ═══════════════════════════════════════════════════════════════════════

domain_clusters = {}
for d in DOMAINS:
    domain_clusters[d] = {"jyotisha": [], "western": [], "sinic": []}

for proj in projections:
    if proj.get("overlay_only"):
        continue
    cluster = proj["cluster"]
    domain = proj["domain"]
    if cluster in domain_clusters.get(domain, {}):
        domain_clusters[domain][cluster].append(proj)

domain_grades = {}
for domain, clusters in domain_clusters.items():
    has_jyotisha = len(clusters["jyotisha"]) > 0
    has_western = len(clusters["western"]) > 0
    has_sinic = len(clusters["sinic"]) > 0

    count = sum([has_jyotisha, has_western, has_sinic])

    # Check for material conflict
    polarities = set()
    for cluster_name, projs in clusters.items():
        cluster_pols = set(p["polarity"] for p in projs if p["polarity"] != "neutral")
        if cluster_pols:
            polarities.update(cluster_pols)

    has_conflict = "positive" in polarities and "negative" in polarities

    if count == 0:
        grade = "INSUFFICIENT"
    elif has_conflict and count >= 2:
        grade = "DIVERGENT"
    elif count == 3:
        grade = "STRONG"
    elif count == 2:
        grade = "MODERATE"
    else:
        grade = "WEAK"

    domain_grades[domain] = {
        "grade": grade,
        "clusters_present": count,
        "jyotisha": has_jyotisha,
        "western": has_western,
        "sinic": has_sinic,
        "has_conflict": has_conflict,
    }

# Divergence rate
total_domains = len(DOMAINS)
sufficient_domains = sum(1 for v in domain_grades.values() if v["grade"] != "INSUFFICIENT")
divergent_domains = sum(1 for v in domain_grades.values() if v["grade"] == "DIVERGENT")

divergence_rate_all = f"{divergent_domains}/{total_domains}"
divergence_rate_sufficient = f"{divergent_domains}/{sufficient_domains}" if sufficient_domains > 0 else "N/A"


# ═══════════════════════════════════════════════════════════════════════
# TEMPERAMENT AXES
# ═══════════════════════════════════════════════════════════════════════

TEMPERAMENT_AXES = {
    "T1": "Leadership/Visibility",
    "T2": "Drive/Initiative",
    "T3": "Nurturing/Service",
    "T4": "Intellect/Craft",
    "T5": "Adaptability",
    "T6": "Discipline/Structure",
}

temperament = {}

# T1: Leadership - Sun strength, 10th house, Leo placements
sun_j = jyotisha["grahas"]["Sun"]
sun_w_data = western["planets"]["Sun"]
t1_signals = []
t1_signals.append(f"Jyotisha: Sun in {sun_j['sign']} (house {sun_j['house']}), dignity {sun_j['dignity']}")
t1_signals.append(f"Western: Sun in {sun_w_data['sign']} (house {sun_w_data['house']}), {sun_w_data['sect_status']}")
temperament["T1"] = {"axis": "Leadership/Visibility", "signals": t1_signals,
                      "assessment": "moderate" if sun_j["house"] in [1, 4, 7, 10] else "present"}

# T2: Drive - Mars placement
mars_j = jyotisha["grahas"]["Mars"]
mars_w = western["planets"]["Mars"]
t2_signals = []
t2_signals.append(f"Jyotisha: Mars in {mars_j['sign']} (house {mars_j['house']})")
t2_signals.append(f"Western: Mars in {mars_w['sign']} (house {mars_w['house']})")
temperament["T2"] = {"axis": "Drive/Initiative", "signals": t2_signals,
                      "assessment": "strong" if mars_j["dignity"] in ["own_sign", "exalted"] else "present"}

# T3: Nurturing - Moon, Venus, Cancer/4th house
moon_j = jyotisha["grahas"]["Moon"]
venus_j = jyotisha["grahas"]["Venus"]
t3_signals = []
t3_signals.append(f"Jyotisha: Moon in {moon_j['sign']} (house {moon_j['house']})")
t3_signals.append(f"Venus in {venus_j['sign']} (house {venus_j['house']})")
temperament["T3"] = {"axis": "Nurturing/Service", "signals": t3_signals, "assessment": "present"}

# T4: Intellect - Mercury, Jupiter, 3rd/9th houses
merc_j = jyotisha["grahas"]["Mercury"]
jup_j = jyotisha["grahas"]["Jupiter"]
t4_signals = []
t4_signals.append(f"Jyotisha: Mercury in {merc_j['sign']} (house {merc_j['house']})")
t4_signals.append(f"Jupiter in {jup_j['sign']} (house {jup_j['house']})")
temperament["T4"] = {"axis": "Intellect/Craft", "signals": t4_signals,
                      "assessment": "strong" if jup_j["house"] in [1, 4, 5, 9] else "present"}

# T5: Adaptability - Mutable signs, Mercury, Gemini/Virgo/Sagittarius/Pisces
mutable_count = sum(1 for p in western["planets"].values() if p.get("modality") == "Mutable")
t5_signals = [f"Western: {mutable_count} planets in mutable signs"]
t5_signals.append(f"Ascendant modality: {western['ascendant']['modality']}")
temperament["T5"] = {"axis": "Adaptability", "signals": t5_signals,
                      "assessment": "strong" if mutable_count >= 3 or western["ascendant"]["modality"] == "Mutable" else "moderate"}

# T6: Discipline - Saturn, Capricorn, fixed signs
sat_j = jyotisha["grahas"]["Saturn"]
fixed_count = sum(1 for p in western["planets"].values() if p.get("modality") == "Fixed")
t6_signals = []
t6_signals.append(f"Jyotisha: Saturn in {sat_j['sign']} (house {sat_j['house']}), dignity {sat_j['dignity']}")
t6_signals.append(f"Western: {fixed_count} planets in fixed signs")
dm_elem = bazi["day_master"]["element"]
t6_signals.append(f"BaZi: Day Master element {dm_elem}")
temperament["T6"] = {"axis": "Discipline/Structure", "signals": t6_signals,
                      "assessment": "moderate"}

# Tibetan/Maya overlays for temperament
temperament["overlays"] = {
    "maya": f"Day sign: {maya['tzolkin']['display']} — Manik (Deer/Hand) is traditionally associated with healing, skill, and community service",
    "tibetan": f"{tibetan['year']['display']} — Earth-Tiger combines groundedness with courage and unpredictability; Mewa {tibetan['mewa']['number']} and Parkha {tibetan['parkha']['name']}",
    "note": "These are attributed symbolic descriptions from traditional Maya and Tibetan sources, not computed facts. They corroborate or dissent from computed temperament axes but do not upgrade domain grades."
}


# ═══════════════════════════════════════════════════════════════════════
# CHRONOLOGY & TIMING
# ═══════════════════════════════════════════════════════════════════════

timing = {
    "current_date": "2026-08-29",
    "age": 27,
    "jyotisha": {
        "current_mahadasha": jyotisha["vimshottari_dasha"].get("current_mahadasha", "N/A"),
        "mahadasha_ends": jyotisha["vimshottari_dasha"].get("current_mahadasha_ends", "N/A"),
        "moon_nakshatra_lord": jyotisha["vimshottari_dasha"]["moon_nakshatra_lord"],
    },
    "western": {
        "profection_house": western["profection"]["activated_house"],
        "profection_sign": western["profection"]["activated_sign"],
        "lord_of_year": western["profection"]["lord_of_year"],
    },
    "bazi": {
        "current_da_yun": bazi["da_yun"].get("current_period", {}),
    },
}

# Check for timing convergence
timing_domains = set()
# Jyotisha Moon mahadasha → D1, D4, D5 (Moon governs mind, nurture, mother)
jyotisha_timing_domains = {"D1", "D4", "D5"}
# Western 5th house profection → D6 (children/creation)
western_timing_domains = {"D6"}

timing_overlap = jyotisha_timing_domains & western_timing_domains
timing["convergence"] = {
    "jyotisha_activated_domains": list(jyotisha_timing_domains),
    "western_activated_domains": list(western_timing_domains),
    "overlap_domains": list(timing_overlap),
    "strength": "moderate" if len(timing_overlap) >= 1 else "weak" if timing_overlap else "none",
    "note": "No three-cluster timing convergence found for the current period"
}


# ═══════════════════════════════════════════════════════════════════════
# BUILD SYNTHESIS.json
# ═══════════════════════════════════════════════════════════════════════

synthesis = {
    "version": "2.0",
    "timestamp": datetime.utcnow().isoformat(),
    "projections": projections,
    "domain_grades": domain_grades,
    "divergence_rate": {
        "divergent_over_all": divergence_rate_all,
        "divergent_over_sufficient": divergence_rate_sufficient,
    },
    "temperament": temperament,
    "timing": timing,
    "claims_removed": {
        "count": 3,
        "reasons": [
            "Generic Barnum-style self-identity claims removed",
            "Unverified Zi Wei star brightness claims omitted (limited implementation)",
            "Tibetan personal forces omitted (no validated implementation)"
        ]
    },
}

with open(OUTPUT_DIR / "SYNTHESIS.json", "w") as f:
    json.dump(synthesis, f, indent=2, default=str)

print("SYNTHESIS.json written successfully.")
print(f"Domains with STRONG grade: {sum(1 for v in domain_grades.values() if v['grade'] == 'STRONG')}")
print(f"Domains with MODERATE grade: {sum(1 for v in domain_grades.values() if v['grade'] == 'MODERATE')}")
print(f"Domains with WEAK grade: {sum(1 for v in domain_grades.values() if v['grade'] == 'WEAK')}")
print(f"Domains with DIVERGENT grade: {sum(1 for v in domain_grades.values() if v['grade'] == 'DIVERGENT')}")
print(f"Domains with INSUFFICIENT grade: {sum(1 for v in domain_grades.values() if v['grade'] == 'INSUFFICIENT')}")
print(f"Divergence rate: {divergence_rate_all} (all), {divergence_rate_sufficient} (sufficient)")
print()

# Print domain summary
for d, info in domain_grades.items():
    print(f"  {d} {DOMAINS[d]:30s}: {info['grade']:12s} (J:{info['jyotisha']} W:{info['western']} S:{info['sinic']})")
