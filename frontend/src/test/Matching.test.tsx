import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { HelperCard } from "@/components/match/HelperCard";
import { RadarPanel } from "@/components/match/RadarPanel";
import { WeightSliders } from "@/components/match/WeightSliders";
import type { HelperMatchItem } from "@/types/match";

const sampleHelper: HelperMatchItem = {
  user_id: "12345678-1234-1234-1234-123456789abc",
  name: "Aarav Sharma",
  headline: "Local Housing Expert",
  bio: "Resident of Whitefield for 5 years helping newcomers find PG accommodation.",
  city: "Bengaluru",
  area: "Whitefield",
  distance_km: 1.2,
  skills: ["Housing", "Local Guidance"],
  scores: {
    semantic_score: 0.88,
    location_score: 0.92,
    experience_score: 0.80,
    reputation_score: null,
    availability_score: null,
    final_score: 0.87,
  },
  dimension_statuses: {
    semantic: "ACTIVE",
    location: "ACTIVE",
    experience: "ACTIVE",
    reputation: "UNAVAILABLE",
    availability: "UNAVAILABLE",
  },
  reasons: [
    {
      category: "semantic",
      title: "Strong Need Alignment",
      explanation: "Profile and background match your request needs with 88% AI semantic similarity.",
    },
    {
      category: "location",
      title: "Immediate Neighborhood",
      explanation: "Located in Whitefield, Bengaluru, only 1.2 km away.",
    },
  ],
  is_available_for_help: true,
};

describe("Phase 5 Matching UI Components", () => {
  it("renders HelperCard with real database candidate data and reasons", () => {
    render(<HelperCard helper={sampleHelper} />);

    expect(screen.getByText("Aarav Sharma")).toBeInTheDocument();
    expect(screen.getByText("Local Housing Expert")).toBeInTheDocument();
    expect(screen.getAllByText(/Whitefield, Bengaluru/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/1.2 km away/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("87%")).toBeInTheDocument();
    expect(screen.getByText("Housing")).toBeInTheDocument();
    expect(screen.getByText(/Why this match\?/i)).toBeInTheDocument();
    expect(screen.getByText(/Strong Need Alignment:/i)).toBeInTheDocument();
  });

  it("renders RadarPanel with honest UNAVAILABLE indicators for reputation and availability", () => {
    render(
      <RadarPanel
        scores={sampleHelper.scores}
        dimensionStatuses={sampleHelper.dimension_statuses}
      />
    );

    // Active dimensions show percentages
    expect(screen.getByText("Semantic Relevance")).toBeInTheDocument();
    expect(screen.getByText("88%")).toBeInTheDocument();
    expect(screen.getByText("92%")).toBeInTheDocument();
    expect(screen.getByText("80%")).toBeInTheDocument();

    // Unavailable dimensions show UNAVAILABLE badge, never fabricated numbers
    const unavailableBadges = screen.getAllByText("UNAVAILABLE");
    expect(unavailableBadges.length).toBe(2);

    // Shows mathematically justified composite score
    expect(screen.getByText("Composite Match Score")).toBeInTheDocument();
    expect(screen.getByText("87%")).toBeInTheDocument();
  });

  it("renders WeightSliders and fires change event when adjusted", () => {
    const handleWeightsChange = vi.fn();
    render(
      <WeightSliders
        onWeightsChange={handleWeightsChange}
      />
    );

    expect(screen.getByText("Matching Weights")).toBeInTheDocument();
    expect(screen.getByText("Semantic Need Match")).toBeInTheDocument();
    expect(screen.getByText("40%")).toBeInTheDocument();

    // Move semantic slider
    const semanticSlider = screen.getByLabelText("Semantic Need Match");
    fireEvent.change(semanticSlider, { target: { value: "0.6" } });

    expect(handleWeightsChange).toHaveBeenCalledWith(
      expect.objectContaining({ semantic: 0.6 })
    );
  });
});
