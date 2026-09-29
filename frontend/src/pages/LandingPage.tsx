import { Link } from "react-router-dom";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Sparkles, Shield, ArrowRight, CheckCircle2 } from "lucide-react";

export function LandingPage() {
  return (
    <div className="space-y-16 md:space-y-24 py-6 md:py-12">
      {/* Hero Section */}
      <section className="text-center max-w-3xl mx-auto space-y-6">
        <Badge variant="primary" size="md" icon={<Sparkles className="w-3.5 h-3.5 text-amber-500" />}>
          AI-Powered Community Assistance
        </Badge>

        <h1 className="text-4xl sm:text-5xl md:text-6xl font-extrabold font-heading text-gray-900 dark:text-gray-100 tracking-tight leading-[1.1]">
          Find Your People. <br />
          <span className="text-brand-primary dark:text-teal-400">Find Your Place.</span>
        </h1>

        <p className="text-lg sm:text-xl text-gray-600 dark:text-gray-300 leading-relaxed max-w-2xl mx-auto">
          Moving to a new city shouldn't mean navigating housing, tiffins, and transit alone.
          NEST pairs newcomers with verified local residents using semantic AI matching.
        </p>

        {/* Dual Primary CTAs */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-3.5 pt-2">
          <Link to="/register?role=newcomer" className="w-full sm:w-auto">
            <Button size="lg" className="w-full sm:w-auto font-semibold shadow-soft" rightIcon={<ArrowRight className="w-4 h-4" />}>
              I'm New Here
            </Button>
          </Link>
          <Link to="/register?role=helper" className="w-full sm:w-auto">
            <Button size="lg" variant="secondary" className="w-full sm:w-auto font-semibold">
              I Want to Help
            </Button>
          </Link>
        </div>

        <p className="text-xs text-gray-400 dark:text-gray-500">
          Free for community members • Zero social media noise • Privacy first
        </p>
      </section>

      {/* How It Works */}
      <section className="space-y-8">
        <div className="text-center space-y-2">
          <h2 className="text-2xl sm:text-3xl font-bold font-heading text-gray-900 dark:text-gray-100">
            How NEST Solves Your Move
          </h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 max-w-md mx-auto">
            A three-step pipeline designed for local problem-solving, not infinite scrolling.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card hover className="space-y-3">
            <div className="w-12 h-12 rounded-xl bg-teal-50 dark:bg-brand-dark-muted/60 text-brand-primary dark:text-teal-300 flex items-center justify-center font-heading font-extrabold text-xl">
              1
            </div>
            <h3 className="text-lg font-bold font-heading text-gray-900 dark:text-gray-100">
              Describe Your Need
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-300 leading-relaxed">
              Write naturally in plain English: "Moving to Whitefield for an IT job. Need a PG under ₹10,000 and vegetarian tiffin."
            </p>
          </Card>

          <Card hover className="space-y-3">
            <div className="w-12 h-12 rounded-xl bg-amber-50 dark:bg-amber-950/40 text-brand-accent flex items-center justify-center font-heading font-extrabold text-xl">
              2
            </div>
            <h3 className="text-lg font-bold font-heading text-gray-900 dark:text-gray-100">
              NEST Understands It
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-300 leading-relaxed">
              Our deterministic NLP extracts your location, budget, dietary habits, and urgency into structured requirements.
            </p>
          </Card>

          <Card hover className="space-y-3">
            <div className="w-12 h-12 rounded-xl bg-green-50 dark:bg-green-950/40 text-brand-success flex items-center justify-center font-heading font-extrabold text-xl">
              3
            </div>
            <h3 className="text-lg font-bold font-heading text-gray-900 dark:text-gray-100">
              Connect With Helpers
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-300 leading-relaxed">
              Match with local guides who know the area, have verified experience, and are genuinely ready to help.
            </p>
          </Card>
        </div>
      </section>

      {/* Honest Trust & Platform Philosophy */}
      <section className="rounded-card bg-teal-50/60 dark:bg-brand-dark-card border border-teal-100 dark:border-brand-dark-border p-6 sm:p-10 space-y-6">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-brand-primary text-white">
            <Shield className="w-6 h-6 text-amber-300" />
          </div>
          <div>
            <h3 className="text-xl font-bold font-heading text-gray-900 dark:text-gray-100">
              Built for Community Problem-Solving, Not Social Media
            </h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Transparent, accountable, and private.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
          <div className="flex items-start gap-2.5 text-gray-700 dark:text-gray-300">
            <CheckCircle2 className="w-5 h-5 text-brand-primary shrink-0 mt-0.5" />
            <span>
              <strong>No fake vanity metrics:</strong> No likes, followers, public feeds, or selfie galleries.
            </span>
          </div>
          <div className="flex items-start gap-2.5 text-gray-700 dark:text-gray-300">
            <CheckCircle2 className="w-5 h-5 text-brand-primary shrink-0 mt-0.5" />
            <span>
              <strong>Honest trust language:</strong> NEST uses reputation and community feedback to help you evaluate connections.
            </span>
          </div>
          <div className="flex items-start gap-2.5 text-gray-700 dark:text-gray-300">
            <CheckCircle2 className="w-5 h-5 text-brand-primary shrink-0 mt-0.5" />
            <span>
              <strong>Area-level privacy:</strong> Exact home addresses and contact numbers are never exposed publicly.
            </span>
          </div>
          <div className="flex items-start gap-2.5 text-gray-700 dark:text-gray-300">
            <CheckCircle2 className="w-5 h-5 text-brand-primary shrink-0 mt-0.5" />
            <span>
              <strong>Explainable AI matching:</strong> Transparent match factors break down why each connection was suggested.
            </span>
          </div>
        </div>

        <div className="pt-4 border-t border-teal-100 dark:border-brand-dark-border flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Ready to find your local community?
          </p>
          <Link to="/register">
            <Button size="md">Get Started on NEST</Button>
          </Link>
        </div>
      </section>
    </div>
  );
}
