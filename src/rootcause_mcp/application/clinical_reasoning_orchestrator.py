"""
Clinical Reasoning Orchestrator.

Agent-friendly API that hides medical complexity behind simple operations.
This is the core "harness" that enables any AI agent to perform specialist-level reasoning.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any

from rootcause_mcp.domain.entities.evidence import (
    Evidence,
    EvidenceSource,
    EvidenceType,
)
from rootcause_mcp.domain.entities.hypothesis import Hypothesis, HypothesisStatus
from rootcause_mcp.domain.entities.reasoning_step import (
    ReasoningChain,
    ReasoningStep,
    ReasoningStepType,
)
from rootcause_mcp.domain.entities.thinking_step import ThinkingChain
from rootcause_mcp.domain.services.guidance_service import ClinicalGuidanceService
from rootcause_mcp.domain.services.provenance_verifier import (
    ProvenanceMatch,
    ProvenanceVerifier,
)
from rootcause_mcp.domain.value_objects.clinical_concept import (
    ClinicalConcept,
    CodingSystem,
)
from rootcause_mcp.domain.value_objects.evidence_quality import (
    EvidenceQuality,
    EvidenceReliability,
    EvidenceStrength,
)
from rootcause_mcp.domain.value_objects.reasoning_guidance import ReasoningGuidance


class ClinicalReasoningOrchestrator:
    """
    Agent-friendly orchestrator for clinical reasoning.

    Hides complexity:
    - Bayesian calculations
    - Evidence quality grading and deterministic provenance verification
    - FHIR/SNOMED coding
    - Multi-loop reasoning guidance for Flash models
    - HFACS classification

    Agent only needs to:
    1. add_evidence("natural language description", source_document="...", raw_snippet="...")
    2. propose_hypothesis("diagnosis name")
    3. link_evidence_to_hypothesis(evidence_id, hypothesis_id)
    4. get_differential_diagnosis()
    """

    def __init__(
        self,
        session_id: str,
    ) -> None:
        """
        Initialize orchestrator for a clinical session.

        Args:
            session_id: RCA session ID
        """
        self.session_id = session_id
        self.reasoning_chain = ReasoningChain(
            session_id=session_id,
            finalized_at=None,
        )
        self.thinking_chain = ThinkingChain(session_id=session_id)
        self.evidence_store: dict[str, Evidence] = {}
        self.hypothesis_store: dict[str, Hypothesis] = {}
        self._provenance_verifier = ProvenanceVerifier()
        self._step_counter = 0

    def restore(
        self,
        *,
        evidence: list[Evidence],
        hypotheses: list[Hypothesis],
        thinking_chain: ThinkingChain | None,
        reasoning_chain: ReasoningChain | None,
    ) -> None:
        """Restore the aggregate from repository snapshots."""
        self.evidence_store = {item.id.value: item for item in evidence}
        self.hypothesis_store = {item.id.value: item for item in hypotheses}
        if thinking_chain is not None:
            self.thinking_chain = thinking_chain
        if reasoning_chain is not None:
            self.reasoning_chain = reasoning_chain
        self._step_counter = len(self.reasoning_chain.steps)

    def add_evidence(
        self,
        content: str,
        evidence_type: str = "DOCUMENT",
        source_document: str | None = None,
        source_location: str | None = None,
        raw_snippet: str | None = None,
        content_hash: str | None = None,
        extraction_method: str | None = None,
        collected_by: str = "agent",
        clinical_strength: str = "MODERATE",
        source_reliability: str = "GRADE_B",
        clinical_context: str | None = None,
        event_timestamp: datetime | None = None,
        auto_verify: bool = True,
    ) -> Evidence:
        """
        Add evidence with automatic quality grading and deterministic provenance verification.

        Agent-friendly API:
        - Just provide natural language content and optional raw snippet
        - System handles Oxford CEBM grading and cryptographic hash
        - System anchors provenance against raw data files on disk

        Args:
            content: Natural language evidence description
            evidence_type: DOCUMENT/OBSERVATION/LAB_RESULT/etc.
            source_document: File path or record ID
            source_location: Location within document (e.g., "Line 42")
            raw_snippet: Exact verbatim quote from the raw document
            content_hash: Optional SHA-256 digest
            extraction_method: Extraction method (e.g., "verbatim_quote", "table_cell")
            collected_by: Who collected this evidence
            clinical_strength: STRONG/MODERATE/WEAK/ANECDOTAL
            source_reliability: GRADE_A/GRADE_B/GRADE_C/GRADE_D
            clinical_context: Clinical context (e.g., "Post-op Day 1")
            event_timestamp: When the clinical event occurred
            auto_verify: Whether to automatically verify against file on disk

        Returns:
            Evidence entity with auto-generated ID and verification status
        """
        # Create quality grading
        quality = EvidenceQuality(
            strength=EvidenceStrength.from_str(clinical_strength),
            reliability=EvidenceReliability.from_str(source_reliability),
        )

        # Compute content hash if snippet provided
        computed_hash = content_hash
        if raw_snippet and not computed_hash:
            digest = hashlib.sha256(raw_snippet.strip().encode("utf-8")).hexdigest()
            computed_hash = f"sha256:{digest}"

        # Create source provenance
        source = EvidenceSource(
            document_id=source_document,
            location=source_location,
            raw_snippet=raw_snippet,
            content_hash=computed_hash,
            extraction_method=extraction_method,
            collected_by=collected_by,
            source_system=None,
        )

        # Create base evidence
        evidence = Evidence(
            content=content,
            evidence_type=EvidenceType.from_str(evidence_type),
            clinical_context=clinical_context,
            quality=quality,
            source=source,
            event_timestamp=event_timestamp,
            verified=False,
            verifier=None,
            verification_method=None,
            matched_lines=[],
            verification_timestamp=None,
        )

        # Deterministic provenance verification against raw files
        if auto_verify and source_document:
            match = self._provenance_verifier.verify_provenance(
                document_id=source_document,
                raw_snippet=raw_snippet,
                location=source_location,
                content=content,
            )
            if match.is_verified:
                evidence = evidence.mark_verified(
                    verifier="SYSTEM_PROVENANCE_VERIFIER",
                    verification_method=match.match_type,
                    matched_lines=list(match.line_numbers),
                    content_hash=match.snippet_hash,
                )

        # Store evidence
        self.evidence_store[evidence.id.value] = evidence

        # Record reasoning step
        self._add_reasoning_step(
            step_type=ReasoningStepType.OBSERVATION,
            content=f"Added evidence: {content[:100]}",
            rationale=(
                f"Evidence type: {evidence_type}, "
                f"Quality: {clinical_strength}/{source_reliability}, "
                f"Verified: {evidence.verified} ({evidence.verification_method or 'UNVERIFIED'})"
            ),
            evidence_ids=[evidence.id.value],
            confidence=quality.overall_score,
        )

        return evidence

    def propose_hypothesis(
        self,
        diagnosis: str,
        icd10_code: str | None = None,
        snomed_code: str | None = None,
        prior_probability: float = 0.1,
        rationale: str = "",
        inclusion_criteria: list[str] | None = None,
        exclusion_criteria: list[str] | None = None,
        created_by: str = "agent",
    ) -> Hypothesis:
        """
        Propose a differential diagnosis hypothesis.

        Agent-friendly API:
        - Just provide diagnosis name and rationale
        - System handles Bayesian setup
        - System validates clinical concept coding

        Args:
            diagnosis: Diagnosis name (e.g., "Acute myocardial infarction")
            icd10_code: ICD-10 code (optional, e.g., "I21.9")
            snomed_code: SNOMED CT code (optional)
            prior_probability: Prior probability P(H) before evidence (0-1)
            rationale: Why this hypothesis is being considered
            inclusion_criteria: Criteria that support this diagnosis
            exclusion_criteria: Criteria that rule out this diagnosis
            created_by: Who proposed this hypothesis

        Returns:
            Hypothesis entity with auto-generated ID
        """
        # Create clinical concept
        if icd10_code:
            concept = ClinicalConcept(
                code=icd10_code,
                display=diagnosis,
                system=CodingSystem.ICD_10,
                version=None,
            )
        elif snomed_code:
            concept = ClinicalConcept(
                code=snomed_code,
                display=diagnosis,
                system=CodingSystem.SNOMED_CT,
                version=None,
            )
        else:
            # No standard code provided, use custom
            normalized_diagnosis = " ".join(diagnosis.split()).casefold()
            digest = hashlib.sha256(normalized_diagnosis.encode()).hexdigest()
            concept = ClinicalConcept(
                code=f"CUSTOM-{digest[:12].upper()}",
                display=diagnosis,
                system=CodingSystem.CUSTOM,
                version=None,
            )

        # Create hypothesis
        hypothesis = Hypothesis(
            diagnosis=concept,
            prior_probability=prior_probability,
            current_probability=prior_probability,
            inclusion_criteria=inclusion_criteria or [],
            exclusion_criteria=exclusion_criteria or [],
            created_by=created_by,
            clinical_rationale=rationale
            or f"Considering {diagnosis} based on clinical presentation",
        )

        # Store hypothesis
        self.hypothesis_store[hypothesis.id.value] = hypothesis

        # Record reasoning step
        self._add_reasoning_step(
            step_type=ReasoningStepType.HYPOTHESIS_GENERATION,
            content=f"Proposed hypothesis: {diagnosis}",
            rationale=rationale or "Initial differential diagnosis",
            hypothesis_ids=[hypothesis.id.value],
            confidence=prior_probability,
        )

        return hypothesis

    def link_evidence_to_hypothesis(
        self,
        evidence_id: str,
        hypothesis_id: str,
        likelihood_ratio: float = 1.0,
        supports: bool = True,
        rationale: str = "",
        updated_by: str = "agent",
    ) -> Hypothesis:
        """
        Link evidence to hypothesis with Bayesian updating.

        Agent-friendly API:
        - Just provide evidence_id, hypothesis_id, and LR
        - System performs Bayesian calculation
        - System tracks audit trail

        Args:
            evidence_id: Evidence ID (e.g., "EVD-abc123")
            hypothesis_id: Hypothesis ID (e.g., "HYP-def456")
            likelihood_ratio: LR+ if supports=True, LR- if supports=False
            supports: True if evidence supports hypothesis, False if contradicts
            rationale: Clinical justification for this LR
            updated_by: Who performed this update

        Returns:
            Updated Hypothesis with new posterior probability

        Raises:
            KeyError: If evidence or hypothesis not found
        """
        # Retrieve entities
        evidence = self.evidence_store.get(evidence_id)
        if not evidence:
            raise KeyError(f"Evidence {evidence_id} not found")

        hypothesis = self.hypothesis_store.get(hypothesis_id)
        if not hypothesis:
            raise KeyError(f"Hypothesis {hypothesis_id} not found")

        # Perform Bayesian update
        updated_hypothesis = hypothesis.bayesian_update(
            evidence_id=evidence_id,
            likelihood_ratio=likelihood_ratio,
            updated_by=updated_by,
            supports=supports,
        )

        # Add likelihood ratio metadata
        updated_hypothesis = updated_hypothesis.add_likelihood_ratio(
            evidence_id=evidence_id,
            lr_positive=likelihood_ratio if supports else 1.0 / likelihood_ratio,
            lr_negative=1.0 / likelihood_ratio if supports else likelihood_ratio,
            rationale=rationale or "No rationale provided",
        )

        # Update store
        self.hypothesis_store[hypothesis_id] = updated_hypothesis

        # Link evidence to hypothesis
        updated_evidence = evidence.link_to_hypothesis(hypothesis_id, supports=supports)
        self.evidence_store[evidence_id] = updated_evidence

        # Record reasoning step
        self._add_reasoning_step(
            step_type=ReasoningStepType.BAYESIAN_UPDATE,
            content=f"Updated hypothesis '{updated_hypothesis.diagnosis.display}' with evidence",
            rationale=rationale or f"LR={likelihood_ratio:.2f}, supports={supports}",
            evidence_ids=[evidence_id],
            hypothesis_ids=[hypothesis_id],
            confidence=updated_hypothesis.current_probability,
        )

        return updated_hypothesis

    def get_differential_diagnosis(
        self,
        status_filter: HypothesisStatus | None = HypothesisStatus.ACTIVE,
        min_probability: float = 0.01,
    ) -> list[Hypothesis]:
        """
        Get ranked differential diagnosis tree.

        Args:
            status_filter: Filter by hypothesis status (default: ACTIVE)
            min_probability: Minimum probability threshold (default: 0.01)

        Returns:
            List of hypotheses sorted by current_probability (descending)
        """
        hypotheses = list(self.hypothesis_store.values())

        # Filter by status
        if status_filter:
            hypotheses = [h for h in hypotheses if h.status == status_filter]

        # Filter by minimum probability
        hypotheses = [h for h in hypotheses if h.current_probability >= min_probability]

        # Sort by probability (descending)
        hypotheses.sort(key=lambda h: h.current_probability, reverse=True)

        return hypotheses

    def exclude_hypothesis(
        self,
        hypothesis_id: str,
        *,
        excluded_by: str,
        reason: str,
    ) -> Hypothesis:
        """Exclude a hypothesis and record the decision in the audit chain."""
        hypothesis = self.hypothesis_store.get(hypothesis_id)
        if hypothesis is None:
            raise KeyError(f"Hypothesis {hypothesis_id} not found")

        excluded = hypothesis.mark_excluded(excluded_by=excluded_by, reason=reason)
        self.hypothesis_store[hypothesis_id] = excluded
        self._add_reasoning_step(
            step_type=ReasoningStepType.HYPOTHESIS_ELIMINATION,
            content=f"Excluded hypothesis: {excluded.diagnosis.display}",
            rationale=reason,
            hypothesis_ids=[hypothesis_id],
            confidence=excluded.current_probability,
            agent_id=excluded_by,
        )
        return excluded

    def get_reasoning_chain(self) -> ReasoningChain:
        """Get complete reasoning chain with audit trail."""
        return self.reasoning_chain

    def get_evidence(self, evidence_id: str) -> Evidence | None:
        """Get evidence by ID."""
        return self.evidence_store.get(evidence_id)

    def verify_evidence(
        self,
        evidence_id: str,
        verified_by: str = "agent",
        raw_snippet: str | None = None,
        document_id: str | None = None,
    ) -> tuple[Evidence, ProvenanceMatch | None]:
        """
        Verify evidence against physical files or mark with reviewer audit.

        Args:
            evidence_id: ID of evidence to verify
            verified_by: Person or system recording verification
            raw_snippet: Optional verbatim quote to verify on disk
            document_id: Optional document ID override

        Returns:
            Tuple of (Updated Evidence, Optional ProvenanceMatch)
        """
        evidence = self.evidence_store.get(evidence_id)
        if not evidence:
            raise KeyError(f"Evidence {evidence_id} not found")

        target_doc = document_id or evidence.source.document_id
        target_snippet = raw_snippet or evidence.source.raw_snippet

        match: ProvenanceMatch | None = None
        if target_doc:
            match = self._provenance_verifier.verify_provenance(
                document_id=target_doc,
                raw_snippet=target_snippet,
                location=evidence.source.location,
                content=evidence.content,
            )
            if match.is_verified:
                verified_evidence = evidence.mark_verified(
                    verifier=verified_by or "SYSTEM_PROVENANCE_VERIFIER",
                    verification_method=match.match_type,
                    matched_lines=list(match.line_numbers),
                    content_hash=match.snippet_hash,
                )
            else:
                verified_evidence = evidence.mark_verified(
                    verifier=verified_by,
                    verification_method="MANUAL_REVIEWER_UNVERIFIED_FILE",
                )
        else:
            verified_evidence = evidence.mark_verified(
                verifier=verified_by,
                verification_method="MANUAL_REVIEWER",
            )

        self.evidence_store[evidence_id] = verified_evidence
        return verified_evidence, match

    def get_guidance(self) -> ReasoningGuidance:
        """
        Get actionable multi-loop reasoning guidance and completeness checklist.

        Returns:
            ReasoningGuidance value object with current stage and next recommended tools.
        """
        return ClinicalGuidanceService.evaluate(
            session_id=self.session_id,
            evidence_store=self.evidence_store,
            hypothesis_store=self.hypothesis_store,
            thinking_chain=self.thinking_chain,
            reasoning_chain=self.reasoning_chain,
        )

    def get_hypothesis(self, hypothesis_id: str) -> Hypothesis | None:
        """Get hypothesis by ID."""
        return self.hypothesis_store.get(hypothesis_id)

    def get_evidence_for_hypothesis(self, hypothesis_id: str) -> list[Evidence]:
        """Get all evidence linked to a hypothesis."""
        return [
            e
            for e in self.evidence_store.values()
            if hypothesis_id in e.supports_hypothesis_ids
        ]

    def get_summary_statistics(self) -> dict[str, Any]:
        """
        Get summary statistics for the reasoning session.

        Returns:
            Dictionary with counts and quality metrics
        """
        metrics = self.reasoning_chain.get_quality_metrics()

        return {
            "session_id": self.session_id,
            "total_evidence": len(self.evidence_store),
            "total_hypotheses": len(self.hypothesis_store),
            "active_hypotheses": len(
                [
                    h
                    for h in self.hypothesis_store.values()
                    if h.status == HypothesisStatus.ACTIVE
                ]
            ),
            "reasoning_steps": metrics["total_steps"],
            "avg_confidence": metrics["avg_confidence"],
            "hypothesis_coverage": metrics["hypothesis_coverage"],
            "evidence_coverage": metrics["evidence_coverage"],
        }

    def _add_reasoning_step(
        self,
        step_type: ReasoningStepType,
        content: str,
        rationale: str,
        evidence_ids: list[str] | None = None,
        hypothesis_ids: list[str] | None = None,
        confidence: float | None = None,
        agent_id: str = "orchestrator",
    ) -> None:
        """Internal method to add reasoning step."""
        self._step_counter += 1

        step = ReasoningStep(
            sequence_number=self._step_counter,
            step_type=step_type,
            content=content,
            rationale=rationale,
            agent_id=agent_id,
            agent_model=None,
            evidence_ids=evidence_ids or [],
            hypothesis_ids=hypothesis_ids or [],
            cause_ids=[],
            confidence=confidence,
            tokens_used=None,
            chain_of_thought=None,
        )

        self.reasoning_chain.add_step(step)
