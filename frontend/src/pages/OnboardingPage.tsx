import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { profileService } from "@/services/profile";
import { useAuthStore } from "@/store/useAuthStore";
import { useToast } from "@/hooks/useToast";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Textarea } from "@/components/ui/Textarea";
import { LocationForm } from "@/components/profile/LocationForm";
import { SkillBadgeList } from "@/components/profile/SkillBadgeList";
import type { FullProfile, LocationCreateOrUpdatePayload, UserSkill } from "@/types/profile";
import { Check, ArrowRight, ArrowLeft, MapPin, User, Sparkles } from "lucide-react";

export function OnboardingPage() {
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [fullProfile, setFullProfile] = useState<FullProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);

  // Step 2 profile fields
  const [headline, setHeadline] = useState("");
  const [bio, setBio] = useState("");
  const [occupation, setOccupation] = useState("");
  const [organization, setOrganization] = useState("");
  const [yearsExperience, setYearsExperience] = useState<string>("0");
  const [languagesStr, setLanguagesStr] = useState("English, Hindi");
  const [skills, setSkills] = useState<UserSkill[]>([]);

  const { user } = useAuthStore();
  const navigate = useNavigate();
  const { success: toastSuccess, error: toastError } = useToast();

  // Load existing profile if any
  useEffect(() => {
    profileService
      .getMyProfile()
      .then((data) => {
        setFullProfile(data);
        if (data.profile) {
          setHeadline(data.profile.headline || "");
          setBio(data.profile.bio || "");
          setOccupation(data.profile.occupation || "");
          setOrganization(data.profile.organization || "");
          setYearsExperience(data.profile.years_experience ? String(data.profile.years_experience) : "0");
          if (data.profile.languages?.length) {
            setLanguagesStr(data.profile.languages.join(", "));
          }
        }
        setSkills(data.skills || []);
      })
      .catch(() => {})
      .finally(() => setIsLoading(false));
  }, []);

  // Step 1: Save Location
  const handleSaveLocation = async (locData: LocationCreateOrUpdatePayload) => {
    setIsSaving(true);
    try {
      const loc = await profileService.setMyLocation(locData);
      setFullProfile((prev) => (prev ? { ...prev, location: loc } : null));
      toastSuccess("Location saved! Let's fill out your profile.", "Step 1 Complete");
      setStep(2);
    } catch (err: unknown) {
      toastError("Could not save location. Please verify details.");
    } finally {
      setIsSaving(false);
    }
  };

  // Step 2: Add Skill
  const handleAddSkill = async (skillName: string) => {
    try {
      const added = await profileService.addMySkill({ name: skillName });
      setSkills((prev) => [...prev, added]);
      toastSuccess(`Added skill: ${added.skill_name}`);
    } catch {
      toastError("Could not add skill.");
    }
  };

  // Step 2: Delete Skill
  const handleDeleteSkill = async (skillId: string) => {
    try {
      await profileService.deleteMySkill(skillId);
      setSkills((prev) => prev.filter((s) => s.id !== skillId));
    } catch {
      toastError("Could not remove skill.");
    }
  };

  // Step 2: Save Profile details
  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    try {
      const languages = languagesStr
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);

      const updated = await profileService.updateMyProfile({
        headline: headline.trim() || undefined,
        bio: bio.trim() || undefined,
        occupation: occupation.trim() || undefined,
        organization: organization.trim() || undefined,
        years_experience: parseFloat(yearsExperience) || 0,
        languages,
      });

      setFullProfile((prev) => (prev ? { ...prev, profile: updated, skills } : null));
      toastSuccess("Profile details saved! Review your setup.", "Step 2 Complete");
      setStep(3);
    } catch {
      toastError("Could not save profile details.");
    } finally {
      setIsSaving(false);
    }
  };

  const handleFinish = () => {
    toastSuccess("Onboarding complete! Welcome to your NEST home.", "Setup Finished");
    navigate("/home");
  };

  if (isLoading) {
    return (
      <div className="max-w-2xl mx-auto py-12 text-center text-sm text-gray-500">
        Loading your setup...
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto py-6 sm:py-10 space-y-8">
      {/* Progress Stepper */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-xs font-semibold text-gray-500 dark:text-gray-400">
          <span>STEP {step} OF 3</span>
          <span>{step === 1 ? "Location" : step === 2 ? "Profile & Skills" : "Review"}</span>
        </div>
        <div className="w-full bg-gray-200 dark:bg-brand-dark-border h-2 rounded-full overflow-hidden">
          <div
            className="bg-brand-primary h-full transition-all duration-300"
            style={{ width: `${(step / 3) * 100}%` }}
          />
        </div>
      </div>

      {/* STEP 1: Location */}
      {step === 1 && (
        <Card className="p-6 sm:p-8 space-y-6">
          <div className="space-y-1">
            <h2 className="text-xl sm:text-2xl font-bold font-heading text-gray-900 dark:text-gray-100 flex items-center gap-2">
              <MapPin className="w-6 h-6 text-brand-primary" />
              Where are you based?
            </h2>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Set your city and neighborhood so NEST can pair you with nearby helpers and requests.
            </p>
          </div>

          <LocationForm
            initialValues={
              fullProfile?.location
                ? {
                    city: fullProfile.location.city,
                    area: fullProfile.location.area || undefined,
                    state: fullProfile.location.state || undefined,
                    country: fullProfile.location.country,
                    latitude: fullProfile.location.latitude || undefined,
                    longitude: fullProfile.location.longitude || undefined,
                  }
                : undefined
            }
            onSubmit={handleSaveLocation}
            isLoading={isSaving}
            submitLabel="Save & Continue to Profile"
          />
        </Card>
      )}

      {/* STEP 2: Profile & Skills */}
      {step === 2 && (
        <Card className="p-6 sm:p-8 space-y-6">
          <div className="flex items-center justify-between">
            <div className="space-y-1">
              <h2 className="text-xl sm:text-2xl font-bold font-heading text-gray-900 dark:text-gray-100 flex items-center gap-2">
                <User className="w-6 h-6 text-brand-primary" />
                Tell the community about yourself
              </h2>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Help local members know who you are and what you can advise on.
              </p>
            </div>
            <button
              onClick={() => setStep(1)}
              className="text-xs text-brand-primary flex items-center gap-1 hover:underline p-1 min-h-[32px]"
            >
              <ArrowLeft className="w-3.5 h-3.5" /> Back
            </button>
          </div>

          <form onSubmit={handleSaveProfile} className="space-y-4">
            <Input
              label="Professional or Personal Headline"
              placeholder="e.g. 5-year Whitefield resident & Software Engineer"
              value={headline}
              onChange={(e) => setHeadline(e.target.value)}
            />

            <Textarea
              label="Bio"
              placeholder="Tell newcomers about your experience in the city, favorite neighborhood spots, or what kind of help you need..."
              rows={3}
              value={bio}
              onChange={(e) => setBio(e.target.value)}
            />

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Input
                label="Occupation"
                placeholder="e.g. Software Engineer, Student"
                value={occupation}
                onChange={(e) => setOccupation(e.target.value)}
              />
              <Input
                label="Company / College"
                placeholder="e.g. Infosys, PES University"
                value={organization}
                onChange={(e) => setOrganization(e.target.value)}
              />
              <Input
                label="Years of Experience / In City"
                type="number"
                min="0"
                step="0.5"
                value={yearsExperience}
                onChange={(e) => setYearsExperience(e.target.value)}
              />
              <Input
                label="Languages Spoken"
                placeholder="e.g. English, Hindi, Kannada"
                value={languagesStr}
                onChange={(e) => setLanguagesStr(e.target.value)}
              />
            </div>

            {/* Skills & Expertise Section */}
            <div className="pt-4 border-t border-gray-100 dark:border-brand-dark-border/60 space-y-2">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-200">
                Skills & Local Advice Areas
              </label>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Add categories you can help newcomers with:
              </p>
              <SkillBadgeList
                skills={skills}
                onAddSkill={handleAddSkill}
                onDeleteSkill={handleDeleteSkill}
                isEditable={true}
              />
            </div>

            <div className="pt-4 flex justify-between gap-3">
              <Button type="button" variant="outline" onClick={() => setStep(3)}>
                Skip for now
              </Button>
              <Button type="submit" isLoading={isSaving} rightIcon={<ArrowRight className="w-4 h-4" />}>
                Save & Review
              </Button>
            </div>
          </form>
        </Card>
      )}

      {/* STEP 3: Review & Finish */}
      {step === 3 && (
        <Card className="p-6 sm:p-8 space-y-6">
          <div className="space-y-1">
            <h2 className="text-xl sm:text-2xl font-bold font-heading text-gray-900 dark:text-gray-100 flex items-center gap-2">
              <Sparkles className="w-6 h-6 text-amber-500" />
              You're all set!
            </h2>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Here is how your profile and location are saved on the NEST network.
            </p>
          </div>

          <div className="p-5 rounded-2xl bg-teal-50/50 dark:bg-brand-dark-muted/20 border border-teal-100 dark:border-brand-dark-border space-y-4">
            <div>
              <h3 className="text-lg font-bold text-gray-900 dark:text-gray-100">{user?.name}</h3>
              <p className="text-xs text-brand-primary dark:text-teal-400 font-semibold uppercase">
                {user?.role}
              </p>
              {headline && <p className="text-sm font-medium text-gray-800 dark:text-gray-200 mt-1">{headline}</p>}
              {bio && <p className="text-xs text-gray-600 dark:text-gray-300 mt-1">{bio}</p>}
            </div>

            {fullProfile?.location && (
              <div className="flex items-center gap-2 text-xs text-gray-600 dark:text-gray-300 pt-2 border-t border-teal-100 dark:border-brand-dark-border">
                <MapPin className="w-4 h-4 text-brand-primary shrink-0" />
                <span>
                  {[fullProfile.location.area, fullProfile.location.city, fullProfile.location.state]
                    .filter(Boolean)
                    .join(", ")}
                </span>
              </div>
            )}

            {skills.length > 0 && (
              <div className="pt-2 border-t border-teal-100 dark:border-brand-dark-border">
                <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 mb-1.5">
                  Saved Skills ({skills.length}):
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {skills.map((s) => (
                    <span
                      key={s.id}
                      className="text-xs px-2.5 py-1 rounded-full bg-white dark:bg-brand-dark-card border border-gray-200 dark:border-brand-dark-border text-gray-800 dark:text-gray-200"
                    >
                      {s.skill_name}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div className="flex items-center justify-between pt-2">
            <button
              onClick={() => setStep(2)}
              className="text-xs text-brand-primary flex items-center gap-1 hover:underline p-1 min-h-[32px]"
            >
              <ArrowLeft className="w-3.5 h-3.5" /> Edit Profile
            </button>

            <Button onClick={handleFinish} size="lg" rightIcon={<Check className="w-4 h-4" />}>
              Finish & Go to Home
            </Button>
          </div>
        </Card>
      )}
    </div>
  );
}
