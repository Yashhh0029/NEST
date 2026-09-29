import { useState } from "react";
import type { UserSkill } from "@/types/profile";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";
import { Input } from "../ui/Input";
import { X, Plus } from "lucide-react";

export interface SkillBadgeListProps {
  skills: UserSkill[];
  onAddSkill?: (skillName: string) => Promise<void>;
  onDeleteSkill?: (skillId: string) => Promise<void>;
  isEditable?: boolean;
}

const COMMON_SKILLS = [
  "Housing Advice",
  "Vegetarian Food",
  "Bangalore Metro",
  "Pune Transit",
  "IT Job Mentorship",
  "Local Guidance",
  "Healthcare / Clinics",
  "Documentation / Rental",
];

export function SkillBadgeList({
  skills,
  onAddSkill,
  onDeleteSkill,
  isEditable = false,
}: SkillBadgeListProps) {
  const [newSkill, setNewSkill] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const existingNames = new Set(skills.map((s) => s.skill_name.toLowerCase()));

  const handleAdd = async (nameToAdd?: string) => {
    const name = (nameToAdd || newSkill).trim();
    if (!name || !onAddSkill) return;

    setIsSubmitting(true);
    try {
      await onAddSkill(name);
      if (!nameToAdd) setNewSkill("");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* Current Skills */}
      <div className="flex flex-wrap gap-2">
        {skills.length === 0 ? (
          <p className="text-sm text-gray-500 dark:text-gray-400 italic">
            No skills added yet. Add areas you can help with or want advice on.
          </p>
        ) : (
          skills.map((skill) => (
            <Badge key={skill.id} variant="primary" size="md">
              <span>{skill.skill_name}</span>
              {isEditable && onDeleteSkill && (
                <button
                  type="button"
                  onClick={() => onDeleteSkill(skill.id)}
                  aria-label={`Remove skill ${skill.skill_name}`}
                  className="ml-1 p-0.5 rounded-full hover:bg-teal-200/50 dark:hover:bg-brand-dark-muted transition-colors min-h-[24px] min-w-[24px] inline-flex items-center justify-center text-teal-800 dark:text-teal-200"
                >
                  <X className="w-3 h-3" />
                </button>
              )}
            </Badge>
          ))
        )}
      </div>

      {/* Editable Add Section */}
      {isEditable && onAddSkill && (
        <div className="pt-3 border-t border-gray-100 dark:border-brand-dark-border/60 space-y-3">
          {/* Quick Add Suggestions */}
          <div>
            <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 mb-2">
              Recommended Local Expertise:
            </p>
            <div className="flex flex-wrap gap-1.5">
              {COMMON_SKILLS.filter((s) => !existingNames.has(s.toLowerCase())).map((suggested) => (
                <button
                  key={suggested}
                  type="button"
                  onClick={() => handleAdd(suggested)}
                  disabled={isSubmitting}
                  className="inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-full border border-gray-200 dark:border-brand-dark-border bg-white dark:bg-brand-dark-card hover:border-brand-primary text-gray-700 dark:text-gray-300 transition-colors"
                >
                  <Plus className="w-3 h-3 text-brand-primary" />
                  {suggested}
                </button>
              ))}
            </div>
          </div>

          {/* Custom Skill Input */}
          <div className="flex items-center gap-2 max-w-md">
            <Input
              placeholder="Or type a custom skill..."
              value={newSkill}
              onChange={(e) => setNewSkill(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  handleAdd();
                }
              }}
            />
            <Button
              type="button"
              onClick={() => handleAdd()}
              isLoading={isSubmitting}
              disabled={!newSkill.trim()}
              size="md"
            >
              Add
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
