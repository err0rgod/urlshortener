from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime, UTC


class User(SQLModel, table=True):
    """
    Represents a registered user in the FlexURL platform.
    Integrates with both local database session management and Firebase Auth records.
    """
    __tablename__ = "users"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    full_name: str  # Stores display name / chosen unique username
    oauth_provider: str  # Authentication provider (e.g., 'firebase', 'google')
    oauth_id: str  # Remote UID from the OAuth provider (e.g., Firebase UID)
    created_at: datetime
    tier: str = Field(default="free")  # Account tier: 'free' or 'premium'

class urldata(SQLModel, table=True):
    """
    Stores individual shortened URLs, click counts, status, ownership, 
    and custom expiration times.
    """
    __tablename__ = "urldata"

    short_url: str = Field(primary_key=True, index=True, nullable=False, max_length=20, unique=True)  # SonyFlake base62 or custom alias
    long_url: str = Field(nullable=False)  # Destination URL
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC).replace(tzinfo=None))
    click_count: int = Field(default=0)
    is_banned: bool = Field(default=False)  # Flagged by Google Safe Browsing API check
    user_id: Optional[int] = Field(default=None, foreign_key="users.id")  # Owner identifier
    exp_time: Optional[datetime] = Field(default=None)  # Auto-expiration datetime
    webhook_url: Optional[str] = Field(default=None)  # Premium: destination for redirection payloads
    ios_url: Optional[str] = Field(default=None)  # Premium: targeted redirect destination for iOS users
    android_url: Optional[str] = Field(default=None)  # Premium: targeted redirect destination for Android users
    password_hash: Optional[str] = Field(default=None)  # Premium: secure link access password hash
    fallback_url: Optional[str] = Field(default=None)  # Premium: fallback destination URL after expiration
    activation_time: Optional[datetime] = Field(default=None)  # Premium: scheduled activation time
    custom_countdown_url: Optional[str] = Field(default=None)  # Premium: custom countdown destination URL

class clicklog(SQLModel, table=True):
    """
    Logs visitor redirection events for real-time analytics reports.
    Contains user-agent parser metrics (IP, country, browser, device, referer).
    """
    __tablename__ = "clicklog"

    id: int = Field(primary_key=True, nullable=False, index=True)
    short_url: str = Field(nullable=False, foreign_key="urldata.short_url")  # Reference to shortened link
    clicked_at: datetime = Field(nullable=False, default_factory=lambda: datetime.now(UTC).replace(tzinfo=None))
    ip_address: str = Field(nullable=False, default="NA")
    country: str = Field(nullable=False, default="NA")
    city: str = Field(nullable=False, default="NA")  # Premium: visitor city name
    browser: str = Field(nullable=False, default="NA")
    device: str = Field(nullable=False, default="NA")
    referer: str = Field(nullable=False, default="NA")
    is_bot: bool = Field(default=False)  # Premium: flag to filter crawler traffic


class CustomDomain(SQLModel, table=True):
    """
    Stores custom domains integrated by premium users for branded redirections.
    """
    __tablename__ = "custom_domains"

    id: Optional[int] = Field(default=None, primary_key=True)
    domain_name: str = Field(unique=True, index=True, nullable=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC).replace(tzinfo=None))
    user_id: int = Field(foreign_key="users.id", nullable=False)
    is_verified: bool = Field(default=False)