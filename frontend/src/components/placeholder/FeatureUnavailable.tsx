import { Card } from "../ui/Card";
import { Badge } from "../ui/Badge";
import { AlertCircle, Terminal, Layers } from "lucide-react";

export interface FeatureUnavailableProps {
  featureName: string;
  targetPhase: string;
  expectedEndpoint: string;
  description: string;
}

export function FeatureUnavailable({
  featureName,
  targetPhase,
  expectedEndpoint,
  description,
}: FeatureUnavailableProps) {
  return (
    <Card className="max-w-2xl mx-auto my-8 p-6 md:p-8 space-y-5 border-dashed">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-xl bg-amber-50 dark:bg-amber-950/40 text-brand-accent flex items-center justify-center shrink-0">
            <AlertCircle className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-lg font-bold font-heading text-gray-900 dark:text-gray-100">
              {featureName}
            </h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Honest Architecture Notice • No Fake Data Policy
            </p>
          </div>
        </div>

        <Badge variant="accent" size="sm">
          {targetPhase}
        </Badge>
      </div>

      <p className="text-sm text-gray-600 dark:text-gray-300 leading-relaxed">
        {description}
      </p>

      <div className="p-4 rounded-xl bg-gray-50 dark:bg-brand-dark-muted/30 border border-gray-200/80 dark:border-brand-dark-border text-xs font-mono space-y-2">
        <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400">
          <Terminal className="w-4 h-4" />
          <span>Expected Backend Data Contract:</span>
        </div>
        <p className="text-brand-primary dark:text-teal-400 font-semibold break-all">
          {expectedEndpoint}
        </p>
      </div>

      <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
        <Layers className="w-4 h-4 text-brand-primary" />
        <span>
          NEST never manufactures mock profiles, scores, or simulated messages. This component will activate as soon as the corresponding backend endpoints are deployed.
        </span>
      </div>
    </Card>
  );
}
