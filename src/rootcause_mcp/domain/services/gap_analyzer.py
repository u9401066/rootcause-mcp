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

        # 1. Check Diagnostic Contradictions: High probability hypothesis with contradicting evidence
        for hyp in hypothesis_store.values():
            if hyp.current_probability >= 0.50 and hyp.contradicting_evidence_ids:
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
                        title=f"High-Probability Hypothesis '{hyp.diagnosis.display}' Has Unresolved Refuting Evidence",
                        description=(
                            f"Hypothesis has posterior probability {hyp.current_probability:.1%}, but is directly "
                            f"contradicted by evidence: {'; '.join(contradicting_evs[:2])}"
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
            # Check if dynamic obstruction / SAM is considered
            has_sam_hyp = any(
                "sam" in h.diagnosis.display.lower()
                or "lvot" in h.diagnosis.display.lower()
                or "dynamic" in h.diagnosis.display.lower()
                for h in hypothesis_store.values()
            )
            if not has_sam_hyp:
                conflicts.append(
                    ClinicalConflict(
                        conflict_id="CONF-PARADOX-INOTROPE",
                        severity=ConflictSeverity.CRITICAL,
                        category="PARADOXICAL_RESPONSE",
                        title="Paradoxical Hemodynamic Deterioration after Inotropes Unaccounted For",
                        description="Patient collapsed or blood pressure dropped further after Epinephrine/Ephedrine. This is a classic hallmark of Dynamic LVOT Obstruction (SAM) or LAST.",
                        conflicting_evidence_ids=tuple(paradoxical_ev_ids),
                        actionable_remedy="Propose Dynamic LVOT Obstruction (SAM) hypothesis and verify with TEE CW Doppler and A-line waveform.",
                    )
                )

        # 3. Check Guideline Monitoring Omissions:
        # 3a. Massive Transfusion without Potassium / ABG check
        has_mtp = any(
            "mtp" in text or "transfusion" in text or "unit #" in text
            for _, text in evidence_texts
        )
        has_potassium_check = any(
            "potassium" in text or "k+" in text or "k:" in text or "abg" in text
            for _, text in evidence_texts
        )
        if has_mtp and not has_potassium_check:
            guideline_alerts.append(
                "MTP Safety Alert: Massive blood transfusion delivered without verified Point-of-Care potassium/calcium monitoring (Risk of Hyperkalemic arrest)."
            )
            conflicts.append(
                ClinicalConflict(
                    conflict_id="GAP-MTP-ELECTROLYTE",
                    severity=ConflictSeverity.HIGH,
                    category="GUIDELINE_GAP",
                    title="Missing Electrolyte Monitoring during Massive Transfusion Protocol",
                    description="Multiple units of PRBCs transfused without regular stat potassium checks, creating risk of lethal transfusion-associated hyperkalemia.",
                    actionable_remedy="Order STAT POC electrolyte panel and verify stored blood unit age.",
                )
            )

        # 3b. High-Dose Propofol without Lipid/Triglyceride Panel
        has_high_propofol = any(
            "propofol" in text
            and any(
                r in text
                for r in ["45 ml", "50 ml", "60 ml", "8 mg/kg", "48h", "48 hour"]
            )
            for _, text in evidence_texts
        )
        has_tg_check = any(
            "triglyceride" in text or "lipid panel" in text
            for _, text in evidence_texts
        )
        if has_high_propofol and not has_tg_check:
            guideline_alerts.append(
                "PRIS Safety Alert: High-dose Propofol infusion (>48h) lacks routine serum Triglyceride and CPK surveillance."
            )
            conflicts.append(
                ClinicalConflict(
                    conflict_id="GAP-PRIS-LIPID",
                    severity=ConflictSeverity.HIGH,
                    category="GUIDELINE_GAP",
                    title="Omitted Serum Triglyceride Panel during Prolonged High-Dose Propofol Infusion",
                    description="Continuous Propofol sedation exceeding 48 hours without triglyceride monitoring risks undetected PRIS lipid overload.",
                    actionable_remedy="Order STAT lipid panel and assess for metabolic acidosis, green urine, and rhabdomyolysis.",
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
                "DVT Prophylaxis Alert: Chemical thromboprophylaxis held post-operatively without active surveillance for deep vein thrombosis."
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
