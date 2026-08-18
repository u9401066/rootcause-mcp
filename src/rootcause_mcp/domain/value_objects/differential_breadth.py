"""Typed, auditable coverage of an appropriately broad differential diagnosis."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Self
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from rootcause_mcp.domain.entities.hypothesis import MechanismCategory


class DifferentialBreadthFramework(StrEnum):
    """Supported clinical frameworks for systematic DDx expansion."""

    VINDICATE = "VINDICATE"
    FIVE_H_FIVE_T = "FIVE_H_FIVE_T"
    ANATOMIC_SYSTEM = "ANATOMIC_SYSTEM"
    MEDICATION_DEVICE_EXPOSURE = "MEDICATION_DEVICE_EXPOSURE"
    CUSTOM = "CUSTOM"


class DifferentialBreadthAuditRole(StrEnum):
    """Whether an audit is the main or a supplementary coverage framework."""

    PRIMARY = "PRIMARY"
    SUPPLEMENTAL = "SUPPLEMENTAL"


class BreadthCellStatus(StrEnum):
    """Four-state review outcome; uncertainty is retained, not treated as exclusion."""

    CANDIDATES_PRESENT = "CANDIDATES_PRESENT"
    REVIEWED_NO_PLAUSIBLE_CANDIDATE = "REVIEWED_NO_PLAUSIBLE_CANDIDATE"
    REVIEWED_INSUFFICIENT_DATA = "REVIEWED_INSUFFICIENT_DATA"
    NOT_ASSESSED = "NOT_ASSESSED"


class BreadthDiscriminatorKind(StrEnum):
    """Kind of prospective information used to resolve an uncertain cell."""

    DATA_RETRIEVAL = "DATA_RETRIEVAL"
    DIAGNOSTIC_TEST = "DIAGNOSTIC_TEST"
    SPECIALIST_REVIEW = "SPECIALIST_REVIEW"
    MONITORING = "MONITORING"


class BreadthDiscriminatorStatus(StrEnum):
    """Pending lifecycle state for a breadth-level discriminator."""

    PLANNED = "PLANNED"
    ORDERED = "ORDERED"


class PlannedBreadthDiscriminator(BaseModel):
    """Typed prospective data/test needed to resolve insufficient information."""

    name: str = Field(..., min_length=1, max_length=200)
    kind: BreadthDiscriminatorKind
    expected_supporting_result: str = Field(..., min_length=1, max_length=500)
    expected_refuting_result: str = Field(..., min_length=1, max_length=500)
    status: BreadthDiscriminatorStatus = BreadthDiscriminatorStatus.PLANNED

    model_config = ConfigDict(frozen=True, extra="forbid")


class DifferentialBreadthCell(BaseModel):
    """Review outcome for one canonical or custom framework cell."""

    cell_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r"^[A-Z][A-Z0-9_]*$",
    )
    status: BreadthCellStatus
    hypothesis_ids: list[str] = Field(default_factory=list)
    mechanism_categories: list[MechanismCategory] = Field(default_factory=list)
    rationale: str = Field(..., min_length=10, max_length=1000)
    unknowns: list[str] = Field(default_factory=list)
    planned_discriminators: list[PlannedBreadthDiscriminator] = Field(
        default_factory=list
    )

    @field_validator("hypothesis_ids", "unknowns")
    @classmethod
    def normalize_nonblank_unique_text(cls, values: list[str]) -> list[str]:
        """Reject blank/duplicate linkage and uncertainty values."""
        normalized = [" ".join(value.split()) for value in values]
        if any(not value for value in normalized):
            raise ValueError("breadth cell lists cannot contain blank values")
        if len(normalized) != len(set(normalized)):
            raise ValueError("breadth cell lists cannot contain duplicate values")
        return normalized

    @model_validator(mode="after")
    def validate_status_obligations(self) -> Self:
        """Keep candidates, exclusions, and insufficient data distinguishable."""
        if len(self.mechanism_categories) != len(set(self.mechanism_categories)):
            raise ValueError("mechanism_categories cannot contain duplicates")
        if MechanismCategory.UNKNOWN in self.mechanism_categories:
            raise ValueError(
                "CANDIDATES_PRESENT linkage cannot use UNKNOWN mechanism_category"
            )
        if self.status is BreadthCellStatus.CANDIDATES_PRESENT:
            if not self.hypothesis_ids or not self.mechanism_categories:
                raise ValueError(
                    "CANDIDATES_PRESENT requires hypothesis_ids and mechanism_categories"
                )
        elif self.hypothesis_ids:
            raise ValueError("only CANDIDATES_PRESENT cells may contain hypothesis_ids")
        if self.status is BreadthCellStatus.REVIEWED_INSUFFICIENT_DATA and (
            not self.unknowns or not self.planned_discriminators
        ):
            raise ValueError(
                "REVIEWED_INSUFFICIENT_DATA requires unknowns and planned_discriminators"
            )
        if self.status is BreadthCellStatus.REVIEWED_NO_PLAUSIBLE_CANDIDATE and (
            self.unknowns or self.planned_discriminators
        ):
            raise ValueError(
                "unknowns and planned_discriminators require REVIEWED_INSUFFICIENT_DATA"
            )
        return self

    model_config = ConfigDict(frozen=True, extra="forbid")


_VINDICATE_CELLS = frozenset(
    {
        "VASCULAR",
        "INFECTIOUS",
        "INFLAMMATORY_IMMUNE",
        "NEOPLASTIC",
        "DRUG_TOXIN_IATROGENIC",
        "METABOLIC_ENDOCRINE",
        "TRAUMATIC_MECHANICAL",
        "CONGENITAL_GENETIC",
        "DEGENERATIVE",
        "FUNCTIONAL_PHYSIOLOGIC",
    }
)
_FIVE_H_FIVE_T_CELLS = frozenset(
    {
        "HYPOVOLEMIA",
        "HYPOXIA",
        "HYDROGEN_ION_ACIDOSIS",
        "HYPOKALEMIA_HYPERKALEMIA",
        "HYPOTHERMIA",
        "TENSION_PNEUMOTHORAX",
        "CARDIAC_TAMPONADE",
        "TOXINS",
        "PULMONARY_THROMBOSIS",
        "CORONARY_THROMBOSIS",
    }
)
_ANATOMIC_SYSTEM_CELLS = frozenset(
    {
        "CARDIOVASCULAR",
        "RESPIRATORY",
        "NEUROLOGIC",
        "GASTROINTESTINAL_HEPATOBILIARY",
        "RENAL_GENITOURINARY",
        "ENDOCRINE_METABOLIC",
        "HEMATOLOGIC",
        "INFECTIOUS_IMMUNE",
        "MUSCULOSKELETAL",
        "DERMATOLOGIC",
        "PSYCHIATRIC_FUNCTIONAL",
    }
)
_MEDICATION_DEVICE_CELLS = frozenset(
    {
        "MEDICATION_THERAPEUTIC_EFFECT",
        "ADVERSE_DRUG_REACTION",
        "OVERDOSE_TOXICITY",
        "WITHDRAWAL_OMISSION",
        "DRUG_DRUG_INTERACTION",
        "DEVICE_MALFUNCTION",
        "DEVICE_MISUSE_CONFIGURATION",
        "PROCEDURE_IATROGENIC",
    }
)

CANONICAL_FRAMEWORK_CELLS: dict[DifferentialBreadthFramework, frozenset[str]] = {
    DifferentialBreadthFramework.VINDICATE: _VINDICATE_CELLS,
    DifferentialBreadthFramework.FIVE_H_FIVE_T: _FIVE_H_FIVE_T_CELLS,
    DifferentialBreadthFramework.ANATOMIC_SYSTEM: _ANATOMIC_SYSTEM_CELLS,
    DifferentialBreadthFramework.MEDICATION_DEVICE_EXPOSURE: (_MEDICATION_DEVICE_CELLS),
}

_NON_UNKNOWN_MECHANISMS = frozenset(
    item for item in MechanismCategory if item is not MechanismCategory.UNKNOWN
)
CANONICAL_CELL_MECHANISM_CATEGORIES: dict[
    DifferentialBreadthFramework,
    dict[str, frozenset[MechanismCategory]],
] = {
    DifferentialBreadthFramework.VINDICATE: {
        cell_id: frozenset({MechanismCategory(cell_id)}) for cell_id in _VINDICATE_CELLS
    },
    DifferentialBreadthFramework.FIVE_H_FIVE_T: {
        "HYPOVOLEMIA": frozenset(
            {
                MechanismCategory.VASCULAR,
                MechanismCategory.TRAUMATIC_MECHANICAL,
            }
        ),
        "HYPOXIA": frozenset(
            {
                MechanismCategory.FUNCTIONAL_PHYSIOLOGIC,
                MechanismCategory.TRAUMATIC_MECHANICAL,
                MechanismCategory.VASCULAR,
            }
        ),
        "HYDROGEN_ION_ACIDOSIS": frozenset({MechanismCategory.METABOLIC_ENDOCRINE}),
        "HYPOKALEMIA_HYPERKALEMIA": frozenset(
            {
                MechanismCategory.METABOLIC_ENDOCRINE,
                MechanismCategory.DRUG_TOXIN_IATROGENIC,
            }
        ),
        "HYPOTHERMIA": frozenset(
            {
                MechanismCategory.METABOLIC_ENDOCRINE,
                MechanismCategory.DRUG_TOXIN_IATROGENIC,
                MechanismCategory.TRAUMATIC_MECHANICAL,
            }
        ),
        "TENSION_PNEUMOTHORAX": frozenset(
            {
                MechanismCategory.TRAUMATIC_MECHANICAL,
                MechanismCategory.FUNCTIONAL_PHYSIOLOGIC,
            }
        ),
        "CARDIAC_TAMPONADE": frozenset(
            {
                MechanismCategory.VASCULAR,
                MechanismCategory.INFECTIOUS,
                MechanismCategory.INFLAMMATORY_IMMUNE,
                MechanismCategory.NEOPLASTIC,
                MechanismCategory.DRUG_TOXIN_IATROGENIC,
                MechanismCategory.TRAUMATIC_MECHANICAL,
            }
        ),
        "TOXINS": frozenset({MechanismCategory.DRUG_TOXIN_IATROGENIC}),
        "PULMONARY_THROMBOSIS": frozenset({MechanismCategory.VASCULAR}),
        "CORONARY_THROMBOSIS": frozenset({MechanismCategory.VASCULAR}),
    },
    # Anatomic localization is orthogonal to etiology. Its cells therefore
    # permit any explicit non-UNKNOWN mechanism while still enforcing exact
    # system-cell coverage and hypothesis linkage.
    DifferentialBreadthFramework.ANATOMIC_SYSTEM: dict.fromkeys(
        _ANATOMIC_SYSTEM_CELLS,
        _NON_UNKNOWN_MECHANISMS,
    ),
    DifferentialBreadthFramework.MEDICATION_DEVICE_EXPOSURE: {
        "MEDICATION_THERAPEUTIC_EFFECT": frozenset(
            {MechanismCategory.DRUG_TOXIN_IATROGENIC}
        ),
        "ADVERSE_DRUG_REACTION": frozenset({MechanismCategory.DRUG_TOXIN_IATROGENIC}),
        "OVERDOSE_TOXICITY": frozenset({MechanismCategory.DRUG_TOXIN_IATROGENIC}),
        "WITHDRAWAL_OMISSION": frozenset({MechanismCategory.DRUG_TOXIN_IATROGENIC}),
        "DRUG_DRUG_INTERACTION": frozenset({MechanismCategory.DRUG_TOXIN_IATROGENIC}),
        "DEVICE_MALFUNCTION": frozenset(
            {
                MechanismCategory.DRUG_TOXIN_IATROGENIC,
                MechanismCategory.TRAUMATIC_MECHANICAL,
            }
        ),
        "DEVICE_MISUSE_CONFIGURATION": frozenset(
            {
                MechanismCategory.DRUG_TOXIN_IATROGENIC,
                MechanismCategory.TRAUMATIC_MECHANICAL,
            }
        ),
        "PROCEDURE_IATROGENIC": frozenset(
            {
                MechanismCategory.DRUG_TOXIN_IATROGENIC,
                MechanismCategory.TRAUMATIC_MECHANICAL,
            }
        ),
    },
}


class DifferentialBreadthAudit(BaseModel):
    """One persisted review proving that a broad framework was actually applied."""

    audit_id: str = Field(
        default_factory=lambda: f"DBA-{uuid4().hex[:8]}",
        min_length=5,
        max_length=64,
        pattern=r"^DBA-[A-Za-z0-9_-]+$",
    )
    framework: DifferentialBreadthFramework
    framework_name: str | None = Field(default=None, min_length=1, max_length=200)
    framework_rationale: str = Field(..., min_length=10, max_length=1000)
    role: DifferentialBreadthAuditRole = DifferentialBreadthAuditRole.PRIMARY
    cells: list[DifferentialBreadthCell] = Field(..., min_length=3)
    stop_rationale: str = Field(..., min_length=10, max_length=1000)
    recorded_by: str = Field(..., min_length=1, max_length=128)
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def validate_framework_coverage(self) -> Self:
        """Require exact built-in cells or an explicitly named custom framework."""
        cell_ids = [cell.cell_id for cell in self.cells]
        if len(cell_ids) != len(set(cell_ids)):
            raise ValueError("differential breadth cell_id values must be unique")
        if self.framework is DifferentialBreadthFramework.CUSTOM:
            if not self.framework_name:
                raise ValueError("CUSTOM breadth audits require framework_name")
            if (
                self.role is DifferentialBreadthAuditRole.PRIMARY
                and len(self.cells) < 3
            ):
                raise ValueError(
                    "PRIMARY CUSTOM breadth audits require at least 3 cells"
                )
        else:
            if self.framework_name is not None:
                raise ValueError("framework_name is only valid for CUSTOM audits")
            expected = CANONICAL_FRAMEWORK_CELLS[self.framework]
            if set(cell_ids) != set(expected):
                missing = sorted(expected - set(cell_ids))
                extra = sorted(set(cell_ids) - expected)
                raise ValueError(
                    f"{self.framework.value} requires exact canonical cells; "
                    f"missing={missing}, extra={extra}"
                )
            allowed_by_cell = CANONICAL_CELL_MECHANISM_CATEGORIES[self.framework]
            for cell in self.cells:
                incompatible = (
                    set(cell.mechanism_categories) - allowed_by_cell[cell.cell_id]
                )
                if incompatible:
                    raise ValueError(
                        f"canonical cell {cell.cell_id} has incompatible mechanism "
                        f"categories: {sorted(item.value for item in incompatible)}"
                    )
        return self

    @property
    def is_complete(self) -> bool:
        """A reviewed unknown is complete; an unassessed cell is not."""
        return all(
            cell.status is not BreadthCellStatus.NOT_ASSESSED for cell in self.cells
        )

    model_config = ConfigDict(frozen=True, extra="forbid")
