import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { PlaceAutocomplete } from "@/components/location/PlaceAutocomplete";
import { LocationPicker } from "@/components/location/LocationPicker";
import { GoogleMap } from "@/components/location/GoogleMap";
import * as locationService from "@/services/location";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

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
      expect(screen.getByText(/Bengaluru, Karnataka, India/i)).toBeInTheDocument();
    }, { timeout: 4000 });

    fireEvent.click(screen.getByText("Whitefield"));
    expect(onSelect).toHaveBeenCalledWith(
      expect.objectContaining({ place_id: "place_123", main_text: "Whitefield" })
    );
  });

  it("renders disambiguation notice and badges for duplicate place names", async () => {
    vi.spyOn(locationService, "autocompletePlaces").mockResolvedValue({
      predictions: [
        {
          place_id: "place_pune",
          main_text: "Mahalunge",
          secondary_text: "Pune, Maharashtra, India",
          description: "Mahalunge, Pune, Maharashtra, India",
        },
        {
          place_id: "place_khed",
          main_text: "Mahalunge",
          secondary_text: "Maharashtra 410501, India",
          description: "Mahalunge, Maharashtra 410501, India",
        },
      ],
    });

    const onSelect = vi.fn();
    render(<PlaceAutocomplete onSelectPrediction={onSelect} />);

    const input = screen.getByPlaceholderText(/Search area, locality, or city/i);
    fireEvent.change(input, { target: { value: "Mahalunge" } });

    await waitFor(() => {
      expect(
        screen.getByText(/Multiple places share this name/i)
      ).toBeInTheDocument();
      expect(screen.getAllByText(/Ambiguous name/i)).toHaveLength(2);
      expect(screen.getByText(/Pune, Maharashtra, India/i)).toBeInTheDocument();
      expect(screen.getByText(/Maharashtra 410501, India/i)).toBeInTheDocument();
    });
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

  it("handles geolocation and shows confirmation card before applying", async () => {
    vi.spyOn(locationService, "reverseGeocodeCoordinates").mockResolvedValue({
      google_place_id: "place_rev_1",
      city: "Pune",
      area: "Mahalunge",
      state: "Maharashtra",
      country: "India",
      postal_code: "411045",
      formatted_address: "Mahalunge, Pune, Maharashtra 411045, India",
      latitude: 18.5738,
      longitude: 73.7561,
      location_precision: "rooftop",
      location_source: "google_places_reverse_nearby",
    });

    const mockGeolocation = {
      getCurrentPosition: vi.fn().mockImplementation((success) =>
        success({
          coords: {
            latitude: 18.5738,
            longitude: 73.7561,
          },
        })
      ),
    };
    vi.stubGlobal("navigator", { ...navigator, geolocation: mockGeolocation });

    const onChange = vi.fn();
    render(
      <LocationPicker
        value={{
          city: "",
          country: "India",
        }}
        onChange={onChange}
      />
    );

    fireEvent.click(screen.getByText(/Use My Current Location/i));

    await waitFor(() => {
      expect(
        screen.getByText(/Current Location Detected via Device GPS/i)
      ).toBeInTheDocument();
      expect(screen.getByText(/Mahalunge, Pune, Maharashtra 411045, India/i)).toBeInTheDocument();
    });

    // Clicking 'Use this location' explicitly confirms and calls onChange
    fireEvent.click(screen.getByText(/Use this location/i));
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({
        city: "Pune",
        area: "Mahalunge",
        postal_code: "411045",
        location_source: "browser_geolocation",
      })
    );
  });

  it("displays clear error when geolocation permission is denied", async () => {
    const mockGeolocation = {
      getCurrentPosition: vi.fn().mockImplementation((_, error) =>
        error({
          code: 1, // PERMISSION_DENIED
          PERMISSION_DENIED: 1,
        })
      ),
    };
    vi.stubGlobal("navigator", { ...navigator, geolocation: mockGeolocation });

    render(
      <LocationPicker
        value={{
          city: "",
          country: "India",
        }}
        onChange={vi.fn()}
      />
    );

    fireEvent.click(screen.getByText(/Use My Current Location/i));

    await waitFor(() => {
      expect(
        screen.getByText(/Location access was denied. You can search or enter your city manually./i)
      ).toBeInTheDocument();
    });
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
