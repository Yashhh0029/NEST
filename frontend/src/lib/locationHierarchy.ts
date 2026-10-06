/**
 * Utility for formatting Indian administrative hierarchy into a brief but complete structure:
 *
 * <Area / Village>
 * <Taluka Taluka, District District>
 * <State> — <PIN>
 * <Country>
 *
 * Gracefully collapses missing levels without fabricating or showing undefined/null/N/A.
 */

export interface LocationHierarchyLines {
  line1: string;
  line2?: string;
  line3?: string;
  line4: string;
  lines: string[];
  fullHierarchy: string;
}

export interface HierarchyInput {
  area?: string | null;
  taluka?: string | null;
  district?: string | null;
  city?: string | null;
  state?: string | null;
  postal_code?: string | null;
  country?: string | null;
  display_name?: string | null;
}

export function formatLocationHierarchy(loc: HierarchyInput): LocationHierarchyLines {
  const rawArea = loc.area?.trim();
  const rawTaluka = loc.taluka?.trim();
  const rawDistrict = loc.district?.trim();
  const rawCity = loc.city?.trim();
  const rawState = loc.state?.trim();
  const rawPostal = loc.postal_code?.trim();
  const rawCountry = loc.country?.trim() || "India";
  const rawDisplayName = loc.display_name?.trim();

  // Line 1: Area / Village / Locality
  // Prefer area if available, else primary part of display_name, else city
  let line1 = rawArea;
  if (!line1 && rawDisplayName && rawDisplayName !== rawCity) {
    line1 = rawDisplayName.split(",")[0]?.trim() || rawDisplayName;
  }
  if (!line1) {
    line1 = rawCity || "Selected Location";
  }

  // Line 2: Taluka / Tehsil & District
  let line2: string | undefined = undefined;
  const talukaFormatted = rawTaluka
    ? (/taluka|tehsil/i.test(rawTaluka) ? rawTaluka : `${rawTaluka} Taluka`)
    : undefined;

  const districtFormatted = rawDistrict
    ? (/district/i.test(rawDistrict) ? rawDistrict : `${rawDistrict} District`)
    : undefined;

  if (talukaFormatted && districtFormatted) {
    line2 = `${talukaFormatted}, ${districtFormatted}`;
  } else if (talukaFormatted) {
    line2 = talukaFormatted;
  } else if (districtFormatted) {
    const dLower = rawDistrict!.toLowerCase();
    const l1Lower = line1.toLowerCase();
    const cLower = (rawCity || "").toLowerCase();
    if (dLower !== l1Lower && (!rawCity || dLower !== cLower)) {
      line2 = districtFormatted;
    } else if (rawCity && cLower !== l1Lower) {
      line2 = rawCity;
    }
  } else if (rawCity && rawCity.toLowerCase() !== line1.toLowerCase()) {
    line2 = rawCity;
  }

  // Line 3: State & PIN
  let line3: string | undefined = undefined;
  if (rawState && rawPostal) {
    line3 = `${rawState} — ${rawPostal}`;
  } else if (rawState) {
    line3 = rawState;
  } else if (rawPostal) {
    line3 = rawPostal;
  }

  // Line 4: Country
  const line4 = rawCountry;

  const lines = [line1, line2, line3, line4].filter(Boolean) as string[];
  const fullHierarchy = lines.join("\n");

  return {
    line1,
    line2,
    line3,
    line4,
    lines,
    fullHierarchy,
  };
}
