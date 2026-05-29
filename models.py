from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey, JSON, Enum
from sqlalchemy.orm import relationship
import enum

from database import Base


class ProjectStatus(str, enum.Enum):
    active = "active"
    completed = "completed"
    paused = "paused"


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    dimensions = Column(Text, nullable=True)
    client_name = Column(String(255), nullable=True)
    status = Column(String(20), default="active", nullable=False)
    photo_url = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    invoices = relationship("Invoice", back_populates="project", cascade="all, delete-orphan")

    @property
    def total_spent(self):
        return sum(
            inv.total_amount or 0
            for inv in self.invoices
            if inv.confirmed
        )


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    photo_url = Column(Text, nullable=True)
    supplier = Column(String(255), nullable=True)
    invoice_number = Column(String(100), nullable=True)
    invoice_date = Column(String(50), nullable=True)
    total_amount = Column(Float, nullable=True)
    currency = Column(String(10), default="COP", nullable=False)
    items = Column(JSON, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    confirmed = Column(Boolean, default=False, nullable=False)

    project = relationship("Project", back_populates="invoices")
