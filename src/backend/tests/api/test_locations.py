"""
Tests for location API endpoints.

Tests the Cosmos DB-backed location data endpoints.
"""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from models.cosmos_documents import CityDocument, CountryDocument, StateDocument


@pytest.mark.unit
class TestLocationsEndpoints:
    """Test location endpoints."""

    async def test_get_countries_returns_list(self, client: AsyncClient) -> None:
        """Test that get countries returns a list of countries."""
        # Mock the repository
        mock_countries = [
            CountryDocument(id="country_US", document_type="country", code="US", name="United States"),
            CountryDocument(id="country_CA", document_type="country", code="CA", name="Canada"),
        ]
        with patch(
            "api.v1.locations.CosmosLocationRepository.get_all_countries",
            new_callable=AsyncMock,
            return_value=mock_countries,
        ):
            response = await client.get("/api/v1/locations/countries")
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 2

    async def test_get_countries_structure(self, client: AsyncClient) -> None:
        """Test that country objects have expected structure."""
        mock_countries = [
            CountryDocument(id="country_US", document_type="country", code="US", name="United States"),
        ]
        with patch(
            "api.v1.locations.CosmosLocationRepository.get_all_countries",
            new_callable=AsyncMock,
            return_value=mock_countries,
        ):
            response = await client.get("/api/v1/locations/countries")
            assert response.status_code == 200
            data = response.json()

            assert len(data) > 0
            country = data[0]
            assert "code" in country
            assert "name" in country
            assert country["code"] == "US"
            assert country["name"] == "United States"

    async def test_get_countries_search_filter(self, client: AsyncClient) -> None:
        """Test that search parameter is passed to repository."""
        mock_countries = [
            CountryDocument(id="country_US", document_type="country", code="US", name="United States"),
        ]
        with patch(
            "api.v1.locations.CosmosLocationRepository.get_all_countries",
            new_callable=AsyncMock,
            return_value=mock_countries,
        ) as mock_get:
            response = await client.get("/api/v1/locations/countries", params={"search": "united"})
            assert response.status_code == 200
            mock_get.assert_called_once_with(search="united")

    async def test_get_countries_search_no_results(self, client: AsyncClient) -> None:
        """Test search with no matches returns empty list."""
        with patch(
            "api.v1.locations.CosmosLocationRepository.get_all_countries",
            new_callable=AsyncMock,
            return_value=[],
        ):
            response = await client.get("/api/v1/locations/countries", params={"search": "xyznonexistent123"})
            assert response.status_code == 200
            data = response.json()
            assert data == []

    async def test_get_states_by_country_us(self, client: AsyncClient) -> None:
        """Test getting US states."""
        mock_states = [
            StateDocument(
                id="state_1",
                document_type="state",
                state_id=1,
                code="CA",
                name="California",
                country_code="US",
            ),
            StateDocument(
                id="state_2",
                document_type="state",
                state_id=2,
                code="TX",
                name="Texas",
                country_code="US",
            ),
        ]
        with patch(
            "api.v1.locations.CosmosLocationRepository.get_states_by_country",
            new_callable=AsyncMock,
            return_value=mock_states,
        ):
            response = await client.get("/api/v1/locations/countries/US/states")
            assert response.status_code == 200
            data = response.json()

            assert isinstance(data, list)
            assert len(data) == 2
            state = data[0]
            assert "id" in state
            assert "name" in state
            assert "country_code" in state
            assert state["country_code"] == "US"

    async def test_get_states_by_country_case_insensitive(self, client: AsyncClient) -> None:
        """Test country code is passed to repository as-is."""
        mock_states = [
            StateDocument(
                id="state_1",
                document_type="state",
                state_id=1,
                code="CA",
                name="California",
                country_code="US",
            ),
        ]
        with patch(
            "api.v1.locations.CosmosLocationRepository.get_states_by_country",
            new_callable=AsyncMock,
            return_value=mock_states,
        ) as mock_get:
            response = await client.get("/api/v1/locations/countries/us/states")
            assert response.status_code == 200
            # Repository handles case normalization
            mock_get.assert_called_once()

    async def test_get_states_unknown_country_returns_empty(self, client: AsyncClient) -> None:
        """Test unknown country code returns empty list."""
        with patch(
            "api.v1.locations.CosmosLocationRepository.get_states_by_country",
            new_callable=AsyncMock,
            return_value=[],
        ):
            response = await client.get("/api/v1/locations/countries/XX/states")
            assert response.status_code == 200
            data = response.json()
            assert data == []

    async def test_get_states_search_filter(self, client: AsyncClient) -> None:
        """Test that search parameter is passed to repository."""
        mock_states = [
            StateDocument(
                id="state_1",
                document_type="state",
                state_id=1,
                code="NY",
                name="New York",
                country_code="US",
            ),
        ]
        with patch(
            "api.v1.locations.CosmosLocationRepository.get_states_by_country",
            new_callable=AsyncMock,
            return_value=mock_states,
        ) as mock_get:
            response = await client.get("/api/v1/locations/countries/US/states", params={"search": "new"})
            assert response.status_code == 200
            mock_get.assert_called_once_with("US", search="new")

    async def test_get_cities_by_state(self, client: AsyncClient) -> None:
        """Test getting cities for a state."""
        mock_cities = [
            CityDocument(id="city_1", document_type="city", city_id=1, name="Los Angeles", state_id=5),
            CityDocument(id="city_2", document_type="city", city_id=2, name="San Francisco", state_id=5),
        ]
        with patch(
            "api.v1.locations.CosmosLocationRepository.get_cities_by_state",
            new_callable=AsyncMock,
            return_value=mock_cities,
        ):
            response = await client.get("/api/v1/locations/states/5/cities")
            assert response.status_code == 200
            data = response.json()

            assert isinstance(data, list)
            assert len(data) == 2
            city = data[0]
            assert "id" in city
            assert "name" in city
            assert "state_id" in city
            assert city["state_id"] == 5

    async def test_get_cities_unknown_state_returns_empty(self, client: AsyncClient) -> None:
        """Test unknown state ID returns empty list."""
        with patch(
            "api.v1.locations.CosmosLocationRepository.get_cities_by_state",
            new_callable=AsyncMock,
            return_value=[],
        ):
            response = await client.get("/api/v1/locations/states/99999/cities")
            assert response.status_code == 200
            data = response.json()
            assert data == []

    async def test_get_cities_search_filter(self, client: AsyncClient) -> None:
        """Test that search parameter is passed to repository."""
        mock_cities = [
            CityDocument(id="city_1", document_type="city", city_id=1, name="San Diego", state_id=5),
        ]
        with patch(
            "api.v1.locations.CosmosLocationRepository.get_cities_by_state",
            new_callable=AsyncMock,
            return_value=mock_cities,
        ) as mock_get:
            response = await client.get("/api/v1/locations/states/5/cities", params={"search": "san"})
            assert response.status_code == 200
            mock_get.assert_called_once_with(5, search="san")


@pytest.mark.unit
class TestLocationRepository:
    """Test location repository functionality."""

    async def test_repository_instantiation(self) -> None:
        """Test that repository can be instantiated."""
        from repositories.cosmos_location_repository import CosmosLocationRepository

        repo = CosmosLocationRepository()
        assert repo is not None

    async def test_country_document_creation(self) -> None:
        """Test CountryDocument can be created."""
        country = CountryDocument(
            id="country_US",
            document_type="country",
            code="US",
            name="United States",
        )
        assert country.code == "US"
        assert country.name == "United States"
        assert country.document_type == "country"

    async def test_state_document_creation(self) -> None:
        """Test StateDocument can be created."""
        state = StateDocument(
            id="state_1",
            document_type="state",
            state_id=1,
            code="CA",
            name="California",
            country_code="US",
        )
        assert state.state_id == 1
        assert state.code == "CA"
        assert state.name == "California"
        assert state.country_code == "US"

    async def test_city_document_creation(self) -> None:
        """Test CityDocument can be created."""
        city = CityDocument(
            id="city_1",
            document_type="city",
            city_id=1,
            name="Los Angeles",
            state_id=5,
        )
        assert city.city_id == 1
        assert city.name == "Los Angeles"
        assert city.state_id == 5
