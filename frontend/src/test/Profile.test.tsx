import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { ProfileHeader } from "@/components/profile/ProfileHeader";
import { SkillBadgeList } from "@/components/profile/SkillBadgeList";
import { LocationForm } from "@/components/profile/LocationForm";
import type { FullProfile } from "@/types/profile";

describe("Profile Components", () => {
  const mockFullProfile: FullProfile = {
    user: {
      id: "u-1",
      name: "Rohit Verma",
      email: "rohit@example.test",
      role: "helper",
      is_active: true,
      is_verified: true,
      created_at: new Date().toISOString(),
    },
    profile: {
      id: "p-1",
      user_id: "u-1",
      headline: "Whitefield Resident for 6 Years",
      bio: "Tech lead and passionate foodie.",
      occupation: "Tech Lead",
      organization: "Google",
      years_experience: 6,
      languages: ["English", "Hindi", "Kannada"],
      availability: true,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    },
    location: {
      id: "l-1",
      city: "Bengaluru",
      area: "Whitefield",
      state: "Karnataka",
      country: "India",
      location_label: "Primary",
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    },
    skills: [
      { id: "s-1", skill_id: "sk-1", skill_name: "Housing Advice", created_at: new Date().toISOString() },
      { id: "s-2", skill_id: "sk-2", skill_name: "Vegetarian Food", created_at: new Date().toISOString() },
    ],
  };

  it("renders profile header without exposing passwords or hashes", () => {
    render(<ProfileHeader fullProfile={mockFullProfile} />);

    expect(screen.getByText("Rohit Verma")).toBeInTheDocument();
    expect(screen.getByText("rohit@example.test")).toBeInTheDocument();
    expect(screen.getByText(/Whitefield Resident for 6 Years/i)).toBeInTheDocument();
    expect(screen.getByText(/Tech Lead at Google/i)).toBeInTheDocument();
    expect(screen.getByText("Whitefield, Bengaluru")).toBeInTheDocument();
    expect(screen.getByText(/Accepting Connections/i)).toBeInTheDocument();

    // Verify sensitive data is never present
    expect(screen.queryByText(/password/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/hash/i)).not.toBeInTheDocument();
  });

  it("renders skill badges and allows interactive removal", async () => {
    const onDelete = vi.fn();
    const user = userEvent.setup();

    render(
      <SkillBadgeList
        skills={mockFullProfile.skills}
        onDeleteSkill={onDelete}
        isEditable={true}
      />
    );

    expect(screen.getByText("Housing Advice")).toBeInTheDocument();
    expect(screen.getByText("Vegetarian Food")).toBeInTheDocument();

    const removeBtn = screen.getByLabelText(/Remove skill Housing Advice/i);
    await user.click(removeBtn);

    expect(onDelete).toHaveBeenCalledWith("s-1");
  });

  it("renders location form with privacy notice and manual inputs", () => {
    render(
      <LocationForm
        initialValues={{ city: "Bengaluru", area: "Whitefield" }}
        onSubmit={vi.fn()}
      />
    );

    expect(screen.getByText(/We use approximate location to improve local recommendations/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/City \*/i)).toHaveValue("Bengaluru");
    expect(screen.getByLabelText(/Area \/ Neighborhood/i)).toHaveValue("Whitefield");
  });
});
