"""SQLAlchemy ORM models for Sudan Intel."""

from sqlalchemy import (
    Boolean, Column, DateTime, Float, Integer, String, Text,
    UniqueConstraint, func,
)

from backend.core.database import Base


class ConflictEvent(Base):
    __tablename__ = "conflict_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(50), default="hdx_hapi")
    admin1_code = Column(String(10), index=True)
    admin1_name = Column(String(100))
    admin2_code = Column(String(10), index=True)
    admin2_name = Column(String(100))
    event_type = Column(String(100))
    events = Column(Integer, default=0)
    fatalities = Column(Integer, default=0)
    reference_period_start = Column(DateTime, index=True)
    reference_period_end = Column(DateTime)
    ingested_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint(
            "source", "admin2_code", "event_type", "reference_period_start",
            name="uq_conflict",
        ),
    )


class Displacement(Base):
    __tablename__ = "displacement"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(50))
    admin1_code = Column(String(10), index=True)
    admin1_name = Column(String(100))
    admin2_code = Column(String(10), index=True)
    admin2_name = Column(String(100))
    displacement_type = Column(String(50))
    population = Column(Integer)
    reference_period_start = Column(DateTime, index=True)
    reference_period_end = Column(DateTime)
    ingested_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint(
            "source", "admin1_code", "admin2_code",
            "displacement_type", "reference_period_start",
            name="uq_displacement",
        ),
    )


class FoodSecurity(Base):
    __tablename__ = "food_security"

    id = Column(Integer, primary_key=True, autoincrement=True)
    admin1_code = Column(String(10), index=True)
    admin1_name = Column(String(100))
    admin2_code = Column(String(10), index=True)
    admin2_name = Column(String(100))
    ipc_phase = Column(String(5))
    ipc_type = Column(String(30))
    population_in_phase = Column(Integer)
    population_fraction_in_phase = Column(Float)
    reference_period_start = Column(DateTime, index=True)
    reference_period_end = Column(DateTime)
    ingested_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint(
            "admin2_code", "ipc_phase", "ipc_type", "reference_period_start",
            name="uq_food_security",
        ),
    )


class FoodPrice(Base):
    __tablename__ = "food_prices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    admin1_code = Column(String(10), index=True)
    admin1_name = Column(String(100))
    admin2_code = Column(String(10))
    admin2_name = Column(String(100))
    market_code = Column(String(20))
    market_name = Column(String(100))
    commodity_code = Column(String(20))
    commodity_name = Column(String(100))
    commodity_category = Column(String(100))
    currency_code = Column(String(10))
    unit = Column(String(50))
    price = Column(Float)
    price_type = Column(String(20))
    lat = Column(Float)
    lon = Column(Float)
    reference_period_start = Column(DateTime, index=True)
    reference_period_end = Column(DateTime)
    ingested_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint(
            "market_code", "commodity_code", "reference_period_start",
            name="uq_food_price",
        ),
    )


class HumanitarianNeed(Base):
    __tablename__ = "humanitarian_needs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    admin1_code = Column(String(10), index=True)
    admin1_name = Column(String(100))
    admin2_code = Column(String(10), index=True)
    admin2_name = Column(String(100))
    sector_code = Column(String(20))
    sector_name = Column(String(100))
    population_status = Column(String(10))
    population = Column(Integer)
    reference_period_start = Column(DateTime, index=True)
    reference_period_end = Column(DateTime)
    ingested_at = Column(DateTime, server_default=func.now())


class OperationalPresence(Base):
    __tablename__ = "operational_presence"

    id = Column(Integer, primary_key=True, autoincrement=True)
    admin1_code = Column(String(10), index=True)
    admin1_name = Column(String(100))
    admin2_code = Column(String(10), index=True)
    admin2_name = Column(String(100))
    org_acronym = Column(String(50))
    org_name = Column(String(200))
    org_type_code = Column(String(10))
    org_type_description = Column(String(100))
    sector_code = Column(String(20))
    sector_name = Column(String(100))
    reference_period_start = Column(DateTime, index=True)
    reference_period_end = Column(DateTime)
    ingested_at = Column(DateTime, server_default=func.now())


class NewsArticle(Base):
    __tablename__ = "news_articles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(50))
    title = Column(String(500))
    url = Column(String(1000), unique=True)
    source_domain = Column(String(200))
    source_country = Column(String(100))
    language = Column(String(50))
    published_at = Column(DateTime, index=True)
    ingested_at = Column(DateTime, server_default=func.now())


class SynthesisBrief(Base):
    __tablename__ = "synthesis_briefs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    scope = Column(String(20))
    region_code = Column(String(10), nullable=True)
    brief_type = Column(String(50))
    content = Column(Text)
    model_used = Column(String(50))
    data_window_start = Column(DateTime)
    data_window_end = Column(DateTime)
    generated_at = Column(DateTime, server_default=func.now())


class DataSourceStatus(Base):
    __tablename__ = "data_source_status"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_name = Column(String(50), unique=True)
    last_success = Column(DateTime, nullable=True)
    last_failure = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    records_last_fetch = Column(Integer, default=0)
    total_records = Column(Integer, default=0)
    is_healthy = Column(Boolean, default=True)
