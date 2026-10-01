import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { Sparkles, MapPin, Home, Bus, IndianRupee, ArrowRight, CheckCircle2, Clock } from "lucide-react";
import { Button } from "@/components/ui/Button";

interface SamplePrompt {
  id: string;
  label: string;
  text: string;
  extracted: {
    location: string;
    needs: { icon: string; label: string }[];
    budget?: string;
    timing?: string;
  };
}

const SAMPLE_PROMPTS: SamplePrompt[] = [
  {
    id: "tech-relocation",
    label: "Tech Job Relocation",
    text: "Moving to Hinjewadi Phase 1 next Monday for an IT job. Need a 1BHK or single occupancy PG under ₹15,000 and tips on company bus routes.",
    extracted: {
      location: "Hinjewadi, Pune",
      needs: [
        { icon: "home", label: "Accommodation" },
        { icon: "bus", label: "Local Transport" },
      ],
      budget: "₹15,000 / mo",
      timing: "Next Monday",
    },
  },
  {
    id: "student-move",
    label: "College Student",
    text: "Joining college in Koramangala Bengaluru. Looking for a budget hostel near 5th Block with pure vegetarian mess food.",
    extracted: {
      location: "Koramangala, Bengaluru",
      needs: [
        { icon: "home", label: "Student Hostel" },
        { icon: "food", label: "Vegetarian Food" },
      ],
      budget: "₹9,000 / mo",
      timing: "Flexible",
    },
  },
  {
    id: "family-advice",
    label: "Doctor & School Advice",
    text: "Relocating with family to Baner Pune. Need guidance on good pediatric clinics and safe family-friendly gated societies.",
    extracted: {
      location: "Baner, Pune",
      needs: [
        { icon: "home", label: "Gated Society" },
        { icon: "health", label: "Healthcare Guidance" },
      ],
      budget: "₹30,000 / mo",
      timing: "This month",
    },
  },
];

export const InteractiveDemoBox: React.FC = () => {
  const [selectedPrompt, setSelectedPrompt] = useState<SamplePrompt>(SAMPLE_PROMPTS[0]);
  const [customText, setCustomText] = useState(SAMPLE_PROMPTS[0].text);
  const navigate = useNavigate();

  const handleSelectPrompt = (prompt: SamplePrompt) => {
    setSelectedPrompt(prompt);
    setCustomText(prompt.text);
  };

  const handleStartWithPrompt = () => {
    // Navigate to register or home with pre-populated draft
    sessionStorage.setItem("nest_draft_prompt", customText);
    navigate("/register?role=newcomer");
  };

  return (
    <div className="w-full max-w-3xl mx-auto rounded-3xl bg-white/90 dark:bg-slate-900/90 backdrop-blur-xl border border-teal-200/60 dark:border-teal-900/50 shadow-2xl p-6 sm:p-8 space-y-6 relative overflow-hidden">
      {/* Decorative gradient orb */}
      <div className="absolute -top-24 -right-24 w-64 h-64 bg-teal-400/10 dark:bg-teal-500/10 rounded-full blur-3xl pointer-events-none" />

      {/* Preset pills */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <label className="text-xs font-semibold tracking-wider uppercase text-teal-800 dark:text-teal-400 flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5 text-amber-500" />
            Try a real-life scenario:
          </label>
          <span className="text-xs text-slate-400 dark:text-slate-500 hidden sm:inline">
            Interactive AI Extraction Demo
          </span>
        </div>
        <div className="flex flex-wrap gap-2">
          {SAMPLE_PROMPTS.map((prompt) => {
            const isSelected = selectedPrompt.id === prompt.id;
            return (
              <button
                key={prompt.id}
                type="button"
                onClick={() => handleSelectPrompt(prompt)}
                className={`text-xs px-3.5 py-1.5 rounded-full font-medium transition-all duration-200 cursor-pointer ${
                  isSelected
                    ? "bg-teal-700 text-white shadow-sm ring-2 ring-teal-600/30"
                    : "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700"
                }`}
              >
                {prompt.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Input area */}
      <div className="relative">
        <textarea
          value={customText}
          onChange={(e) => setCustomText(e.target.value)}
          rows={3}
          placeholder="Describe what you need in plain words..."
          className="w-full px-4 py-3.5 text-sm sm:text-base rounded-2xl bg-slate-50 dark:bg-slate-950/60 border border-slate-200 dark:border-slate-800 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent text-slate-900 dark:text-slate-100 placeholder:text-slate-400 transition-all resize-none font-sans"
        />
      </div>

      {/* Live AI extracted tags */}
      <div className="space-y-2.5 pt-1">
        <div className="text-xs font-semibold text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
          <CheckCircle2 className="w-3.5 h-3.5 text-teal-600 dark:text-teal-400" />
          <span>NEST Structured Understanding:</span>
        </div>

        <AnimatePresence mode="wait">
          <motion.div
            key={selectedPrompt.id}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.2 }}
            className="flex flex-wrap items-center gap-2"
          >
            {/* Location Chip */}
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-medium bg-teal-50 dark:bg-teal-950/60 border border-teal-200 dark:border-teal-800/80 text-teal-800 dark:text-teal-300">
              <MapPin className="w-3 h-3 text-teal-600 dark:text-teal-400" />
              {selectedPrompt.extracted.location}
            </span>

            {/* Needs Chips */}
            {selectedPrompt.extracted.needs.map((n, idx) => (
              <span
                key={idx}
                className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-medium bg-amber-50 dark:bg-amber-950/60 border border-amber-200 dark:border-amber-800/80 text-amber-900 dark:text-amber-300"
              >
                {n.icon === "home" ? (
                  <Home className="w-3 h-3 text-amber-600 dark:text-amber-400" />
                ) : (
                  <Bus className="w-3 h-3 text-amber-600 dark:text-amber-400" />
                )}
                {n.label}
              </span>
            ))}

            {/* Budget Chip */}
            {selectedPrompt.extracted.budget && (
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-medium bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-200 dark:border-emerald-800/80 text-emerald-800 dark:text-emerald-300">
                <IndianRupee className="w-3 h-3 text-emerald-600 dark:text-emerald-400" />
                {selectedPrompt.extracted.budget}
              </span>
            )}

            {/* Timing Chip */}
            {selectedPrompt.extracted.timing && (
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-medium bg-indigo-50 dark:bg-indigo-950/60 border border-indigo-200 dark:border-indigo-800/80 text-indigo-800 dark:text-indigo-300">
                <Clock className="w-3 h-3 text-indigo-600 dark:text-indigo-400" />
                {selectedPrompt.extracted.timing}
              </span>
            )}
          </motion.div>
        </AnimatePresence>
      </div>

      {/* Action Footer */}
      <div className="pt-2 flex flex-col sm:flex-row items-center justify-between gap-3 border-t border-slate-100 dark:border-slate-800">
        <div className="text-xs text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span>Real-time matching active across registered local helpers</span>
        </div>
        <Button
          onClick={handleStartWithPrompt}
          size="sm"
          className="w-full sm:w-auto font-semibold shadow-md gap-2"
        >
          <span>Find Helpers For This Need</span>
          <ArrowRight className="w-4 h-4" />
        </Button>
      </div>
    </div>
  );
};
