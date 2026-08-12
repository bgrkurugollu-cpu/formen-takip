import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class ForemanMonthlyReport(TimestampMixin, Base):

    __tablename__ = "foreman_monthly_reports"
    __table_args__ = (
        UniqueConstraint("foreman_id", "year", "month", name="uq_foreman_monthly_reports_foreman_year_month"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    foreman_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("foremen.id"), nullable=False, index=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)

    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    overall_score: Mapped[float | None] = mapped_column(Numeric(6, 2))
    overall_level_name: Mapped[str | None] = mapped_column(String(50))
    is_reliable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    report_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
