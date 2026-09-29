import { FeatureUnavailable } from "@/components/placeholder/FeatureUnavailable";

export function FutureCommunityPage() {
  return (
    <div className="max-w-4xl mx-auto py-6">
      <FeatureUnavailable
        featureName="Local Neighborhood Community Hubs"
        targetPhase="Phase 7"
        expectedEndpoint="GET /api/community/posts, GET /api/community/events"
        description="Neighborhood-specific knowledge bases and newcomer Q&A boards will activate once community forum backend models and moderation are in place."
      />
    </div>
  );
}
