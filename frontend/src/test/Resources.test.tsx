import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { ResourceCard } from "@/components/resource/ResourceCard";
import { ResourcesPage } from "@/pages/ResourcesPage";
import * as resourceService from "@/services/resources";
import type { ResourceCategory, ResourceItem, ResourceSearchResponse } from "@/types/resource";

// Mock Google Maps loader to return false (graceful fallback in test environment)
vi.mock("@/lib/google-maps-loader", () => ({
  loadGoogleMaps: vi.fn().mockResolvedValue(false),
}));

const mockCategories: ResourceCategory[] = [
  {
    id: "pg_coliving",
    display_name: "PG & Co-Living",
    icon: "Home",
    description: "Paying guest accommodations, hostels, and shared flats",
    default_query_terms: ["pg", "hostel", "coliving"],
  },
  {
    id: "tiffin_food",
    display_name: "Tiffin & Mess",
    icon: "Utensils",
    description: "Daily meal services, mess, home-style food, and caterers",
    default_query_terms: ["tiffin", "mess", "dabba"],
  },
  {
    id: "healthcare_pharmacy",
    display_name: "Healthcare & Pharmacy",
    icon: "Hospital",
    description: "Clinics, hospitals, 24/7 medical stores, and doctors",
    default_query_terms: ["clinic", "hospital", "pharmacy"],
  },
];

const mockResourceWithFullDetails: ResourceItem = {
  id: "res-1",
  name: "Zolo Stays Hinjewadi",
  category: "pg_coliving",
  category_display_name: "PG & Co-Living",
  formatted_address: "Phase 1, Hinjewadi Rajiv Gandhi Infotech Park, Pune",
  latitude: 18.5912,
  longitude: 73.7389,
  distance_km: 1.5,
  rating: 4.5,
  review_count: 120,
  price_level: "MODERATE",
  is_open_now: true,
  google_place_id: "ChIJ1234567890",
  maps_url: "https://maps.google.com/?cid=123",
  website_url: "https://example.com",
  phone_number: "+91 98765 43210",
  ranking_score: 0.82,
  ranking_reasons: [
    "Nearby (1.5 km)",
    "High rating: 4.5★ (120 reviews)",
    "Category match: pg_coliving",
  ],
};

const mockResourceWithMissingFields: ResourceItem = {
  id: "res-2",
  name: "Local Hinjewadi Tiffin Center",
  category: "tiffin_food",
  category_display_name: "Tiffin & Mess",
  formatted_address: "Near Shivaji Chowk, Hinjewadi, Pune",
  latitude: 18.5925,
  longitude: 73.7401,
  distance_km: 0.8,
  rating: null,
  review_count: null,
  price_level: null,
  is_open_now: null,
  google_place_id: "ChIJ0987654321",
  maps_url: null,
  website_url: null,
  phone_number: null,
  ranking_score: 0.74,
  ranking_reasons: ["Nearby (0.8 km)", "Category match: tiffin_food"],
};

describe("Phase 10: ResourceCard Component", () => {
  it("renders all resource details, rating, distance, open status, and ranking reasons", () => {
    render(<ResourceCard resource={mockResourceWithFullDetails} />);

    expect(screen.getByText("Zolo Stays Hinjewadi")).toBeInTheDocument();
    expect(screen.getByText("4.5")).toBeInTheDocument();
    expect(screen.getByText("(120)")).toBeInTheDocument();
    expect(screen.getByText("1.5 km away")).toBeInTheDocument();
    expect(screen.getByText("Open Now")).toBeInTheDocument();
    expect(
      screen.getByText("Phase 1, Hinjewadi Rajiv Gandhi Infotech Park, Pune")
    ).toBeInTheDocument();
    expect(screen.getByText("MODERATE")).toBeInTheDocument();
    expect(
      screen.getByText(/Nearby \(1.5 km\) • High rating: 4.5★ \(120 reviews\) • Category match: pg_coliving/)
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /open in maps/i })).toBeInTheDocument();
  });

  it("honestly renders null ratings and missing hours without fabricating fake data", () => {
    render(<ResourceCard resource={mockResourceWithMissingFields} />);

    expect(screen.getByText("Local Hinjewadi Tiffin Center")).toBeInTheDocument();
    expect(screen.getByText("Rating unavailable")).toBeInTheDocument();
    expect(screen.queryByText("(0)")).not.toBeInTheDocument();
    expect(screen.queryByText("Open Now")).not.toBeInTheDocument();
    expect(screen.queryByText("Closed")).not.toBeInTheDocument();
    expect(screen.getByText("800 m away")).toBeInTheDocument();
  });
});

describe("Phase 10: ResourcesPage Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(resourceService, "getResourceCategories").mockResolvedValue({
      categories: mockCategories,
      total: mockCategories.length,
    });
  });

  it("loads and displays category filter chips and default search results", async () => {
    const mockSearchResponse: ResourceSearchResponse = {
      status: "SUCCESS",
      total: 1,
      resources: [mockResourceWithFullDetails],
      search_center: {
        latitude: 18.5912,
        longitude: 73.7389,
        label: "Hinjewadi, Pune",
      },
      category: "pg_coliving",
      query: "pg hostel coliving",
      radius_meters: 5000,
    };

    vi.spyOn(resourceService, "searchResources").mockResolvedValue(mockSearchResponse);

    render(
      <MemoryRouter initialEntries={["/resources"]}>
        <ResourcesPage />
      </MemoryRouter>
    );

    // Verify categories load
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /pg & co-living/i })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /tiffin & mess/i })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /healthcare & pharmacy/i })).toBeInTheDocument();
    });

    // Verify search results load
    await waitFor(() => {
      expect(screen.getByText("Zolo Stays Hinjewadi")).toBeInTheDocument();
      expect(screen.getByText(/Searching places near/i)).toBeInTheDocument();
    });
  });

  it("handles category selection and text search query", async () => {
    const searchSpy = vi.spyOn(resourceService, "searchResources").mockResolvedValue({
      status: "SUCCESS",
      total: 1,
      resources: [mockResourceWithMissingFields],
      search_center: {
        latitude: 18.5912,
        longitude: 73.7389,
        label: "Hinjewadi, Pune",
      },
      category: "tiffin_food",
      query: "home mess",
      radius_meters: 5000,
    });

    render(
      <MemoryRouter initialEntries={["/resources"]}>
        <ResourcesPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /tiffin & mess/i })).toBeInTheDocument();
    });

    // Click Tiffin & Mess category chip
    fireEvent.click(screen.getByRole("button", { name: /tiffin & mess/i }));

    // Enter custom query
    const input = screen.getByPlaceholderText(/Search places by name or specialty/i);
    fireEvent.change(input, { target: { value: "home mess" } });

    await waitFor(() => {
      expect(searchSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          category: "tiffin_food",
        })
      );
      expect(screen.getByText("Local Hinjewadi Tiffin Center")).toBeInTheDocument();
    });
  });

  it("displays provider unavailable state honestly when Google Places is unconfigured or fails", async () => {
    vi.spyOn(resourceService, "searchResources").mockResolvedValue({
      status: "PROVIDER_UNAVAILABLE",
      total: 0,
      resources: [],
      search_center: {
        latitude: 18.5912,
        longitude: 73.7389,
        label: "Hinjewadi, Pune",
      },
      category: "pg_coliving",
      query: "pg hostel",
      radius_meters: 5000,
    });

    render(
      <MemoryRouter initialEntries={["/resources"]}>
        <ResourcesPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("Local Places Search Unavailable")).toBeInTheDocument();
      expect(
        screen.getByText(/NEST does not fabricate fake businesses/i)
      ).toBeInTheDocument();
    });
  });

  it("toggles between List View and Map View", async () => {
    vi.spyOn(resourceService, "searchResources").mockResolvedValue({
      status: "SUCCESS",
      total: 1,
      resources: [mockResourceWithFullDetails],
      search_center: {
        latitude: 18.5912,
        longitude: 73.7389,
        label: "Hinjewadi, Pune",
      },
      category: "pg_coliving",
      query: "pg hostel",
      radius_meters: 5000,
    });

    render(
      <MemoryRouter initialEntries={["/resources"]}>
        <ResourcesPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("Zolo Stays Hinjewadi")).toBeInTheDocument();
    });

    // Click Map toggle button
    const mapBtn = screen.getByRole("button", { name: /^Map$/i });
    fireEvent.click(mapBtn);

    // Map container fallback should render
    await waitFor(() => {
      expect(screen.getByText(/Geographic Distribution/i)).toBeInTheDocument();
      expect(screen.getByText(/Privacy Protected/i)).toBeInTheDocument();
    });
  });
});
