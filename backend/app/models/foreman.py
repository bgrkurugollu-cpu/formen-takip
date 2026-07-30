import uuid
from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, ForeignKeyConstraint, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Chief(TimestampMixin, Base):

    __tablename__ = "chiefs"
    __table_args__ = (UniqueConstraint("id", "plant_id", name="uq_chiefs_id_plant_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    plant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("plants.id"), nullable=False, index=True)
    hire_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sap_personnel_number: Mapped[str | None] = mapped_column(String(30))

    assignments: Mapped[list["ForemanAssignment"]] = relationship(back_populates="chief")


class Foreman(TimestampMixin, Base):

    __tablename__ = "foremen"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    hire_date: Mapped[date] = mapped_column(Date, nullable=False)
    termination_date: Mapped[date | None] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sap_personnel_number: Mapped[str | None] = mapped_column(String(30))
    photo_url: Mapped[str | None] = mapped_column(String(500))

    assignments: Mapped[list["ForemanAssignment"]] = relationship(back_populates="foreman")


class ForemanAssignment(TimestampMixin, Base):

    __tablename__ = "foreman_assignments"
    __table_args__ = (
        ForeignKeyConstraint(["chief_id", "plant_id"], ["chiefs.id", "chiefs.plant_id"], name="fk_foreman_assignments_chief_plant"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    foreman_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("foremen.id"), nullable=False, index=True)
    plant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("plants.id"), nullable=False, index=True)
    chief_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    shift_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("shifts.id"), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    end_date: Mapped[date | None] = mapped_column(Date, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    foreman: Mapped[Foreman] = relationship(back_populates="assignments")
    chief: Mapped[Chief] = relationship(back_populates="assignments")
