import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import DataQualityStatus, SourceSystem


class PerformanceRecord(TimestampMixin, Base):

    __tablename__ = "performance_records"
    __table_args__ = (
        UniqueConstraint("source_system", "source_record_id", name="uq_perf_record_source"),
        UniqueConstraint(
            "foreman_id", "kpi_id", "chief_id", "shift_id", "performance_date",
            name="uq_perf_record_natural_key",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    source_system: Mapped[SourceSystem] = mapped_column(Enum(SourceSystem, name="source_system"), nullable=False)
    source_record_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    integration_run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("integration_runs.id"), nullable=False, index=True)

    performance_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    plant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("plants.id"), nullable=False, index=True)
    chief_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chiefs.id"), nullable=False, index=True)
    shift_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("shifts.id"), nullable=False, index=True)
    foreman_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("foremen.id"), nullable=False, index=True)
    kpi_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("kpis.id"), nullable=False, index=True)

    target_value: Mapped[float | None] = mapped_column(Numeric(14, 4))
    actual_value: Mapped[float | None] = mapped_column(Numeric(14, 4))
    numerator_value: Mapped[float | None] = mapped_column(Numeric(14, 4))
    denominator_value: Mapped[float | None] = mapped_column(Numeric(14, 4))
    unit: Mapped[str] = mapped_column(String(30), nullable=False)

    data_quality_status: Mapped[DataQualityStatus] = mapped_column(
        Enum(DataQualityStatus, name="data_quality_status"), nullable=False, default=DataQualityStatus.COMPLETE
    )

    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    scores: Mapped[list["PerformanceScore"]] = relationship(back_populates="performance_record")


class PerformanceScore(TimestampMixin, Base):

    __tablename__ = "performance_scores"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    performance_record_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("performance_records.id"), nullable=False, unique=True, index=True
    )
    calculation_rule_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("kpi_calculation_rules.id"), nullable=False)

    raw_score: Mapped[float] = mapped_column(Numeric(8, 3), nullable=False)
    capped_score: Mapped[float] = mapped_column(Numeric(8, 3), nullable=False)
    kpi_weight: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    weighted_contribution: Mapped[float] = mapped_column(Numeric(8, 3), nullable=False)
    calculation_version: Mapped[int] = mapped_column(Integer, nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    performance_record: Mapped[PerformanceRecord] = relationship(back_populates="scores")
