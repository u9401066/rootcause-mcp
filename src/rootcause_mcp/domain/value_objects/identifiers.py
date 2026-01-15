"""
Identifier Value Objects.

Strong typing for domain identifiers to prevent mixing up IDs.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Self


@dataclass(frozen=True, slots=True)
class SessionId:
    """Strongly-typed Session identifier."""

    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("SessionId cannot be empty")
        if not self.value.startswith("rc_sess_"):
            raise ValueError(f"SessionId must start with 'rc_sess_', got: {self.value}")

    @classmethod
    def generate(cls) -> Self:
        """Generate a new unique SessionId."""
        unique_part = uuid.uuid4().hex[:8]
        return cls(f"rc_sess_{unique_part}")

    @classmethod
    def from_string(cls, value: str) -> Self:
        """Create SessionId from string, validating format."""
        return cls(value)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class CauseId:
    """Strongly-typed Cause identifier."""

    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("CauseId cannot be empty")
        if not self.value.startswith("c_"):
            raise ValueError(f"CauseId must start with 'c_', got: {self.value}")

    @classmethod
    def generate(cls) -> Self:
        """Generate a new unique CauseId."""
        unique_part = uuid.uuid4().hex[:8]
        return cls(f"c_{unique_part}")

    @classmethod
    def from_string(cls, value: str) -> Self:
        """Create CauseId from string, validating format."""
        return cls(value)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class FishboneId:
    """Strongly-typed Fishbone identifier."""

    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("FishboneId cannot be empty")
        if not self.value.startswith("fb_"):
            raise ValueError(f"FishboneId must start with 'fb_', got: {self.value}")

    @classmethod
    def generate(cls) -> Self:
        """Generate a new unique FishboneId."""
        unique_part = uuid.uuid4().hex[:8]
        return cls(f"fb_{unique_part}")

    @classmethod
    def from_string(cls, value: str) -> Self:
        """Create FishboneId from string, validating format."""
        return cls(value)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class ActionId:
    """Strongly-typed Action identifier."""

    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("ActionId cannot be empty")
        if not self.value.startswith("act_"):
            raise ValueError(f"ActionId must start with 'act_', got: {self.value}")

    @classmethod
    def generate(cls) -> Self:
        """Generate a new unique ActionId."""
        unique_part = uuid.uuid4().hex[:8]
        return cls(f"act_{unique_part}")

    @classmethod
    def from_string(cls, value: str) -> Self:
        """Create ActionId from string, validating format."""
        return cls(value)

    def __str__(self) -> str:
        return self.value
