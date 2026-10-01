import { Link } from "react-router-dom";
import {
  Sparkles,
  Shield,
  ArrowRight,
  CheckCircle2,
  Users,
  Calendar,
  MapPin,
  Award,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Reveal, Stagger, StaggerItem, MagneticButton } from "@/components/motion";
import { InteractiveDemoBox } from "@/components/landing/InteractiveDemoBox";
import { GoogleSignInButton } from "@/components/auth/GoogleSignInButton";

export function LandingPage() {
  return (
    <div className="space-y-20 md:space-y-32 py-6 md:py-12 overflow-hidden">
      {/* 1. Hero Section */}
      <section className="relative text-center max-w-4xl mx-auto space-y-8 px-4">
        {/* Glow ambient background element */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-gradient-to-tr from-teal-400/20 to-amber-300/15 dark:from-teal-900/30 dark:to-amber-900/20 rounded-full blur-3xl pointer-events-none -z-10" />

        <Reveal direction="down" delay={0.1}>
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-teal-50 dark:bg-teal-950/70 border border-teal-200 dark:border-teal-800 text-teal-800 dark:text-teal-200 text-xs sm:text-sm font-medium shadow-sm">
            <Sparkles className="w-4 h-4 text-amber-500 animate-pulse" />
            <span>AI-Powered Local Community Assistance</span>
            <span className="w-1.5 h-1.5 rounded-full bg-teal-500" />
            <span className="text-slate-500 dark:text-slate-400">Bengaluru • Pune • Mumbai</span>
          </div>
        </Reveal>

        <Reveal direction="up" delay={0.2}>
          <h1 className="text-4xl sm:text-6xl md:text-7xl font-extrabold font-heading text-slate-900 dark:text-white tracking-tight leading-[1.08]">
            Find Your People. <br />
            <span className="bg-gradient-to-r from-teal-600 via-teal-500 to-amber-500 bg-clip-text text-transparent">
              Find Your Place.
            </span>
          </h1>
        </Reveal>

        <Reveal direction="up" delay={0.3}>
          <p className="text-base sm:text-xl text-slate-600 dark:text-slate-300 leading-relaxed max-w-2xl mx-auto">
            Moving to a new city shouldn't mean navigating housing, transit, and daily life alone.
            Tell NEST what you need — our AI matches you with enrolled local guides who actually live there.
          </p>
        </Reveal>

        {/* Dual Primary CTAs + Google Fast Track */}
        <Reveal direction="up" delay={0.4}>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-2 max-w-md mx-auto">
            <Link to="/register?role=newcomer" className="w-full sm:w-auto flex-1">
              <MagneticButton className="w-full inline-flex items-center justify-center gap-2 px-6 py-3.5 rounded-full bg-teal-700 hover:bg-teal-800 text-white font-semibold text-base shadow-lg shadow-teal-700/25 transition-all">
                <span>I'm New Here</span>
                <ArrowRight className="w-4 h-4" />
              </MagneticButton>
            </Link>
            <Link to="/register?role=helper" className="w-full sm:w-auto flex-1">
              <MagneticButton className="w-full inline-flex items-center justify-center gap-2 px-6 py-3.5 rounded-full border-2 border-slate-300 dark:border-slate-700 hover:border-teal-600 dark:hover:border-teal-500 bg-white dark:bg-slate-900 text-slate-800 dark:text-slate-200 font-semibold text-base transition-all">
                <span>I Want to Help</span>
              </MagneticButton>
            </Link>
          </div>

          {/* Google Fast Track */}
          <div className="pt-4 max-w-xs mx-auto">
            <div className="relative flex py-2 items-center">
              <div className="flex-grow border-t border-slate-200 dark:border-slate-800"></div>
              <span className="flex-shrink mx-3 text-xs text-slate-400 uppercase tracking-wider">or fast track with</span>
              <div className="flex-grow border-t border-slate-200 dark:border-slate-800"></div>
            </div>
            <GoogleSignInButton text="continue_with" />
          </div>
        </Reveal>

        {/* Interactive Demo Prompt Box */}
        <Reveal direction="up" delay={0.5} className="pt-6">
          <InteractiveDemoBox />
        </Reveal>
      </section>

      {/* 2. The 6-Step Human Loop Storytelling */}
      <section className="space-y-12 max-w-5xl mx-auto px-4">
        <div className="text-center space-y-3 max-w-2xl mx-auto">
          <Badge variant="neutral" size="sm">The NEST Journey</Badge>
          <h2 className="text-3xl sm:text-4xl font-extrabold font-heading text-slate-900 dark:text-white">
            How NEST Actually Solves Your Move
          </h2>
          <p className="text-sm sm:text-base text-slate-600 dark:text-slate-400">
            A purposeful, closed-loop coordination system designed for real-life solutions.
          </p>
        </div>

        <Stagger className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {/* Step 1 */}
          <StaggerItem>
            <Card hover className="p-6 h-full flex flex-col justify-between border-slate-200/80 dark:border-slate-800">
              <div className="space-y-3">
                <div className="w-12 h-12 rounded-2xl bg-teal-100 dark:bg-teal-950/60 text-teal-700 dark:text-teal-300 flex items-center justify-center font-heading font-extrabold text-lg">
                  01
                </div>
                <h3 className="text-lg font-bold font-heading text-slate-900 dark:text-white">
                  Speak Like a Human
                </h3>
                <p className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed">
                  No 20-field bureaucratic forms. Type your real requirements naturally: "Moving to Hinjewadi for my first job, need a PG under ₹12k and transit advice."
                </p>
              </div>
              <div className="pt-4 text-xs font-medium text-teal-600 dark:text-teal-400 flex items-center gap-1">
                <Sparkles className="w-3.5 h-3.5" />
                Natural Language Input
              </div>
            </Card>
          </StaggerItem>

          {/* Step 2 */}
          <StaggerItem>
            <Card hover className="p-6 h-full flex flex-col justify-between border-slate-200/80 dark:border-slate-800">
              <div className="space-y-3">
                <div className="w-12 h-12 rounded-2xl bg-amber-100 dark:bg-amber-950/60 text-amber-700 dark:text-amber-300 flex items-center justify-center font-heading font-extrabold text-lg">
                  02
                </div>
                <h3 className="text-lg font-bold font-heading text-slate-900 dark:text-white">
                  Grounded AI Parsing
                </h3>
                <p className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed">
                  NEST deterministically extracts exact neighborhood targets, budget boundaries, timing windows, and specific categories without AI hallucinations.
                </p>
              </div>
              <div className="pt-4 text-xs font-medium text-amber-600 dark:text-amber-400 flex items-center gap-1">
                <MapPin className="w-3.5 h-3.5" />
                Zero Hallucinations
              </div>
            </Card>
          </StaggerItem>

          {/* Step 3 */}
          <StaggerItem>
            <Card hover className="p-6 h-full flex flex-col justify-between border-slate-200/80 dark:border-slate-800">
              <div className="space-y-3">
                <div className="w-12 h-12 rounded-2xl bg-indigo-100 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-300 flex items-center justify-center font-heading font-extrabold text-lg">
                  03
                </div>
                <h3 className="text-lg font-bold font-heading text-slate-900 dark:text-white">
                  Local Helper Alerts
                </h3>
                <p className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed">
                  Enrolled helpers in that neighborhood see your need in their "Help Requests Near You" feed, matched by geographic proximity and proven domain knowledge.
                </p>
              </div>
              <div className="pt-4 text-xs font-medium text-indigo-600 dark:text-indigo-400 flex items-center gap-1">
                <Users className="w-3.5 h-3.5" />
                Real Local Residents
              </div>
            </Card>
          </StaggerItem>

          {/* Step 4 */}
          <StaggerItem>
            <Card hover className="p-6 h-full flex flex-col justify-between border-slate-200/80 dark:border-slate-800">
              <div className="space-y-3">
                <div className="w-12 h-12 rounded-2xl bg-emerald-100 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 flex items-center justify-center font-heading font-extrabold text-lg">
                  04
                </div>
                <h3 className="text-lg font-bold font-heading text-slate-900 dark:text-white">
                  Schedule Assistance Sessions
                </h3>
                <p className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed">
                  Coordinate 1-on-1 walkthroughs or meetups. Sessions enforce verified public venues (community centers, cafes, libraries) and calendar synchronization.
                </p>
              </div>
              <div className="pt-4 text-xs font-medium text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
                <Calendar className="w-3.5 h-3.5" />
                Verified Public Venues
              </div>
            </Card>
          </StaggerItem>

          {/* Step 5 */}
          <StaggerItem>
            <Card hover className="p-6 h-full flex flex-col justify-between border-slate-200/80 dark:border-slate-800">
              <div className="space-y-3">
                <div className="w-12 h-12 rounded-2xl bg-cyan-100 dark:bg-cyan-950/60 text-cyan-700 dark:text-cyan-300 flex items-center justify-center font-heading font-extrabold text-lg">
                  05
                </div>
                <h3 className="text-lg font-bold font-heading text-slate-900 dark:text-white">
                  Track Need Resolution
                </h3>
                <p className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed">
                  Mark each item as resolved (accommodation found, metro card understood, tiffin booked) with verified attribution to the helper who helped you.
                </p>
              </div>
              <div className="pt-4 text-xs font-medium text-cyan-600 dark:text-cyan-400 flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5" />
                Real Problem Solved
              </div>
            </Card>
          </StaggerItem>

          {/* Step 6 */}
          <StaggerItem>
            <Card hover className="p-6 h-full flex flex-col justify-between border-slate-200/80 dark:border-slate-800">
              <div className="space-y-3">
                <div className="w-12 h-12 rounded-2xl bg-rose-100 dark:bg-rose-950/60 text-rose-700 dark:text-rose-300 flex items-center justify-center font-heading font-extrabold text-lg">
                  06
                </div>
                <h3 className="text-lg font-bold font-heading text-slate-900 dark:text-white">
                  Earn Flocking Reputation
                </h3>
                <p className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed">
                  Both participants leave authentic reviews. Helpers earn reputation points that level them from Egg to Hatchling, Fledgling, and Roost Guide.
                </p>
              </div>
              <div className="pt-4 text-xs font-medium text-rose-600 dark:text-rose-400 flex items-center gap-1">
                <Award className="w-3.5 h-3.5" />
                Flock Reputation System
              </div>
            </Card>
          </StaggerItem>
        </Stagger>
      </section>

      {/* 3. Reputation & Trust Tiers Showcase */}
      <section className="max-w-4xl mx-auto px-4">
        <Reveal direction="up">
          <div className="rounded-3xl bg-gradient-to-br from-teal-900 to-slate-900 text-white p-8 sm:p-12 shadow-2xl relative overflow-hidden">
            <div className="absolute top-0 right-0 w-80 h-80 bg-teal-500/10 rounded-full blur-3xl pointer-events-none" />

            <div className="space-y-8 relative z-10">
              <div className="space-y-2">
                <span className="text-xs uppercase tracking-wider text-amber-400 font-semibold">Community Meritocracy</span>
                <h3 className="text-2xl sm:text-3xl font-extrabold font-heading">
                  The Nest Flock: Verified Reputation
                </h3>
                <p className="text-sm text-slate-300 max-w-xl">
                  No fake followers or pay-to-win badges. Reputation on NEST is earned strictly through completed sessions and verified newcomer resolutions.
                </p>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-2">
                <div className="p-4 rounded-2xl bg-white/5 border border-white/10 text-center space-y-1.5 backdrop-blur-sm">
                  <div className="text-2xl">🥚</div>
                  <div className="text-sm font-bold">Egg</div>
                  <div className="text-[11px] text-slate-400">Newly enrolled helper</div>
                </div>
                <div className="p-4 rounded-2xl bg-white/5 border border-white/10 text-center space-y-1.5 backdrop-blur-sm">
                  <div className="text-2xl">🐣</div>
                  <div className="text-sm font-bold">Hatchling</div>
                  <div className="text-[11px] text-slate-400">First completed session</div>
                </div>
                <div className="p-4 rounded-2xl bg-white/5 border border-white/10 text-center space-y-1.5 backdrop-blur-sm">
                  <div className="text-2xl">🐥</div>
                  <div className="text-sm font-bold">Fledgling</div>
                  <div className="text-[11px] text-slate-400">5+ verified resolutions</div>
                </div>
                <div className="p-4 rounded-2xl bg-teal-500/20 border border-teal-400/40 text-center space-y-1.5 backdrop-blur-sm">
                  <div className="text-2xl">🦅</div>
                  <div className="text-sm font-bold text-amber-300">Roost Guide</div>
                  <div className="text-[11px] text-teal-200">Community pillars (4.8★)</div>
                </div>
              </div>
            </div>
          </div>
        </Reveal>
      </section>

      {/* 4. Privacy & Safety Guarantees */}
      <section className="max-w-4xl mx-auto px-4">
        <Reveal direction="up">
          <div className="rounded-3xl bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-8 sm:p-10 space-y-6">
            <div className="flex items-center gap-3">
              <div className="p-3 rounded-2xl bg-teal-700 text-white shadow-md">
                <Shield className="w-6 h-6 text-amber-300" />
              </div>
              <div>
                <h3 className="text-xl font-bold font-heading text-slate-900 dark:text-white">
                  Built for Community Problem-Solving, Not Social Media
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Transparent, accountable, and private.
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
              <div className="flex items-start gap-3 text-slate-700 dark:text-slate-300">
                <CheckCircle2 className="w-5 h-5 text-teal-600 dark:text-teal-400 shrink-0 mt-0.5" />
                <span>
                  <strong>No fake vanity metrics:</strong> No likes, followers, public feeds, or selfie galleries.
                </span>
              </div>
              <div className="flex items-start gap-3 text-slate-700 dark:text-slate-300">
                <CheckCircle2 className="w-5 h-5 text-teal-600 dark:text-teal-400 shrink-0 mt-0.5" />
                <span>
                  <strong>Honest trust language:</strong> NEST uses reputation and community feedback to help you evaluate connections.
                </span>
              </div>
              <div className="flex items-start gap-3 text-slate-700 dark:text-slate-300">
                <CheckCircle2 className="w-5 h-5 text-teal-600 dark:text-teal-400 shrink-0 mt-0.5" />
                <span>
                  <strong>Area-level privacy:</strong> Exact home addresses and contact numbers are never exposed publicly.
                </span>
              </div>
              <div className="flex items-start gap-3 text-slate-700 dark:text-slate-300">
                <CheckCircle2 className="w-5 h-5 text-teal-600 dark:text-teal-400 shrink-0 mt-0.5" />
                <span>
                  <strong>Explainable AI matching:</strong> Transparent match factors break down why each connection was suggested.
                </span>
              </div>
            </div>

            <div className="pt-4 border-t border-slate-200 dark:border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-4">
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Join thousands of newcomers settling smoothly into their new city.
              </p>
              <Link to="/register">
                <Button size="md" className="font-semibold shadow-sm">
                  Get Started Today
                </Button>
              </Link>
            </div>
          </div>
        </Reveal>
      </section>
    </div>
  );
}
