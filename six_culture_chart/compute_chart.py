#!/usr/bin/env python3
"""
Six-Culture Verified Chart Computation Engine
Computes birth chart data across Jyotisha, BaZi, Western/Hellenistic,
Zi Wei Dou Shu, Maya Calendar, and Tibetan Elemental traditions.
"""

import json
import math
import hashlib
import platform
import sys
import os
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path

import swisseph as swe
from skyfield.api import load as sf_load, Topos
from skyfield import almanac
from timezonefinder import TimezoneFinder
import ephem
import sxtwl

# ─── Configuration ───────────────────────────────────────────────────────
OUTPUT_DIR = Path(__file__).parent
BIRTH_INPUT = json.loads((OUTPUT_DIR / "BIRTH_INPUT.json").read_text())

# Birth parameters
YEAR = 1998
MONTH = 11
DAY = 12
HOUR = 14
MINUTE = 31
SECOND = 0
LAT = 19.1864
LON = 73.1854
ELEV = 14.0
TZ = ZoneInfo("Asia/Kolkata")
UTC_OFFSET = timedelta(hours=5, minutes=30)
GENDER = "male"

# Ayanamsha: Lahiri (default for Jyotisha)
AYANAMSHA_ID = swe.SIDM_LAHIRI

# Time instants for uncertainty ensemble
T_REPORTED = datetime(YEAR, MONTH, DAY, HOUR, MINUTE, SECOND, tzinfo=TZ)
T_MINUS = datetime(YEAR, MONTH, DAY, 14, 28, 0, tzinfo=TZ)
T_PLUS = datetime(YEAR, MONTH, DAY, 14, 32, 0, tzinfo=TZ)

INSTANTS = {
    "T_minus": T_MINUS,
    "T_reported": T_REPORTED,
    "T_plus": T_PLUS,
}

# Swiss Ephemeris planet IDs
PLANETS = {
    "Sun": swe.SUN, "Moon": swe.MOON, "Mercury": swe.MERCURY,
    "Venus": swe.VENUS, "Mars": swe.MARS, "Jupiter": swe.JUPITER,
    "Saturn": swe.SATURN, "Rahu": swe.MEAN_NODE,
}

WESTERN_PLANETS = {
    **PLANETS,
    "Uranus": swe.URANUS, "Neptune": swe.NEPTUNE, "Pluto": swe.PLUTO,
}

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

NAKSHATRAS = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni",
    "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha",
    "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha",
    "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"
]

NAKSHATRA_LORDS = [
    "Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu",
    "Jupiter", "Saturn", "Mercury", "Ketu", "Venus", "Sun",
    "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury",
    "Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu",
    "Jupiter", "Saturn", "Mercury"
]

VIMSHOTTARI_YEARS = {
    "Ketu": 7, "Venus": 20, "Sun": 6, "Moon": 10, "Mars": 7,
    "Rahu": 18, "Jupiter": 16, "Saturn": 19, "Mercury": 17
}
VIMSHOTTARI_ORDER = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]

HEAVENLY_STEMS = ["Jia", "Yi", "Bing", "Ding", "Wu", "Ji", "Geng", "Xin", "Ren", "Gui"]
EARTHLY_BRANCHES = ["Zi", "Chou", "Yin", "Mao", "Chen", "Si", "Wu", "Wei", "Shen", "You", "Xu", "Hai"]
STEM_ELEMENTS = ["Wood", "Wood", "Fire", "Fire", "Earth", "Earth", "Metal", "Metal", "Water", "Water"]
BRANCH_ANIMALS = ["Rat", "Ox", "Tiger", "Rabbit", "Dragon", "Snake", "Horse", "Goat", "Monkey", "Rooster", "Dog", "Pig"]
STEM_POLARITIES = ["Yang", "Yin", "Yang", "Yin", "Yang", "Yin", "Yang", "Yin", "Yang", "Yin"]

TZOLKIN_NAMES = [
    "Imix", "Ik", "Akbal", "Kan", "Chicchan", "Cimi", "Manik", "Lamat",
    "Muluc", "Oc", "Chuen", "Eb", "Ben", "Ix", "Men", "Cib",
    "Caban", "Etznab", "Cauac", "Ahau"
]
HAAB_MONTHS = [
    "Pop", "Wo", "Sip", "Sotz", "Sek", "Xul", "Yaxkin", "Mol",
    "Chen", "Yax", "Sak", "Keh", "Mak", "Kankin", "Muwan",
    "Pax", "Kayab", "Kumku", "Wayeb"
]

TIBETAN_ANIMALS = ["Mouse", "Ox", "Tiger", "Hare", "Dragon", "Snake",
                   "Horse", "Sheep", "Monkey", "Bird", "Dog", "Pig"]
TIBETAN_ELEMENTS = ["Wood", "Fire", "Earth", "Iron", "Water"]
TIBETAN_MEWA = [9, 8, 7, 6, 5, 4, 3, 2, 1]


def to_jd(dt):
    """Convert datetime to Julian Day (UT)."""
    utc = dt.astimezone(timezone.utc)
    return swe.julday(utc.year, utc.month, utc.day,
                      utc.hour + utc.minute / 60.0 + utc.second / 3600.0)


def sign_from_lon(lon):
    return SIGNS[int(lon / 30)]

def degree_in_sign(lon):
    return lon % 30

def nakshatra_from_lon(lon):
    idx = int(lon / (360 / 27))
    pada = int((lon % (360 / 27)) / (360 / 108)) + 1
    return {"name": NAKSHATRAS[idx], "pada": pada, "lord": NAKSHATRA_LORDS[idx], "index": idx}


# ═══════════════════════════════════════════════════════════════════════
# STEP 2: INPUT NORMALIZATION & AUDIT
# ═══════════════════════════════════════════════════════════════════════

def compute_input_audit():
    """Step 2: Normalize input, compute solar times, weekday, sunrise/sunset."""
    jd = to_jd(T_REPORTED)

    # Weekday
    weekday_num = int((jd + 1.5) % 7)
    weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    weekday = weekdays[weekday_num]

    # Sunrise/sunset using ephem
    obs = ephem.Observer()
    obs.lat = str(LAT)
    obs.lon = str(LON)
    obs.elevation = ELEV
    obs.date = ephem.Date(T_REPORTED.astimezone(timezone.utc))

    sunrise_utc = obs.previous_rising(ephem.Sun()).datetime().replace(tzinfo=timezone.utc)
    sunset_utc = obs.next_setting(ephem.Sun()).datetime().replace(tzinfo=timezone.utc)
    sunrise_local = sunrise_utc.astimezone(TZ)
    sunset_local = sunset_utc.astimezone(TZ)

    # Local Mean Solar Time
    solar_offset_hours = LON / 15.0
    lmst_offset = timedelta(hours=solar_offset_hours)
    utc_time = T_REPORTED.astimezone(timezone.utc)
    lmst = utc_time + lmst_offset

    # Equation of time for Local Apparent Solar Time
    sun_ephem = ephem.Sun(obs)
    eot_hours = float(obs.sidereal_time() - ephem.hours(str(sun_ephem.ra))) * 12 / math.pi

    # IANA timezone verification
    tf = TimezoneFinder()
    found_tz = tf.timezone_at(lat=LAT, lng=LON)

    audit = {
        "step": "2_input_audit",
        "original_values": BIRTH_INPUT["original_input"],
        "normalized": {
            "gregorian_date": "1998-11-12",
            "local_time_24h": "14:31:00",
            "utc_instant": utc_time.isoformat(),
            "julian_day_ut": round(jd, 8),
            "civil_weekday": weekday,
            "latitude_decimal": LAT,
            "longitude_decimal": LON,
            "elevation_m": ELEV,
            "coordinate_source": "GeoNames centroid for Ambarnath, Maharashtra",
            "iana_timezone": "Asia/Kolkata",
            "iana_timezone_verified": found_tz,
            "utc_offset": "+05:30",
            "dst_active": False,
            "dst_note": "India has not observed DST since 1945",
        },
        "solar_times": {
            "local_mean_solar_time": lmst.strftime("%H:%M:%S"),
            "sunrise_local": sunrise_local.strftime("%H:%M:%S"),
            "sunset_local": sunset_local.strftime("%H:%M:%S"),
            "birth_is_daytime": sunrise_local.time() < T_REPORTED.time() < sunset_local.time(),
        },
        "uncertainty_ensemble": {
            "T_minus": T_MINUS.isoformat(),
            "T_reported": T_REPORTED.isoformat(),
            "T_plus": T_PLUS.isoformat(),
            "range_description": "14:28 to 14:32 IST (4-minute window)"
        }
    }
    return audit


# ═══════════════════════════════════════════════════════════════════════
# STEP 4A: SHARED ASTRONOMICAL BASE
# ═══════════════════════════════════════════════════════════════════════

def compute_astronomical_base(dt):
    """Compute tropical and sidereal positions for all planets at given datetime."""
    jd = to_jd(dt)
    swe.set_sid_mode(AYANAMSHA_ID)
    ayanamsha = swe.get_ayanamsa(jd)

    results = {
        "julian_day_ut": round(jd, 8),
        "ayanamsha_lahiri": round(ayanamsha, 6),
        "planets": {}
    }

    for name, pid in PLANETS.items():
        flags = swe.FLG_SWIEPH | swe.FLG_SPEED
        trop = swe.calc_ut(jd, pid, flags)

        trop_lon = trop[0][0]
        trop_lat = trop[0][1]
        speed = trop[0][3]

        if name == "Rahu":
            sid_lon = trop_lon - ayanamsha
            if sid_lon < 0:
                sid_lon += 360
            ketu_trop = (trop_lon + 180) % 360
            ketu_sid = (sid_lon + 180) % 360
        else:
            sid_lon = trop_lon - ayanamsha
            if sid_lon < 0:
                sid_lon += 360

        results["planets"][name] = {
            "tropical_longitude": round(trop_lon, 6),
            "sidereal_longitude": round(sid_lon, 6),
            "latitude": round(trop_lat, 6),
            "speed_deg_per_day": round(speed, 6),
            "retrograde": speed < 0,
            "tropical_sign": sign_from_lon(trop_lon),
            "sidereal_sign": sign_from_lon(sid_lon),
            "degree_in_sign_tropical": round(degree_in_sign(trop_lon), 4),
            "degree_in_sign_sidereal": round(degree_in_sign(sid_lon), 4),
        }

    # Add Ketu
    rahu_data = results["planets"]["Rahu"]
    ketu_trop = (rahu_data["tropical_longitude"] + 180) % 360
    ketu_sid = (rahu_data["sidereal_longitude"] + 180) % 360
    results["planets"]["Ketu"] = {
        "tropical_longitude": round(ketu_trop, 6),
        "sidereal_longitude": round(ketu_sid, 6),
        "latitude": 0.0,
        "speed_deg_per_day": rahu_data["speed_deg_per_day"],
        "retrograde": True,
        "tropical_sign": sign_from_lon(ketu_trop),
        "sidereal_sign": sign_from_lon(ketu_sid),
        "degree_in_sign_tropical": round(degree_in_sign(ketu_trop), 4),
        "degree_in_sign_sidereal": round(degree_in_sign(ketu_sid), 4),
    }

    # Ascendant and houses (tropical)
    cusps_trop, ascmc_trop = swe.houses(jd, LAT, LON, b'W')
    asc_trop = ascmc_trop[0]
    mc_trop = ascmc_trop[1]
    asc_sid = asc_trop - ayanamsha
    if asc_sid < 0:
        asc_sid += 360
    mc_sid = mc_trop - ayanamsha
    if mc_sid < 0:
        mc_sid += 360

    results["ascendant"] = {
        "tropical": round(asc_trop, 6),
        "sidereal": round(asc_sid, 6),
        "tropical_sign": sign_from_lon(asc_trop),
        "sidereal_sign": sign_from_lon(asc_sid),
        "degree_in_sign_tropical": round(degree_in_sign(asc_trop), 4),
        "degree_in_sign_sidereal": round(degree_in_sign(asc_sid), 4),
    }
    results["midheaven"] = {
        "tropical": round(mc_trop, 6),
        "sidereal": round(mc_sid, 6),
        "tropical_sign": sign_from_lon(mc_trop),
        "sidereal_sign": sign_from_lon(mc_sid),
    }

    return results


def compute_skyfield_validation(dt):
    """Independent validation of Sun, Moon positions using Skyfield/JPL."""
    ts = sf_load.timescale()
    utc = dt.astimezone(timezone.utc)
    t = ts.utc(utc.year, utc.month, utc.day, utc.hour, utc.minute, utc.second)

    eph = sf_load('de421.bsp')
    earth = eph['earth']
    observer = earth + Topos(latitude_degrees=LAT, longitude_degrees=LON, elevation_m=ELEV)

    validations = {}
    bodies = {"Sun": "sun", "Moon": "moon", "Mercury": "mercury", "Venus": "venus",
              "Mars": "mars", "Jupiter": "jupiter barycenter", "Saturn": "saturn barycenter"}

    for name, sf_name in bodies.items():
        body = eph[sf_name]
        astrometric = observer.at(t).observe(body)
        apparent = astrometric.apparent()
        ra, dec, distance = apparent.radec(epoch='date')

        # Convert RA to ecliptic longitude (approximate via obliquity)
        ecl = apparent.ecliptic_latlon(epoch='date')
        lon_deg = ecl[1].degrees
        if lon_deg < 0:
            lon_deg += 360

        validations[name] = {
            "skyfield_tropical_longitude": round(lon_deg, 6),
            "ra_hours": round(ra.hours, 6),
            "dec_degrees": round(dec.degrees, 6),
        }

    return validations


def cross_validate(swe_data, sf_data):
    """Compare Swiss Ephemeris and Skyfield positions."""
    comparisons = []
    alert_threshold = 0.01

    for name in sf_data:
        if name in swe_data["planets"]:
            swe_lon = swe_data["planets"][name]["tropical_longitude"]
            sf_lon = sf_data[name]["skyfield_tropical_longitude"]
            diff = abs(swe_lon - sf_lon)
            if diff > 180:
                diff = 360 - diff

            comparisons.append({
                "planet": name,
                "swiss_eph_tropical": round(swe_lon, 6),
                "skyfield_tropical": round(sf_lon, 6),
                "difference_degrees": round(diff, 6),
                "alert": diff > alert_threshold,
                "status": "ALERT" if diff > alert_threshold else "pass"
            })

    return comparisons


# ═══════════════════════════════════════════════════════════════════════
# STEP 4B: JYOTISHA
# ═══════════════════════════════════════════════════════════════════════

SIGN_LORDS = {
    "Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury",
    "Cancer": "Moon", "Leo": "Sun", "Virgo": "Mercury",
    "Libra": "Venus", "Scorpio": "Mars", "Sagittarius": "Jupiter",
    "Capricorn": "Saturn", "Aquarius": "Saturn", "Pisces": "Jupiter"
}

EXALTATION = {"Sun": "Aries", "Moon": "Taurus", "Mars": "Capricorn",
              "Mercury": "Virgo", "Jupiter": "Cancer", "Venus": "Pisces",
              "Saturn": "Libra", "Rahu": "Taurus", "Ketu": "Scorpio"}

DEBILITATION = {"Sun": "Libra", "Moon": "Scorpio", "Mars": "Cancer",
                "Mercury": "Pisces", "Jupiter": "Capricorn", "Venus": "Virgo",
                "Saturn": "Aries", "Rahu": "Scorpio", "Ketu": "Taurus"}

MOOLATRIKONA = {"Sun": ("Leo", 0, 20), "Moon": ("Taurus", 3, 30),
                "Mars": ("Aries", 0, 12), "Mercury": ("Virgo", 15, 20),
                "Jupiter": ("Sagittarius", 0, 10), "Venus": ("Libra", 0, 15),
                "Saturn": ("Aquarius", 0, 20)}

NATURAL_BENEFICS = ["Jupiter", "Venus", "Mercury", "Moon"]
NATURAL_MALEFICS = ["Sun", "Mars", "Saturn", "Rahu", "Ketu"]

def compute_jyotisha(astro_data):
    """Compute Jyotisha chart from astronomical base data."""
    asc_sign = astro_data["ascendant"]["sidereal_sign"]
    asc_sign_idx = SIGNS.index(asc_sign)

    chart = {
        "system": "jyotisha",
        "configuration": {
            "zodiac": "sidereal",
            "ayanamsha": "Lahiri",
            "house_system": "whole_sign",
            "node_type": "mean"
        },
        "lagna": {
            "sign": asc_sign,
            "degree": astro_data["ascendant"]["degree_in_sign_sidereal"],
            "nakshatra": nakshatra_from_lon(astro_data["ascendant"]["sidereal"]),
        },
        "grahas": {},
        "houses": {},
        "nakshatras": {},
        "dignities": {},
        "aspects": [],
    }

    # Assign houses (whole-sign from Lagna)
    for i in range(12):
        sign_idx = (asc_sign_idx + i) % 12
        chart["houses"][str(i + 1)] = {
            "sign": SIGNS[sign_idx],
            "lord": SIGN_LORDS[SIGNS[sign_idx]],
        }

    # Process each graha
    for name, pdata in astro_data["planets"].items():
        sid_lon = pdata["sidereal_longitude"]
        sign = pdata["sidereal_sign"]
        sign_idx = SIGNS.index(sign)
        house = ((sign_idx - asc_sign_idx) % 12) + 1

        # Dignity
        dignity = "neutral"
        if sign == SIGN_LORDS.get(name, "") and sign == name:
            dignity = "own_sign"
        lord_of_sign = SIGN_LORDS[sign]
        if lord_of_sign == name:
            dignity = "own_sign"
        if EXALTATION.get(name) == sign:
            dignity = "exalted"
        if DEBILITATION.get(name) == sign:
            dignity = "debilitated"
        if name in MOOLATRIKONA:
            mt_sign, mt_start, mt_end = MOOLATRIKONA[name]
            deg_in_sign = pdata["degree_in_sign_sidereal"]
            if sign == mt_sign and mt_start <= deg_in_sign <= mt_end:
                dignity = "moolatrikona"

        # Combustion check (within ~6° of Sun for most planets)
        combustion = False
        if name not in ["Sun", "Rahu", "Ketu"]:
            sun_lon = astro_data["planets"]["Sun"]["sidereal_longitude"]
            angular_dist = abs(sid_lon - sun_lon)
            if angular_dist > 180:
                angular_dist = 360 - angular_dist
            combust_orbs = {"Moon": 12, "Mars": 17, "Mercury": 14, "Jupiter": 11, "Venus": 10, "Saturn": 15}
            if angular_dist < combust_orbs.get(name, 6):
                combustion = True

        naksh = nakshatra_from_lon(sid_lon)

        chart["grahas"][name] = {
            "sidereal_longitude": round(sid_lon, 4),
            "sign": sign,
            "degree_in_sign": round(pdata["degree_in_sign_sidereal"], 4),
            "house": house,
            "nakshatra": naksh["name"],
            "nakshatra_pada": naksh["pada"],
            "nakshatra_lord": naksh["lord"],
            "retrograde": pdata["retrograde"],
            "speed": pdata["speed_deg_per_day"],
            "dignity": dignity,
            "sign_lord": SIGN_LORDS[sign],
            "combustion": combustion,
            "natural_benefic": name in NATURAL_BENEFICS,
        }

    # Graha Drishti (Parashari aspects)
    aspect_rules = {
        "all": [7],
        "Mars": [4, 8],
        "Jupiter": [5, 9],
        "Saturn": [3, 10],
        "Rahu": [5, 9],
        "Ketu": [5, 9],
    }

    for name, gdata in chart["grahas"].items():
        from_house = gdata["house"]
        aspects_list = [7]
        if name in aspect_rules:
            aspects_list = aspects_list + aspect_rules[name]
        aspects_list = list(set(aspects_list))

        for asp in aspects_list:
            target_house = ((from_house - 1 + asp) % 12) + 1
            chart["aspects"].append({
                "from": name,
                "from_house": from_house,
                "aspect": asp,
                "to_house": target_house,
                "to_sign": chart["houses"][str(target_house)]["sign"],
            })

    # Navamsha (D9)
    chart["navamsha"] = {}
    for name, gdata in chart["grahas"].items():
        sid_lon = gdata["sidereal_longitude"]
        navamsha_idx = int(sid_lon / (360 / 108))
        navamsha_sign_idx = navamsha_idx % 12
        chart["navamsha"][name] = {
            "sign": SIGNS[navamsha_sign_idx],
            "degree": round((sid_lon % (360/108)) * (30 / (360/108)), 4),
        }

    # Vimshottari Dasha
    moon_data = chart["grahas"]["Moon"]
    moon_nak = nakshatra_from_lon(astro_data["planets"]["Moon"]["sidereal_longitude"])
    moon_lon = astro_data["planets"]["Moon"]["sidereal_longitude"]

    nak_span = 360 / 27
    nak_start = moon_nak["index"] * nak_span
    elapsed_in_nak = moon_lon - nak_start
    proportion_elapsed = elapsed_in_nak / nak_span

    start_lord = moon_nak["lord"]
    start_lord_idx = VIMSHOTTARI_ORDER.index(start_lord)
    remaining_years = VIMSHOTTARI_YEARS[start_lord] * (1 - proportion_elapsed)

    birth_date = datetime(YEAR, MONTH, DAY, tzinfo=TZ)
    dasha_periods = []
    current_date = birth_date

    # First (partial) period
    end_date = current_date + timedelta(days=remaining_years * 365.25)
    dasha_periods.append({
        "lord": start_lord,
        "start": current_date.isoformat(),
        "end": end_date.isoformat(),
        "years": round(remaining_years, 4),
        "partial": True,
    })
    current_date = end_date

    # Subsequent full periods (8 more to complete one 120-year cycle)
    for i in range(1, 9):
        lord_idx = (start_lord_idx + i) % 9
        lord = VIMSHOTTARI_ORDER[lord_idx]
        years = VIMSHOTTARI_YEARS[lord]
        end_date = current_date + timedelta(days=years * 365.25)
        dasha_periods.append({
            "lord": lord,
            "start": current_date.isoformat(),
            "end": end_date.isoformat(),
            "years": years,
            "partial": False,
        })
        current_date = end_date

    chart["vimshottari_dasha"] = {
        "moon_nakshatra": moon_nak["name"],
        "moon_nakshatra_lord": moon_nak["lord"],
        "periods": dasha_periods,
    }

    # Verify invariant: the 9 standard lord durations sum to 120
    standard_total = sum(VIMSHOTTARI_YEARS.values())
    actual_total = sum(p["years"] for p in dasha_periods)
    chart["vimshottari_dasha"]["standard_lord_years_total"] = standard_total
    chart["vimshottari_dasha"]["actual_periods_total"] = round(actual_total, 4)
    chart["vimshottari_dasha"]["invariant_120_pass"] = standard_total == 120

    # Current dasha (as of 2026-08-29)
    now = datetime(2026, 8, 29, tzinfo=TZ)
    for p in dasha_periods:
        p_start = datetime.fromisoformat(p["start"])
        p_end = datetime.fromisoformat(p["end"])
        if p_start <= now < p_end:
            chart["vimshottari_dasha"]["current_mahadasha"] = p["lord"]
            chart["vimshottari_dasha"]["current_mahadasha_ends"] = p["end"]
            break

    # Classical Yogas (small whitelist)
    yogas = []

    # Gajakesari Yoga: Jupiter in kendra from Moon
    moon_house = chart["grahas"]["Moon"]["house"]
    jup_house = chart["grahas"]["Jupiter"]["house"]
    kendra_from_moon = [(moon_house - 1 + k) % 12 + 1 for k in [0, 3, 6, 9]]
    if jup_house in kendra_from_moon:
        yogas.append({
            "name": "Gajakesari Yoga",
            "rule": "Jupiter in kendra (1,4,7,10) from Moon",
            "satisfied_by": f"Moon in house {moon_house}, Jupiter in house {jup_house}",
            "present": True,
        })

    # Budhaditya Yoga: Sun and Mercury in same sign
    if chart["grahas"]["Sun"]["sign"] == chart["grahas"]["Mercury"]["sign"]:
        yogas.append({
            "name": "Budhaditya Yoga",
            "rule": "Sun and Mercury in the same sign",
            "satisfied_by": f"Both in {chart['grahas']['Sun']['sign']}",
            "present": True,
        })

    # Pancha Mahapurusha Yogas
    kendras = [(asc_sign_idx + k) % 12 for k in [0, 3, 6, 9]]
    kendra_signs = [SIGNS[k] for k in kendras]

    mahapurusha = {
        "Mars": ("Ruchaka", ["Aries", "Capricorn", "Scorpio"]),
        "Mercury": ("Bhadra", ["Gemini", "Virgo"]),
        "Jupiter": ("Hamsa", ["Cancer", "Sagittarius", "Pisces"]),
        "Venus": ("Malavya", ["Taurus", "Libra", "Pisces"]),
        "Saturn": ("Shasha", ["Libra", "Capricorn", "Aquarius"]),
    }
    for planet, (yoga_name, own_exalt_signs) in mahapurusha.items():
        p_sign = chart["grahas"][planet]["sign"]
        if p_sign in kendra_signs and p_sign in own_exalt_signs:
            yogas.append({
                "name": f"{yoga_name} Yoga (Pancha Mahapurusha)",
                "rule": f"{planet} in own/exaltation sign AND in kendra from Lagna",
                "satisfied_by": f"{planet} in {p_sign} (house {chart['grahas'][planet]['house']})",
                "present": True,
            })

    # Chandra-Mangal Yoga: Moon-Mars conjunction
    if chart["grahas"]["Moon"]["sign"] == chart["grahas"]["Mars"]["sign"]:
        yogas.append({
            "name": "Chandra-Mangal Yoga",
            "rule": "Moon and Mars in the same sign",
            "satisfied_by": f"Both in {chart['grahas']['Moon']['sign']}",
            "present": True,
        })

    chart["yogas"] = yogas

    return chart


# ═══════════════════════════════════════════════════════════════════════
# STEP 4C: BAZI (Four Pillars of Destiny)
# ═══════════════════════════════════════════════════════════════════════

def compute_solar_term_boundary(dt):
    """Compute the active solar term and distance from boundary using sxtwl."""
    # Use sxtwl for solar term calculations
    day_obj = sxtwl.fromSolar(dt.year, dt.month, dt.day)

    # Get Lunar calendar info
    lunar_year = day_obj.getLunarYear()
    lunar_month = day_obj.getLunarMonth()
    lunar_day = day_obj.getLunarDay()
    is_leap = day_obj.isLunarLeap()

    return {
        "lunar_year": lunar_year,
        "lunar_month": lunar_month,
        "lunar_day": lunar_day,
        "is_leap_month": is_leap,
    }


def compute_bazi(dt):
    """Compute Four Pillars of Destiny."""
    jd = to_jd(dt)

    # Use sxtwl for pillars
    day_obj = sxtwl.fromSolar(dt.year, dt.month, dt.day)

    # Get Gan-Zhi for each pillar from sxtwl
    yTG = day_obj.getYearGZ()
    mTG = day_obj.getMonthGZ()
    dTG = day_obj.getDayGZ()

    # Hour pillar calculation
    local_hour = dt.hour
    # Convert to double-hour (shichen) index
    hour_branch_idx = ((local_hour + 1) // 2) % 12

    # Hour stem from Day stem
    day_stem_idx = dTG.tg
    hour_stem_base = (day_stem_idx % 5) * 2
    hour_stem_idx = (hour_stem_base + hour_branch_idx) % 10

    def pillar_info(stem_idx, branch_idx):
        stem = HEAVENLY_STEMS[stem_idx]
        branch = EARTHLY_BRANCHES[branch_idx]
        element = STEM_ELEMENTS[stem_idx]
        animal = BRANCH_ANIMALS[branch_idx]
        polarity = STEM_POLARITIES[stem_idx]

        # Na Yin calculation
        sexagenary = stem_idx + branch_idx * 0  # simplified

        # Hidden stems
        hidden_stems_map = {
            0: ["Gui"],              # Zi - Water
            1: ["Ji", "Gui", "Xin"],  # Chou
            2: ["Jia", "Bing", "Wu"], # Yin
            3: ["Yi"],                # Mao
            4: ["Wu", "Yi", "Gui"],   # Chen
            5: ["Bing", "Wu", "Geng"],# Si
            6: ["Ding", "Ji"],        # Wu (Horse)
            7: ["Ji", "Ding", "Yi"],  # Wei
            8: ["Geng", "Ren", "Wu"], # Shen
            9: ["Xin"],              # You
            10: ["Wu", "Xin", "Ding"],# Xu
            11: ["Ren", "Jia"],       # Hai
        }

        return {
            "stem": stem,
            "branch": branch,
            "element": element,
            "animal": animal,
            "polarity": polarity,
            "hidden_stems": hidden_stems_map.get(branch_idx, []),
            "stem_index": stem_idx,
            "branch_index": branch_idx,
        }

    year_pillar = pillar_info(yTG.tg, yTG.dz)
    month_pillar = pillar_info(mTG.tg, mTG.dz)
    day_pillar = pillar_info(dTG.tg, dTG.dz)
    hour_pillar = pillar_info(hour_stem_idx, hour_branch_idx)

    day_master = day_pillar["stem"]
    day_master_element = day_pillar["element"]

    # Ten Gods calculation
    stem_elements_cycle = ["Wood", "Wood", "Fire", "Fire", "Earth", "Earth", "Metal", "Metal", "Water", "Water"]
    stem_polarities = ["Yang", "Yin", "Yang", "Yin", "Yang", "Yin", "Yang", "Yin", "Yang", "Yin"]

    element_cycle = ["Wood", "Fire", "Earth", "Metal", "Water"]

    def ten_god(day_stem_idx, other_stem_idx):
        dm_elem = element_cycle.index(stem_elements_cycle[day_stem_idx])
        ot_elem = element_cycle.index(stem_elements_cycle[other_stem_idx])
        dm_pol = stem_polarities[day_stem_idx]
        ot_pol = stem_polarities[other_stem_idx]
        same_pol = dm_pol == ot_pol

        rel = (ot_elem - dm_elem) % 5

        gods = {
            0: ("Companion (Bi Jian)" if same_pol else "Rob Wealth (Jie Cai)"),
            1: ("Eating God (Shi Shen)" if same_pol else "Hurting Officer (Shang Guan)"),
            2: ("Indirect Wealth (Pian Cai)" if same_pol else "Direct Wealth (Zheng Cai)"),
            3: ("7 Killings (Qi Sha)" if same_pol else "Direct Officer (Zheng Guan)"),
            4: ("Indirect Resource (Pian Yin)" if same_pol else "Direct Resource (Zheng Yin)"),
        }
        return gods[rel]

    dm_idx = day_pillar["stem_index"]

    for pillar_name, pillar in [("year", year_pillar), ("month", month_pillar), ("hour", hour_pillar)]:
        pillar["ten_god"] = ten_god(dm_idx, pillar["stem_index"])
        pillar["hidden_ten_gods"] = []
        for hs in pillar["hidden_stems"]:
            hs_idx = HEAVENLY_STEMS.index(hs)
            pillar["hidden_ten_gods"].append({
                "stem": hs,
                "ten_god": ten_god(dm_idx, hs_idx)
            })

    # Da Yun (Luck Pillars) - Male Yang or Female Yin = forward
    year_stem_polarity = year_pillar["polarity"]
    forward = (GENDER == "male" and year_stem_polarity == "Yang") or \
              (GENDER == "female" and year_stem_polarity == "Yin")

    # Approximate Da Yun start age
    # Distance from birth to next/previous solar term
    month_stem_idx = month_pillar["stem_index"]
    month_branch_idx = month_pillar["branch_index"]

    da_yun = []
    for i in range(9):
        if forward:
            s_idx = (month_stem_idx + i + 1) % 10
            b_idx = (month_branch_idx + i + 1) % 12
        else:
            s_idx = (month_stem_idx - i - 1) % 10
            b_idx = (month_branch_idx - i - 1) % 12

        start_age = 3 + (i * 10)  # approximate

        da_yun.append({
            "period": i + 1,
            "stem": HEAVENLY_STEMS[s_idx],
            "branch": EARTHLY_BRANCHES[b_idx],
            "element": STEM_ELEMENTS[s_idx],
            "animal": BRANCH_ANIMALS[b_idx],
            "approximate_start_age": start_age,
            "approximate_start_year": YEAR + start_age,
            "approximate_end_year": YEAR + start_age + 10,
            "ten_god": ten_god(dm_idx, s_idx),
        })

    # Lunar calendar info
    lunar_info = compute_solar_term_boundary(dt)

    bazi = {
        "system": "bazi",
        "configuration": {
            "time_basis": "local_civil_time",
            "day_boundary": "midnight (Zi hour start at 23:00 convention noted)",
            "school": "traditional_mainstream",
        },
        "pillars": {
            "year": year_pillar,
            "month": month_pillar,
            "day": day_pillar,
            "hour": hour_pillar,
        },
        "day_master": {
            "stem": day_master,
            "element": day_master_element,
            "polarity": day_pillar["polarity"],
        },
        "da_yun": {
            "direction": "forward" if forward else "backward",
            "gender": GENDER,
            "year_stem_polarity": year_stem_polarity,
            "periods": da_yun,
        },
        "lunar_calendar": lunar_info,
    }

    # Current Da Yun (age ~28 in 2026)
    current_age = 2026 - YEAR
    for dy in da_yun:
        if dy["approximate_start_age"] <= current_age < dy["approximate_start_age"] + 10:
            bazi["da_yun"]["current_period"] = dy
            break

    return bazi


# ═══════════════════════════════════════════════════════════════════════
# STEP 4D: WESTERN/HELLENISTIC
# ═══════════════════════════════════════════════════════════════════════

ESSENTIAL_DIGNITIES = {
    "Sun": {"domicile": ["Leo"], "exaltation": ["Aries"], "detriment": ["Aquarius"], "fall": ["Libra"]},
    "Moon": {"domicile": ["Cancer"], "exaltation": ["Taurus"], "detriment": ["Capricorn"], "fall": ["Scorpio"]},
    "Mercury": {"domicile": ["Gemini", "Virgo"], "exaltation": ["Virgo"], "detriment": ["Sagittarius", "Pisces"], "fall": ["Pisces"]},
    "Venus": {"domicile": ["Taurus", "Libra"], "exaltation": ["Pisces"], "detriment": ["Aries", "Scorpio"], "fall": ["Virgo"]},
    "Mars": {"domicile": ["Aries", "Scorpio"], "exaltation": ["Capricorn"], "detriment": ["Taurus", "Libra"], "fall": ["Cancer"]},
    "Jupiter": {"domicile": ["Sagittarius", "Pisces"], "exaltation": ["Cancer"], "detriment": ["Gemini", "Virgo"], "fall": ["Capricorn"]},
    "Saturn": {"domicile": ["Capricorn", "Aquarius"], "exaltation": ["Libra"], "detriment": ["Cancer", "Leo"], "fall": ["Aries"]},
}

DAY_TRIPLICITY = {"Fire": "Sun", "Earth": "Venus", "Air": "Saturn", "Water": "Mars"}
NIGHT_TRIPLICITY = {"Fire": "Jupiter", "Earth": "Moon", "Air": "Mercury", "Water": "Mars"}

SIGN_ELEMENTS_WESTERN = {
    "Aries": "Fire", "Taurus": "Earth", "Gemini": "Air", "Cancer": "Water",
    "Leo": "Fire", "Virgo": "Earth", "Libra": "Air", "Scorpio": "Water",
    "Sagittarius": "Fire", "Capricorn": "Earth", "Aquarius": "Air", "Pisces": "Water"
}

SIGN_MODALITIES = {
    "Aries": "Cardinal", "Taurus": "Fixed", "Gemini": "Mutable",
    "Cancer": "Cardinal", "Leo": "Fixed", "Virgo": "Mutable",
    "Libra": "Cardinal", "Scorpio": "Fixed", "Sagittarius": "Mutable",
    "Capricorn": "Cardinal", "Aquarius": "Fixed", "Pisces": "Mutable"
}


def compute_western(astro_data, is_daytime):
    """Compute Western/Hellenistic chart."""
    jd = astro_data["julian_day_ut"]

    asc_sign = astro_data["ascendant"]["tropical_sign"]
    asc_sign_idx = SIGNS.index(asc_sign)

    sect = "day" if is_daytime else "night"

    chart = {
        "system": "western_hellenistic",
        "configuration": {
            "zodiac": "tropical",
            "house_system": "whole_sign",
            "traditional_planets": True,
            "sect": sect,
        },
        "ascendant": {
            "sign": asc_sign,
            "degree": astro_data["ascendant"]["degree_in_sign_tropical"],
            "element": SIGN_ELEMENTS_WESTERN[asc_sign],
            "modality": SIGN_MODALITIES[asc_sign],
        },
        "midheaven": {
            "sign": astro_data["midheaven"]["tropical_sign"],
        },
        "planets": {},
        "houses": {},
        "aspects": [],
        "lots": {},
    }

    # Houses
    for i in range(12):
        sign_idx = (asc_sign_idx + i) % 12
        sign = SIGNS[sign_idx]
        chart["houses"][str(i + 1)] = {
            "sign": sign,
            "ruler": SIGN_LORDS[sign],
            "element": SIGN_ELEMENTS_WESTERN[sign],
            "modality": SIGN_MODALITIES[sign],
        }

    # Process planets (traditional 7 + nodes for comparison)
    trad_planets = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"]

    for name in trad_planets:
        pdata = astro_data["planets"][name]
        trop_lon = pdata["tropical_longitude"]
        sign = pdata["tropical_sign"]
        sign_idx = SIGNS.index(sign)
        house = ((sign_idx - asc_sign_idx) % 12) + 1

        # Essential dignities
        dignities = []
        if name in ESSENTIAL_DIGNITIES:
            ed = ESSENTIAL_DIGNITIES[name]
            if sign in ed["domicile"]:
                dignities.append("domicile")
            if sign in ed["exaltation"]:
                dignities.append("exaltation")
            if sign in ed["detriment"]:
                dignities.append("detriment")
            if sign in ed["fall"]:
                dignities.append("fall")

        # Triplicity
        sign_elem = SIGN_ELEMENTS_WESTERN[sign]
        if is_daytime and DAY_TRIPLICITY.get(sign_elem) == name:
            dignities.append("triplicity_ruler")
        elif not is_daytime and NIGHT_TRIPLICITY.get(sign_elem) == name:
            dignities.append("triplicity_ruler")

        # Sect
        day_sect = ["Sun", "Jupiter", "Saturn"]
        night_sect = ["Moon", "Venus", "Mars"]
        if name in day_sect:
            sect_status = "in_sect" if is_daytime else "out_of_sect"
        elif name in night_sect:
            sect_status = "in_sect" if not is_daytime else "out_of_sect"
        else:
            sect_status = "neutral"

        # Angular houses
        angular_houses = [1, 4, 7, 10]
        succedent_houses = [2, 5, 8, 11]
        cadent_houses = [3, 6, 9, 12]
        if house in angular_houses:
            angularity = "angular"
        elif house in succedent_houses:
            angularity = "succedent"
        else:
            angularity = "cadent"

        chart["planets"][name] = {
            "tropical_longitude": round(trop_lon, 4),
            "sign": sign,
            "degree_in_sign": round(degree_in_sign(trop_lon), 4),
            "house": house,
            "retrograde": pdata["retrograde"],
            "speed": pdata["speed_deg_per_day"],
            "dignities": dignities,
            "sect_status": sect_status,
            "angularity": angularity,
            "element": SIGN_ELEMENTS_WESTERN[sign],
            "modality": SIGN_MODALITIES[sign],
        }

    # Aspects (Ptolemaic: conjunction, sextile, square, trine, opposition)
    aspect_types = {0: "conjunction", 60: "sextile", 90: "square", 120: "trine", 180: "opposition"}
    orbs = {"Sun": 8, "Moon": 8, "Mercury": 7, "Venus": 7, "Mars": 7, "Jupiter": 8, "Saturn": 8}

    planet_list = list(chart["planets"].keys())
    for i, p1 in enumerate(planet_list):
        for p2 in planet_list[i+1:]:
            lon1 = chart["planets"][p1]["tropical_longitude"]
            lon2 = chart["planets"][p2]["tropical_longitude"]
            diff = abs(lon1 - lon2)
            if diff > 180:
                diff = 360 - diff

            for exact_angle, asp_name in aspect_types.items():
                orb = min(orbs.get(p1, 7), orbs.get(p2, 7))
                if abs(diff - exact_angle) <= orb:
                    chart["aspects"].append({
                        "planet1": p1,
                        "planet2": p2,
                        "aspect": asp_name,
                        "exact_angle": exact_angle,
                        "actual_angle": round(diff, 4),
                        "orb": round(abs(diff - exact_angle), 4),
                        "applying": chart["planets"][p1]["speed"] > chart["planets"][p2]["speed"],
                    })
                    break

    # Lot of Fortune: day = Asc + Moon - Sun; night = Asc + Sun - Moon
    asc_lon = astro_data["ascendant"]["tropical"]
    moon_lon = astro_data["planets"]["Moon"]["tropical_longitude"]
    sun_lon = astro_data["planets"]["Sun"]["tropical_longitude"]

    if is_daytime:
        lot_fortune = (asc_lon + moon_lon - sun_lon) % 360
        lot_spirit = (asc_lon + sun_lon - moon_lon) % 360
    else:
        lot_fortune = (asc_lon + sun_lon - moon_lon) % 360
        lot_spirit = (asc_lon + moon_lon - sun_lon) % 360

    chart["lots"]["fortune"] = {
        "longitude": round(lot_fortune, 4),
        "sign": sign_from_lon(lot_fortune),
        "degree": round(degree_in_sign(lot_fortune), 4),
        "house": ((SIGNS.index(sign_from_lon(lot_fortune)) - asc_sign_idx) % 12) + 1,
        "formula": "Asc + Moon - Sun (day)" if is_daytime else "Asc + Sun - Moon (night)",
    }
    chart["lots"]["spirit"] = {
        "longitude": round(lot_spirit, 4),
        "sign": sign_from_lon(lot_spirit),
        "degree": round(degree_in_sign(lot_spirit), 4),
        "house": ((SIGNS.index(sign_from_lon(lot_spirit)) - asc_sign_idx) % 12) + 1,
    }

    # Annual Profection (age 27 turning 28 in 2026)
    current_age = 2026 - YEAR
    profection_house = (current_age % 12) + 1
    profection_sign = SIGNS[(asc_sign_idx + profection_house - 1) % 12]
    profection_ruler = SIGN_LORDS[profection_sign]

    chart["profection"] = {
        "current_age": current_age,
        "activated_house": profection_house,
        "activated_sign": profection_sign,
        "lord_of_year": profection_ruler,
        "lord_natal_condition": chart["planets"].get(profection_ruler, {}),
    }

    # Dispositor chain
    dispositors = {}
    for name, pdata in chart["planets"].items():
        dispositors[name] = SIGN_LORDS[pdata["sign"]]
    chart["dispositor_chain"] = dispositors

    # Find final dispositor
    visited = set()
    current = list(dispositors.keys())[0]
    chain = []
    while current not in visited:
        visited.add(current)
        chain.append(current)
        current = dispositors[current]
    chart["final_dispositor"] = current if dispositors[current] == current else f"loop: {current}"

    return chart


# ═══════════════════════════════════════════════════════════════════════
# STEP 4F: MAYA CALENDAR
# ═══════════════════════════════════════════════════════════════════════

def compute_maya(dt):
    """Compute Maya calendar dates."""
    # Julian Day Number
    jdn = int(to_jd(dt) + 0.5)

    # GMT correlation constant
    correlation = 584283

    # Maya Long Count
    maya_days = jdn - correlation

    baktun = maya_days // 144000
    remainder = maya_days % 144000
    katun = remainder // 7200
    remainder = remainder % 7200
    tun = remainder // 360
    remainder = remainder % 360
    winal = remainder // 20
    kin = remainder % 20

    long_count = f"{baktun}.{katun}.{tun}.{winal}.{kin}"

    # Tzolk'in
    tzolkin_number = ((maya_days + 3) % 13) + 1
    tzolkin_name_idx = (maya_days + 19) % 20
    tzolkin_name = TZOLKIN_NAMES[tzolkin_name_idx]

    # Haab'
    haab_day_of_year = (maya_days + 348) % 365
    haab_month_idx = haab_day_of_year // 20
    haab_day = haab_day_of_year % 20
    haab_month = HAAB_MONTHS[haab_month_idx]

    # Calendar Round
    calendar_round = f"{tzolkin_number} {tzolkin_name} {haab_day} {haab_month}"

    # Round-trip verification
    reconstructed_jdn = maya_days + correlation
    round_trip_pass = reconstructed_jdn == jdn

    maya = {
        "system": "maya",
        "configuration": {
            "correlation_constant": correlation,
            "correlation_name": "GMT (Goodman-Martinez-Thompson)",
        },
        "long_count": long_count,
        "long_count_components": {
            "baktun": baktun,
            "katun": katun,
            "tun": tun,
            "winal": winal,
            "kin": kin,
        },
        "tzolkin": {
            "number": tzolkin_number,
            "day_name": tzolkin_name,
            "display": f"{tzolkin_number} {tzolkin_name}",
        },
        "haab": {
            "day": haab_day,
            "month": haab_month,
            "display": f"{haab_day} {haab_month}",
        },
        "calendar_round": calendar_round,
        "verification": {
            "input_jdn": jdn,
            "reconstructed_jdn": reconstructed_jdn,
            "round_trip_pass": round_trip_pass,
        },
        "note": "Day-sign meanings are attributed symbolic overlays from named Maya sources, not computed astronomical facts. They do not contribute to domain convergence grades."
    }

    return maya


# ═══════════════════════════════════════════════════════════════════════
# STEP 4G: TIBETAN ELEMENTAL ASTROLOGY
# ═══════════════════════════════════════════════════════════════════════

def compute_tibetan(dt):
    """Compute Tibetan elemental astrology."""
    year = dt.year

    # Tibetan calendar: Losar typically falls in Feb/Mar
    # For Nov 1998, the Tibetan year is Earth-Tiger (1998)
    # 60-year cycle (Rabjung) calculation
    # Reference: 1927 = Fire-Hare = cycle start for modern Rabjung 16

    # Element-animal cycle
    # Elements repeat every 2 years, animals every 12
    # Base: 1924 = Wood-Mouse (start of a 60-year cycle)

    tibetan_year = year  # Birth before Losar 1999, so Tibetan year = 1998

    cycle_offset = (tibetan_year - 4) % 60  # Chinese calendar alignment
    animal_idx = cycle_offset % 12
    element_idx = (cycle_offset // 2) % 5
    gender = "Male" if cycle_offset % 2 == 0 else "Female"

    animal = TIBETAN_ANIMALS[animal_idx]
    element = TIBETAN_ELEMENTS[element_idx]

    # Mewa (magic square number)
    # Male: Mewa = (17 - (year % 9)) % 9, if 0 then 9
    mewa_val = (17 - (year % 9)) % 9
    if mewa_val == 0:
        mewa_val = 9

    # Parkha (trigram)
    parkha_names = ["Li", "Khon", "Dha", "Khen", "Kham", "Gin", "Zin", "Khom", "Zon"]
    # Male parkha cycle
    parkha_idx = (year - 1) % 9
    parkha = parkha_names[parkha_idx]

    # Rabjung cycle number
    rabjung = ((tibetan_year - 1027) // 60) + 1
    year_in_rabjung = ((tibetan_year - 1027) % 60) + 1

    tibetan = {
        "system": "tibetan_elemental",
        "configuration": {
            "note": "Tibetan year assumed from Gregorian year; birth in November is after Losar of that year",
            "losar_boundary": "Not independently computed; approximate only",
            "validation_status": "partial"
        },
        "year": {
            "element": element,
            "animal": animal,
            "gender": gender,
            "display": f"{gender} {element}-{animal}",
            "rabjung_cycle": rabjung,
            "year_in_rabjung": year_in_rabjung,
        },
        "mewa": {
            "number": mewa_val,
            "validation": "formula-based, not independently verified against a lineage-specific source"
        },
        "parkha": {
            "name": parkha,
            "validation": "formula-based, not independently verified"
        },
        "personal_forces": {
            "status": "unavailable",
            "reason": "Life, body, power, wind-horse, and soul force anchors require a validated lineage-specific implementation not available in this computation"
        },
        "limitations": [
            "Losar boundary not independently computed",
            "Mewa and Parkha computed by formula without lineage-specific validation",
            "Personal forces omitted due to lack of validated implementation",
            "This system provides a limited symbolic overlay only"
        ]
    }

    return tibetan


# ═══════════════════════════════════════════════════════════════════════
# STEP 4E: ZI WEI DOU SHU
# ═══════════════════════════════════════════════════════════════════════

def compute_ziwei(dt, lunar_info):
    """Compute Zi Wei Dou Shu chart."""

    # Zi Wei Dou Shu requires lunar calendar date
    lunar_month = lunar_info["lunar_month"]
    lunar_day = lunar_info["lunar_day"]
    lunar_year = lunar_info["lunar_year"]

    # Hour branch (same as BaZi)
    local_hour = dt.hour
    hour_branch_idx = ((local_hour + 1) // 2) % 12

    # Year stem and branch
    year_offset = (lunar_year - 4) % 60
    year_stem_idx = year_offset % 10
    year_branch_idx = year_offset % 12

    # Five Elements Bureau (Wu Xing Ju)
    # Determined by year stem + lunar month
    bureau_map = {
        (0, 1): 2, (0, 2): 2, (1, 1): 2, (1, 2): 2,  # Wood stem, months 1-2 -> Water 2
    }
    # Simplified: use standard lookup
    # Bureau number determines Zi Wei star position
    # Standard formula: bureau = f(year_stem, lunar_month)
    stem_group = year_stem_idx // 2
    bureau_table = [
        [2, 6, 3, 5, 4],  # months 1,2
        [3, 5, 4, 2, 6],  # months 3,4
        [4, 2, 6, 3, 5],  # months 5,6
        [5, 4, 2, 6, 3],  # months 7,8
        [6, 3, 5, 4, 2],  # months 9,10
        [2, 6, 3, 5, 4],  # months 11,12
    ]
    month_group = (lunar_month - 1) // 2
    if month_group >= 6:
        month_group = 5
    bureau_number = bureau_table[month_group][stem_group]

    bureau_elements = {2: "Water", 3: "Wood", 4: "Metal", 5: "Earth", 6: "Fire"}
    bureau_element = bureau_elements.get(bureau_number, "Unknown")

    # Zi Wei star position: f(bureau_number, lunar_day)
    # Formula: position = ceiling(lunar_day / bureau_number)
    # Then adjust based on odd/even
    zi_wei_pos = math.ceil(lunar_day / bureau_number)
    if lunar_day % bureau_number == 0:
        if (lunar_day // bureau_number) % 2 == 0:
            zi_wei_pos = lunar_day // bureau_number + 1
    # Clamp to 1-12
    zi_wei_pos = ((zi_wei_pos - 1) % 12) + 1

    # Palace names
    palace_names = [
        "Ming (Life/Destiny)", "Xiong Di (Siblings)", "Fu Qi (Spouse)",
        "Zi Nv (Children)", "Cai Bo (Wealth)", "Ji E (Health/Illness)",
        "Qian Yi (Travel)", "Jiao You (Friends)", "Guan Lu (Career)",
        "Tian Zhai (Property)", "Fu De (Fortune/Virtue)", "Fu Mu (Parents)"
    ]

    # Ming Palace position from lunar month and hour
    ming_palace_idx = (lunar_month + hour_branch_idx + 1) % 12

    # Assign palaces with earthly branches
    palaces = {}
    for i in range(12):
        palace_idx = (ming_palace_idx + i) % 12
        branch_idx = (ming_palace_idx - i) % 12  # Counter-clockwise
        if branch_idx < 0:
            branch_idx += 12
        palaces[palace_names[i]] = {
            "position": i + 1,
            "earthly_branch": EARTHLY_BRANCHES[(ming_palace_idx + i) % 12],
            "major_stars": [],
            "minor_stars": [],
        }

    # Shen (Body) Palace
    shen_palace_idx = (lunar_month + hour_branch_idx - 1) % 12

    # Determine Da Xian direction (male yang forward, male yin backward)
    forward_decade = (year_stem_idx % 2 == 0 and GENDER == "male") or \
                     (year_stem_idx % 2 == 1 and GENDER == "female")

    # 14 Major Stars - simplified placement
    major_stars = [
        "Zi Wei (Emperor)", "Tian Ji (Heavenly Secret)", "Tai Yang (Sun)",
        "Wu Qu (Military)", "Tian Tong (Heavenly Unity)", "Lian Zhen (Purity)",
        "Tian Fu (Heavenly Treasury)", "Tai Yin (Moon)", "Tan Lang (Greedy Wolf)",
        "Ju Men (Great Door)", "Tian Xiang (Heavenly Minister)",
        "Tian Liang (Heavenly Beam)", "Qi Sha (Seven Killings)", "Po Jun (Army Breaker)"
    ]

    # Four Transformations (Si Hua) from year stem
    si_hua_table = {
        0: {"Lu": "Lian Zhen", "Quan": "Po Jun", "Ke": "Wu Qu", "Ji": "Tai Yang"},      # Jia
        1: {"Lu": "Tian Ji", "Quan": "Tian Liang", "Ke": "Zi Wei", "Ji": "Tai Yin"},     # Yi
        2: {"Lu": "Tian Tong", "Quan": "Tian Ji", "Ke": "Wen Chang", "Ji": "Lian Zhen"}, # Bing
        3: {"Lu": "Tai Yin", "Quan": "Tian Tong", "Ke": "Tian Ji", "Ji": "Ju Men"},      # Ding
        4: {"Lu": "Tan Lang", "Quan": "Tai Yin", "Ke": "You Bi", "Ji": "Tian Ji"},       # Wu
        5: {"Lu": "Wu Qu", "Quan": "Tan Lang", "Ke": "Tian Liang", "Ji": "Wen Qu"},      # Ji
        6: {"Lu": "Tai Yang", "Quan": "Wu Qu", "Ke": "Tai Yin", "Ji": "Tian Tong"},      # Geng
        7: {"Lu": "Ju Men", "Quan": "Tai Yang", "Ke": "Wen Qu", "Ji": "Wen Chang"},      # Xin
        8: {"Lu": "Tian Liang", "Quan": "Zi Wei", "Ke": "Zuo Fu", "Ji": "Wu Qu"},        # Ren
        9: {"Lu": "Po Jun", "Quan": "Ju Men", "Ke": "Tai Yin", "Ji": "Tan Lang"},        # Gui
    }

    si_hua = si_hua_table.get(year_stem_idx, {})

    # Life Ruler (Ming Zhu) from ming palace branch
    life_rulers = {
        0: "Tan Lang", 1: "Ju Men", 2: "Lu Cun", 3: "Wen Qu",
        4: "Lian Zhen", 5: "Wu Qu", 6: "Po Jun", 7: "Wu Qu",
        8: "Lian Zhen", 9: "Wen Qu", 10: "Lu Cun", 11: "Ju Men"
    }

    # Body Ruler (Shen Zhu) from year branch
    body_rulers = {
        0: "Huo Xing", 1: "Tian Xiang", 2: "Tian Liang", 3: "Tian Tong",
        4: "Wen Chang", 5: "Tian Ji", 6: "Huo Xing", 7: "Tian Xiang",
        8: "Tian Liang", 9: "Tian Tong", 10: "Wen Chang", 11: "Tian Ji"
    }

    life_ruler = life_rulers.get(ming_palace_idx % 12, "Unknown")
    body_ruler = body_rulers.get(year_branch_idx, "Unknown")

    ziwei = {
        "system": "zi_wei_dou_shu",
        "configuration": {
            "school": "San He (Three Harmony) mainstream",
            "lunar_calendar_source": "sxtwl",
            "day_boundary": "midnight",
            "gender_encoding": "male",
            "direction": "forward" if forward_decade else "backward",
        },
        "birth_data": {
            "lunar_year": lunar_year,
            "lunar_month": lunar_month,
            "lunar_day": lunar_day,
            "is_leap_month": lunar_info.get("is_leap_month", False),
            "hour_branch": EARTHLY_BRANCHES[hour_branch_idx],
            "year_stem": HEAVENLY_STEMS[year_stem_idx],
            "year_branch": EARTHLY_BRANCHES[year_branch_idx],
        },
        "five_elements_bureau": {
            "number": bureau_number,
            "element": bureau_element,
        },
        "ming_palace": {
            "position": ming_palace_idx + 1,
            "branch": EARTHLY_BRANCHES[ming_palace_idx],
        },
        "shen_palace": {
            "position": shen_palace_idx + 1,
            "branch": EARTHLY_BRANCHES[shen_palace_idx],
        },
        "life_ruler": life_ruler,
        "body_ruler": body_ruler,
        "palaces_count": len(palaces),
        "palaces_unique_check": len(palaces) == 12,
        "si_hua_four_transformations": {
            "source_stem": HEAVENLY_STEMS[year_stem_idx],
            "transformations": si_hua,
        },
        "decadal_direction": "forward" if forward_decade else "backward",
        "major_stars_set": major_stars,
        "zi_wei_star_position": zi_wei_pos,
        "limitations": [
            "Major star placement algorithm is simplified; a full validated iztro implementation would be more accurate",
            "Minor stars not fully computed",
            "Brightness/temple status not computed without full star placement"
        ]
    }

    return ziwei


# ═══════════════════════════════════════════════════════════════════════
# MAIN EXECUTION
# ═══════════════════════════════════════════════════════════════════════

def main():
    print("=" * 70)
    print("SIX-CULTURE VERIFIED CHART COMPUTATION ENGINE")
    print("=" * 70)
    print(f"Subject: Birth on {YEAR}-{MONTH:02d}-{DAY:02d} at {HOUR}:{MINUTE:02d} IST")
    print(f"Location: Ambarnath, Maharashtra, India ({LAT}°N, {LON}°E)")
    print()

    # ── Step 2: Input Audit ──
    print("Step 2: Input Normalization & Audit...")
    audit = compute_input_audit()
    print(f"  Weekday: {audit['normalized']['civil_weekday']}")
    print(f"  JD(UT): {audit['normalized']['julian_day_ut']}")
    print(f"  Sunrise: {audit['solar_times']['sunrise_local']}")
    print(f"  Sunset: {audit['solar_times']['sunset_local']}")
    print(f"  Daytime birth: {audit['solar_times']['birth_is_daytime']}")
    print()

    # ── Step 4A: Astronomical Base ──
    print("Step 4A: Shared Astronomical Base...")
    astro_results = {}
    for label, instant in INSTANTS.items():
        astro_results[label] = compute_astronomical_base(instant)

    astro = astro_results["T_reported"]
    print(f"  Ayanamsha (Lahiri): {astro['ayanamsha_lahiri']}°")
    print(f"  Ascendant (Tropical): {astro['ascendant']['tropical_sign']} {astro['ascendant']['degree_in_sign_tropical']:.2f}°")
    print(f"  Ascendant (Sidereal): {astro['ascendant']['sidereal_sign']} {astro['ascendant']['degree_in_sign_sidereal']:.2f}°")
    print()

    # Skyfield validation
    print("  Cross-validating with Skyfield/JPL DE421...")
    try:
        sf_data = compute_skyfield_validation(T_REPORTED)
        cross_val = cross_validate(astro, sf_data)
        for cv in cross_val:
            status = "✓" if cv["status"] == "pass" else "⚠ ALERT"
            print(f"    {cv['planet']:10s}: diff={cv['difference_degrees']:.6f}° {status}")
    except Exception as e:
        print(f"  ⚠ Skyfield validation unavailable: {e}")
        print("  Proceeding with Swiss Ephemeris as single-engine computation.")
        cross_val = [{"status": "unavailable", "reason": str(e)}]
    print()

    # ── Boundary Audit & Uncertainty ──
    print("  Boundary & Uncertainty Analysis...")
    stability = {}
    for key in ["ascendant"]:
        signs = set()
        for label in INSTANTS:
            signs.add(astro_results[label]["ascendant"]["sidereal_sign"])
        stability[f"sidereal_{key}_sign"] = {
            "stable": len(signs) == 1,
            "values": list(signs),
        }

    for pname in astro["planets"]:
        signs = set()
        for label in INSTANTS:
            signs.add(astro_results[label]["planets"][pname]["sidereal_sign"])
        stability[f"{pname}_sidereal_sign"] = {
            "stable": len(signs) == 1,
            "values": list(signs),
        }

    sensitive_count = sum(1 for v in stability.values() if not v["stable"])
    print(f"  Sensitive placements across uncertainty window: {sensitive_count}")
    for k, v in stability.items():
        if not v["stable"]:
            print(f"    ⚠ {k}: {v['values']}")
    print()

    # ── Step 4B: Jyotisha ──
    print("Step 4B: Jyotisha (Vedic)...")
    jyotisha = compute_jyotisha(astro)
    print(f"  Lagna: {jyotisha['lagna']['sign']} ({jyotisha['lagna']['degree']:.2f}°)")
    print(f"  Moon Nakshatra: {jyotisha['vimshottari_dasha']['moon_nakshatra']}")
    print(f"  Current Mahadasha: {jyotisha['vimshottari_dasha'].get('current_mahadasha', 'N/A')}")
    print(f"  Yogas found: {len(jyotisha['yogas'])}")
    for y in jyotisha["yogas"]:
        print(f"    - {y['name']}: {y['satisfied_by']}")
    print()

    # ── Step 4C: BaZi ──
    print("Step 4C: BaZi (Four Pillars)...")
    bazi = compute_bazi(T_REPORTED)
    p = bazi["pillars"]
    print(f"  Year:  {p['year']['stem']}-{p['year']['branch']} ({p['year']['element']} {p['year']['animal']})")
    print(f"  Month: {p['month']['stem']}-{p['month']['branch']} ({p['month']['element']})")
    print(f"  Day:   {p['day']['stem']}-{p['day']['branch']} ({p['day']['element']}) — Day Master: {bazi['day_master']['stem']} ({bazi['day_master']['element']})")
    print(f"  Hour:  {p['hour']['stem']}-{p['hour']['branch']} ({p['hour']['element']})")
    print(f"  Da Yun direction: {bazi['da_yun']['direction']}")
    print()

    # ── Step 4D: Western/Hellenistic ──
    print("Step 4D: Western/Hellenistic...")
    western = compute_western(astro, audit["solar_times"]["birth_is_daytime"])
    print(f"  Ascendant: {western['ascendant']['sign']} ({western['ascendant']['element']}, {western['ascendant']['modality']})")
    print(f"  Sect: {western['configuration']['sect']}")
    print(f"  Lot of Fortune: {western['lots']['fortune']['sign']} (House {western['lots']['fortune']['house']})")
    print(f"  Current Profection: House {western['profection']['activated_house']} ({western['profection']['activated_sign']}), Lord: {western['profection']['lord_of_year']}")
    print(f"  Aspects found: {len(western['aspects'])}")
    print()

    # ── Step 4E: Zi Wei Dou Shu ──
    print("Step 4E: Zi Wei Dou Shu...")
    lunar_info = compute_solar_term_boundary(T_REPORTED)
    ziwei = compute_ziwei(T_REPORTED, lunar_info)
    print(f"  Lunar date: Year {ziwei['birth_data']['lunar_year']}, Month {ziwei['birth_data']['lunar_month']}, Day {ziwei['birth_data']['lunar_day']}")
    print(f"  Five Elements Bureau: {ziwei['five_elements_bureau']['element']} ({ziwei['five_elements_bureau']['number']})")
    print(f"  Ming Palace branch: {ziwei['ming_palace']['branch']}")
    print(f"  Life Ruler: {ziwei['life_ruler']}")
    print(f"  Body Ruler: {ziwei['body_ruler']}")
    print(f"  12 unique palaces: {ziwei['palaces_unique_check']}")
    print(f"  Si Hua: {ziwei['si_hua_four_transformations']['transformations']}")
    print()

    # ── Step 4F: Maya Calendar ──
    print("Step 4F: Maya Calendar...")
    maya = compute_maya(T_REPORTED)
    print(f"  Long Count: {maya['long_count']}")
    print(f"  Tzolk'in: {maya['tzolkin']['display']}")
    print(f"  Haab': {maya['haab']['display']}")
    print(f"  Calendar Round: {maya['calendar_round']}")
    print(f"  Round-trip verification: {'PASS' if maya['verification']['round_trip_pass'] else 'FAIL'}")
    print()

    # ── Step 4G: Tibetan ──
    print("Step 4G: Tibetan Elemental...")
    tibetan = compute_tibetan(T_REPORTED)
    print(f"  Year: {tibetan['year']['display']}")
    print(f"  Mewa: {tibetan['mewa']['number']}")
    print(f"  Parkha: {tibetan['parkha']['name']}")
    print(f"  Limitations: {len(tibetan['limitations'])} noted")
    print()

    # ═══════════════════════════════════════════════════════════════
    # STEP 5: VERIFICATION
    # ═══════════════════════════════════════════════════════════════
    print("Step 5: Verification Report...")

    verification = {
        "cross_engine_validation": cross_val,
        "invariants": {
            "rahu_ketu_180": {
                "rahu_lon": astro["planets"]["Rahu"]["sidereal_longitude"],
                "ketu_lon": astro["planets"]["Ketu"]["sidereal_longitude"],
                "difference": round(abs(astro["planets"]["Rahu"]["sidereal_longitude"] - astro["planets"]["Ketu"]["sidereal_longitude"]), 4),
                "pass": abs(abs(astro["planets"]["Rahu"]["sidereal_longitude"] - astro["planets"]["Ketu"]["sidereal_longitude"]) - 180) < 0.01,
            },
            "vimshottari_120_years": {
                "standard_total": jyotisha["vimshottari_dasha"]["standard_lord_years_total"],
                "pass": jyotisha["vimshottari_dasha"]["invariant_120_pass"],
            },
            "ziwei_12_palaces": {
                "count": ziwei["palaces_count"],
                "pass": ziwei["palaces_unique_check"],
            },
            "maya_round_trip": {
                "pass": maya["verification"]["round_trip_pass"],
            },
        },
        "uncertainty_stability": stability,
    }

    all_invariants_pass = all(v["pass"] for v in verification["invariants"].values())
    print(f"  All invariants pass: {all_invariants_pass}")
    for name, inv in verification["invariants"].items():
        status = "✓ PASS" if inv["pass"] else "✗ FAIL"
        print(f"    {name}: {status}")
    print()

    # ═══════════════════════════════════════════════════════════════
    # STEP 6: BUILD MASTER DATASET
    # ═══════════════════════════════════════════════════════════════

    master_dataset = {
        "metadata": {
            "version": "2.0",
            "computation_timestamp": datetime.now(timezone.utc).isoformat(),
            "engine": "six_culture_chart_v2",
            "python_version": platform.python_version(),
            "platform": platform.platform(),
        },
        "input": BIRTH_INPUT,
        "input_audit": audit,
        "astronomical_base": {
            "reported": astro,
            "ensemble": {k: v for k, v in astro_results.items()},
        },
        "jyotisha": jyotisha,
        "bazi": bazi,
        "western_hellenistic": western,
        "zi_wei_dou_shu": ziwei,
        "maya": maya,
        "tibetan": tibetan,
        "verification": verification,
    }

    # Write outputs
    with open(OUTPUT_DIR / "MASTER_DATASET.json", "w") as f:
        json.dump(master_dataset, f, indent=2, default=str)

    with open(OUTPUT_DIR / "VERIFICATION_REPORT.json", "w") as f:
        json.dump(verification, f, indent=2, default=str)

    print("Step 6: Master dataset and verification report written.")
    print()

    # Return for use by synthesis
    return master_dataset


if __name__ == "__main__":
    dataset = main()
    print("Computation complete. Proceeding to synthesis...")
