import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { profileService } from "@/services/profile";
import { useAuthStore } from "@/store/useAuthStore";
import { useToast } from "@/hooks/useToast";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Textarea } from "@/components/ui/Textarea";
import { Button } from "@/components/ui/Button";
import { LocationForm } from "@/components/profile/LocationForm";
import { SkillBadgeList } from "@/components/profile/SkillBadgeList";
import type { FullProfile, LocationCreateOrUpdatePayload, UserSkill } from "@/types/profile";
import { ArrowLeft, Save, User, MapPin, Award, Users } from "lucide-react";

export function ProfileEditPage() {
  const [fullProfile, setFullProfile] = useState<FullProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSavingProfile, setIsSavingProfile] = useState(false);
  const [isSavingLocation, setIsSavingLocation] = useState(false);
  const [isSavingRole, setIsSavingRole] = useState(false);

  // Form states
  const [communityRole, setCommunityRole] = useState<"newcomer" | "helper" | "both">("newcomer");
  const [headline, setHeadline] = useState("");
  const [bio, setBio] = useState("");
  const [occupation, setOccupation] = useState("");
  const [organization, setOrganization] = useState("");
  const [yearsExperience, setYearsExperience] = useState("0");
  const [languagesStr, setLanguagesStr] = useState("");
  const [helpDescription, setHelpDescription] = useState("");
  const [needsDescription, setNeedsDescription] = useState("");
  const [availability, setAvailability] = useState(true);
  const [skills, setSkills] = useState<UserSkill[]>([]);

  const { success: toastSuccess, error: toastError } = useToast();
  const { setUser } = useAuthStore();

  useEffect(() => {
    profileService
      .getMyProfile()
      .then((data) => {
        setFullProfile(data);
        if (data.user?.role) {
          const r = data.user.role;
          if (r === "newcomer" || r === "helper" || r === "both") {
            setCommunityRole(r);
          }
        }
        if (data.profile) {
          setHeadline(data.profile.headline || "");
          setBio(data.profile.bio || "");
          setOccupation(data.profile.occupation || "");
          setOrganization(data.profile.organization || "");
          setYearsExperience(data.profile.years_experience ? String(data.profile.years_experience) : "0");
          setLanguagesStr(data.profile.languages?.join(", ") || "");
          setHelpDescription(data.profile.help_description || "");
          setNeedsDescription(data.profile.needs_description || "");
          setAvailability(data.profile.availability);
        }
        setSkills(data.skills || []);
        if (window.location.hash === "#location") {
          setTimeout(() => {
            document.getElementById("location")?.scrollIntoView({ behavior: "smooth" });
          }, 150);
        }
      })
      .catch(() => toastError("Could not load profile."))
      .finally(() => setIsLoading(false));
  }, []);

  const handleSaveRole = async () => {
    setIsSavingRole(true);
    try {
      const updatedUser = await profileService.updateMyRole(communityRole);
      setFullProfile((prev) => (prev ? { ...prev, user: { ...prev.user, role: updatedUser.role } } : null));
      setUser(updatedUser);
      toastSuccess(`Community role updated to ${communityRole}!`, "Role Updated");
    } catch {
      toastError("Failed to update community role.");
    } finally {
      setIsSavingRole(false);
    }
  };

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSavingProfile(true);
    try {
      const languages = languagesStr
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);

      const updated = await profileService.updateMyProfile({
        role: communityRole,
        headline: headline.trim() || undefined,
        bio: bio.trim() || undefined,
        occupation: occupation.trim() || undefined,
        organization: organization.trim() || undefined,
        years_experience: parseFloat(yearsExperience) || 0,
        languages,
        help_description: helpDescription.trim() || undefined,
        needs_description: needsDescription.trim() || undefined,
        availability,
      });

      setFullProfile((prev) => (prev ? { ...prev, profile: updated } : null));
      toastSuccess("Profile information updated successfully!");
    } catch {
      toastError("Failed to update profile details.");
    } finally {
      setIsSavingProfile(false);
    }
  };

  const handleSaveLocation = async (locData: LocationCreateOrUpdatePayload) => {
    setIsSavingLocation(true);
    try {
      const loc = await profileService.setMyLocation(locData);
      setFullProfile((prev) => (prev ? { ...prev, location: loc } : null));
      toastSuccess("Location updated successfully!");
    } catch {
      toastError("Failed to update location.");
    } finally {
      setIsSavingLocation(false);
    }
  };

  const handleAddSkill = async (skillName: string) => {
    try {
      const added = await profileService.addMySkill({ name: skillName });
      setSkills((prev) => [...prev, added]);
      toastSuccess(`Added skill: ${added.skill_name}`);
    } catch {
      toastError("Could not add skill.");
    }
  };

  const handleDeleteSkill = async (skillId: string) => {
    try {
      await profileService.deleteMySkill(skillId);
      setSkills((prev) => prev.filter((s) => s.id !== skillId));
      toastSuccess("Skill removed.");
    } catch {
      toastError("Could not remove skill.");
    }
  };

  if (isLoading) {
    return (
      <div className="max-w-4xl mx-auto py-12 text-center text-sm text-gray-500">
        Loading profile editor...
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto py-2 sm:py-6 space-y-8">
      {/* Back to Profile */}
      <div className="flex items-center justify-between">
        <Link
          to="/profile"
          className="text-xs font-semibold text-brand-primary dark:text-teal-400 flex items-center gap-1 hover:underline min-h-[44px]"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Profile
        </Link>
        <Link to="/profile">
          <Button variant="secondary" size="sm">Done Editing</Button>
        </Link>
      </div>

      <div className="space-y-8">
        {/* Community Role Section */}
        <Card className="p-6 sm:p-8 space-y-5 border border-teal-100 dark:border-brand-dark-border shadow-xs">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-gray-100 dark:border-brand-dark-border pb-4">
            <div className="flex items-center gap-2.5">
              <div className="w-9 h-9 rounded-xl bg-teal-50 dark:bg-brand-dark-card flex items-center justify-center text-brand-primary dark:text-teal-300">
                <Users className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-xl font-bold font-heading text-gray-900 dark:text-gray-100">
                  Community Role
                </h2>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                  Choose how you participate in NEST. Helpers and members with Both roles receive nearby help alerts.
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2 self-start sm:self-auto">
              <span className="text-xs text-gray-500 dark:text-gray-400">Current role:</span>
              <span className="text-xs px-3 py-1 rounded-full font-bold uppercase tracking-wider bg-teal-50 dark:bg-brand-dark-card text-brand-primary dark:text-teal-300 border border-teal-200 dark:border-teal-800">
                {fullProfile?.user?.role || "newcomer"}
              </span>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {[
              {
                id: "newcomer" as const,
                title: "Newcomer",
                description: "Looking for local guidance, accommodation, and settling into a new city.",
              },
              {
                id: "helper" as const,
                title: "Helper",
                description: "Offering local guidance and community support to newcomers in your area.",
              },
              {
                id: "both" as const,
                title: "Both",
                description: "Both seeking assistance and open to helping others in your neighborhood.",
              },
            ].map((option) => (
              <label
                key={option.id}
                className={`relative flex flex-col p-4 rounded-xl border cursor-pointer transition-all ${
                  communityRole === option.id
                    ? "border-brand-primary bg-teal-50/60 dark:bg-teal-950/20 ring-2 ring-brand-primary/20 shadow-xs"
                    : "border-gray-200 dark:border-brand-dark-border hover:bg-gray-50 dark:hover:bg-brand-dark-card"
                }`}
              >
                <div className="flex items-center justify-between mb-1.5">
                  <span className="font-semibold text-sm text-gray-900 dark:text-gray-100">
                    {option.title}
                  </span>
                  <input
                    type="radio"
                    name="communityRole"
                    value={option.id}
                    checked={communityRole === option.id}
                    onChange={() => setCommunityRole(option.id)}
                    className="w-4 h-4 accent-brand-primary cursor-pointer"
                  />
                </div>
                <p className="text-xs text-gray-500 dark:text-gray-400 leading-relaxed">
                  {option.description}
                </p>
              </label>
            ))}
          </div>

          <div className="flex justify-end pt-1">
            <Button
              type="button"
              onClick={handleSaveRole}
              isLoading={isSavingRole}
              disabled={communityRole === fullProfile?.user?.role}
              leftIcon={<Save className="w-4 h-4" />}
            >
              Update Community Role
            </Button>
          </div>
        </Card>

        {/* Section 1: Basic Profile Details */}
        <Card className="p-6 sm:p-8 space-y-6">
          <div className="flex items-center gap-2">
            <User className="w-5 h-5 text-brand-primary" />
            <h2 className="text-xl font-bold font-heading text-gray-900 dark:text-gray-100">
              Basic Details & Bio
            </h2>
          </div>

          <form onSubmit={handleSaveProfile} className="space-y-4">
            <Input
              label="Professional / Community Headline"
              placeholder="e.g. 4-year resident in Hinjewadi, Tech Mentor"
              value={headline}
              onChange={(e) => setHeadline(e.target.value)}
            />

            <Textarea
              label="Biography"
              placeholder="Tell other members about your background, hobbies, or local experience..."
              rows={4}
              value={bio}
              onChange={(e) => setBio(e.target.value)}
            />

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Input
                label="Occupation"
                placeholder="e.g. Software Engineer"
                value={occupation}
                onChange={(e) => setOccupation(e.target.value)}
              />
              <Input
                label="Organization / Company"
                placeholder="e.g. Wipro, Infosys"
                value={organization}
                onChange={(e) => setOrganization(e.target.value)}
              />
              <Input
                label="Years of Experience"
                type="number"
                min="0"
                step="0.5"
                value={yearsExperience}
                onChange={(e) => setYearsExperience(e.target.value)}
              />
              <Input
                label="Languages (comma separated)"
                placeholder="e.g. English, Hindi, Marathi"
                value={languagesStr}
                onChange={(e) => setLanguagesStr(e.target.value)}
              />
            </div>

            <Textarea
              label="What advice or help can you offer newcomers?"
              placeholder="e.g. Affordable flats in Hinjewadi Phase 1, good vegetarian mess recommendations..."
              rows={3}
              value={helpDescription}
              onChange={(e) => setHelpDescription(e.target.value)}
            />

            <Textarea
              label="What assistance are you currently looking for?"
              placeholder="e.g. Looking for badminton groups, weekend commute carpools..."
              rows={2}
              value={needsDescription}
              onChange={(e) => setNeedsDescription(e.target.value)}
            />

            <div className="flex items-center gap-3 pt-2">
              <input
                type="checkbox"
                id="availability-check"
                checked={availability}
                onChange={(e) => setAvailability(e.target.checked)}
                className="w-4 h-4 rounded accent-brand-primary cursor-pointer"
              />
              <label
                htmlFor="availability-check"
                className="text-sm font-medium text-gray-700 dark:text-gray-200 cursor-pointer"
              >
                Accepting new community connection requests
              </label>
            </div>

            <div className="pt-4 flex justify-end">
              <Button type="submit" isLoading={isSavingProfile} leftIcon={<Save className="w-4 h-4" />}>
                Save Profile Details
              </Button>
            </div>
          </form>
        </Card>

        {/* Section 2: Location Form */}
        <div id="location">
          <Card className="p-6 sm:p-8 space-y-6">
            <div className="flex items-center gap-2">
              <MapPin className="w-5 h-5 text-brand-primary" />
              <h2 className="text-xl font-bold font-heading text-gray-900 dark:text-gray-100">
                Your Primary Location
              </h2>
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
                      display_name: fullProfile.location.display_name || undefined,
                      place_types: fullProfile.location.place_types || undefined,
                      google_place_id: fullProfile.location.google_place_id || undefined,
                      formatted_address: fullProfile.location.formatted_address || undefined,
                      postal_code: fullProfile.location.postal_code || undefined,
                      private_unit: fullProfile.location.private_unit || undefined,
                      location_source: fullProfile.location.location_source || undefined,
                      location_precision: fullProfile.location.location_precision || undefined,
                    }
                  : undefined
              }
              onSubmit={handleSaveLocation}
              isLoading={isSavingLocation}
              submitLabel="Update Location"
            />
          </Card>
        </div>

        {/* Section 3: Skills & Expertise */}
        <Card className="p-6 sm:p-8 space-y-6">
          <div className="flex items-center gap-2">
            <Award className="w-5 h-5 text-brand-primary" />
            <h2 className="text-xl font-bold font-heading text-gray-900 dark:text-gray-100">
              Manage Skills & Local Knowledge
            </h2>
          </div>

          <SkillBadgeList
            skills={skills}
            onAddSkill={handleAddSkill}
            onDeleteSkill={handleDeleteSkill}
            isEditable={true}
          />
        </Card>
      </div>
    </div>
  );
}
