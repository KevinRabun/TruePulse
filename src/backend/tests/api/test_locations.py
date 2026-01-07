"""
Tests for location API endpoints.

Tests the static JSON-based location data endpoints.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.unit
class TestLocationsEndpoints:
    """Test location endpoints."""

    async def test_get_countries_returns_list(self, client: AsyncClient) -> None:
        """Test that get countries returns a list of countries."""
        response = await client.get("/api/v1/locations/countries")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should have at least some countries
        assert len(data) > 0

    async def test_get_countries_structure(self, client: AsyncClient) -> None:
        """Test that country objects have expected structure."""
        response = await client.get("/api/v1/locations/countries")
        assert response.status_code == 200
        data = response.json()

        # Check first country has expected fields
        if len(data) > 0:
            country = data[0]
            assert "code" in country
            assert "name" in country
            assert isinstance(country["code"], str)
            assert isinstance(country["name"], str)

    async def test_get_countries_sorted_by_name(self, client: AsyncClient) -> None:
        """Test that countries are sorted by name."""
        response = await client.get("/api/v1/locations/countries")
        assert response.status_code == 200
        data = response.json()

        if len(data) > 1:
            names = [c["name"] for c in data]
            assert names == sorted(names)

    async def test_get_countries_search_filter(self, client: AsyncClient) -> None:
        """Test that search parameter filters countries."""
        response = await client.get("/api/v1/locations/countries", params={"search": "united"})
        assert response.status_code == 200
        data = response.json()

        # All returned countries should contain "united" (case-insensitive)
        for country in data:
            assert "united" in country["name"].lower()

    async def test_get_countries_search_no_results(self, client: AsyncClient) -> None:
        """Test search with no matches returns empty list."""
        response = await client.get("/api/v1/locations/countries", params={"search": "xyznonexistent123"})
        assert response.status_code == 200
        data = response.json()
        assert data == []

    async def test_get_states_by_country_us(self, client: AsyncClient) -> None:
        """Test getting US states."""
        response = await client.get("/api/v1/locations/countries/US/states")
        assert response.status_code == 200
        data = response.json()

        # Should have US states
        assert isinstance(data, list)
        if len(data) > 0:
            state = data[0]
            assert "id" in state
            assert "name" in state
            assert "country_code" in state
            assert state["country_code"] == "US"

    async def test_get_states_by_country_case_insensitive(self, client: AsyncClient) -> None:
        """Test country code is case insensitive."""
        response_upper = await client.get("/api/v1/locations/countries/US/states")
        response_lower = await client.get("/api/v1/locations/countries/us/states")

        assert response_upper.status_code == 200
        assert response_lower.status_code == 200
        assert response_upper.json() == response_lower.json()

    async def test_get_states_unknown_country_returns_empty(self, client: AsyncClient) -> None:
        """Test unknown country code returns empty list."""
        response = await client.get("/api/v1/locations/countries/XX/states")
        assert response.status_code == 200
        data = response.json()
        assert data == []

    async def test_get_states_search_filter(self, client: AsyncClient) -> None:
        """Test that search parameter filters states."""
        response = await client.get("/api/v1/locations/countries/US/states", params={"search": "new"})
        assert response.status_code == 200
        data = response.json()

        # All returned states should contain "new" (case-insensitive)
        for state in data:
            assert "new" in state["name"].lower()

    async def test_get_cities_by_state(self, client: AsyncClient) -> None:
        """Test getting cities for a state."""
        # California (id=5) should have cities
        response = await client.get("/api/v1/locations/states/5/cities")
        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        if len(data) > 0:
            city = data[0]
            assert "id" in city
            assert "name" in city
            assert "state_id" in city
            assert city["state_id"] == 5

    async def test_get_cities_unknown_state_returns_empty(self, client: AsyncClient) -> None:
        """Test unknown state ID returns empty list."""
        response = await client.get("/api/v1/locations/states/99999/cities")
        assert response.status_code == 200
        data = response.json()
        assert data == []

    async def test_get_cities_search_filter(self, client: AsyncClient) -> None:
        """Test that search parameter filters cities."""
        response = await client.get("/api/v1/locations/states/5/cities", params={"search": "san"})
        assert response.status_code == 200
        data = response.json()

        # All returned cities should contain "san" (case-insensitive)
        for city in data:
            assert "san" in city["name"].lower()


@pytest.mark.unit
class TestLocationDataLoading:
    """Test location data loading functionality."""

    def test_location_data_loads(self) -> None:
        """Test that location data loads from JSON file."""
        from api.v1.locations import _load_location_data

        data = _load_location_data()
        assert "countries" in data
        assert "states" in data
        assert "cities" in data

    def test_get_countries_data_returns_list(self) -> None:
        """Test get_countries_data returns a list."""
        from api.v1.locations import get_countries_data

        countries = get_countries_data()
        assert isinstance(countries, list)
        assert len(countries) > 0

    def test_get_states_data_us(self) -> None:
        """Test get_states_data for US."""
        from api.v1.locations import get_states_data

        states = get_states_data("US")
        assert isinstance(states, list)
        assert len(states) > 0

    def test_get_states_data_unknown_country(self) -> None:
        """Test get_states_data for unknown country returns empty list."""
        from api.v1.locations import get_states_data

        states = get_states_data("XX")
        assert states == []

    def test_get_cities_data(self) -> None:
        """Test get_cities_data for California (id=5)."""
        from api.v1.locations import get_cities_data

        cities = get_cities_data(5)
        assert isinstance(cities, list)
        assert len(cities) > 0

    def test_get_cities_data_unknown_state(self) -> None:
        """Test get_cities_data for unknown state returns empty list."""
        from api.v1.locations import get_cities_data

        cities = get_cities_data(99999)
        assert cities == []
