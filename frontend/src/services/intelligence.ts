import { api } from "./api";
import type {
  NeedProgressUpdate,
  RequestIntelligenceResponse,
  SavedResource,
  SavedResourceCreate,
} from "@/types/intelligence";

export const intelligenceService = {
  /**
   * Fetch unified intelligence for a request (People, Community, Resources, Connections, Progress).
   */
  async getIntelligence(requestId: string): Promise<RequestIntelligenceResponse> {
    const res = await api.get<RequestIntelligenceResponse>(
      `/api/requests/${requestId}/intelligence`
    );
    return res.data;
  },

  /**
   * Update progress on a specific extracted need category.
   */
  async updateNeedProgress(
    requestId: string,
    payload: NeedProgressUpdate
  ): Promise<RequestIntelligenceResponse> {
    const res = await api.patch<RequestIntelligenceResponse>(
      `/api/requests/${requestId}/need-progress`,
      payload
    );
    return res.data;
  },

  /**
   * Mark overall request as RESOLVED with optional closing summary.
   */
  async resolveRequest(
    requestId: string,
    resolutionSummary?: string
  ): Promise<RequestIntelligenceResponse> {
    const res = await api.post<RequestIntelligenceResponse>(
      `/api/requests/${requestId}/resolve`,
      { resolution_summary: resolutionSummary }
    );
    return res.data;
  },

  /**
   * Bookmark a discovered resource to a request.
   */
  async saveResource(
    requestId: string,
    payload: SavedResourceCreate
  ): Promise<SavedResource> {
    const res = await api.post<SavedResource>(
      `/api/requests/${requestId}/saved-resources`,
      payload
    );
    return res.data;
  },

  /**
   * List all saved / bookmarked resources for a request.
   */
  async getSavedResources(requestId: string): Promise<SavedResource[]> {
    const res = await api.get<SavedResource[]>(
      `/api/requests/${requestId}/saved-resources`
    );
    return res.data;
  },

  /**
   * Delete a saved resource bookmark from a request.
   */
  async deleteSavedResource(requestId: string, placeId: string): Promise<void> {
    await api.delete(`/api/requests/${requestId}/saved-resources/${placeId}`);
  },
};
