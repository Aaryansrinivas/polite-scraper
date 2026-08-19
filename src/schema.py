"""
Stage 3 & 4 — the shape of a record.

RawRecord: exactly what Stage 3 scrapes off the page, no cleaning.
BookRecord: the normalized, validated shape that is safe to store.
A record that cannot become a valid BookRecord is rejected and goes
to errors.json together with the reason — it never reaches books.json.
"""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, HttpUrl, field_validator


class RawRecord(BaseModel):
    """Untouched strings straight out of the HTML. Stage 3 output."""

    title: str
    product_url: str
    price_text: str
    availability_text: str
    rating_text: str
    description: Optional[str] = None
    source_page: str
    fetched_at: str


RATING_WORDS = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}


class BookRecord(BaseModel):
    """Clean, checked record. Stage 4 output — this is what books.json holds."""

    title: str
    product_url: HttpUrl  # canonical URL — this record's identity
    price_text: str
    price_gbp: float
    availability_text: str
    rating_text: str
    rating_num: Optional[int] = None
    description: Optional[str] = None
    source_page: str
    fetched_at: str

    @field_validator("price_gbp")
    @classmethod
    def price_must_be_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError(f"price_gbp must be positive, got {v}")
        return v

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("title is empty")
        return v
