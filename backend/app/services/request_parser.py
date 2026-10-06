import re
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

# ==========================================
# Domain Dictionaries & Normalized Mappings
# ==========================================

CITY_MAPPINGS: Dict[str, Dict[str, str]] = {
    "bengaluru": {
        "city": "Bengaluru",
        "state": "Karnataka",
        "country": "India",
        "aliases": ["bengaluru", "bangalore", "bengalooru", "blr"],
    },
    "pune": {
        "city": "Pune",
        "state": "Maharashtra",
        "country": "India",
        "aliases": ["pune", "poona", "puney"],
    },
    "mumbai": {
        "city": "Mumbai",
        "state": "Maharashtra",
        "country": "India",
        "aliases": ["mumbai", "bombay"],
    },
    "hyderabad": {
        "city": "Hyderabad",
        "state": "Telangana",
        "country": "India",
        "aliases": ["hyderabad", "cyberabad", "hyd"],
    },
    "delhi": {
        "city": "Delhi",
        "state": "Delhi",
        "country": "India",
        "aliases": ["delhi", "new delhi", "ncr"],
    },
    "chennai": {
        "city": "Chennai",
        "state": "Tamil Nadu",
        "country": "India",
        "aliases": ["chennai", "madras"],
    },
    "kochi": {
        "city": "Kochi",
        "state": "Kerala",
        "country": "India",
        "aliases": ["kochi", "cochin", "ernakulam"],
    },
    "kolkata": {
        "city": "Kolkata",
        "state": "West Bengal",
        "country": "India",
        "aliases": ["kolkata", "calcutta"],
    },
    "gurgaon": {
        "city": "Gurgaon",
        "state": "Haryana",
        "country": "India",
        "aliases": ["gurgaon", "gurugram"],
    },
    "noida": {
        "city": "Noida",
        "state": "Uttar Pradesh",
        "country": "India",
        "aliases": ["noida", "greater noida"],
    },
    "ahmedabad": {
        "city": "Ahmedabad",
        "state": "Gujarat",
        "country": "India",
        "aliases": ["ahmedabad", "amdavad"],
    },
    "jaipur": {
        "city": "Jaipur",
        "state": "Rajasthan",
        "country": "India",
        "aliases": ["jaipur"],
    },
    "chandigarh": {
        "city": "Chandigarh",
        "state": "Chandigarh",
        "country": "India",
        "aliases": ["chandigarh", "mohali", "panchkula"],
    },
    "thiruvananthapuram": {
        "city": "Thiruvananthapuram",
        "state": "Kerala",
        "country": "India",
        "aliases": ["thiruvananthapuram", "trivandrum"],
    },
}

AREA_TO_CITY: Dict[str, str] = {
    # Bengaluru
    "whitefield": "bengaluru",
    "marathahalli": "bengaluru",
    "koramangala": "bengaluru",
    "hsr layout": "bengaluru",
    "hsr": "bengaluru",
    "electronic city": "bengaluru",
    "ecity": "bengaluru",
    "indiranagar": "bengaluru",
    "jayanagar": "bengaluru",
    "bellandur": "bengaluru",
    "btm layout": "bengaluru",
    "btm": "bengaluru",
    "sarjapur": "bengaluru",
    "hebbal": "bengaluru",
    "yelahanka": "bengaluru",
    "rajajinagar": "bengaluru",
    "malleshwaram": "bengaluru",
    # Pune
    "hinjewadi": "pune",
    "hinjawadi": "pune",
    "wakad": "pune",
    "baner": "pune",
    "balewadi": "pune",
    "kothrud": "pune",
    "viman nagar": "pune",
    "aundh": "pune",
    "magarpatta": "pune",
    "kharadi": "pune",
    "hadapsar": "pune",
    "shivaji nagar": "pune",
    "koregaon park": "pune",
    "kalyani nagar": "pune",
    # Kochi
    "kakkanad": "kochi",
    "edappally": "kochi",
    "kaloor": "kochi",
    "aluva": "kochi",
    "fort kochi": "kochi",
    "panampilly nagar": "kochi",
    # Hyderabad
    "gachibowli": "hyderabad",
    "madhapur": "hyderabad",
    "kondapur": "hyderabad",
    "hitec city": "hyderabad",
    "jubilee hills": "hyderabad",
    # Gurgaon
    "cyber city": "gurgaon",
    "dlf phase": "gurgaon",
    "sohna road": "gurgaon",
    "golf course road": "gurgaon",
    # Noida
    "sector 62": "noida",
    "sector 18": "noida",
    # Kolkata
    "salt lake": "kolkata",
    "new town": "kolkata",
    # Chennai
    "velachery": "chennai",
    "omr": "chennai",
    "adyar": "chennai",
    "t nagar": "chennai",
}

AREA_CANONICAL_NAMES: Dict[str, str] = {
    "whitefield": "Whitefield",
    "marathahalli": "Marathahalli",
    "koramangala": "Koramangala",
    "hsr layout": "HSR Layout",
    "hsr": "HSR Layout",
    "electronic city": "Electronic City",
    "ecity": "Electronic City",
    "indiranagar": "Indiranagar",
    "jayanagar": "Jayanagar",
    "bellandur": "Bellandur",
    "btm layout": "BTM Layout",
    "btm": "BTM Layout",
    "sarjapur": "Sarjapur",
    "hebbal": "Hebbal",
    "yelahanka": "Yelahanka",
    "rajajinagar": "Rajajinagar",
    "malleshwaram": "Malleshwaram",
    "hinjewadi": "Hinjewadi",
    "hinjawadi": "Hinjewadi",
    "wakad": "Wakad",
    "baner": "Baner",
    "balewadi": "Balewadi",
    "kothrud": "Kothrud",
    "viman nagar": "Viman Nagar",
    "aundh": "Aundh",
    "magarpatta": "Magarpatta",
    "kharadi": "Kharadi",
    "hadapsar": "Hadapsar",
    "shivaji nagar": "Shivaji Nagar",
    "koregaon park": "Koregaon Park",
    "kalyani nagar": "Kalyani Nagar",
    "kakkanad": "Kakkanad",
    "edappally": "Edappally",
    "kaloor": "Kaloor",
    "aluva": "Aluva",
    "fort kochi": "Fort Kochi",
    "panampilly nagar": "Panampilly Nagar",
    "gachibowli": "Gachibowli",
    "madhapur": "Madhapur",
    "kondapur": "Kondapur",
    "hitec city": "HITEC City",
    "jubilee hills": "Jubilee Hills",
    "cyber city": "Cyber City",
    "dlf phase": "DLF Phase",
    "sohna road": "Sohna Road",
    "golf course road": "Golf Course Road",
    "sector 62": "Sector 62",
    "sector 18": "Sector 18",
    "salt lake": "Salt Lake",
    "new town": "New Town",
    "velachery": "Velachery",
    "omr": "OMR",
    "adyar": "Adyar",
    "t nagar": "T. Nagar",
}

NEEDS_CATEGORIES: Dict[str, List[Tuple[str, str]]] = {
    "accommodation": [
        (r"\bpg\b", "PG accommodation"),
        (r"\bpaying\s+guest\b", "PG accommodation"),
        (r"\bhostel\b", "hostel accommodation"),
        (r"\b(1\s*bhk|2\s*bhk|3\s*bhk)\b", "apartment / flat"),
        (r"\b(flat|apartment|flatmate|room)\b", "flat / room rental"),
        (r"\bco-?living\b", "co-living space"),
        (r"\baccommodation\b", "general accommodation"),
    ],
    "food": [
        (r"\bvegetarian\s+food\b", "vegetarian food"),
        (r"\bveg\s+food\b", "vegetarian food"),
        (r"\bnon-?veg(etarian)?\s+food\b", "non-vegetarian food"),
        (r"\btiffin(\s+services?)?\b", "tiffin service"),
        (r"\bmess(\s+food)?\b", "mess food"),
        (r"\b(cook|dabba)\b", "home cooking / dabba service"),
        (r"\b(meals?|food)\b", "food & meals"),
    ],
    "transport": [
        (r"\bmetro(\s+station|\s+route)?\b", "metro navigation"),
        (r"\bbus(\s+route|\s+passes)?\b", "bus transit"),
        (r"\b(commute|cab|auto|rickshaw)\b", "local commute"),
        (r"\bpublic\s+transport\b", "public transportation"),
    ],
    "jobs": [
        (r"\b(first\s+job|tech\s+job|it\s+job|developer\s+job)\b", "tech / IT jobs"),
        (r"\b(internship|intern)\b", "internship"),
        (r"\b(jobs?|hiring|careers?)\b", "employment"),
    ],
    "healthcare": [
        (r"\b(doctor|clinic|hospital|pharmacy|chemist)\b", "healthcare / medical"),
    ],
    "education": [
        (r"\b(college|university|school|coaching|tuition)\b", "education / training"),
    ],
    "local guidance": [
        (r"\b(local\s+guid(e|ance)|local\s+tips|settling\s+in|neighborhood\s+guide)\b", "local guidance"),
    ],
    "documentation": [
        (r"\b(rental?\s+agreement|police\s+verification|aadhaar|gas\s+connection|bank\s+account)\b", "legal & documentation"),
    ],
}

PREFERENCE_PATTERNS: List[Tuple[str, str]] = [
    (r"\b(pure\s+veg|vegetarian|veg)\b", "vegetarian"),
    (r"\bnon-?veg(etarian)?\b", "non-vegetarian"),
    (r"\b(affordable|cheap|budget-?friendly|economical|low-?cost)\b", "affordable"),
    (r"\bnear\s+(the\s+)?metro\b", "near metro"),
    (r"\bnear\s+(my\s+)?(office|company|workplace|tech\s+park|itpl)\b", "near office"),
    (r"\b(fully\s+furnished|furnished)\b", "furnished"),
    (r"\bsemi-?furnished\b", "semi-furnished"),
    (r"\b(girls|women|female)-?friendly\b", "female-friendly"),
    (r"\b(bachelor|student)-?friendly\b", "bachelor-friendly"),
    (r"\b(family|kids)-?friendly\b", "family-friendly"),
    (r"\b(quiet|peaceful)\b", "quiet environment"),
    (r"\b(single\s+room|private\s+room)\b", "private room"),
    (r"\b(sharing|shared\s+room)\b", "shared room"),
    (r"\bpet-?friendly\b", "pet-friendly"),
]

CONTEXT_PATTERNS: List[Tuple[str, str]] = [
    (r"\b(first\s+job|first\s+it\s+job)\b", "first job"),
    (r"\b(fresher|new\s+graduate|recent\s+grad)\b", "fresher / new graduate"),
    (r"\b(intern|internship)\b", "intern"),
    (r"\b(college\s+student|student)\b", "student"),
    (r"\b(working\s+professional|software\s+engineer|tech\s+worker)\b", "working professional"),
    (r"\b(new\s+to\s+(the\s+)?city|moving\s+to|relocating)\b", "relocating newcomer"),
    (r"\b(moving\s+next\s+month|next\s+week)\b", "moving soon"),
]


# ==========================================
# Extraction Result Schema
# ==========================================

class BudgetInfo(BaseModel):
    amount: Optional[float] = None
    currency: Optional[str] = "INR"
    operator: Optional[str] = None  # "<=", ">=", "==", "~="
    period: Optional[str] = None  # "monthly", "weekly", "daily", "yearly", None
    raw_text: Optional[str] = None


class ExtractedNeed(BaseModel):
    category: str
    item: str
    matched_text: str
    source: str = "explicit_text"


class ExtractedLocation(BaseModel):
    city: Optional[str] = None
    area: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = "India"
    city_source: Optional[str] = None
    area_source: Optional[str] = None
    display_name: Optional[str] = None
    formatted_address: Optional[str] = None
    google_place_id: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    location_precision: Optional[str] = None
    location_source: Optional[str] = None
    origin_city: Optional[str] = None


class ExtractedRequest(BaseModel):
    raw_text: str
    intent: str = "newcomer_assistance"
    location: ExtractedLocation
    needs: List[ExtractedNeed] = Field(default_factory=list)
    budget: Optional[BudgetInfo] = None
    preferences: List[str] = Field(default_factory=list)
    user_context: List[str] = Field(default_factory=list)
    explanations: Dict[str, Any] = Field(default_factory=dict)
    extraction_method: str = "deterministic_nlp_rule_based_v1"


# ==========================================
# Parser Implementation
# ==========================================

def _extract_location(text: str) -> ExtractedLocation:
    """
    Extract and normalize target destination location from natural language.
    Strictly separates origin vs destination, supports compound localities (e.g. 'Boisar, Mumbai'),
    and leverages Google forward geocoding for authoritative coordinates and administrative hierarchy.
    """
    from app.services.google_maps_service import google_maps_service

    lower_text = text.lower()
    loc = ExtractedLocation()

    # 1. Detect Origin City (e.g. "from Bangalore to Pune", "leaving Delhi")
    # Store strictly in loc.origin_city so it is never confused with target destination
    origin_match = re.search(
        r"\b(?:from|origin|leaving|staying in|living in|currently in|native is)\s+([A-Za-z\s]{2,30}?)(?=(?:\s+to\b|,|\.|\s+and|\s+for|$))",
        lower_text,
    )
    if origin_match:
        cand_origin = origin_match.group(1).strip()
        for c_key, c_meta in CITY_MAPPINGS.items():
            if any(alias in cand_origin for alias in c_meta["aliases"]):
                loc.origin_city = c_meta["city"]
                break
        if not loc.origin_city and cand_origin:
            loc.origin_city = cand_origin.title()

    # 2. Extract Candidate Destination String
    # Look for relocation destination signals e.g. "shifting to boisar,mumbai", "moving to Kakkanad, Kochi"
    dest_match = re.search(
        r"(?:(?:shifting|moving|relocating|relocate|settling|settle|heading|going|new|transferred|transferring)\s+to|(?:living|staying)\s+in)\s+([A-Za-z0-9\s,.-]+?)(?=(?:\s+(?:for|i\s+want|want|looking|need|searching|please|and\s+also|where|flat|pg|mess|room|hostel|job|internship|work|near|with|at|under|budget|next|\.))|$)",
        lower_text,
    )

    candidate_dest_raw: Optional[str] = None
    if dest_match:
        raw_candidate = dest_match.group(1).strip()
        for prefix in ["the ", "a ", "an ", "im ", "i'm "]:
            if raw_candidate.startswith(prefix):
                raw_candidate = raw_candidate[len(prefix):].strip()
        if len(raw_candidate) >= 2 and not any(raw_candidate == w for w in ["flat", "pg", "mess", "room", "food", "job"]):
            candidate_dest_raw = raw_candidate

    # 3. Handle Compound Relocation Destination (e.g. "boisar,mumbai" or "kakkanad, kochi")
    # If the user provides "Locality, City/State" where the locality is an independent town not in AREA_TO_CITY,
    # the primary locality must take precedence over the parent metropolitan city.
    if candidate_dest_raw and any(sep in candidate_dest_raw for sep in [",", "/"]):
        parts = [p.strip() for p in re.split(r"[,/]", candidate_dest_raw) if p.strip()]
        p0_lower = parts[0].lower() if parts else ""
        if p0_lower in AREA_TO_CITY:
            loc.area = AREA_CANONICAL_NAMES[p0_lower]
            loc.area_source = "explicit_text"
            parent_city_key = AREA_TO_CITY[p0_lower]
            loc.city = CITY_MAPPINGS[parent_city_key]["city"]
            loc.state = CITY_MAPPINGS[parent_city_key]["state"]
            loc.country = CITY_MAPPINGS[parent_city_key]["country"]
            loc.city_source = "explicit_text"
        else:
            # Independent locality / suburb (e.g. Boisar)
            loc.city = parts[0].title()
            loc.area = None
            loc.city_source = "explicit_text"
            loc.country = "India"
            if len(parts) > 1:
                sec_lower = parts[1].lower()
                for c_key, c_meta in CITY_MAPPINGS.items():
                    if any(alias in sec_lower for alias in c_meta["aliases"]):
                        loc.state = c_meta["state"]
                        break

            # Forward geocode to resolve canonical coordinates and administrative details
            resolved = google_maps_service.geocode_address(candidate_dest_raw)
            if not resolved or resolved.is_unresolved:
                resolved = google_maps_service.geocode_address(parts[0])

            if resolved and not resolved.is_unresolved:
                if resolved.city:
                    loc.city = resolved.city
                if resolved.area:
                    loc.area = resolved.area
                if resolved.state:
                    loc.state = resolved.state
                loc.country = resolved.country or "India"
                loc.display_name = resolved.display_name or resolved.name or loc.city
                loc.formatted_address = resolved.formatted_address
                loc.google_place_id = resolved.google_place_id
                loc.latitude = resolved.latitude
                loc.longitude = resolved.longitude
                loc.location_precision = resolved.location_precision or "locality"
                loc.location_source = resolved.location_source or "google_places"
            return loc

    # 4. Standard Detection (Area & City Matching)
    # Area detection
    detected_area_key: Optional[str] = None
    for area_key in sorted(AREA_TO_CITY.keys(), key=len, reverse=True):
        pattern = rf"\b{re.escape(area_key)}\b"
        if re.search(pattern, lower_text):
            detected_area_key = area_key
            loc.area = AREA_CANONICAL_NAMES[area_key]
            loc.area_source = "explicit_text"
            break

    # City detection (skipping origin city if detected)
    detected_city_key: Optional[str] = None
    for city_key, city_meta in CITY_MAPPINGS.items():
        if loc.origin_city and city_meta["city"].lower() == loc.origin_city.lower():
            continue
        for alias in city_meta["aliases"]:
            if re.search(rf"\b{re.escape(alias)}\b", lower_text):
                detected_city_key = city_key
                loc.city = city_meta["city"]
                loc.state = city_meta["state"]
                loc.country = city_meta["country"]
                loc.city_source = "explicit_text"
                break
        if detected_city_key:
            break

    # Indian state pattern detection (e.g. "moving to Ranoli, Gujarat")
    if not loc.city:
        indian_states = [
            "andhra pradesh", "arunachal pradesh", "assam", "bihar", "chhattisgarh",
            "goa", "gujarat", "haryana", "himachal pradesh", "jharkhand", "karnataka",
            "kerala", "madhya pradesh", "maharashtra", "manipur", "meghalaya", "mizoram",
            "nagaland", "odisha", "punjab", "rajasthan", "sikkim", "tamil nadu",
            "telangana", "tripura", "uttar pradesh", "uttarakhand", "west bengal",
            "delhi", "chandigarh", "puducherry"
        ]
        states_regex = "|".join(re.escape(s) for s in sorted(indian_states, key=len, reverse=True))
        state_match = re.search(rf"(?:(?:moving|relocating|shifted|shifting|settling|going|heading|living)\s+to|(?:in|near|at))\s+([A-Za-z\s]{{2,30}}?),\s*({states_regex})\b", lower_text)
        if not state_match:
            state_match = re.search(rf"\b([A-Za-z\s]{{2,30}}?),\s*({states_regex})\b", lower_text)
        if state_match:
            extracted_place = state_match.group(1).strip()
            for prefix in [
                "moving to", "relocating to", "shifted to", "shifting to",
                "going to", "heading to", "living in", "settling in",
                "in", "near", "at", "i am", "im", "i'm"
            ]:
                if extracted_place.lower().startswith(prefix):
                    extracted_place = extracted_place[len(prefix):].strip()
            matched_state = state_match.group(2).strip().title()
            if extracted_place and len(extracted_place) >= 2:
                loc.city = extracted_place.title()
                loc.area = extracted_place.title()
                loc.state = matched_state
                loc.country = "India"
                loc.city_source = "explicit_text"

    # Inferred from area if city missing
    if detected_area_key and not loc.city:
        inferred_city_key = AREA_TO_CITY[detected_area_key]
        city_meta = CITY_MAPPINGS[inferred_city_key]
        loc.city = city_meta["city"]
        loc.state = city_meta["state"]
        loc.country = city_meta["country"]
        loc.city_source = "inferred_from_area"

    # 5. Geocode to attach canonical coordinates, display name, and place ID
    if loc.city or loc.area:
        geo_query_parts = []
        if loc.area:
            geo_query_parts.append(loc.area)
        if loc.city and (not loc.area or loc.city.lower() != loc.area.lower()):
            geo_query_parts.append(loc.city)
        if loc.state:
            geo_query_parts.append(loc.state)
        geo_query = ", ".join(filter(None, geo_query_parts + ["India"]))
        if geo_query and geo_query != "India":
            resolved = google_maps_service.geocode_address(geo_query)
            if resolved and not resolved.is_unresolved:
                loc.latitude = resolved.latitude
                loc.longitude = resolved.longitude
                loc.google_place_id = resolved.google_place_id
                loc.formatted_address = resolved.formatted_address
                loc.display_name = resolved.display_name or resolved.name or loc.area or loc.city
                loc.location_precision = resolved.location_precision or "locality"
                loc.location_source = resolved.location_source or "google_places"

    return loc


def _extract_budget(text: str) -> Optional[BudgetInfo]:
    """
    Extract budget amount, currency, comparison operator, and period.
    Handles ₹, Rs, Rs., 10k, 10,000, 'under 10k', 'below ₹12,000/month', etc.
    """
    lower_text = text.lower()

    # Pattern for budget:
    # Optional operator: under, below, less than, up to, max, min, above
    # Optional symbol: ₹, rs, rs., inr, rupees
    # Amount: 10,000 | 10000 | 10k | 8.5k | 8k
    # Optional suffix: rupees, bucks, /-
    # Optional period: /month, per month, /mo, monthly, weekly, yearly, daily
    budget_regex = re.compile(
        r"(?P<operator>under|below|less\s+than|up\s+to|max|maximum|at\s+most|above|more\s+than|min|minimum|around|about|approx)?\s*"
        r"(?:₹|rs\.?|inr)?\s*"
        r"(?P<amount>\d+(?:,\d+)*(?:\.\d+)?\s*k|\d+(?:,\d+)*(?:\.\d+)?)\s*"
        r"(?:rupees?|rs\.?|bucks|/-)?\s*"
        r"(?P<period>/month|per\s+month|/mo|monthly|a\s+month|/week|per\s+week|/wk|weekly|a\s+week|/day|per\s+day|daily|/year|per\s+year|/yr|yearly|annually)?",
        re.IGNORECASE,
    )

    matches = list(budget_regex.finditer(text))
    # Filter for matches that genuinely look like a budget (have symbol, keyword, or suffix)
    for m in matches:
        raw_match = m.group(0).strip()
        op_raw = m.group("operator")
        amount_raw = m.group("amount")
        period_raw = m.group("period")

        # Discard standalone numbers that lack budget context unless marked by ₹/Rs/k/under
        has_currency_hint = any(sym in raw_match.lower() for sym in ["₹", "rs", "inr", "rupee", "k", "under", "below", "budget", "cost", "/mo", "month"])
        if not has_currency_hint and not op_raw and not period_raw:
            continue

        # Parse amount (handling 'k' multiplier and commas)
        amount_clean = amount_raw.lower().replace(",", "").strip()
        try:
            if amount_clean.endswith("k"):
                multiplier = 1000.0
                num_val = float(amount_clean[:-1]) * multiplier
            else:
                num_val = float(amount_clean)
        except ValueError:
            continue

        # Ignore tiny numbers like "1 job", "2 BHK" accidentally matched
        if num_val < 50 and not any(sym in raw_match.lower() for sym in ["₹", "rs", "inr"]):
            continue

        # Determine operator
        op: Optional[str] = None
        if op_raw:
            op_lower = op_raw.lower()
            if any(w in op_lower for w in ["under", "below", "less than", "up to", "max", "at most"]):
                op = "<="
            elif any(w in op_lower for w in ["above", "more than", "min", "minimum"]):
                op = ">="
            elif any(w in op_lower for w in ["around", "about", "approx"]):
                op = "~="
        else:
            # Check context before match for "under" or "below"
            prefix = lower_text[: m.start()]
            if re.search(r"\b(under|below|less than|up to|max)\b\s*$", prefix):
                op = "<="

        # Determine period
        period: Optional[str] = None
        if period_raw:
            p_lower = period_raw.lower()
            if any(w in p_lower for w in ["month", "mo"]):
                period = "monthly"
            elif any(w in p_lower for w in ["week", "wk"]):
                period = "weekly"
            elif any(w in p_lower for w in ["day"]):
                period = "daily"
            elif any(w in p_lower for w in ["year", "yr", "annually"]):
                period = "yearly"
        else:
            # Lookahead for period in following words
            suffix = lower_text[m.end() : m.end() + 25]
            if re.search(r"\b(per\s+month|monthly|a\s+month|/mo)\b", suffix):
                period = "monthly"
            elif re.search(r"\b(per\s+week|weekly|a\s+week)\b", suffix):
                period = "weekly"
            elif re.search(r"\b(per\s+day|daily)\b", suffix):
                period = "daily"
            elif re.search(r"\b(per\s+year|yearly|annually)\b", suffix):
                period = "yearly"

        return BudgetInfo(
            amount=num_val,
            currency="INR",
            operator=op or "<=" if op_raw else op,
            period=period,
            raw_text=raw_match,
        )

    return None


def _extract_needs(text: str) -> List[ExtractedNeed]:
    """Extract category and specific items requested."""
    lower_text = text.lower()
    needs: List[ExtractedNeed] = []
    seen_categories = set()

    for category, pattern_list in NEEDS_CATEGORIES.items():
        for pattern, item_name in pattern_list:
            match = re.search(pattern, lower_text)
            if match:
                needs.append(
                    ExtractedNeed(
                        category=category,
                        item=item_name,
                        matched_text=match.group(0),
                        source="explicit_text",
                    )
                )
                seen_categories.add(category)
                # Found the most specific item for this category in this sentence
                break

    return needs


def _extract_preferences(text: str) -> List[str]:
    """Extract normalized user preferences (e.g. vegetarian, affordable, near metro)."""
    lower_text = text.lower()
    prefs: List[str] = []
    seen = set()

    for pattern, pref_name in PREFERENCE_PATTERNS:
        if re.search(pattern, lower_text):
            if pref_name not in seen:
                # Handle mutually exclusive vegetarian vs non-vegetarian
                if pref_name == "vegetarian" and "non-vegetarian" in seen:
                    continue
                if pref_name == "non-vegetarian" and "vegetarian" in seen:
                    prefs.remove("vegetarian")
                    seen.remove("vegetarian")
                prefs.append(pref_name)
                seen.add(pref_name)

    return prefs


def _extract_context(text: str) -> List[str]:
    """Extract user background or stage (e.g. first job, fresher, student, moving soon)."""
    lower_text = text.lower()
    contexts: List[str] = []
    seen = set()

    for pattern, ctx_name in CONTEXT_PATTERNS:
        if re.search(pattern, lower_text):
            if ctx_name not in seen:
                contexts.append(ctx_name)
                seen.add(ctx_name)

    return contexts


def parse_request(text: str) -> ExtractedRequest:
    """
    Main deterministic NLP requirement parser.
    Converts natural-language newcomer text into structured requirements,
    preserving raw text and providing transparent rule-based explanations.
    """
    clean_text = text.strip()
    if not clean_text:
        return ExtractedRequest(
            raw_text="",
            location=ExtractedLocation(),
            needs=[],
            budget=None,
            preferences=[],
            user_context=[],
            explanations={"status": "empty_input"},
        )

    location = _extract_location(clean_text)
    needs = _extract_needs(clean_text)
    budget = _extract_budget(clean_text)
    preferences = _extract_preferences(clean_text)
    user_context = _extract_context(clean_text)

    # Compile explainable metadata
    explanations = {
        "city_extracted": location.city,
        "city_source": location.city_source,
        "area_extracted": location.area,
        "area_source": location.area_source,
        "display_name": location.display_name,
        "latitude": location.latitude,
        "longitude": location.longitude,
        "google_place_id": location.google_place_id,
        "origin_city": location.origin_city,
        "needs_count": len(needs),
        "needs_categories": [n.category for n in needs],
        "budget_detected": budget is not None,
        "budget_amount": budget.amount if budget else None,
        "budget_operator": budget.operator if budget else None,
        "budget_period": budget.period if budget else None,
        "preferences_count": len(preferences),
        "user_context_items": user_context,
        "rule_engine": "deterministic_nlp_rule_based_v1",
        "confidence_level": "deterministic_rule_match",
    }

    return ExtractedRequest(
        raw_text=clean_text,
        intent="newcomer_assistance",
        location=location,
        needs=needs,
        budget=budget,
        preferences=preferences,
        user_context=user_context,
        explanations=explanations,
        extraction_method="deterministic_nlp_rule_based_v1",
    )
