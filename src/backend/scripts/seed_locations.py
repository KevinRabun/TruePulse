"""
Seed location data (countries, states, cities) from the countries-states-cities-database.
Downloads JSON data from GitHub and imports into the database.
"""

import asyncio

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import scripts._common  # noqa: F401 - Sets up sys.path for imports
from db.session import async_session_maker
from models.location import City, Country, StateProvince

# GitHub raw content URLs
BASE_URL = "https://raw.githubusercontent.com/dr5hn/countries-states-cities-database/master/json"
COUNTRIES_URL = f"{BASE_URL}/countries.json"
STATES_URL = f"{BASE_URL}/states.json"
# Cities file is gzipped due to size - we'll use a different approach
CITIES_URL = f"{BASE_URL}/cities.json.gz"


async def fetch_json(url: str) -> list:
    """Fetch JSON data from URL (supports gzip)."""
    import gzip
    import json

    async with httpx.AsyncClient(timeout=180.0) as client:
        print(f"  Fetching {url}...")
        response = await client.get(url)
        response.raise_for_status()

        # Check if gzipped
        if url.endswith(".gz"):
            decompressed = gzip.decompress(response.content)
            return json.loads(decompressed.decode("utf-8"))
        return response.json()


async def seed_countries(db: AsyncSession) -> dict[str, int]:
    """Seed countries and return mapping of ISO2 code to database ID."""
    print("\n📍 Step 1: Seeding countries...")

    # Check if already seeded
    result = await db.execute(select(Country).limit(1))
    if result.scalar_one_or_none():
        print("  Countries already seeded, fetching existing mapping...")
        result = await db.execute(select(Country))
        countries = result.scalars().all()
        return {c.code: c.id for c in countries}

    countries_data = await fetch_json(COUNTRIES_URL)
    print(f"  Found {len(countries_data)} countries")

    country_map = {}
    for c in countries_data:
        country = Country(code=c["iso2"], name=c["name"], is_active=True)
        db.add(country)
        await db.flush()
        country_map[c["iso2"]] = country.id

    await db.commit()
    print(f"  ✓ Seeded {len(country_map)} countries")
    return country_map


async def seed_states(db: AsyncSession, country_map: dict[str, int]) -> dict[tuple[str, str], int]:
    """Seed states/provinces and return mapping of (country_code, state_name) to database ID."""
    print("\n📍 Step 2: Seeding states/provinces...")

    # Check if already seeded
    result = await db.execute(select(StateProvince).limit(1))
    if result.scalar_one_or_none():
        print("  States already seeded, fetching existing mapping...")
        result = await db.execute(select(StateProvince).join(Country))
        states = result.scalars().all()
        state_map = {}
        for s in states:
            country_result = await db.execute(select(Country).where(Country.id == s.country_id))
            country = country_result.scalar_one()
            state_map[(country.code, s.name)] = s.id
        return state_map

    states_data = await fetch_json(STATES_URL)
    print(f"  Found {len(states_data)} states/provinces")

    state_map = {}
    batch_size = 500
    count = 0

    for i, s in enumerate(states_data):
        country_code = s.get("country_code")
        if country_code not in country_map:
            continue

        state = StateProvince(
            country_id=country_map[country_code],
            code=s.get("iso2") or s.get("state_code"),
            name=s["name"],
            is_active=True,
        )
        db.add(state)
        count += 1

        # Batch commit
        if (i + 1) % batch_size == 0:
            await db.flush()
            print(f"  Progress: {i + 1}/{len(states_data)} states processed...")

    await db.commit()

    # Build state map
    result = await db.execute(select(StateProvince))
    states = result.scalars().all()
    for s in states:
        country_result = await db.execute(select(Country).where(Country.id == s.country_id))
        country = country_result.scalar_one()
        state_map[(country.code, s.name)] = s.id

    print(f"  ✓ Seeded {count} states/provinces")
    return state_map


async def seed_cities(
    db: AsyncSession,
    state_map: dict[tuple[str, str], int],
    limit_per_state: int | None = None,
):
    """Seed cities, optionally limiting to N per state for manageability."""
    if limit_per_state:
        print(f"\n📍 Step 3: Seeding cities (top {limit_per_state} per state)...")
    else:
        print("\n📍 Step 3: Seeding all cities...")

    # Check if already seeded
    result = await db.execute(select(City).limit(1))
    if result.scalar_one_or_none():
        print("  Cities already seeded, skipping...")
        return

    cities_data = await fetch_json(CITIES_URL)
    print(f"  Found {len(cities_data)} cities total")

    # Group cities by state
    cities_by_state: dict[tuple, list] = {}
    for c in cities_data:
        key = (c.get("country_code"), c.get("state_name"))
        if key not in cities_by_state:
            cities_by_state[key] = []
        cities_by_state[key].append(c)

    print(f"  Grouped into {len(cities_by_state)} states")

    count = 0
    batch_size = 1000
    processed_states = 0

    for (country_code, state_name), cities in cities_by_state.items():
        state_key = (country_code, state_name)
        if state_key not in state_map:
            continue

        state_id = state_map[state_key]

        # Take cities (limited if specified)
        city_list = cities[:limit_per_state] if limit_per_state else cities
        for c in city_list:
            city = City(state_province_id=state_id, name=c["name"], is_active=True)
            db.add(city)
            count += 1

            # Batch commit
            if count % batch_size == 0:
                await db.flush()
                print(f"  Progress: {count} cities added...")

        processed_states += 1
        if processed_states % 100 == 0:
            await db.flush()
            print(f"  Progress: {processed_states}/{len(cities_by_state)} states processed, {count} cities added...")

    await db.commit()
    print(f"  ✓ Seeded {count} cities")


async def seed_locations():
    """Main function to seed all location data."""
    print("=" * 60)
    print("🌍 LOCATION DATA SEEDING")
    print("=" * 60)
    print("\nSource: github.com/dr5hn/countries-states-cities-database")

    async with async_session_maker() as db:
        try:
            # Step 1: Countries
            country_map = await seed_countries(db)

            # Step 2: States
            state_map = await seed_states(db, country_map)

            # Step 3: Cities (no limit - import all)
            await seed_cities(db, state_map, limit_per_state=None)

            print("\n" + "=" * 60)
            print("✅ Location seeding complete!")
            print("=" * 60)

        except Exception as e:
            print(f"\n❌ Error seeding locations: {e}")
            await db.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(seed_locations())
