import React, { useState, useEffect } from "react";
import { Button } from "../ui/Button";
import { useToast } from "@/hooks/useToast";
import type { LocationCreateOrUpdatePayload } from "@/types/profile";
import { ShieldCheck } from "lucide-react";
import { LocationPicker } from "../location/LocationPicker";

export interface LocationFormProps {
  initialValues?: LocationCreateOrUpdatePayload;
  onSubmit: (data: LocationCreateOrUpdatePayload) => Promise<void>;
  isLoading?: boolean;
  submitLabel?: string;
}

export function LocationForm({
  initialValues,
  onSubmit,
  isLoading = false,
  submitLabel = "Save Location",
}: LocationFormProps) {
  const [locationData, setLocationData] = useState<LocationCreateOrUpdatePayload>(
    initialValues || { city: "", country: "India" }
  );

  useEffect(() => {
    if (initialValues) {
      setLocationData(initialValues);
    }
  }, [initialValues]);

  const { error: toastError } = useToast();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!locationData.city?.trim()) {
      toastError("City is required.");
      return;
    }

    await onSubmit({
      ...locationData,
      city: locationData.city.trim(),
      area: locationData.area?.trim() || undefined,
      state: locationData.state?.trim() || undefined,
      country: locationData.country?.trim() || "India",
      display_name: locationData.display_name?.trim() || undefined,
      place_types: locationData.place_types || undefined,
      google_place_id: locationData.google_place_id || undefined,
      formatted_address: locationData.formatted_address || undefined,
      postal_code: locationData.postal_code || undefined,
      private_unit: locationData.private_unit?.trim() || undefined,
      location_source: locationData.location_source || "manual",
      location_precision: locationData.location_precision || "locality",
    });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <div className="flex items-start gap-2.5 p-3.5 rounded-xl bg-teal-50/70 dark:bg-brand-dark-muted/30 border border-teal-100 dark:border-brand-dark-border">
        <ShieldCheck className="w-5 h-5 text-brand-primary dark:text-teal-400 mt-0.5 shrink-0" />
        <p className="text-xs text-gray-600 dark:text-gray-300">
          We use approximate location to improve local recommendations. We never expose your exact home address.
        </p>
      </div>

      <LocationPicker
        value={locationData}
        onChange={setLocationData}
        disabled={isLoading}
      />

      <Button type="submit" isLoading={isLoading} className="w-full sm:w-auto">
        {submitLabel}
      </Button>
    </form>
  );
}
