"""
Cosmos DB Location repository.

Handles location reference data (countries, states, cities).
Provides efficient queries for location lookups.
"""

import logging
from typing import Optional

from db.cosmos_session import (
    LOCATIONS_CONTAINER,
    query_items,
    upsert_item,
)
from models.cosmos_documents import (
    CityDocument,
    CountryDocument,
    StateDocument,
)

logger = logging.getLogger(__name__)


class CosmosLocationRepository:
    """
    Repository for location operations using Cosmos DB.

    Manages:
    - Country reference data
    - State/province reference data
    - City reference data

    All location data is stored in a single 'locations' container
    with document_type as the partition key for efficient queries.
    """

    # ========================================================================
    # Country Operations
    # ========================================================================

    async def get_all_countries(self, search: Optional[str] = None) -> list[CountryDocument]:
        """
        Get all countries, optionally filtered by search term.

        Args:
            search: Optional search term to filter by country name

        Returns:
            List of country documents sorted by name
        """
        if search:
            query = """
                SELECT * FROM c
                WHERE c.document_type = 'country'
                AND CONTAINS(LOWER(c.name), LOWER(@search))
                ORDER BY c.name
            """
            results = await query_items(
                LOCATIONS_CONTAINER,
                query,
                parameters=[{"name": "@search", "value": search}],
                partition_key="country",
            )
        else:
            query = """
                SELECT * FROM c
                WHERE c.document_type = 'country'
                ORDER BY c.name
            """
            results = await query_items(
                LOCATIONS_CONTAINER,
                query,
                partition_key="country",
            )
        return [CountryDocument(**r) for r in results]

    async def get_country_by_code(self, country_code: str) -> Optional[CountryDocument]:
        """
        Get a country by its ISO code.

        Args:
            country_code: ISO 3166-1 alpha-2 country code

        Returns:
            Country document or None if not found
        """
        query = """
            SELECT * FROM c
            WHERE c.document_type = 'country'
            AND c.code = @code
        """
        results = await query_items(
            LOCATIONS_CONTAINER,
            query,
            parameters=[{"name": "@code", "value": country_code.upper()}],
            partition_key="country",
            max_items=1,
        )
        if results:
            return CountryDocument(**results[0])
        return None

    async def upsert_country(self, country: CountryDocument) -> CountryDocument:
        """Upsert a country document."""
        result = await upsert_item(LOCATIONS_CONTAINER, country.model_dump(mode="json"))
        return CountryDocument(**result)

    # ========================================================================
    # State Operations
    # ========================================================================

    async def get_states_by_country(self, country_code: str, search: Optional[str] = None) -> list[StateDocument]:
        """
        Get all states/provinces for a country.

        Args:
            country_code: ISO country code
            search: Optional search term to filter by state name

        Returns:
            List of state documents sorted by name
        """
        if search:
            query = """
                SELECT * FROM c
                WHERE c.document_type = 'state'
                AND c.country_code = @country_code
                AND CONTAINS(LOWER(c.name), LOWER(@search))
                ORDER BY c.name
            """
            results = await query_items(
                LOCATIONS_CONTAINER,
                query,
                parameters=[
                    {"name": "@country_code", "value": country_code.upper()},
                    {"name": "@search", "value": search},
                ],
                partition_key="state",
            )
        else:
            query = """
                SELECT * FROM c
                WHERE c.document_type = 'state'
                AND c.country_code = @country_code
                ORDER BY c.name
            """
            results = await query_items(
                LOCATIONS_CONTAINER,
                query,
                parameters=[{"name": "@country_code", "value": country_code.upper()}],
                partition_key="state",
            )
        return [StateDocument(**r) for r in results]

    async def get_state_by_id(self, state_id: int) -> Optional[StateDocument]:
        """
        Get a state by its numeric ID.

        Args:
            state_id: Unique state identifier

        Returns:
            State document or None if not found
        """
        query = """
            SELECT * FROM c
            WHERE c.document_type = 'state'
            AND c.state_id = @state_id
        """
        results = await query_items(
            LOCATIONS_CONTAINER,
            query,
            parameters=[{"name": "@state_id", "value": state_id}],
            partition_key="state",
            max_items=1,
        )
        if results:
            return StateDocument(**results[0])
        return None

    async def upsert_state(self, state: StateDocument) -> StateDocument:
        """Upsert a state document."""
        result = await upsert_item(LOCATIONS_CONTAINER, state.model_dump(mode="json"))
        return StateDocument(**result)

    # ========================================================================
    # City Operations
    # ========================================================================

    async def get_cities_by_state(self, state_id: int, search: Optional[str] = None) -> list[CityDocument]:
        """
        Get all cities for a state.

        Args:
            state_id: State identifier
            search: Optional search term to filter by city name

        Returns:
            List of city documents sorted by name
        """
        if search:
            query = """
                SELECT * FROM c
                WHERE c.document_type = 'city'
                AND c.state_id = @state_id
                AND CONTAINS(LOWER(c.name), LOWER(@search))
                ORDER BY c.name
            """
            results = await query_items(
                LOCATIONS_CONTAINER,
                query,
                parameters=[
                    {"name": "@state_id", "value": state_id},
                    {"name": "@search", "value": search},
                ],
                partition_key="city",
            )
        else:
            query = """
                SELECT * FROM c
                WHERE c.document_type = 'city'
                AND c.state_id = @state_id
                ORDER BY c.name
            """
            results = await query_items(
                LOCATIONS_CONTAINER,
                query,
                parameters=[{"name": "@state_id", "value": state_id}],
                partition_key="city",
            )
        return [CityDocument(**r) for r in results]

    async def get_city_by_id(self, city_id: int) -> Optional[CityDocument]:
        """
        Get a city by its numeric ID.

        Args:
            city_id: Unique city identifier

        Returns:
            City document or None if not found
        """
        query = """
            SELECT * FROM c
            WHERE c.document_type = 'city'
            AND c.city_id = @city_id
        """
        results = await query_items(
            LOCATIONS_CONTAINER,
            query,
            parameters=[{"name": "@city_id", "value": city_id}],
            partition_key="city",
            max_items=1,
        )
        if results:
            return CityDocument(**results[0])
        return None

    async def upsert_city(self, city: CityDocument) -> CityDocument:
        """Upsert a city document."""
        result = await upsert_item(LOCATIONS_CONTAINER, city.model_dump(mode="json"))
        return CityDocument(**result)

    # ========================================================================
    # Bulk Operations (for seeding)
    # ========================================================================

    async def upsert_countries_bulk(self, countries: list[dict]) -> tuple[int, int]:
        """
        Bulk upsert countries from source data.

        Args:
            countries: List of country dictionaries with 'code' and 'name'

        Returns:
            Tuple of (inserted_count, updated_count)
        """
        inserted = 0
        updated = 0

        for country_data in countries:
            country = CountryDocument(
                id=f"country_{country_data['code']}",
                document_type="country",
                code=country_data["code"],
                name=country_data["name"],
            )
            # Check if exists to track inserted vs updated
            existing = await self.get_country_by_code(country_data["code"])
            await self.upsert_country(country)
            if existing:
                updated += 1
            else:
                inserted += 1

        return inserted, updated

    async def upsert_states_bulk(self, states_by_country: dict[str, list[dict]]) -> tuple[int, int]:
        """
        Bulk upsert states from source data.

        Args:
            states_by_country: Dict of country_code -> list of state dictionaries

        Returns:
            Tuple of (inserted_count, updated_count)
        """
        inserted = 0
        updated = 0

        for country_code, states in states_by_country.items():
            for state_data in states:
                state = StateDocument(
                    id=f"state_{state_data['id']}",
                    document_type="state",
                    state_id=state_data["id"],
                    code=state_data.get("code"),
                    name=state_data["name"],
                    country_code=country_code.upper(),
                )
                # Check if exists to track inserted vs updated
                existing = await self.get_state_by_id(state_data["id"])
                await self.upsert_state(state)
                if existing:
                    updated += 1
                else:
                    inserted += 1

        return inserted, updated

    async def upsert_cities_bulk(self, cities_by_state: dict[str, list[dict]]) -> tuple[int, int]:
        """
        Bulk upsert cities from source data.

        Args:
            cities_by_state: Dict of state_id -> list of city dictionaries

        Returns:
            Tuple of (inserted_count, updated_count)
        """
        inserted = 0
        updated = 0

        for state_id_str, cities in cities_by_state.items():
            state_id = int(state_id_str)
            for city_data in cities:
                city = CityDocument(
                    id=f"city_{city_data['id']}",
                    document_type="city",
                    city_id=city_data["id"],
                    name=city_data["name"],
                    state_id=state_id,
                )
                # Check if exists to track inserted vs updated
                existing = await self.get_city_by_id(city_data["id"])
                await self.upsert_city(city)
                if existing:
                    updated += 1
                else:
                    inserted += 1

        return inserted, updated
