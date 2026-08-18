"""
Clinical Gap & Evidence Conflict Analyzer Domain Service.

Provides deterministic, automated detection of:
1. Diagnostic contradictions (active hypotheses conflicting with refuting evidence)
2. Guideline monitoring gaps (e.g., MTP without potassium, high-dose propofol without triglycerides)
3. Cross-document data discrepancies
4. Cognitive anchoring and premature closure alerts
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from rootcause_mcp.domain.entities.evidence import Evidence
    from rootcause_mcp.domain.entities.hypothesis import Hypothesis
    from rootcause_mcp.domain.entities.reasoning_step import ReasoningChain
    from rootcause_mcp.domain.entities.thinking_step import ThinkingChain


class ConflictSeverity(str, Enum):
    """Severity of clinical evidence conflict or gap."""

    CRITICAL = "CRITICAL"  # Paradoxical drug response, lethal overlooked conflict
    HIGH = "HIGH"  # Leading hypothesis contradicted by verified evidence
    MODERATE = "MODERATE"  # Guideline omission or unmonitored risk factor
    LOW = "LOW"  # Minor documentation inconsistency or timing ambiguity


@dataclass(frozen=True, slots=True)
class ClinicalConflict:
    """A detected clinical conflict, contradiction, or guideline gap."""

    conflict_id: str
    severity: ConflictSeverity
    category: str  # "DIAGNOSTIC_CONTRADICTION", "PARADOXICAL_RESPONSE", "GUIDELINE_GAP", "TEMPORAL_DISCREPANCY"
    title: str
    description: str
    conflicting_evidence_ids: tuple[str, ...] = ()
    involved_hypothesis_ids: tuple[str, ...] = ()
    actionable_remedy: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON output."""
        return {
            "conflict_id": self.conflict_id,
            "severity": self.severity.value,
            "category": self.category,
            "title": self.title,
            "description": self.description,
            "conflicting_evidence_ids": list(self.conflicting_evidence_ids),
            "involved_hypothesis_ids": list(self.involved_hypothesis_ids),
            "actionable_remedy": self.actionable_remedy,
        }


@dataclass(slots=True)
class GapAnalysisReport:
    """Comprehensive gap analysis and conflict audit report."""

    session_id: str
    total_conflicts: int
    critical_count: int
    high_count: int
    conflicts: list[ClinicalConflict] = field(default_factory=list)
    guideline_alerts: list[str] = field(default_factory=list)
    safety_invariants_met: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "session_id": self.session_id,
            "total_conflicts": self.total_conflicts,
            "critical_count": self.critical_count,
            "high_count": self.high_count,
            "conflicts": [c.to_dict() for c in self.conflicts],
            "guideline_alerts": self.guideline_alerts,
            "safety_invariants_met": self.safety_invariants_met,
        }


class ClinicalGapAnalyzer:
    """
    Domain Service for automated diagnostic conflict and clinical guideline gap analysis.

    Enables agents to detect hidden contradictions and guideline omissions
    before diagnostic synthesis.
    """

    @classmethod
    def analyze(
        cls,
        session_id: str,
        evidence_store: dict[str, Evidence],
        hypothesis_store: dict[str, Hypothesis],
        thinking_chain: ThinkingChain | None = None,
        reasoning_chain: ReasoningChain | None = None,
    ) -> GapAnalysisReport:
        """Analyze evidence and hypotheses for diagnostic contradictions and safety gaps."""
        conflicts: list[ClinicalConflict] = []
        guideline_alerts: list[str] = []
        _ = (
            thinking_chain,
            reasoning_chain,
        )  # Extensibility anchor for future cognitive metrics

        # 1. Check Diagnostic Contradictions.  Numeric Bayesian compatibility
        # values are deliberately ignored because they are not calibrated
        # clinical probability.  Only an explicit high-certainty/confirmed
        # qualitative disposition makes the contradiction a HIGH conflict.
        for hyp in hypothesis_store.values():
            high_certainty = hyp.certainty.value in {"HIGH_CONFIDENCE", "CONFIRMED"}
            confirmed_status = hyp.status.value == "CONFIRMED"
            if (high_certainty or confirmed_status) and hyp.contradicting_evidence_ids:
                contradicting_evs = [
                    evidence_store[ev_id].content
                    for ev_id in hyp.contradicting_evidence_ids
                    if ev_id in evidence_store
                ]
                conflicts.append(
                    ClinicalConflict(
                        conflict_id=f"CONF-DIAG-{hyp.id.value}",
                        severity=ConflictSeverity.HIGH,
                        category="DIAGNOSTIC_CONTRADICTION",
                        title=f"High-Certainty Hypothesis '{hyp.diagnosis.display}' Has Unresolved Refuting Evidence",
                        description=(
                            "The explicitly recorded qualitative disposition is "
                            f"{hyp.certainty.value}/{hyp.status.value}, but the hypothesis "
                            "is directly contradicted by evidence: "
                            f"{'; '.join(contradicting_evs[:2])}"
                        ),
                        conflicting_evidence_ids=tuple(hyp.contradicting_evidence_ids),
                        involved_hypothesis_ids=(hyp.id.value,),
                        actionable_remedy="Re-evaluate likelihood ratios or explore whether alternative diagnoses explain these refuting findings.",
                    )
                )

        # 2. Check Paradoxical Drug Responses in Evidence (e.g. Inotropes making hypotension worse)
        evidence_texts = [
            (e.id.value, f"{e.content} {e.source.raw_snippet or ''}".lower())
            for e in evidence_store.values()
        ]

        paradoxical_ev_ids = [
            eid
            for eid, text in evidence_texts
            if any(
                p in text
                for p in [
                    "got worse",
                    "worsening with epi",
                    "no response",
                    "crash",
                    "bp dropping further",
                ]
            )
            and any(
                d in text for d in ["epinephrine", "ephedrine", "inotrop", "dobutamine"]
            )
        ]
        if paradoxical_ev_ids:
            has_hemodynamic_mechanism = any(
                any(
                    term in h.diagnosis.display.lower()
                    for term in (
                        "lvot",
                        "dynamic obstruction",
                        "preload",
                        "afterload",
                        "arrhythm",
                        "anaphyl",
                        "toxic",
                    )
                )
                for h in hypothesis_store.values()
            )
            if not has_hemodynamic_mechanism:
                conflicts.append(
                    ClinicalConflict(
                        conflict_id="CONF-PARADOX-INOTROPE",
                        severity=ConflictSeverity.MODERATE,
                        category="DIAGNOSTIC_BREADTH_GAP",
                        title=(
                            "Documented Hemodynamic Deterioration after a Vasoactive "
                            "Intervention Needs Broader Mechanism Review"
                        ),
                        description=(
                            "The temporal response is source-linked but is not specific "
                            "for one diagnosis. Review dynamic obstruction, preload/"
                            "afterload mismatch, arrhythmia, medication/toxin effects, "
                            "allergic physiology, measurement artifact, and event timing."
                        ),
                        conflicting_evidence_ids=tuple(paradoxical_ev_ids),
                        actionable_remedy=(
                            "Retrospectively retrieve the original waveform, medication "
                            "administration record, hemodynamic trend, and available "
                            "echocardiography for qualified-clinician review."
                        ),
                    )
                )

        # 3. Monitoring audit.  A trigger without a monitoring mention is only a
        # source-coverage gap; it is never evidence that monitoring was omitted.
        mtp_ev_ids = [
            evidence_id
            for evidence_id, text in evidence_texts
            if "mtp" in text or "transfusion" in text or "unit #" in text
        ]
        has_mtp = bool(mtp_ev_ids)
        has_potassium_check = any(
            "potassium" in text or "k+" in text or "k:" in text or "abg" in text
            for _, text in evidence_texts
        )
        electrolyte_absence_ev_ids = [
            evidence_id
            for evidence_id, text in evidence_texts
            if _explicit_monitoring_absence(
                text,
                ("potassium", "electrolyte", "abg", "blood gas"),
            )
        ]
        if has_mtp and electrolyte_absence_ev_ids:
            guideline_alerts.append(
                "MTP retrospective audit: a source explicitly records absent "
                "electrolyte monitoring."
            )
            conflicts.append(
                ClinicalConflict(
                    conflict_id="GAP-MTP-ELECTROLYTE",
                    severity=ConflictSeverity.HIGH,
                    category="GUIDELINE_GAP",
                    title="Explicitly Documented Absent Electrolyte Monitoring during MTP",
                    description=(
                        "A supplied source explicitly states that electrolyte/blood-gas "
                        "monitoring was not performed during the recorded transfusion."
                    ),
                    conflicting_evidence_ids=tuple(
                        sorted(set(mtp_ev_ids + electrolyte_absence_ev_ids))
                    ),
                    actionable_remedy=(
                        "Retrospectively verify the complete transfusion, laboratory, "
                        "and point-of-care records with a qualified reviewer."
                    ),
                )
            )
        elif has_mtp and not has_potassium_check:
            guideline_alerts.append(
                "MTP monitoring status is unknown in the supplied sources; absence "
                "of a potassium/ABG mention is not proof of omission."
            )
            conflicts.append(
                ClinicalConflict(
                    conflict_id="DATA-GAP-MTP-ELECTROLYTE",
                    severity=ConflictSeverity.LOW,
                    category="DATA_GAP",
                    title="MTP Electrolyte Monitoring Status Unknown",
                    description=(
                        "The supplied evidence mentions transfusion but neither records "
                        "monitoring nor explicitly records its absence."
                    ),
                    conflicting_evidence_ids=tuple(mtp_ev_ids),
                    actionable_remedy=(
                        "Retrieve the complete laboratory, blood-gas, transfusion, and "
                        "point-of-care records for retrospective reviewer confirmation."
                    ),
                )
            )

        # 3b. High-Dose Propofol without Lipid/Triglyceride Panel
        propofol_ev_ids = [
            evidence_id
            for evidence_id, text in evidence_texts
            if "propofol" in text
            and any(
                marker in text
                for marker in ("45 ml", "50 ml", "60 ml", "8 mg/kg", "48h", "48 hour")
            )
        ]
        has_high_propofol = bool(propofol_ev_ids)
        has_tg_check = any(
            "triglyceride" in text or "lipid panel" in text
            for _, text in evidence_texts
        )
        lipid_absence_ev_ids = [
            evidence_id
            for evidence_id, text in evidence_texts
            if _explicit_monitoring_absence(
                text,
                ("triglyceride", "lipid panel", "lipid monitoring"),
            )
        ]
        if has_high_propofol and lipid_absence_ev_ids:
            guideline_alerts.append(
                "Propofol retrospective audit: a source explicitly records absent "
                "lipid/triglyceride monitoring."
            )
            conflicts.append(
                ClinicalConflict(
                    conflict_id="GAP-PRIS-LIPID",
                    severity=ConflictSeverity.HIGH,
                    category="GUIDELINE_GAP",
                    title="Explicitly Documented Absent Lipid Monitoring during Propofol",
                    description=(
                        "A supplied source explicitly states that triglyceride/lipid "
                        "monitoring was not performed during the recorded exposure."
                    ),
                    conflicting_evidence_ids=tuple(
                        sorted(set(propofol_ev_ids + lipid_absence_ev_ids))
                    ),
                    actionable_remedy=(
                        "Retrospectively verify the full medication, laboratory, and "
                        "monitoring record with a qualified reviewer."
                    ),
                )
            )
        elif has_high_propofol and not has_tg_check:
            guideline_alerts.append(
                "Propofol lipid-monitoring status is unknown in the supplied sources; "
                "absence of a triglyceride mention is not proof of omission."
            )
            conflicts.append(
                ClinicalConflict(
                    conflict_id="DATA-GAP-PROPOFOL-LIPID",
                    severity=ConflictSeverity.LOW,
                    category="DATA_GAP",
                    title="Propofol Lipid-Monitoring Status Unknown",
                    description=(
                        "The supplied evidence records Propofol exposure but neither "
                        "records lipid monitoring nor explicitly records its absence."
                    ),
                    conflicting_evidence_ids=tuple(propofol_ev_ids),
                    actionable_remedy=(
                        "Retrieve the complete medication administration, laboratory, "
                        "and monitoring records for retrospective reviewer confirmation."
                    ),
                )
            )

        # 3c. Held Anticoagulation without Expiration/Renewal Safety Net
        has_held_anticoag = any(
            "clexane" in text
            and ("held" in text or "hold" in text or "not_given" in text)
            for _, text in evidence_texts
        )
        has_dvt_monitoring = any(
            "doppler" in text
            or "ultrasound" in text
            or "cta" in text
            or "d-dimer" in text
            for _, text in evidence_texts
        )
        if has_held_anticoag and not has_dvt_monitoring:
            guideline_alerts.append(
                "Anticoagulation-surveillance status is unknown in the supplied "
                "sources; absence of a surveillance mention is not proof of omission."
            )

        # 4. Check Premature Closure (<3 hypotheses in critical event)
        if len(hypothesis_store) < 3 and len(evidence_store) >= 3:
            conflicts.append(
                ClinicalConflict(
                    conflict_id="GAP-PREMATURE-CLOSURE",
                    severity=ConflictSeverity.MODERATE,
                    category="COGNITIVE_GAP",
                    title="Potential Premature Diagnostic Closure (<3 Hypotheses)",
                    description=f"Only {len(hypothesis_store)} differential diagnosis hypothesis/hypotheses modeled. Minimum 3 required for defensible RCA.",
                    actionable_remedy="Expand differential to include high-risk emergency rule-outs.",
                )
            )

        critical_count = sum(
            1 for c in conflicts if c.severity == ConflictSeverity.CRITICAL
        )
        high_count = sum(1 for c in conflicts if c.severity == ConflictSeverity.HIGH)
        safety_invariants_met = critical_count == 0 and high_count == 0

        return GapAnalysisReport(
            session_id=session_id,
            total_conflicts=len(conflicts),
            critical_count=critical_count,
            high_count=high_count,
            conflicts=conflicts,
            guideline_alerts=guideline_alerts,
            safety_invariants_met=safety_invariants_met,
        )


def _explicit_monitoring_absence(text: str, targets: tuple[str, ...]) -> bool:
    """Return true only for an explicit source statement that monitoring was absent."""
    absence_patterns = (
        "no {target}",
        "without {target}",
        "{target} was not performed",
        "{target} was not checked",
        "{target} was not monitored",
        "{target} not performed",
        "{target} not checked",
        "{target} not monitored",
    )
    return any(
        pattern.format(target=target) in text
        for target in targets
        for pattern in absence_patterns
    )
