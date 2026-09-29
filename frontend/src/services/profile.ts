import { api } from "./api";
import type {
  FullProfile,
  Location,
  LocationCreateOrUpdatePayload,
  Profile,
  ProfileUpdatePayload,
  SkillCreatePayload,
  UserSkill,
} from "@/types/profile";

export const profileService = {
  async getMyProfile(): Promise<FullProfile> {
    const res = await api.get<FullProfile>("/api/profile/me");
    return res.data;
  },

  async updateMyProfile(payload: ProfileUpdatePayload): Promise<Profile> {
    const res = await api.put<Profile>("/api/profile/me", payload);
    return res.data;
  },

  async patchMyProfile(payload: ProfileUpdatePayload): Promise<Profile> {
    const res = await api.patch<Profile>("/api/profile/me", payload);
    return res.data;
  },

  async setMyLocation(payload: LocationCreateOrUpdatePayload): Promise<Location> {
    const res = await api.put<Location>("/api/profile/me/location", payload);
    return res.data;
  },

  async getMyLocation(): Promise<Location> {
    const res = await api.get<Location>("/api/profile/me/location");
    return res.data;
  },

  async deleteMyLocation(): Promise<{ detail: string }> {
    const res = await api.delete<{ detail: string }>("/api/profile/me/location");
    return res.data;
  },

  async addMySkill(payload: SkillCreatePayload): Promise<UserSkill> {
    const res = await api.post<UserSkill>("/api/profile/me/skills", payload);
    return res.data;
  },

  async getMySkills(): Promise<UserSkill[]> {
    const res = await api.get<UserSkill[]>("/api/profile/me/skills");
    return res.data;
  },

  async deleteMySkill(skillId: string): Promise<{ detail: string }> {
    const res = await api.delete<{ detail: string }>(`/api/profile/me/skills/${skillId}`);
    return res.data;
  },
};
