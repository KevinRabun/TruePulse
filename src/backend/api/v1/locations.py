"""
Location API endpoints for countries, states/provinces, and cities.

Uses static JSON data for location reference data. This approach is:
- Simpler: No external database dependency for read-only reference data
- Faster: Data loaded in memory, no network calls
- Cheaper: No Azure Table Storage or Cosmos DB costs for static data
- More reliable: No service dependency for simple lookups
"""

import json
from functools import lru_cache
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

router = APIRouter(prefix="/locations", tags=["locations"])


# Location data file path
LOCATIONS_DATA_PATH = Path(__file__).parent.parent.parent / "data" / "locations.json"


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


@lru_cache(maxsize=1)
def _load_location_data() -> dict:
    """
    Load location data from JSON file.

    Uses LRU cache to load data once and keep in memory.
    """
    if LOCATIONS_DATA_PATH.exists():
        with open(LOCATIONS_DATA_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {"countries": [], "states": {}, "cities": {}}


def get_countries_data() -> list[dict]:
    """Get all countries from static data."""
    data = _load_location_data()
    return data.get("countries", [])


def get_states_data(country_code: str) -> list[dict]:
    """Get states/provinces for a country from static data."""
    data = _load_location_data()
    return data.get("states", {}).get(country_code.upper(), [])


def get_cities_data(state_id: int) -> list[dict]:
    """Get cities for a state from static data."""
    data = _load_location_data()
    return data.get("cities", {}).get(str(state_id), [])


@router.get("/countries", response_model=list[CountryResponse])
async def get_countries(
    search: Optional[str] = Query(None, description="Search term for country name"),
) -> list[CountryResponse]:
    """Get all countries, optionally filtered by search term."""
    countries = get_countries_data()

    # Sort by name
    countries = sorted(countries, key=lambda c: c["name"])

    # Filter by search term if provided
    if search:
        search_lower = search.lower()
        countries = [c for c in countries if search_lower in c["name"].lower()]

    return [CountryResponse(code=c["code"], name=c["name"]) for c in countries]


@router.get("/countries/{country_code}/states", response_model=list[StateProvinceResponse])
async def get_states_by_country(
    country_code: str,
    search: Optional[str] = Query(None, description="Search term for state/province name"),
) -> list[StateProvinceResponse]:
    """Get all states/provinces for a given country code."""
    states = get_states_data(country_code)

    if not states:
        return []

    # Sort by name
    states = sorted(states, key=lambda s: s["name"])

    # Filter by search term if provided
    if search:
        search_lower = search.lower()
        states = [s for s in states if search_lower in s["name"].lower()]

    return [
        StateProvinceResponse(
            id=s["id"],
            code=s.get("code"),
            name=s["name"],
            country_code=country_code.upper(),
        )
        for s in states
    ]


@router.get("/states/{state_id}/cities", response_model=list[CityResponse])
async def get_cities_by_state(
    state_id: int,
    search: Optional[str] = Query(None, description="Search term for city name"),
) -> list[CityResponse]:
    """Get all cities for a given state/province ID."""
    cities = get_cities_data(state_id)

    if not cities:
        return []

    # Sort by name
    cities = sorted(cities, key=lambda c: c["name"])

    # Filter by search term if provided
    if search:
        search_lower = search.lower()
        cities = [c for c in cities if search_lower in c["name"].lower()]

    return [CityResponse(id=c["id"], name=c["name"], state_id=state_id) for c in cities]
