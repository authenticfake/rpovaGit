"""
CoffeeBuddy Database Models
SQLAlchemy ORM models for PostgreSQL schema
"""
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all ORM models"""
    pass


class User(Base):
    """User entity representing Slack users"""
    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp(), onupdate=func.current_timestamp()
    )

    # Relationships
    initiated_runs: Mapped[list["CoffeeRun"]] = relationship(
        "CoffeeRun", foreign_keys="CoffeeRun.initiator_user_id", back_populates="initiator"
    )
    assigned_runs: Mapped[list["CoffeeRun"]] = relationship(
        "CoffeeRun", foreign_keys="CoffeeRun.runner_user_id", back_populates="runner"
    )
    orders: Mapped[list["Order"]] = relationship("Order", back_populates="user")
    preferences: Mapped[list["UserPreference"]] = relationship("UserPreference", back_populates="user")
    audit_logs: Mapped[list["AuditLog"]] = relationship("AuditLog", back_populates="user")

    __table_args__ = (
        Index("idx_users_email", "email"),
        Index("idx_users_updated_at", "updated_at"),
    )


class CoffeeRun(Base):
    """CoffeeRun entity representing a coffee coordination session"""
    __tablename__ = "coffee_runs"

    run_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[str] = mapped_column(String(64), nullable=False)
    channel_id: Mapped[str] = mapped_column(String(64), nullable=False)
    initiator_user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    runner_user_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.current_timestamp())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    reminder_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    initiator: Mapped["User"] = relationship("User", foreign_keys=[initiator_user_id], back_populates="initiated_runs")
    runner: Mapped[Optional["User"]] = relationship("User", foreign_keys=[runner_user_id], back_populates="assigned_runs")
    orders: Mapped[list["Order"]] = relationship("Order", back_populates="run")
    audit_logs: Mapped[list["AuditLog"]] = relationship("AuditLog", back_populates="run")

    __table_args__ = (
        CheckConstraint("status IN ('active', 'completed', 'cancelled')", name="check_status"),
        Index("idx_coffee_runs_workspace_id", "workspace_id"),
        Index("idx_coffee_runs_channel_id", "channel_id"),
        Index("idx_coffee_runs_status", "status"),
        Index("idx_coffee_runs_created_at", "created_at"),
        Index("idx_coffee_runs_initiator_user_id", "initiator_user_id"),
        Index("idx_coffee_runs_runner_user_id", "runner_user_id"),
    )


class Order(Base):
    """Order entity representing a single coffee order"""
    __tablename__ = "orders"

    order_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("coffee_runs.run_id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    drink_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size: Mapped[str] = mapped_column(String(20), nullable=False)
    customizations: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.current_timestamp())

    # Relationships
    run: Mapped["CoffeeRun"] = relationship("CoffeeRun", back_populates="orders")
    user: Mapped["User"] = relationship("User", back_populates="orders")

    __table_args__ = (
        Index("idx_orders_run_id", "run_id"),
        Index("idx_orders_user_id", "user_id"),
        Index("idx_orders_created_at", "created_at"),
    )


class UserPreference(Base):
    """UserPreference entity storing user's order history"""
    __tablename__ = "user_preferences"

    preference_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    drink_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size: Mapped[str] = mapped_column(String(20), nullable=False)
    customizations: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    order_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    last_ordered_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.current_timestamp())

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="preferences")

    __table_args__ = (
        Index("idx_user_preferences_user_id", "user_id"),
        Index("idx_user_preferences_last_ordered_at", "last_ordered_at"),
    )


class AuditLog(Base):
    """AuditLog entity for event tracking and compliance"""
    __tablename__ = "audit_logs"

    log_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    user_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    run_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("coffee_runs.run_id", ondelete="SET NULL"), nullable=True)
    payload: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.current_timestamp())

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", back_populates="audit_logs")
    run: Mapped[Optional["CoffeeRun"]] = relationship("CoffeeRun", back_populates="audit_logs")

    __table_args__ = (
        Index("idx_audit_logs_event_type", "event_type"),
        Index("idx_audit_logs_timestamp", "timestamp"),
        Index("idx_audit_logs_user_id", "user_id"),
        Index("idx_audit_logs_run_id", "run_id"),
    )
```

```python