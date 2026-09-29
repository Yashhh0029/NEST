import { FeatureUnavailable } from "@/components/placeholder/FeatureUnavailable";

export function FutureResourcesPage() {
  return (
    <div className="max-w-4xl mx-auto py-6">
      <FeatureUnavailable
        featureName="Curated Local Resources & Directories"
        targetPhase="Phase 8"
        expectedEndpoint="GET /api/resources, GET /api/resources/{id}"
        description="Verified emergency clinics, rental guidance templates, metro smart card recharge stations, and local tiffin directories will be populated from PostgreSQL as verified resources."
      />
    </div>
  );
}
