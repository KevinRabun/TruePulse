"""
Location API endpoints for countries, states/provinces, and cities.

Uses Cosmos DB for location reference data. This approach:
- Reduces memory footprint: Only query what's needed, not load entire dataset
- Scales horizontally: Works with multiple container instances
- Enables efficient queries: Cosmos indexing for fast lookups
- Maintains consistency: Same pattern as other entities (achievements, etc.)
- Auto-updates: Data seeded on container startup from JSON source
"""

from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

from repositories.cosmos_location_repository import CosmosLocationRepository

router = APIRouter(prefix="/locations", tags=["locations"])


class CountryResponse(BaseModel):
    """Response model for country data."""

    code: str
    name: str


class StateProvinceResponse(BaseModel):
    """Response model for state/province data."""

    id: int
    code: Optional[str]
    name: str
    country_code: str


class CityResponse(BaseModel):
    """Response model for city data."""

    id: int
    name: str
    state_id: int


def _get_location_repo() -> CosmosLocationRepository:
    """Get location repository instance."""
    return CosmosLocationRepository()


@router.get("/countries", response_model=list[CountryResponse])
async def get_countries(
    search: Optional[str] = Query(None, description="Search term for country name"),
) -> list[CountryResponse]:
    """Get all countries, optionally filtered by search term."""
    repo = _get_location_repo()
    countries = await repo.get_all_countries(search=search)

    return [CountryResponse(code=c.code, name=c.name) for c in countries]


@router.get("/countries/{country_code}/states", response_model=list[StateProvinceResponse])
async def get_states_by_country(
    country_code: str,
    search: Optional[str] = Query(None, description="Search term for state/province name"),
) -> list[StateProvinceResponse]:
    """Get all states/provinces for a given country code."""
    repo = _get_location_repo()
    states = await repo.get_states_by_country(country_code, search=search)

    return [
        StateProvinceResponse(
            id=s.state_id,
            code=s.code,
            name=s.name,
            country_code=s.country_code,
        )
        for s in states
    ]


@router.get("/states/{state_id}/cities", response_model=list[CityResponse])
async def get_cities_by_state(
    state_id: int,
    search: Optional[str] = Query(None, description="Search term for city name"),
) -> list[CityResponse]:
    """Get all cities for a given state/province ID."""
    repo = _get_location_repo()
    cities = await repo.get_cities_by_state(state_id, search=search)

    return [CityResponse(id=c.city_id, name=c.name, state_id=c.state_id) for c in cities]
