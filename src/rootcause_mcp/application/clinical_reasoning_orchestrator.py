"""
Clinical Reasoning Orchestrator.

Agent-friendly API that hides medical complexity behind simple operations.
This is the core harness for recording a consistent, auditable reasoning workflow.
"""

from __future__ import annotations

import hashlib
import os
from datetime import datetime
from typing import Any, cast

from rootcause_mcp.domain.entities.evidence import (
    Evidence,
    EvidenceSource,
    EvidenceType,
)
from rootcause_mcp.domain.entities.hypothesis import (
    DiagnosticCertainty,
    DiagnosticReasoningBasis,
    DiagnosticRole,
    Hypothesis,
    HypothesisStatus,
    LikelihoodRatioCalibrationStatus,
    MechanismCategory,
    PlannedDiagnosticTest,
)
from rootcause_mcp.domain.entities.reasoning_step import (
    ReasoningChain,
    ReasoningStep,
    ReasoningStepType,
)
from rootcause_mcp.domain.entities.thinking_step import (
    ThinkingChain,
    ThinkingStep,
    ThinkingType,
)
from rootcause_mcp.domain.services.guidance_service import ClinicalGuidanceService
from rootcause_mcp.domain.services.provenance_verifier import (
    ProvenanceMatch,
    ProvenanceVerifier,
)
from rootcause_mcp.domain.value_objects.clinical_concept import (
    ClinicalConcept,
    CodingSystem,
)
from rootcause_mcp.domain.value_objects.clinical_temporal import (
    ClinicalTemporal,
    resolve_clinical_temporal,
)
from rootcause_mcp.domain.value_objects.differential_breadth import (
    BreadthCellStatus,
    DifferentialBreadthAudit,
)
from rootcause_mcp.domain.value_objects.evidence_quality import (
    EvidenceQuality,
    EvidenceReliability,
    EvidenceStrength,
)
from rootcause_mcp.domain.value_objects.identifiers import HypothesisId
from rootcause_mcp.domain.value_objects.leading_hypothesis import (
    LeadingHypothesisSelection,
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
        initial_problem: str | None = None,
    ) -> None:
        """
        Initialize orchestrator for a clinical session.

        Args:
            session_id: RCA session ID
            initial_problem: Optional initial chief complaint or clinical event summary
        """
        self.session_id = session_id
        self.initial_problem = initial_problem
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
        temporal: ClinicalTemporal | dict[str, Any] | None = None,
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
            temporal: Typed instant/date/range/relative/unknown source time. Only
                an aware instant also populates legacy ``event_timestamp``.
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
        resolved_temporal = resolve_clinical_temporal(temporal, event_timestamp)
        evidence = Evidence(
            content=content,
            evidence_type=EvidenceType.from_str(evidence_type),
            clinical_context=clinical_context,
            quality=quality,
            source=source,
            temporal=resolved_temporal,
            event_timestamp=resolved_temporal.source_aware_instant,
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
        prior_probability: float = 0.5,
        rationale: str = "",
        inclusion_criteria: list[str] | None = None,
        exclusion_criteria: list[str] | None = None,
        must_not_miss: bool = False,
        mechanism_category: MechanismCategory | str = MechanismCategory.UNKNOWN,
        diagnostic_role: DiagnosticRole | str = DiagnosticRole.UNKNOWN,
        certainty: DiagnosticCertainty | str = DiagnosticCertainty.UNKNOWN,
        reasoning_basis: DiagnosticReasoningBasis | str = (
            DiagnosticReasoningBasis.UNKNOWN
        ),
        alternatives_considered: list[dict[str, Any]] | None = None,
        uncertainty_factors: list[str] | None = None,
        confidence_rationale: str = "",
        planned_tests: list[dict[str, Any]] | None = None,
        created_by: str = "agent",
    ) -> Hypothesis:
        """
        Propose a differential diagnosis hypothesis.

        Agent-friendly API:
        - Just provide diagnosis name and rationale
        - Omission uses a neutral 0.5 uncalibrated implementation baseline
        - System validates clinical concept coding

        Args:
            diagnosis: Diagnosis name (e.g., "Acute myocardial infarction")
            icd10_code: ICD-10 code (optional, e.g., "I21.9")
            snomed_code: SNOMED CT code (optional)
            prior_probability: Numeric Bayesian starting value (0-1); the 0.5
                default is an UNCALIBRATED implementation baseline, not a
                patient-specific clinical probability or certainty label
            rationale: Why this hypothesis is being considered
            inclusion_criteria: Criteria that support this diagnosis
            exclusion_criteria: Criteria that rule out this diagnosis
            must_not_miss: Explicitly reviewed high-harm rule-out marker
            mechanism_category: Broad etiologic mechanism used for DDx breadth
            diagnostic_role: Role of the candidate in the clinical explanation
            certainty: Explicit qualitative certainty; never inferred from probability
            reasoning_basis: Observed/documented diagnosis, mechanism inference, or unknown
            alternatives_considered: Deprecated context-only alternative notes;
                propose each plausible diagnosis separately and persist a breadth audit
            uncertainty_factors: Known uncertainty retained with the hypothesis
            confidence_rationale: Why the candidate is considered plus calibration
                and source limitations of any supplied numeric starting value
            planned_tests: Typed tests planned or ordered to challenge this hypothesis
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

        hypothesis_id = HypothesisId.generate()
        bound_planned_tests: list[PlannedDiagnosticTest] = []
        for planned_test in planned_tests or []:
            payload = dict(planned_test)
            supplied_target = payload.pop("target_hypothesis_id", None)
            if supplied_target not in {None, "SELF", hypothesis_id.value}:
                raise ValueError(
                    "planned test target_hypothesis_id must be omitted or SELF when "
                    "proposing a new hypothesis"
                )
            payload["target_hypothesis_id"] = hypothesis_id.value
            bound_planned_tests.append(PlannedDiagnosticTest.model_validate(payload))

        # Create hypothesis
        hypothesis = Hypothesis(
            id=hypothesis_id,
            diagnosis=concept,
            prior_probability=prior_probability,
            current_probability=prior_probability,
            inclusion_criteria=inclusion_criteria or [],
            exclusion_criteria=exclusion_criteria or [],
            must_not_miss=must_not_miss,
            mechanism_category=cast("MechanismCategory", mechanism_category),
            diagnostic_role=cast("DiagnosticRole", diagnostic_role),
            certainty=cast("DiagnosticCertainty", certainty),
            reasoning_basis=cast("DiagnosticReasoningBasis", reasoning_basis),
            alternatives_considered=alternatives_considered or [],
            uncertainty_factors=uncertainty_factors or [],
            confidence_rationale=confidence_rationale,
            planned_tests=bound_planned_tests,
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
            # The numeric prior is an uncalibrated compatibility value.  It must
            # never be copied into a field presented as clinical confidence.
            confidence=None,
        )

        return hypothesis

    def link_evidence_to_hypothesis(
        self,
        evidence_id: str,
        hypothesis_id: str,
        likelihood_ratio: float = 1.0,
        supports: bool | None = None,
        rationale: str = "",
        calibration_status: LikelihoodRatioCalibrationStatus | str | None = None,
        calibration_source_ref: str | None = None,
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
            calibration_status: Whether a quantitative source calibrates the LR;
                required even when the LR is neutral/quantitatively unknown
            calibration_source_ref: EVD-* reference to a verified literature
                calibration record in this session's evidence ledger
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

        if any(
            update.evidence_id == evidence_id for update in hypothesis.bayesian_history
        ):
            raise ValueError(
                f"Evidence {evidence_id} is already linked to hypothesis "
                f"{hypothesis_id}; duplicate Bayesian updates are not allowed"
            )

        if calibration_status is None:
            raise ValueError(
                "calibration_status is required; migrate links to "
                "SOURCE_CALIBRATED with a verifiable reference or "
                "QUANTITATIVELY_UNKNOWN with likelihood_ratio=1.0"
            )
        try:
            typed_calibration_status = LikelihoodRatioCalibrationStatus(
                calibration_status
            )
        except ValueError as exc:
            raise ValueError(
                f"Unsupported calibration_status: {calibration_status}"
            ) from exc

        if (
            typed_calibration_status
            is LikelihoodRatioCalibrationStatus.SOURCE_CALIBRATED
        ):
            calibration_evidence = self.evidence_store.get(
                str(calibration_source_ref or "").strip()
            )
            if not self._is_admissible_lr_calibration_evidence(calibration_evidence):
                raise ValueError(
                    "SOURCE_CALIBRATED requires calibration_source_ref to identify "
                    "a verified LITERATURE evidence record with an exact source "
                    "snippet, document location, extraction method, and content hash"
                )
            if (
                not evidence.verified
                or evidence.evidence_type is EvidenceType.LITERATURE
                or evidence_id == calibration_source_ref
            ):
                raise ValueError(
                    "A non-neutral LR requires distinct verified case evidence as "
                    "the relationship target; LITERATURE calibration evidence cannot "
                    "replace a patient/case observation"
                )

        # Validate the calibration record before applying any numeric update.
        calibrated_hypothesis = hypothesis.add_likelihood_ratio(
            evidence_id=evidence_id,
            lr_positive=likelihood_ratio if supports is True else None,
            lr_negative=likelihood_ratio if supports is False else None,
            rationale=rationale or "No rationale provided",
            calibration_status=typed_calibration_status,
            calibration_source_ref=calibration_source_ref,
            applied_likelihood_ratio=likelihood_ratio,
            supports=supports,
        )

        # Perform the Bayesian compatibility update only after admission succeeds.
        updated_hypothesis = calibrated_hypothesis.bayesian_update(
            evidence_id=evidence_id,
            likelihood_ratio=likelihood_ratio,
            updated_by=updated_by,
            supports=supports,
        )

        # Update store
        self.hypothesis_store[hypothesis_id] = updated_hypothesis

        # Link evidence to hypothesis
        updated_evidence = (
            evidence.link_to_hypothesis(hypothesis_id, supports=supports)
            if supports is not None
            else evidence
        )
        self.evidence_store[evidence_id] = updated_evidence

        # Record reasoning step
        self._add_reasoning_step(
            step_type=ReasoningStepType.BAYESIAN_UPDATE,
            content=f"Updated hypothesis '{updated_hypothesis.diagnosis.display}' with evidence",
            rationale=rationale or f"LR={likelihood_ratio:.2f}, supports={supports}",
            evidence_ids=[evidence_id],
            hypothesis_ids=[hypothesis_id],
            # Preserve the numeric update only in the Bayesian ledger.  The
            # reasoning audit must not present it as clinical confidence.
            confidence=None,
        )

        return updated_hypothesis

    @staticmethod
    def _is_admissible_lr_calibration_evidence(
        evidence: Evidence | None,
    ) -> bool:
        """Validate the local evidence-ledger side of an LR calibration link."""
        if evidence is None or evidence.evidence_type is not EvidenceType.LITERATURE:
            return False
        source = evidence.source
        content_hash = str(source.content_hash or "").removeprefix("sha256:")
        return bool(
            evidence.verified
            and str(evidence.verifier or "").strip()
            and str(evidence.verification_method or "").strip()
            in {
                "EXACT_SNIPPET_MATCH",
                "NORMALIZED_SNIPPET_MATCH",
                "MANUAL_REVIEWER_CONFIRMATION",
            }
            and str(source.document_id or "").strip()
            and str(source.location or "").strip()
            and str(source.raw_snippet or "").strip()
            and str(source.extraction_method or "").strip()
            and len(content_hash) == 64
            and all(character in "0123456789abcdefABCDEF" for character in content_hash)
        )

    def get_differential_diagnosis(
        self,
        status_filter: HypothesisStatus | None = HypothesisStatus.ACTIVE,
        min_probability: float = 0.01,
    ) -> list[Hypothesis]:
        """
        Get the differential diagnosis in stable working-ledger order.

        Args:
            status_filter: Filter by hypothesis status (default: ACTIVE)
            min_probability: Deprecated compatibility argument.  It is ignored
                because the stored numeric value is not a calibrated clinical
                probability and therefore cannot safely filter the DDx.

        Returns:
            Hypotheses in insertion order after the requested status filter
        """
        hypotheses = list(self.hypothesis_store.values())

        # Filter by status
        if status_filter:
            hypotheses = [h for h in hypotheses if h.status == status_filter]

        # Keep accepting the old argument so persisted harness calls remain
        # compatible, but never use an uncalibrated value to filter or rank.
        _ = min_probability

        return hypotheses

    def record_differential_breadth_audit(
        self,
        audit_payload: dict[str, Any],
    ) -> DifferentialBreadthAudit:
        """Persist one typed breadth audit inside the durable thinking ledger."""
        audit = DifferentialBreadthAudit.model_validate(audit_payload)
        for cell in audit.cells:
            if cell.status is not BreadthCellStatus.CANDIDATES_PRESENT:
                continue
            permitted_categories = set(cell.mechanism_categories)
            for hypothesis_id in cell.hypothesis_ids:
                hypothesis = self.hypothesis_store.get(hypothesis_id)
                if hypothesis is None:
                    raise ValueError(
                        f"breadth audit references unknown hypothesis {hypothesis_id}"
                    )
                if hypothesis.mechanism_category not in permitted_categories:
                    raise ValueError(
                        "breadth audit mechanism linkage mismatch for "
                        f"{hypothesis_id}: {hypothesis.mechanism_category.value}"
                    )

        self.thinking_chain.add_step(
            ThinkingStep(
                thinking_type=ThinkingType.BRANCH_EXPLORED,
                content=(
                    f"Recorded {audit.framework.value} differential breadth audit "
                    f"{audit.audit_id}"
                ),
                internal_reasoning=audit.framework_rationale,
                confidence=0.0,
                uncertainty_factors=[
                    unknown for cell in audit.cells for unknown in cell.unknowns
                ],
                related_hypothesis_ids=sorted(
                    {
                        hypothesis_id
                        for cell in audit.cells
                        for hypothesis_id in cell.hypothesis_ids
                    }
                ),
                structured_data={
                    "record_type": "DIFFERENTIAL_BREADTH_AUDIT",
                    "confidence_semantics": "NOT_CLINICAL_CERTAINTY",
                    "audit": audit.model_dump(mode="json"),
                },
            )
        )
        return audit

    def get_differential_breadth_audits(self) -> list[DifferentialBreadthAudit]:
        """Project the latest valid version of each persisted breadth audit."""
        audits_by_id: dict[str, DifferentialBreadthAudit] = {}
        for step in self.thinking_chain.steps:
            if step.structured_data.get("record_type") != (
                "DIFFERENTIAL_BREADTH_AUDIT"
            ):
                continue
            payload = step.structured_data.get("audit")
            if not isinstance(payload, dict):
                continue
            try:
                audit = DifferentialBreadthAudit.model_validate(payload)
            except ValueError:
                continue
            audits_by_id[audit.audit_id] = audit
        return list(audits_by_id.values())

    def select_leading_hypothesis(
        self,
        hypothesis_id: str,
        *,
        reason: str,
        changed_by: str,
    ) -> LeadingHypothesisSelection:
        """Select one eligible diagnosis explicitly and append immutable history."""
        hypothesis = self.hypothesis_store.get(hypothesis_id)
        if hypothesis is None:
            raise KeyError(f"Hypothesis {hypothesis_id} not found")
        if hypothesis.status in {HypothesisStatus.EXCLUDED, HypothesisStatus.ON_HOLD}:
            raise ValueError(
                "The leading hypothesis must be ACTIVE or CONFIRMED, not "
                f"{hypothesis.status.value}"
            )
        previous_hypothesis_id = self.get_leading_hypothesis_id()
        if previous_hypothesis_id == hypothesis_id:
            raise ValueError(
                f"Hypothesis {hypothesis_id} is already the explicit leading diagnosis"
            )
        selection = LeadingHypothesisSelection(
            hypothesis_id=hypothesis_id,
            previous_hypothesis_id=previous_hypothesis_id,
            reason=reason,
            changed_by=changed_by,
        )
        self.thinking_chain.add_step(
            ThinkingStep(
                timestamp=selection.changed_at,
                thinking_type=ThinkingType.DECISION_POINT,
                content=(
                    f"Selected {hypothesis.diagnosis.display} ({hypothesis_id}) "
                    "as the explicit leading diagnosis"
                ),
                internal_reasoning=selection.reason,
                confidence=None,
                related_hypothesis_ids=[hypothesis_id],
                structured_data={
                    "record_type": "LEADING_HYPOTHESIS_SELECTION",
                    "selection": selection.model_dump(mode="json"),
                },
            )
        )
        return selection

    def get_leading_hypothesis_selection_history(
        self,
    ) -> list[LeadingHypothesisSelection]:
        """Project valid leading selections from the durable thinking ledger."""
        selections: list[LeadingHypothesisSelection] = []
        for step in self.thinking_chain.steps:
            if step.structured_data.get("record_type") != (
                "LEADING_HYPOTHESIS_SELECTION"
            ):
                continue
            payload = step.structured_data.get("selection")
            if not isinstance(payload, dict):
                continue
            try:
                selection = LeadingHypothesisSelection.model_validate(payload)
            except ValueError:
                continue
            selections.append(selection)
        return selections

    def get_leading_hypothesis_id(self) -> str | None:
        """Return the latest explicit ID, never array order or numeric ranking."""
        history = self.get_leading_hypothesis_selection_history()
        return history[-1].hypothesis_id if history else None

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
            confidence=None,
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
        manual_confirmation: bool = False,
        expected_source_sha256: str | None = None,
        fail_closed: bool = False,
        provenance_verifier: ProvenanceVerifier | None = None,
    ) -> tuple[Evidence, ProvenanceMatch | None]:
        """
        Verify evidence against physical files or mark with reviewer audit.

        Args:
            evidence_id: ID of evidence to verify
            verified_by: Person or system recording verification
            raw_snippet: Optional verbatim quote to verify on disk
            document_id: Optional document ID override
            manual_confirmation: Explicit assertion that a qualified human
                independently checked the source when deterministic matching is
                unavailable
            expected_source_sha256: Whole-file digest pinned by a source manifest
            fail_closed: Revoke prior verification when manifest-bound physical
                verification fails
            provenance_verifier: Optional shared verifier used by a manifest-aware
                handler so URI resolution and snippet verification use identical roots

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
            verifier = provenance_verifier or self._provenance_verifier
            match = verifier.verify_provenance(
                document_id=target_doc,
                raw_snippet=target_snippet,
                location=evidence.source.location,
                content=evidence.content,
                expected_source_sha256=expected_source_sha256,
            )
            if match.is_verified:
                verified_evidence = evidence.mark_verified(
                    verifier=verified_by or "SYSTEM_PROVENANCE_VERIFIER",
                    verification_method=match.match_type,
                    matched_lines=list(match.line_numbers),
                    content_hash=match.snippet_hash,
                )
            elif (
                match.match_type != "SOURCE_HASH_MISMATCH"
                and manual_confirmation
                and self._is_authorized_human_reviewer(verified_by)
            ):
                verified_evidence = evidence.mark_verified(
                    verifier=verified_by,
                    verification_method="MANUAL_REVIEWER_CONFIRMATION",
                )
            elif fail_closed:
                verified_evidence = self.record_failed_provenance_verification(
                    evidence_id,
                    match,
                )
            else:
                verified_evidence = evidence
        elif manual_confirmation and self._is_authorized_human_reviewer(verified_by):
            verified_evidence = evidence.mark_verified(
                verifier=verified_by,
                verification_method="MANUAL_REVIEWER_CONFIRMATION",
            )
        else:
            verified_evidence = evidence

        self.evidence_store[evidence_id] = verified_evidence
        return verified_evidence, match

    def record_failed_provenance_verification(
        self,
        evidence_id: str,
        match: ProvenanceMatch,
    ) -> Evidence:
        """Persist an explicit unverified state for a manifest-bound failure."""
        evidence = self.evidence_store.get(evidence_id)
        if evidence is None:
            raise KeyError(f"Evidence {evidence_id} not found")
        unverified = evidence.model_copy(
            update={
                "verified": False,
                "verifier": None,
                "verification_method": match.match_type,
                "matched_lines": [],
                "verification_timestamp": None,
            }
        )
        self.evidence_store[evidence_id] = unverified
        return unverified

    @staticmethod
    def _is_authorized_human_reviewer(verified_by: str) -> bool:
        """Require an operator-controlled allowlist for manual verification."""
        normalized = verified_by.strip().casefold()
        authorized = {
            reviewer.strip().casefold()
            for reviewer in os.environ.get("ROOTCAUSE_AUTHORIZED_REVIEWERS", "").split(
                ","
            )
            if reviewer.strip()
        }
        return bool(normalized) and normalized in authorized

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
            leading_hypothesis_id=self.get_leading_hypothesis_id(),
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
