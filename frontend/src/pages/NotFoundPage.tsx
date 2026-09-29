import { Link } from "react-router-dom";
import { Button } from "@/components/ui/Button";
import { Compass, Home } from "lucide-react";

export function NotFoundPage() {
  return (
    <div className="max-w-md mx-auto py-16 text-center space-y-6">
      <div className="w-16 h-16 rounded-2xl bg-teal-50 dark:bg-brand-dark-muted/60 text-brand-primary dark:text-teal-300 mx-auto flex items-center justify-center">
        <Compass className="w-8 h-8 animate-spin" style={{ animationDuration: "8s" }} />
      </div>

      <div className="space-y-2">
        <h1 className="text-3xl font-extrabold font-heading text-gray-900 dark:text-gray-100">
          Page Not Found
        </h1>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          The place you're looking for doesn't seem to exist on this map.
        </p>
      </div>

      <Link to="/home">
        <Button leftIcon={<Home className="w-4 h-4" />}>Back to Home</Button>
      </Link>
    </div>
  );
}
