import { useState } from "react";
import type { MatchScoreWeights } from "@/types/match";
import { Card } from "../ui/Card";
import { Sliders, RefreshCw, AlertCircle } from "lucide-react";

export interface WeightSlidersProps {
  initialWeights?: MatchScoreWeights;
  onWeightsChange?: (weights: MatchScoreWeights) => void;
  disabled?: boolean;
}

const DEFAULT_WEIGHTS: MatchScoreWeights = {
  semantic: 0.40,
  location: 0.25,
  experience: 0.15,
  reputation: 0.10,
  availability: 0.10,
};

export function WeightSliders({
  initialWeights = DEFAULT_WEIGHTS,
  onWeightsChange,
  disabled = false,
}: WeightSlidersProps) {
  const [weights, setWeights] = useState<MatchScoreWeights>(initialWeights);

  const handleSlider = (key: keyof MatchScoreWeights, value: number) => {
    if (disabled) return;
    const next = { ...weights, [key]: value };
    setWeights(next);
    onWeightsChange?.(next);
  };

  const handleReset = () => {
    if (disabled) return;
    setWeights(DEFAULT_WEIGHTS);
    onWeightsChange?.(DEFAULT_WEIGHTS);
  };

  const items: Array<{
    key: keyof MatchScoreWeights;
    label: string;
    desc: string;
    isActive: boolean;
  }> = [
    {
      key: "semantic",
      label: "Semantic Need Match",
      desc: "Cosine similarity between request and candidate profile embeddings",
      isActive: true,
    },
    {
      key: "location",
      label: "Proximity & Area",
      desc: "Haversine distance decay from real GPS coordinates",
      isActive: true,
    },
    {
      key: "experience",
      label: "Experience & Tenure",
      desc: "Profile tenure and verified skill proficiencies",
      isActive: true,
    },
    {
      key: "reputation",
      label: "Community Reputation",
      desc: "Reviews & ratings (Phase 7 - Dimension marked UNAVAILABLE)",
      isActive: false,
    },
    {
      key: "availability",
      label: "Availability Engine",
      desc: "Calendar scheduling (Phase 6 - Dimension marked UNAVAILABLE)",
      isActive: false,
    },
  ];

  return (
    <Card className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sliders className="w-5 h-5 text-brand-primary" />
          <h4 className="font-bold font-heading text-gray-900 dark:text-gray-100">
            Matching Weights
          </h4>
        </div>
        {!disabled && (
          <button
            onClick={handleReset}
            className="text-xs text-brand-primary hover:underline flex items-center gap-1 p-1 min-h-[32px]"
          >
            <RefreshCw className="w-3 h-3" />
            Reset Defaults
          </button>
        )}
      </div>

      <div className="space-y-3.5 pt-2">
        {items.map(({ key, label, desc, isActive }) => (
          <div key={key} className="space-y-1">
            <div className="flex justify-between text-xs font-medium items-center">
              <span className="text-gray-800 dark:text-gray-200">{label}</span>
              <div className="flex items-center gap-2">
                {!isActive && (
                  <span className="text-[10px] text-amber-600 dark:text-amber-400 font-mono flex items-center gap-0.5">
                    <AlertCircle className="w-3 h-3" />
                    UNAVAILABLE
                  </span>
                )}
                <span className="font-mono text-brand-primary dark:text-teal-400 font-bold">
                  {Math.round(weights[key] * 100)}%
                </span>
              </div>
            </div>
            <input
              type="range"
              min={0}
              max={1}
              step={0.05}
              value={weights[key]}
              disabled={disabled || !isActive}
              onChange={(e) => handleSlider(key, parseFloat(e.target.value))}
              aria-label={label}
              className={`w-full accent-brand-primary cursor-pointer ${
                !isActive ? "opacity-40 cursor-not-allowed" : ""
              }`}
            />
            <p className="text-[11px] text-gray-400">{desc}</p>
          </div>
        ))}
      </div>
    </Card>
  );
}
