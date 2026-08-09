"""
Clinical Concept Value Object.

Encapsulates medical terminology with standard coding systems:
- SNOMED CT (Systematized Nomenclature of Medicine - Clinical Terms)
- ICD-10 (International Classification of Diseases, 10th Revision)
- RxNorm (Medications)
- LOINC (Laboratory tests)
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Any, Self

from pydantic import BaseModel, Field, ValidationInfo, field_validator


class CodingSystem(str, Enum):
    """Supported medical coding systems."""

    SNOMED_CT = "SNOMED_CT"  # http://snomed.info/sct
    ICD_10 = "ICD_10"  # WHO ICD-10
    ICD_10_CM = "ICD_10_CM"  # US Clinical Modification
    RXNORM = "RXNORM"  # Medications
    LOINC = "LOINC"  # Laboratory/Observations
    CPT = "CPT"  # Procedures
    CUSTOM = "CUSTOM"  # Local/proprietary coding


class ClinicalConcept(BaseModel):
    """
    Medical concept with standardized coding.

    Examples:
        - Acute myocardial infarction: SNOMED 57054005, ICD-10 I21.9
        - Propofol: RxNorm 8782
        - Troponin I: LOINC 10839-9
    """

    code: str = Field(..., description="Concept code in specified system")
    display: str = Field(..., description="Human-readable concept name")
    system: CodingSystem = Field(..., description="Coding system used")
    version: str | None = Field(None, description="Coding system version (optional)")

    @field_validator("code")
    @classmethod
    def validate_code_format(cls, v: str, info: ValidationInfo) -> str:
        """
        Validate code format based on system.

        Raises:
            ValueError: If code format is invalid for the specified system
        """
        system = info.data.get("system")

        if system == CodingSystem.ICD_10 or system == CodingSystem.ICD_10_CM:
            # ICD-10 format: Letter + 2 digits + optional decimal + more digits
            # Examples: I21.9, E11.65, S52.501A
            if not re.match(r"^[A-Z]\d{2}(\.\d{1,4}[A-Z]?)?$", v):
                raise ValueError(
                    f"Invalid ICD-10 code format: {v}. "
                    f"Expected format: Letter + 2 digits + optional decimal (e.g., I21.9)"
                )

        elif system == CodingSystem.SNOMED_CT:
            # SNOMED CT codes are numeric
            if not v.isdigit():
                raise ValueError(
                    f"Invalid SNOMED CT code: {v}. Must be numeric."
                )

        elif system == CodingSystem.RXNORM:
            # RxNorm CUIs are numeric
            if not v.isdigit():
                raise ValueError(f"Invalid RxNorm code: {v}. Must be numeric.")

        elif system == CodingSystem.LOINC:
            # LOINC format: digits + hyphen + check digit
            if not re.match(r"^\d+-\d$", v):
                raise ValueError(
                    f"Invalid LOINC code: {v}. Expected format: digits-checkdigit (e.g., 10839-9)"
                )

        return v

    @field_validator("display")
    @classmethod
    def validate_display_not_empty(cls, v: str) -> str:
        """Ensure display name is not empty."""
        if not v.strip():
            raise ValueError("Clinical concept display name cannot be empty")
        return v.strip()

    def __str__(self) -> str:
        """Human-readable representation."""
        return f"{self.display} ({self.system.value}:{self.code})"
        """
        Convert to FHIR Coding format.

        Returns:
            FHIR Coding dict: {system, code, display, version?}
        """
        system_urls = {
            CodingSystem.SNOMED_CT: "http://snomed.info/sct",
            CodingSystem.ICD_10: "http://hl7.org/fhir/sid/icd-10",
            CodingSystem.ICD_10_CM: "http://hl7.org/fhir/sid/icd-10-cm",
            CodingSystem.RXNORM: "http://www.nlm.nih.gov/research/umls/rxnorm",
            CodingSystem.LOINC: "http://loinc.org",
            CodingSystem.CPT: "http://www.ama-assn.org/go/cpt",
            CodingSystem.CUSTOM: "http://example.org/fhir/custom",
        }

        coding = {
            "system": system_urls[self.system],
            "code": self.code,
            "display": self.display,
        }

        if self.version:
            coding["version"] = self.version

        return coding

    model_config = {"frozen": True}  # Immutable value object


# Common clinical concepts (pre-configured)
class CommonConcepts:
    """Frequently used clinical concepts."""

    @staticmethod
    def acute_mi() -> ClinicalConcept:
        """Acute myocardial infarction."""
        return ClinicalConcept(
            code="I21.9",
            display="Acute myocardial infarction, unspecified",
            system=CodingSystem.ICD_10,
            version=None,
        )

    @staticmethod
    def propofol() -> ClinicalConcept:
        """Propofol (medication)."""
        return ClinicalConcept(
            code="8782",
            display="Propofol",
            system=CodingSystem.RXNORM,
            version=None,
        )

    @staticmethod
    def troponin_i() -> ClinicalConcept:
        """Troponin I (lab test)."""
        return ClinicalConcept(
            code="10839-9",
            display="Troponin I.cardiac [Mass/volume] in Serum or Plasma",
            system=CodingSystem.LOINC,
            version=None,
        )
