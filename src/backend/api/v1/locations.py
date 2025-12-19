"""Location API endpoints for countries, states/provinces, and cities."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from pydantic import BaseModel

from db.session import get_db
from models.location import Country, StateProvince, City


router = APIRouter(prefix="/locations", tags=["locations"])


class CountryResponse(BaseModel):
    """Response model for country data."""
    code: str
    name: str
    
    class Config:
        from_attributes = True


class StateProvinceResponse(BaseModel):
    """Response model for state/province data."""
    id: int
    code: Optional[str]
    name: str
    country_code: str
    
    class Config:
        from_attributes = True


class CityResponse(BaseModel):
    """Response model for city data."""
    id: int
    name: str
    state_id: int
    
    class Config:
        from_attributes = True


@router.get("/countries", response_model=List[CountryResponse])
async def get_countries(
    db: AsyncSession = Depends(get_db),
    search: Optional[str] = Query(None, description="Search term for country name")
):
    """Get all active countries, optionally filtered by search term."""
    query = select(Country).where(Country.is_active == True).order_by(Country.name)
    
    if search:
        query = query.where(Country.name.ilike(f"%{search}%"))
    
    result = await db.execute(query)
    countries = result.scalars().all()
    
    return [CountryResponse(code=c.code, name=c.name) for c in countries]


@router.get("/countries/{country_code}/states", response_model=List[StateProvinceResponse])
async def get_states_by_country(
    country_code: str,
    db: AsyncSession = Depends(get_db),
    search: Optional[str] = Query(None, description="Search term for state/province name")
):
    """Get all active states/provinces for a given country code."""
    # First get the country
    country_result = await db.execute(
        select(Country).where(Country.code == country_code.upper())
    )
    country = country_result.scalar_one_or_none()
    
    if not country:
        return []
    
    # Get states for this country
    query = (
        select(StateProvince)
        .where(StateProvince.country_id == country.id)
        .where(StateProvince.is_active == True)
        .order_by(StateProvince.name)
    )
    
    if search:
        query = query.where(StateProvince.name.ilike(f"%{search}%"))
    
    result = await db.execute(query)
    states = result.scalars().all()
    
    return [
        StateProvinceResponse(
            id=s.id,
            code=s.code,
            name=s.name,
            country_code=country_code.upper()
        )
        for s in states
    ]


@router.get("/states/{state_id}/cities", response_model=List[CityResponse])
async def get_cities_by_state(
    state_id: int,
    db: AsyncSession = Depends(get_db),
    search: Optional[str] = Query(None, description="Search term for city name")
):
    """Get all active cities for a given state/province ID."""
    # Verify state exists
    state_result = await db.execute(
        select(StateProvince).where(StateProvince.id == state_id)
    )
    state = state_result.scalar_one_or_none()
    
    if not state:
        return []
    
    # Get cities for this state
    query = (
        select(City)
        .where(City.state_province_id == state_id)
        .where(City.is_active == True)
        .order_by(City.name)
    )
    
    if search:
        query = query.where(City.name.ilike(f"%{search}%"))
    
    result = await db.execute(query)
    cities = result.scalars().all()
    
    return [
        CityResponse(
            id=c.id,
            name=c.name,
            state_id=state_id
        )
        for c in cities
    ]
