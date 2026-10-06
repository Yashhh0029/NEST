export interface LocalPreviewItem {
  id: string;
  type: "location" | "need" | "budget" | "preference";
  label: string;
  icon: string;
}

const KNOWN_CITIES = [
  "Bengaluru",
  "Bangalore",
  "Pune",
  "Mumbai",
  "Hyderabad",
  "Delhi",
  "Chennai",
  "Kochi",
  "Cochin",
  "Kolkata",
  "Gurgaon",
  "Gurugram",
  "Noida",
  "Ahmedabad",
  "Jaipur",
  "Chandigarh",
  "Thiruvananthapuram",
];

const KNOWN_AREAS = [
  "Whitefield",
  "Koramangala",
  "Indiranagar",
  "HSR Layout",
  "Electronic City",
  "Bellandur",
  "Hinjewadi",
  "Baner",
  "Wakad",
  "Kothrud",
  "Viman Nagar",
  "Kakkanad",
  "Edappally",
  "Fort Kochi",
  "Gachibowli",
  "Madhapur",
  "Cyber City",
  "Salt Lake",
];

export function extractLocalPreview(text: string): LocalPreviewItem[] {
  const clean = text.trim();
  if (!clean || clean.length < 3) return [];

  const items: LocalPreviewItem[] = [];

  // 1. Detect Relocation / Movement Destination (e.g. "shifting to boisar,mumbai", "moving from Pune to Kochi")
  const destRegex = /\b(?:moving\s+to|shifting\s+to|relocating\s+to|settling\s+in|heading\s+to|going\s+to|transferred\s+to|relocate\s+to|shift\s+to|move\s+to)\s+([A-Za-z0-9\s,.-]+?)(?=\s+(?:for|to\s+live|i\s+need|i\s+want|need|want|looking|and\s+also|and\s+i|with|under|\b\d+k\b|₹|rs\.?|\.|$))/i;
  const destMatch = clean.match(destRegex);

  let locationDetected = false;

  if (destMatch && destMatch[1]) {
    let rawDest = destMatch[1].trim();
    // Clean filler prefixes
    for (const prefix of ["i am", "im", "i'm", "we are"]) {
      if (rawDest.toLowerCase().startsWith(prefix)) {
        rawDest = rawDest.slice(prefix.length).trim();
      }
    }
    const parts = rawDest.split(",").map((p) => p.trim()).filter(Boolean);
    const primaryPart = parts[0];
    if (primaryPart && primaryPart.length >= 2 && !/^(flat|room|pg|mess|food|help)$/i.test(primaryPart)) {
      const formatted = primaryPart.charAt(0).toUpperCase() + primaryPart.slice(1);
      items.push({
        id: `loc-dest-${formatted.toLowerCase()}`,
        type: "location",
        label: formatted === "Bangalore" ? "Bengaluru" : formatted,
        icon: "📍",
      });
      locationDetected = true;
    }
  }

  // 2. Fallback to Known Areas (prioritized over broader cities)
  if (!locationDetected) {
    for (const area of KNOWN_AREAS) {
      const regex = new RegExp(`\\b${area}\\b`, "i");
      if (regex.test(clean)) {
        items.push({
          id: `loc-area-${area}`,
          type: "location",
          label: area,
          icon: "📍",
        });
        locationDetected = true;
        break;
      }
    }
  }

  // 3. Fallback to Known Cities
  if (!locationDetected) {
    // Check if user specified "from <city>" - do not use origin as target destination if moving
    const originRegex = /\b(?:from|currently\s+(?:living\s+)?in|based\s+in|living\s+in)\s+([A-Za-z]+)\b/i;
    const originMatch = clean.match(originRegex);
    const originCity = originMatch ? originMatch[1].toLowerCase() : null;

    for (const city of KNOWN_CITIES) {
      const regex = new RegExp(`\\b${city}\\b`, "i");
      if (regex.test(clean)) {
        if (originCity && city.toLowerCase() === originCity && /\b(?:to|moving|shifting)\b/i.test(clean)) {
          // Skip origin city when a destination is expected
          continue;
        }
        items.push({
          id: `loc-city-${city}`,
          type: "location",
          label: city === "Bangalore" ? "Bengaluru" : city,
          icon: "📍",
        });
        break;
      }
    }
  }

  // 2. Detect Needs (PG, Flat, Food, Transport)
  if (/\b(pg|paying\s+guest|hostel)\b/i.test(clean)) {
    items.push({ id: "need-pg", type: "need", label: "PG Accommodation", icon: "🏠" });
  } else if (/\b(1bhk|2bhk|flat|apartment|house|room|rent)\b/i.test(clean)) {
    items.push({ id: "need-flat", type: "need", label: "Rental Housing", icon: "🏠" });
  }

  if (/\b(tiffin|mess|veg\s+food|non-?veg\s+food|meals?|cook)\b/i.test(clean)) {
    items.push({ id: "need-food", type: "need", label: "Food / Tiffin", icon: "🍛" });
  }

  if (/\b(metro|bus|commute|cab|transport)\b/i.test(clean)) {
    items.push({ id: "need-transport", type: "need", label: "Local Transport", icon: "🚇" });
  }

  // 3. Detect Budget (₹ / Rs / k)
  const budgetMatch = clean.match(/(?:₹|rs\.?|inr)?\s*(\d+(?:,\d+)*(?:\.\d+)?)\s*(k|thousand|lakh)?\b/i);
  if (budgetMatch && budgetMatch[1]) {
    let num = parseFloat(budgetMatch[1].replace(/,/g, ""));
    const suffix = (budgetMatch[2] || "").toLowerCase();
    if (suffix === "k" || suffix === "thousand") num *= 1000;
    else if (suffix === "lakh") num *= 100000;

    if (num >= 500 && num <= 500000) {
      items.push({
        id: "budget-preview",
        type: "budget",
        label: `₹${num.toLocaleString("en-IN")}`,
        icon: "💰",
      });
    }
  }

  // 4. Detect Preferences (Vegetarian, near metro, etc.)
  if (/\b(pure\s+veg|vegetarian|veg)\b/i.test(clean)) {
    items.push({ id: "pref-veg", type: "preference", label: "Vegetarian", icon: "🌱" });
  }
  if (/\b(near\s+(the\s+)?metro)\b/i.test(clean)) {
    items.push({ id: "pref-metro", type: "preference", label: "Near Metro", icon: "⚡" });
  }

  return items;
}
