import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { PlaceAutocomplete } from "@/components/location/PlaceAutocomplete";
import { LocationPicker } from "@/components/location/LocationPicker";
import { GoogleMap } from "@/components/location/GoogleMap";
import * as locationService from "@/services/location";

describe("PlaceAutocomplete Component", () => {
  it("renders search input with placeholder", () => {
    render(<PlaceAutocomplete onSelectPrediction={vi.fn()} />);
    expect(
      screen.getByPlaceholderText(/Search area, locality, or city/i)
    ).toBeInTheDocument();
  });

  it("fetches and displays predictions when typing", async () => {
    vi.spyOn(locationService, "autocompletePlaces").mockResolvedValue({
      predictions: [
        {
          place_id: "place_123",
          main_text: "Whitefield",
          secondary_text: "Bengaluru, Karnataka, India",
          description: "Whitefield, Bengaluru, Karnataka, India",
        },
      ],
    });

    const onSelect = vi.fn();
    render(<PlaceAutocomplete onSelectPrediction={onSelect} />);

    const input = screen.getByPlaceholderText(/Search area, locality, or city/i);
    fireEvent.change(input, { target: { value: "Whitefield" } });

    await waitFor(() => {
      expect(screen.getByText("Whitefield")).toBeInTheDocument();
      expect(screen.getByText("Bengaluru, Karnataka, India")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Whitefield"));
    expect(onSelect).toHaveBeenCalledWith(
      expect.objectContaining({ place_id: "place_123", main_text: "Whitefield" })
    );
  });
});

describe("LocationPicker Component", () => {
  it("renders place search, geolocation button, and manual fields", () => {
    const onChange = vi.fn();
    render(
      <LocationPicker
        value={{
          city: "Bengaluru",
          area: "Whitefield",
          country: "India",
          location_source: "google_places",
          latitude: 12.97,
          longitude: 77.75,
        }}
        onChange={onChange}
      />
    );

    expect(screen.getByText(/Search Location in India/i)).toBeInTheDocument();
    expect(screen.getByText(/Use My Current Location/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/City \*/i)).toHaveValue("Bengaluru");
    expect(screen.getByLabelText(/Area \/ Neighborhood/i)).toHaveValue("Whitefield");
    expect(screen.getByText(/Source: google places/i)).toBeInTheDocument();
  });
});

describe("GoogleMap Component", () => {
  it("renders privacy-protected fallback view gracefully when Google JS API is not loaded", async () => {
    render(
      <GoogleMap
        targetLocation={{
          latitude: 12.9698,
          longitude: 77.7500,
          label: "Whitefield, Bengaluru",
        }}
        candidates={[
          {
            id: "user-1",
            name: "Rahul Sharma",
            approximateLatitude: 12.97,
            approximateLongitude: 77.75,
            area: "Whitefield",
            city: "Bengaluru",
            distanceKm: 1.2,
            score: 0.88,
          },
        ]}
      />
    );

    await waitFor(() => {
      expect(screen.getByText(/Privacy Protected/i)).toBeInTheDocument();
      expect(screen.getByText(/Whitefield, Bengaluru/i)).toBeInTheDocument();
      expect(screen.getByText(/Rahul/i)).toBeInTheDocument();
    });
  });
});
