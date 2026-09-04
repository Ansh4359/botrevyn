from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Float
from sqlalchemy.orm import relationship
from .session import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    github_id = Column(Integer, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    avatar_url = Column(String, nullable=True)
    email = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    installations = relationship("AppInstallation", back_populates="user")


class AppInstallation(Base):
    __tablename__ = "app_installations"

    id = Column(Integer, primary_key=True, index=True)
    installation_id = Column(Integer, unique=True, index=True, nullable=False)
    target_id = Column(Integer, nullable=False)
    target_type = Column(String, nullable=False) # Organization or User
    account_name = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="installations")


class ReviewRecord(Base):
    __tablename__ = "review_records"

    id = Column(Integer, primary_key=True, index=True)
    repo_full_name = Column(String, index=True, nullable=False)
    pr_number = Column(Integer, index=True, nullable=False)
    installation_id = Column(Integer, index=True, nullable=False)
    status = Column(String, nullable=False) # "pending", "success", "error"
    findings_count = Column(Integer, default=0)
    verdict = Column(String, nullable=True) # "APPROVE", "COMMENT", "REQUEST_CHANGES"
    duration_seconds = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    error_message = Column(String, nullable=True)
