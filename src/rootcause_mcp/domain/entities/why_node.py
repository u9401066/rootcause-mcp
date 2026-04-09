"""
Why Node Entity.

Represents a node in the 5-Why analysis tree.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Self

from rootcause_mcp.domain.value_objects.enums import CausalLinkType, TeachingLevel
from rootcause_mcp.domain.value_objects.identifiers import CauseId, SessionId
from rootcause_mcp.domain.value_objects.scores import ConfidenceScore


@dataclass(frozen=True, slots=True)
class CausalLink:
    """Directed causal relationship between two Why nodes."""

    source_id: CauseId
    target_id: CauseId
    relationship: CausalLinkType = CausalLinkType.CONTRIBUTES_TO
    strength: float = 0.5
    evidence: tuple[str, ...] = ()
    note: str = ""
    bidirectional: bool = False

    def __post_init__(self) -> None:
        """Validate link fields."""
        if self.source_id == self.target_id:
            raise ValueError("Causal link must connect two different nodes")
        if not 0.0 <= self.strength <= 1.0:
            raise ValueError(
                f"Causal link strength must be 0.0-1.0, got: {self.strength}"
            )

    def to_dict(self) -> dict[str, object]:
        """Export CausalLink to dictionary format."""
        return {
            "source_id": str(self.source_id),
            "target_id": str(self.target_id),
            "relationship": self.relationship.value,
            "strength": self.strength,
            "evidence": list(self.evidence),
            "note": self.note,
            "bidirectional": self.bidirectional,
        }


@dataclass(frozen=True, slots=True)
class FeedbackLoop:
    """Closed causal feedback loop discovered in the Why chain."""

    node_ids: tuple[CauseId, ...]
    summary: str

    def to_dict(self) -> dict[str, object]:
        """Export FeedbackLoop to dictionary format."""
        return {
            "node_ids": [str(node_id) for node_id in self.node_ids],
            "summary": self.summary,
        }


@dataclass(frozen=True, slots=True)
class TeachingCase:
    """Lesson-plan artifact generated from an RCA chain."""

    learner_level: TeachingLevel
    case_summary: str
    learning_objectives: tuple[str, ...]
    teaching_flow: tuple[str, ...]
    discussion_questions: tuple[str, ...]
    clinical_pearls: tuple[str, ...]
    common_pitfalls: tuple[str, ...]
    feedback_loops: tuple[str, ...]
    reverse_causality_prompts: tuple[str, ...]
    source_node_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        """Export TeachingCase to dictionary format."""
        return {
            "learner_level": self.learner_level.value,
            "case_summary": self.case_summary,
            "learning_objectives": list(self.learning_objectives),
            "teaching_flow": list(self.teaching_flow),
            "discussion_questions": list(self.discussion_questions),
            "clinical_pearls": list(self.clinical_pearls),
            "common_pitfalls": list(self.common_pitfalls),
            "feedback_loops": list(self.feedback_loops),
            "reverse_causality_prompts": list(self.reverse_causality_prompts),
            "source_node_ids": list(self.source_node_ids),
        }


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
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

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
        self.updated_at = datetime.now(UTC)

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
        parent: WhyNode,
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
    causal_links: list[CausalLink] = field(default_factory=list)

    def add_node(self, node: WhyNode) -> None:
        """Add a node to the chain."""
        self.nodes.append(node)

    def add_causal_link(self, link: CausalLink) -> None:
        """Add a directed or bidirectional causal link between existing nodes."""
        existing_node_ids = {str(node.id) for node in self.nodes}
        if str(link.source_id) not in existing_node_ids:
            raise ValueError(f"Source node not found: {link.source_id}")
        if str(link.target_id) not in existing_node_ids:
            raise ValueError(f"Target node not found: {link.target_id}")
        if link not in self.causal_links:
            self.causal_links.append(link)

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

    def detect_feedback_loops(self) -> list[FeedbackLoop]:
        """Detect feedback loops created by parent-child flow and causal links."""
        adjacency: dict[str, set[str]] = {str(node.id): set() for node in self.nodes}
        for node in self.nodes:
            if node.parent_id is not None:
                adjacency.setdefault(str(node.parent_id), set()).add(str(node.id))

        for link in self.causal_links:
            adjacency.setdefault(str(link.source_id), set()).add(str(link.target_id))
            if link.bidirectional:
                adjacency.setdefault(str(link.target_id), set()).add(
                    str(link.source_id)
                )

        if not adjacency:
            return []

        node_index = {str(node.id): node for node in self.nodes}
        discovered: dict[tuple[str, ...], FeedbackLoop] = {}

        def canonicalize(cycle: list[str]) -> tuple[str, ...]:
            rotations = [
                tuple(cycle[idx:] + cycle[:idx]) for idx in range(len(cycle))
            ]
            reverse = list(reversed(cycle))
            rotations.extend(
                tuple(reverse[idx:] + reverse[:idx]) for idx in range(len(reverse))
            )
            return min(rotations)

        def dfs(start: str, current: str, path: list[str]) -> None:
            for neighbor in adjacency.get(current, set()):
                if neighbor == start and len(path) > 1:
                    signature = canonicalize(path)
                    if signature not in discovered:
                        summary = " -> ".join(
                            node_index[node_id].answer for node_id in path
                        )
                        discovered[signature] = FeedbackLoop(
                            node_ids=tuple(
                                CauseId.from_string(node_id) for node_id in path
                            ),
                            summary=summary,
                        )
                    continue
                if neighbor in path:
                    continue
                dfs(start, neighbor, [*path, neighbor])

        for start_node in adjacency:
            dfs(start_node, start_node, [start_node])

        return list(discovered.values())

    def build_teaching_case(
        self,
        learner_level: TeachingLevel = TeachingLevel.MEDICAL_STUDENT,
    ) -> TeachingCase:
        """Transform RCA output into a learner-ready teaching case."""
        if not self.nodes:
            raise ValueError("Cannot build teaching case from an empty WhyChain")

        proximate_nodes = [
            node for node in self.nodes if node.level == 1
        ] or [self.nodes[0]]
        root_nodes = self.root_causes or [
            node for node in self.nodes if node.level == self.depth
        ]
        feedback_loops = self.detect_feedback_loops()

        learner_verbs = {
            TeachingLevel.MEDICAL_STUDENT: "辨識",
            TeachingLevel.INTERN: "初步整合",
            TeachingLevel.RESIDENT: "整合並優先排序",
            TeachingLevel.FELLOW: "設計並指導",
        }
        learner_focus = learner_verbs[learner_level]

        first_proximate = proximate_nodes[0].answer
        first_root = root_nodes[0].answer
        case_summary = (
            f"{self.initial_problem}. Case starts from proximate factor "
            f"'{first_proximate}' and traces deeper cause '{first_root}' "
            "for causal-chain and systems-thinking teaching."
        )

        learning_objectives = (
            f"{learner_focus}個案中的近端原因, 系統根因與中間機制.",
            (
                f"{learner_focus}造成事件惡化的回饋迴圈: "
                f"{feedback_loops[0].summary}."
                if feedback_loops
                else f"{learner_focus}哪些節點可能形成尚未明說的雙向因果循環."
            ),
            f"{learner_focus}可中斷事件進展的介入點, 並轉成可教學的臨床行動.",
        )

        teaching_flow = (
            (
                f"Case trigger: 先呈現問題 '{self.initial_problem}' 與第一個表象原因 "
                f"'{first_proximate}'."
            ),
            "Causal unpacking: 依 Why 1 -> Why N 逐層追問, 要求學員說出每一層機制.",
            (
                "Loop analysis: 標記互相強化的節點, 討論如何打斷惡性循環."
                if feedback_loops
                else "Loop analysis: 要求學員主動提出可能的惡性循環與漏掉的系統因素."
            ),
            (
                "Action translation: 把根因轉成 bedside decision, "
                "team communication 與 system redesign."
            ),
        )

        clinical_pearls = tuple(
            f"Why {node.level}: {node.answer}" for node in root_nodes[:3]
        ) or (first_root,)
        common_pitfalls = (
            f"只停留在表象原因: {first_proximate}",
            *(
                f"忽略回饋迴圈: {loop.summary}" for loop in feedback_loops[:2]
            ),
            "沒有把根因轉譯成可觀察的臨床徵象, 決策點與復盤問題.",
        )

        discussion_questions = (
            "這個案例的第一個『看起來合理但不夠深』的解釋是什麼?",
            "哪一個節點最值得最早介入, 才能阻斷後續因果鏈?",
            "如果你要把這個案例教給下一屆醫學生, 最想保留哪三個 decision points?",
        )

        reverse_causality_prompts = tuple(
            (
                f"若教學目標是避免再次發生『{root.answer}』, "
                "學生應先倒推出哪些前驅徵象與流程漏洞?"
            )
            for root in root_nodes[:2]
        ) or (
            (
                f"若教學目標是避免再次發生『{first_root}』, "
                "學生應先倒推出哪些前驅徵象與流程漏洞?"
            ),
        )

        return TeachingCase(
            learner_level=learner_level,
            case_summary=case_summary,
            learning_objectives=learning_objectives,
            teaching_flow=teaching_flow,
            discussion_questions=discussion_questions,
            clinical_pearls=tuple(clinical_pearls),
            common_pitfalls=tuple(common_pitfalls),
            feedback_loops=tuple(loop.summary for loop in feedback_loops),
            reverse_causality_prompts=reverse_causality_prompts,
            source_node_ids=tuple(str(node.id) for node in root_nodes),
        )

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
            "causal_links": [link.to_dict() for link in self.causal_links],
            "feedback_loops": [loop.to_dict() for loop in self.detect_feedback_loops()],
        }
