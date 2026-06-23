"""
SQLAlchemy models — mirrors ERD.md exactly.
Single-user scope for hackathon; schema shaped for multi-user extension (user_profile_id FKs present).
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Integer, String, Text, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db import Base


class UserProfile(Base):
    __tablename__ = "user_profile"

    id:                    Mapped[int]           = mapped_column(Integer, primary_key=True)
    cv_raw_text:           Mapped[Optional[str]] = mapped_column(Text)
    current_seniority_tier:Mapped[Optional[str]] = mapped_column(String(50))
    # nullable — only populated once Gmail is connected (ARCHITECTURE §2.9)
    notification_email:    Mapped[Optional[str]] = mapped_column(String(255))
    cv_updated_at:         Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at:            Mapped[datetime]      = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    saved_jobs:             Mapped[list["SavedJob"]]            = relationship(back_populates="user")
    work_log_entries:       Mapped[list["WorkLogEntry"]]        = relationship(back_populates="user")
    notifications:          Mapped[list["Notification"]]        = relationship(back_populates="user")
    notification_rule_states: Mapped[list["NotificationRuleState"]] = relationship(back_populates="user")
    email_connection:       Mapped[Optional["EmailConnection"]] = relationship(back_populates="user", uselist=False)


class EmailConnection(Base):
    """
    Holds the per-user Gmail OAuth grant.
    Kept in its own table (not a column on UserProfile) because this is the
    most security-sensitive data in the schema — see ERD.md notes.
    """
    __tablename__ = "email_connection"

    id:                      Mapped[int]           = mapped_column(Integer, primary_key=True)
    user_profile_id:         Mapped[int]           = mapped_column(ForeignKey("user_profile.id"))
    provider:                Mapped[str]           = mapped_column(String(50), default="gmail")
    # encrypted at rest — never logged, never committed
    encrypted_refresh_token: Mapped[str]           = mapped_column(Text)
    granted_scope:           Mapped[str]           = mapped_column(String(255), default="gmail.readonly")
    connected_at:            Mapped[datetime]      = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_synced_at:          Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    user: Mapped["UserProfile"] = relationship(back_populates="email_connection")


class SavedJob(Base):
    """
    Two-stage lifecycle: 'spotted' (raw_jd_text IS NULL) → 'analyzed' (raw_jd_text populated).
    See ERD.md for full lifecycle notes.
    """
    __tablename__ = "saved_job"

    id:                 Mapped[int]           = mapped_column(Integer, primary_key=True)
    user_profile_id:    Mapped[int]           = mapped_column(ForeignKey("user_profile.id"))
    company:            Mapped[Optional[str]] = mapped_column(String(255))
    title:              Mapped[Optional[str]] = mapped_column(String(255))
    # null = email/Apify "spotted" entry; populated once full JD is pasted via chat
    raw_jd_text:        Mapped[Optional[str]] = mapped_column(Text)
    # linkedin_email | apify_linkedin | apify_indeed | manual_paste_via_chat
    source:             Mapped[str]           = mapped_column(String(50))
    date_posted:        Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    date_saved:         Mapped[datetime]      = mapped_column(DateTime(timezone=True), server_default=func.now())
    # entry | mid | senior | staff_principal | manager_plus
    seniority_tier:     Mapped[Optional[str]] = mapped_column(String(50))
    # rule | llm
    seniority_method:   Mapped[Optional[str]] = mapped_column(String(10))
    seniority_reasoning:Mapped[Optional[str]] = mapped_column(Text)
    # low | medium | high
    interest_level:     Mapped[str]           = mapped_column(String(10), default="low")
    # derived | user_stated
    interest_source:    Mapped[str]           = mapped_column(String(15), default="derived")

    user:         Mapped["UserProfile"]      = relationship(back_populates="saved_jobs")
    skill_matches:Mapped[list["SkillMatchCache"]] = relationship(
        primaryjoin="and_(SkillMatchCache.source_type=='saved_job', "
                    "foreign(SkillMatchCache.source_id)==SavedJob.id)",
        viewonly=True,
    )


class WorkLogEntry(Base):
    __tablename__ = "work_log_entry"

    id:                    Mapped[int]           = mapped_column(Integer, primary_key=True)
    user_profile_id:       Mapped[int]           = mapped_column(ForeignKey("user_profile.id"))
    date_logged:           Mapped[datetime]      = mapped_column(DateTime(timezone=True), server_default=func.now())
    period_covered:        Mapped[Optional[str]] = mapped_column(String(255))
    raw_text:              Mapped[str]           = mapped_column(Text)
    activities_summary:    Mapped[Optional[str]] = mapped_column(Text)
    # individual_contributor | leading_others | strategic | unclear
    seniority_signal:      Mapped[Optional[str]] = mapped_column(String(30))
    # high | medium | low
    extraction_confidence: Mapped[Optional[str]] = mapped_column(String(10))

    user: Mapped["UserProfile"] = relationship(back_populates="work_log_entries")


class SkillMatchCache(Base):
    """
    Polymorphic cache table: one row per (source_type, source_id, canonical_skill_title).
    source_type = 'cv' | 'saved_job' | 'work_log_entry'
    source_id   = FK-like ref to the relevant table (no DB-level FK — see ERD.md notes)
    canonical_skill_title = string ref to skills_master.csv, not a live FK
    """
    __tablename__ = "skill_match_cache"

    id:                   Mapped[int] = mapped_column(Integer, primary_key=True)
    # cv | saved_job | work_log_entry
    source_type:          Mapped[str] = mapped_column(String(20))
    source_id:            Mapped[int] = mapped_column(Integer)
    # string ref to skills_master.csv — enforced in app code, not DB
    canonical_skill_title:Mapped[str] = mapped_column(String(255))
    # exact_phrase | synonym | fuzzy | llm_fallback
    match_method:         Mapped[str] = mapped_column(String(20))
    confidence:           Mapped[int] = mapped_column(Integer)
    evidence_snippet:     Mapped[Optional[str]] = mapped_column(Text)
    computed_at:          Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class NotificationRule(Base):
    """
    Rules live in the schema, not the codebase — from PyCon SG 2026 Day 2 talk pattern.
    Adding a new alert type = inserting a row, not a code change.
    """
    __tablename__ = "notification_rule"

    id:                    Mapped[int]  = mapped_column(Integer, primary_key=True)
    # inactivity | new_emerging_skill_match | cv_staleness
    trigger_type:          Mapped[str]  = mapped_column(String(50))
    schedule_description:  Mapped[str]  = mapped_column(String(255))
    condition_description: Mapped[str]  = mapped_column(Text)
    template_id:           Mapped[str]  = mapped_column(String(100))
    active:                Mapped[bool] = mapped_column(Boolean, default=True)

    states:        Mapped[list["NotificationRuleState"]] = relationship(back_populates="rule")
    notifications: Mapped[list["Notification"]]          = relationship(back_populates="rule")


class NotificationRuleState(Base):
    """
    Per-(rule, user) state. last_fired_at is the dedup guard — see ERD.md.
    Split from NotificationRule so the rule definition is shared while dedup is per-user.
    """
    __tablename__ = "notification_rule_state"

    id:                   Mapped[int]           = mapped_column(Integer, primary_key=True)
    notification_rule_id: Mapped[int]           = mapped_column(ForeignKey("notification_rule.id"))
    user_profile_id:      Mapped[int]           = mapped_column(ForeignKey("user_profile.id"))
    last_fired_at:        Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_evaluated_at:    Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    rule: Mapped["NotificationRule"] = relationship(back_populates="states")
    user: Mapped["UserProfile"]      = relationship(back_populates="notification_rule_states")


class Notification(Base):
    """
    Represents an outbound email send via Resend — NOT an in-app inbox item.
    delivery_status tracks did-it-send, not did-they-read. See ERD.md.
    """
    __tablename__ = "notification"

    id:                   Mapped[int]           = mapped_column(Integer, primary_key=True)
    notification_rule_id: Mapped[int]           = mapped_column(ForeignKey("notification_rule.id"))
    user_profile_id:      Mapped[int]           = mapped_column(ForeignKey("user_profile.id"))
    recipient_email:      Mapped[str]           = mapped_column(String(255))
    subject:              Mapped[str]           = mapped_column(String(500))
    message:              Mapped[str]           = mapped_column(Text)
    payload_json:         Mapped[Optional[str]] = mapped_column(Text)
    # queued | sent | failed
    delivery_status:      Mapped[str]           = mapped_column(String(10), default="queued")
    resend_message_id:    Mapped[Optional[str]] = mapped_column(String(255))
    created_at:           Mapped[datetime]      = mapped_column(DateTime(timezone=True), server_default=func.now())
    sent_at:              Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    rule: Mapped["NotificationRule"] = relationship(back_populates="notifications")
    user: Mapped["UserProfile"]      = relationship(back_populates="notifications")
