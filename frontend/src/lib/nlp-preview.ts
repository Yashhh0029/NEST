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

  // 1. Detect City / Area
  for (const city of KNOWN_CITIES) {
    const regex = new RegExp(`\\b${city}\\b`, "i");
    if (regex.test(clean)) {
      items.push({
        id: `loc-city-${city}`,
        type: "location",
        label: city === "Bangalore" ? "Bengaluru" : city,
        icon: "📍",
      });
      break;
    }
  }

  for (const area of KNOWN_AREAS) {
    const regex = new RegExp(`\\b${area}\\b`, "i");
    if (regex.test(clean)) {
      items.push({
        id: `loc-area-${area}`,
        type: "location",
        label: area,
        icon: "📍",
      });
      break;
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
