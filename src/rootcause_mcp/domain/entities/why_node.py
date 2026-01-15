"""
Why Node Entity.

Represents a node in the 5-Why analysis tree.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Self

from rootcause_mcp.domain.value_objects.identifiers import CauseId, SessionId
from rootcause_mcp.domain.value_objects.scores import ConfidenceScore


@dataclass
class WhyNode:
    """
    A node in the 5-Why analysis tree.

    Each node represents an answer to "Why?" and can have child nodes
    for deeper analysis.
    """

    # Identity
    id: CauseId
    session_id: SessionId

    # Content
    question: str  # The "Why?" question
    answer: str  # The answer (cause)

    # Hierarchy
    level: int  # 1-5 (first why, second why, etc.)
    parent_id: CauseId | None = None

    # Evidence & Confidence
    evidence: list[str] = field(default_factory=list)
    confidence: ConfidenceScore | None = None

    # Status
    is_root_cause: bool = False  # True if this is identified as a root cause
    needs_further_analysis: bool = True  # True if more "why" questions needed
    is_proximate: bool = False  # True if this is a proximate (direct) cause (Level 1-2)

    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        """Validate WhyNode data."""
        if self.level < 1 or self.level > 5:
            raise ValueError(f"Why level must be 1-5, got: {self.level}")

    # === Evidence Management ===

    def add_evidence(self, evidence: str) -> None:
        """Add supporting evidence."""
        if evidence not in self.evidence:
            self.evidence.append(evidence)
            self._touch()

    # === Root Cause Identification ===

    def mark_as_root_cause(self, confidence: float = 0.8) -> None:
        """Mark this node as a root cause."""
        self.is_root_cause = True
        self.needs_further_analysis = False
        self.confidence = ConfidenceScore(confidence)
        self._touch()

    def mark_needs_analysis(self) -> None:
        """Mark that this node needs further "why" analysis."""
        self.is_root_cause = False
        self.needs_further_analysis = True
        self._touch()

    # === Queries ===

    @property
    def is_first_why(self) -> bool:
        """Check if this is the first level why."""
        return self.level == 1

    @property
    def is_final_why(self) -> bool:
        """Check if this is the fifth (final) level why."""
        return self.level == 5

    @property
    def can_ask_why(self) -> bool:
        """Check if we can ask another "why" for this node."""
        return self.level < 5 and self.needs_further_analysis and not self.is_root_cause

    @property
    def confidence_level(self) -> str:
        """Get confidence level as string."""
        if self.confidence:
            return self.confidence.to_level()
        return "unknown"

    # === Private Methods ===

    def _touch(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.now(timezone.utc)

    # === Factory Methods ===

    @classmethod
    def create_first_why(
        cls,
        session_id: SessionId,
        initial_problem: str,
        answer: str,
    ) -> Self:
        """Create the first "Why?" node.
        
        The first Why is typically a proximate (direct) cause - the immediate
        action/error that directly led to the incident (HFACS Level 1-2).
        """
        return cls(
            id=CauseId.generate(),
            session_id=session_id,
            question=f"Why did {initial_problem} occur?",
            answer=answer,
            level=1,
            parent_id=None,
            is_proximate=True,  # First why is typically a proximate cause
        )

    @classmethod
    def create_follow_up_why(
        cls,
        session_id: SessionId,
        parent: "WhyNode",
        answer: str,
    ) -> Self:
        """Create a follow-up "Why?" node based on parent's answer."""
        if not parent.can_ask_why:
            raise ValueError("Cannot create more why questions for this node")

        return cls(
            id=CauseId.generate(),
            session_id=session_id,
            question=f"Why did '{parent.answer}' happen?",
            answer=answer,
            level=parent.level + 1,
            parent_id=parent.id,
        )


@dataclass
class WhyChain:
    """
    A complete 5-Why analysis chain.

    Represents a sequence of Why questions from initial problem to root cause.
    """

    session_id: SessionId
    initial_problem: str
    nodes: list[WhyNode] = field(default_factory=list)

    def add_node(self, node: WhyNode) -> None:
        """Add a node to the chain."""
        self.nodes.append(node)

    @property
    def depth(self) -> int:
        """Get the current depth of the analysis."""
        if not self.nodes:
            return 0
        return max(node.level for node in self.nodes)

    @property
    def root_causes(self) -> list[WhyNode]:
        """Get all identified root causes."""
        return [node for node in self.nodes if node.is_root_cause]

    @property
    def needs_analysis(self) -> list[WhyNode]:
        """Get nodes that need further analysis."""
        return [node for node in self.nodes if node.needs_further_analysis]

    @property
    def is_complete(self) -> bool:
        """Check if analysis is complete (all branches reach root cause or level 5)."""
        if not self.nodes:
            return False
        return len(self.needs_analysis) == 0

    def get_node(self, node_id: CauseId) -> WhyNode | None:
        """Get a node by ID."""
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None

    def get_chain_to_root(self, root_node: WhyNode) -> list[WhyNode]:
        """Get the chain of nodes from first why to a specific root cause."""
        if not root_node.is_root_cause:
            raise ValueError("Node is not a root cause")

        chain: list[WhyNode] = [root_node]
        current = root_node

        while current.parent_id:
            parent = self.get_node(current.parent_id)
            if parent:
                chain.insert(0, parent)
                current = parent
            else:
                break

        return chain

    def to_dict(self) -> dict[str, object]:
        """Export WhyChain to dictionary format."""
        return {
            "initial_problem": self.initial_problem,
            "depth": self.depth,
            "is_complete": self.is_complete,
            "nodes": [
                {
                    "id": str(node.id),
                    "level": node.level,
                    "question": node.question,
                    "answer": node.answer,
                    "is_root_cause": node.is_root_cause,
                    "is_proximate": node.is_proximate,
                    "evidence": node.evidence,
                    "parent_id": str(node.parent_id) if node.parent_id else None,
                }
                for node in self.nodes
            ],
            "root_causes": [str(node.id) for node in self.root_causes],
        }
