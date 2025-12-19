"""Location models for countries, states/provinces, and cities."""

from typing import List, Optional

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


class Country(Base):
    """Country model for storing country information."""

    __tablename__ = "countries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    code: Mapped[str] = mapped_column(
        String(2), unique=True, index=True
    )  # ISO 3166-1 alpha-2
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationship to states
    states: Mapped[List["StateProvince"]] = relationship(
        "StateProvince", back_populates="country", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Country {self.code}: {self.name}>"


class StateProvince(Base):
    """State/Province model for storing regional divisions."""

    __tablename__ = "states_provinces"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    country_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("countries.id"), nullable=False
    )
    code: Mapped[Optional[str]] = mapped_column(
        String(10), nullable=True
    )  # State/province code
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationship to country
    country: Mapped["Country"] = relationship("Country", back_populates="states")

    # Relationship to cities
    cities: Mapped[List["City"]] = relationship(
        "City", back_populates="state_province", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<StateProvince {self.name}>"


class City(Base):
    """City model for storing city/town information."""

    __tablename__ = "cities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    state_province_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("states_provinces.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationship to state/province
    state_province: Mapped["StateProvince"] = relationship(
        "StateProvince", back_populates="cities"
    )

    def __repr__(self) -> str:
        return f"<City {self.name}>"
