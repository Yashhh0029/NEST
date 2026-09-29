import { useParams } from "react-router-dom";
import { FeatureUnavailable } from "@/components/placeholder/FeatureUnavailable";

export function FutureChatPage() {
  const { connectionId } = useParams<{ connectionId: string }>();

  return (
    <div className="max-w-4xl mx-auto py-6">
      <FeatureUnavailable
        featureName="Direct Helper & Newcomer Messaging"
        targetPhase="Phase 6"
        expectedEndpoint={`WS /ws/chat/${connectionId || ":connectionId"} / GET /api/messages`}
        description="End-to-end community chat with read receipts, rate limits, and safety guidelines will be implemented with real WebSockets. No simulated or bot messages are fabricated."
      />
    </div>
  );
}
