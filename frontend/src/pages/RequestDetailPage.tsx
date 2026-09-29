import { useState, useEffect } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { requestsService } from "@/services/requests";
import { useToast } from "@/hooks/useToast";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Textarea } from "@/components/ui/Textarea";
import { Modal } from "@/components/ui/Modal";
import { AreaMap } from "@/components/map/AreaMap";
import { RequestCommunityKnowledge } from "@/components/community/RequestCommunityKnowledge";
import { formatDate } from "@/lib/utils";
import type { NewcomerRequest } from "@/types/request";
import {
  Sparkles,
  MapPin,
  Edit3,
  Trash2,
  ArrowLeft,
  CheckCircle2,
  Clock,
  Layers,
} from "lucide-react";

export function RequestDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [request, setRequest] = useState<NewcomerRequest | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isEditing, setIsEditing] = useState(false);
  const [editText, setEditText] = useState("");
  const [editStatus, setEditStatus] = useState("OPEN");
  const [isUpdating, setIsUpdating] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);

  const navigate = useNavigate();
  const { success: toastSuccess, error: toastError } = useToast();

  const loadRequest = () => {
    if (!id) return;
    setIsLoading(true);
    requestsService
      .getRequestById(id)
      .then((data) => {
        setRequest(data);
        setEditText(data.raw_text);
        setEditStatus(data.status);
      })
      .catch(() => {
        toastError("Could not find this request.");
        navigate("/requests");
      })
      .finally(() => setIsLoading(false));
  };

  useEffect(() => {
    loadRequest();
  }, [id]);

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!id || !editText.trim()) return;

    setIsUpdating(true);
    try {
      const updated = await requestsService.updateRequest(id, {
        text: editText.trim(),
        status: editStatus,
      });
      setRequest(updated);
      setIsEditing(false);
      toastSuccess("Request updated and re-parsed by backend NLP engine!", "Updated");
    } catch {
      toastError("Failed to update request.");
    } finally {
      setIsUpdating(false);
    }
  };

  const handleDelete = async () => {
    if (!id) return;
    setIsDeleting(true);
    try {
      await requestsService.deleteRequest(id);
      toastSuccess("Request deleted.");
      navigate("/requests");
    } catch {
      toastError("Failed to delete request.");
    } finally {
      setIsDeleting(false);
    }
  };

  if (isLoading || !request) {
    return (
      <div className="max-w-4xl mx-auto py-12 text-center text-sm text-gray-500">
        Loading request details...
      </div>
    );
  }

  const needs = request.extracted_requirements?.needs || [];
  const preferences = request.preferences || [];
  const userContext = request.user_context || [];

  return (
    <div className="space-y-8 max-w-4xl mx-auto py-2 sm:py-6">
      {/* Back button and Meta */}
      <div className="flex items-center justify-between">
        <Link
          to="/requests"
          className="text-xs font-semibold text-brand-primary dark:text-teal-400 flex items-center gap-1 hover:underline min-h-[44px]"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Requests
        </Link>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsEditing(!isEditing)}
            leftIcon={<Edit3 className="w-3.5 h-3.5" />}
          >
            {isEditing ? "Cancel Edit" : "Edit Request"}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowDeleteModal(true)}
            className="text-brand-danger hover:bg-red-50 dark:hover:bg-red-950/30"
            leftIcon={<Trash2 className="w-3.5 h-3.5" />}
          >
            Delete
          </Button>
        </div>
      </div>

      {/* Main Request & Understanding Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Original Request & Edit */}
        <div className="lg:col-span-2 space-y-6">
          <Card className="space-y-5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-gray-400 flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5" />
                Submitted {formatDate(request.created_at)}
              </span>
              <Badge variant={request.status === "MATCHED" ? "success" : "primary"}>
                {request.status}
              </Badge>
            </div>

            {isEditing ? (
              <form onSubmit={handleUpdate} className="space-y-4 pt-2">
                <Textarea
                  label="Update Request Text (triggers automatic backend NLP re-parse)"
                  value={editText}
                  onChange={(e) => setEditText(e.target.value)}
                  rows={4}
                  required
                />

                <div className="space-y-1.5">
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-200">
                    Status
                  </label>
                  <select
                    value={editStatus}
                    onChange={(e) => setEditStatus(e.target.value)}
                    className="w-full rounded-input border border-gray-300 dark:border-brand-dark-border bg-white dark:bg-brand-dark-card text-gray-900 dark:text-gray-100 p-2.5 text-sm"
                  >
                    <option value="OPEN">OPEN</option>
                    <option value="MATCHED">MATCHED</option>
                    <option value="CLOSED">CLOSED</option>
                  </select>
                </div>

                <div className="flex justify-end gap-2 pt-2">
                  <Button type="button" variant="outline" onClick={() => setIsEditing(false)}>
                    Cancel
                  </Button>
                  <Button type="submit" isLoading={isUpdating}>
                    Save & Re-parse
                  </Button>
                </div>
              </form>
            ) : (
              <div>
                <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
                  Original User Request
                </h2>
                <p className="text-lg font-medium text-gray-900 dark:text-gray-100 leading-relaxed italic bg-gray-50/70 dark:bg-brand-dark-muted/20 p-4 rounded-xl border border-gray-200/60 dark:border-brand-dark-border">
                  "{request.raw_text}"
                </p>
              </div>
            )}
          </Card>

          {/* Structured Intelligence Section */}
          <Card className="space-y-5">
            <div className="flex items-center gap-2 text-brand-primary dark:text-teal-300">
              <Sparkles className="w-5 h-5 text-amber-500" />
              <h3 className="text-lg font-bold font-heading text-gray-900 dark:text-gray-100">
                What NEST Extracted
              </h3>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
              {/* Target Location */}
              <div className="p-3.5 rounded-xl bg-teal-50/50 dark:bg-brand-dark-muted/20 border border-teal-100 dark:border-brand-dark-border space-y-1">
                <span className="text-xs font-semibold text-gray-500 dark:text-gray-400 flex items-center gap-1">
                  <MapPin className="w-3.5 h-3.5 text-brand-primary" />
                  Target Area & City
                </span>
                <p className="font-bold text-gray-900 dark:text-gray-100 text-base">
                  {[request.area, request.city].filter(Boolean).join(", ") || "City-wide"}
                </p>
                {request.state && (
                  <p className="text-xs text-gray-500">{request.state}, {request.country || "India"}</p>
                )}
              </div>

              {/* Target Budget */}
              <div className="p-3.5 rounded-xl bg-amber-50/50 dark:bg-amber-950/20 border border-amber-100 dark:border-amber-900/40 space-y-1">
                <span className="text-xs font-semibold text-gray-500 dark:text-gray-400">
                  Target Budget
                </span>
                <p className="font-bold text-amber-900 dark:text-amber-200 text-base">
                  {request.budget_amount != null
                    ? `${request.budget_operator === "<=" ? "Under " : ""}₹${request.budget_amount.toLocaleString("en-IN")}${request.budget_period ? ` / ${request.budget_period}` : ""}`
                    : "Flexible / Not specified"}
                </p>
              </div>
            </div>

            {/* Extracted Needs */}
            <div className="space-y-2">
              <span className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Categorized Needs ({needs.length})
              </span>
              <div className="flex flex-wrap gap-2">
                {needs.length === 0 ? (
                  <span className="text-xs text-gray-400 italic">General assistance</span>
                ) : (
                  needs.map((n, idx) => (
                    <Badge key={idx} variant="primary" size="md" icon="🏠">
                      <span>{n.item}</span>
                      <span className="text-[10px] text-gray-400">({n.category})</span>
                    </Badge>
                  ))
                )}
              </div>
            </div>

            {/* Preferences */}
            {preferences.length > 0 && (
              <div className="space-y-2 pt-2 border-t border-gray-100 dark:border-brand-dark-border/60">
                <span className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Dietary & Lifestyle Preferences
                </span>
                <div className="flex flex-wrap gap-2">
                  {preferences.map((p, idx) => (
                    <Badge key={idx} variant="success" size="md" icon="🌱">
                      {p}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {/* User Context */}
            {userContext.length > 0 && (
              <div className="space-y-2 pt-2 border-t border-gray-100 dark:border-brand-dark-border/60">
                <span className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Situation & Purpose
                </span>
                <div className="flex flex-wrap gap-2">
                  {userContext.map((c, idx) => (
                    <Badge key={idx} variant="muted" size="md" icon="💼">
                      {c}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            <div className="pt-2 text-right">
              <span className="text-[11px] text-gray-400 font-mono">
                Parser: {request.extraction_method}
              </span>
            </div>
          </Card>
        </div>

        {/* Right Sidebar: Approximate Map & Matching Status */}
        <div className="space-y-6">
          <AreaMap
            areaName={request.area || undefined}
            cityName={request.city || undefined}
          />

          <Card className="p-5 space-y-3 bg-teal-50/40 dark:bg-brand-dark-muted/20 border-teal-100 dark:border-brand-dark-border">
            <div className="flex items-center gap-2 text-brand-primary dark:text-teal-300 font-semibold text-sm">
              <Layers className="w-4 h-4" />
              <span>Semantic Embedding</span>
            </div>
            <p className="text-xs text-gray-600 dark:text-gray-300 leading-relaxed">
              This request is vectorized into 384 dimensions on PostgreSQL 16 using all-MiniLM-L6-v2 and ready for Phase 5 hybrid cosine scoring.
            </p>
          </Card>

          <RequestCommunityKnowledge
            requestId={request.id}
            city={request.city}
            area={request.area}
          />
        </div>
      </div>

      {/* Phase 5 Live Hybrid Matching Section */}
      <section className="pt-6 border-t border-gray-200 dark:border-brand-dark-border space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h3 className="text-xl font-bold font-heading text-gray-900 dark:text-gray-100 flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-brand-primary" />
              Recommended Community Helpers
            </h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              PostgreSQL pgvector cosine scoring, location proximity decay, and skill compatibility.
            </p>
          </div>
          <Link to={`/results/${request.id}`}>
            <Button
              variant="primary"
              size="md"
              leftIcon={<Sparkles className="w-4 h-4 text-amber-300" />}
            >
              View Hybrid Match Results
            </Button>
          </Link>
        </div>

        <Card className="p-6 bg-teal-50/30 dark:bg-brand-dark-muted/10 border-teal-100 dark:border-brand-dark-border flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="space-y-1">
            <h4 className="font-bold text-gray-900 dark:text-gray-100 text-sm">
              Real-Time AI Candidate Matching Ready
            </h4>
            <p className="text-xs text-gray-600 dark:text-gray-300">
              Explore candidates ranked by 384-dimensional vector similarity, adjust multi-factor weight sliders, and inspect radar scores.
            </p>
          </div>
          <Link to={`/results/${request.id}`}>
            <Button variant="outline" size="sm">
              Explore Candidates →
            </Button>
          </Link>
        </Card>
      </section>

      {/* Delete Modal */}
      <Modal
        isOpen={showDeleteModal}
        onClose={() => setShowDeleteModal(false)}
        title="Delete Request"
        description="Permanently delete this request from the NEST database? This action cannot be undone."
      >
        <div className="flex justify-end gap-3 pt-4">
          <Button
            variant="outline"
            onClick={() => setShowDeleteModal(false)}
            disabled={isDeleting}
          >
            Cancel
          </Button>
          <Button
            variant="danger"
            isLoading={isDeleting}
            onClick={handleDelete}
            leftIcon={<Trash2 className="w-4 h-4" />}
          >
            Delete Permanently
          </Button>
        </div>
      </Modal>
    </div>
  );
}
