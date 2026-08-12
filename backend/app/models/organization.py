import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Time, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Factory(TimestampMixin, Base):

    __tablename__ = "factories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    location: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    plants: Mapped[list["Plant"]] = relationship(back_populates="factory")


class Plant(TimestampMixin, Base):

    __tablename__ = "plants"
    __table_args__ = (
        UniqueConstraint("sequence_number", name="uq_plants_sequence_number"),
        UniqueConstraint("id", "chief_id", name="uq_plants_id_chief_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    factory_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("factories.id"), nullable=False, index=True)
    chief_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chiefs.id"), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String(1000))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sap_plant_code: Mapped[str | None] = mapped_column(String(20))

    factory: Mapped[Factory] = relationship(back_populates="plants")
    chief: Mapped["Chief"] = relationship(back_populates="plants")


class Shift(TimestampMixin, Base):
    __tablename__ = "shifts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    start_time: Mapped[Time] = mapped_column(Time, nullable=False)
    end_time: Mapped[Time] = mapped_column(Time, nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    crosses_midnight: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
