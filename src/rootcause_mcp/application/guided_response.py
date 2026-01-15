"""
Guided Response Builder.

Builds structured responses that guide the Agent through RCA process:
- Includes progress tracking
- Suggests next actions
- Provides "push" questions to deepen analysis
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from rootcause_mcp.application.session_progress import SessionProgress


@dataclass
class NextAction:
    """Describes the next recommended action."""
    
    required: bool = False
    tool: str = ""
    question: str = ""  # 逼問 - push question to deepen analysis
    hint: str = ""
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "required": self.required,
            "tool": self.tool,
            "question": self.question,
            "hint": self.hint,
        }


@dataclass 
class GuidedResponse:
    """Structured response with guidance for the Agent."""
    
    # Original result
    result: dict[str, Any] = field(default_factory=dict)
    
    # Session progress
    session_progress: dict[str, Any] = field(default_factory=dict)
    
    # Current analysis state
    current_state: dict[str, Any] = field(default_factory=dict)
    
    # Next recommended action
    next_action: NextAction = field(default_factory=NextAction)
    
    # Completion status
    is_complete: bool = False
    completion_criteria: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "result": self.result,
            "session_progress": self.session_progress,
            "current_state": self.current_state,
            "next_action": self.next_action.to_dict(),
            "is_complete": self.is_complete,
            "completion_criteria": self.completion_criteria,
        }


class GuidedResponseBuilder:
    """
    Builds guided responses that help Agent navigate RCA process.
    
    Key Features:
    - Progress tracking (how far along is the analysis?)
    - State summarization (what do we know so far?)
    - Next action suggestion (what should we do next?)
    - Push questions (逼問 - questions that deepen analysis)
    """
    
    # Tool categories for next action suggestions
    FISHBONE_TOOLS = {
        "add_fishbone_cause",
        "get_fishbone_causes",
        "remove_fishbone_cause",
        "get_fishbone_summary",
    }
    
    WHY_TREE_TOOLS = {
        "add_why_node",
        "get_why_chain",
        "mark_root_cause",
        "get_why_summary",
    }
    
    VERIFICATION_TOOLS = {
        "verify_causation",
    }
    
    # Push questions for each stage (逼問)
    PUSH_QUESTIONS = {
        "fishbone_empty": [
            "這個問題發生時，現場的人員狀況如何？(Man)",
            "使用的設備、儀器有什麼異常嗎？(Machine)", 
            "操作方法或流程有哪些步驟可能出錯？(Method)",
            "使用的材料、藥品有什麼問題嗎？(Material)",
            "測量或監控有什麼遺漏嗎？(Measurement)",
            "環境因素（溫度、照明、噪音）有影響嗎？(Environment)",
        ],
        "fishbone_partial": [
            "還有哪些類別沒有考慮到？",
            "目前列出的原因中，哪個最可疑？",
            "有沒有多個原因互相影響的情況？",
        ],
        "why_shallow": [
            "為什麼會發生這個情況？",
            "這個原因背後還有什麼更深的原因嗎？",
            "如果這個問題被解決了，同樣的事件還會再發生嗎？",
            "還能再追問一個「為什麼」嗎？",
        ],
        "why_deep": [
            "這是最根本的原因嗎？還是只是表象？",
            "如果解決這個原因，問題真的不會再發生嗎？",
            "有沒有系統性的問題被忽略了？",
        ],
        "root_cause_found": [
            "這個根本原因符合 HFACS 的哪個分類？",
            "需要驗證這個因果關係的強度嗎？",
            "有沒有其他的根本原因也需要標記？",
        ],
        "verification_needed": [
            "這個因果關係的 temporality (時間順序) 是否明確？",
            "有沒有其他可能的解釋 (alternative explanation)？",
            "證據的強度足夠嗎？",
        ],
    }
    
    def __init__(self) -> None:
        """Initialize builder."""
        pass
    
    def build(
        self,
        result: dict[str, Any],
        progress: SessionProgress,
        tool_name: str,
    ) -> GuidedResponse:
        """
        Build a guided response.
        
        Args:
            result: The original tool result
            progress: Current session progress
            tool_name: The tool that was just called
            
        Returns:
            GuidedResponse with progress and next action
        """
        response = GuidedResponse(
            result=result,
            session_progress=self._build_progress_dict(progress),
            current_state=self._build_state_dict(progress),
            is_complete=progress.is_complete,
            completion_criteria=progress.completion_criteria,
        )
        
        # Determine next action based on current state
        response.next_action = self._suggest_next_action(progress, tool_name)
        
        return response
    
    def _build_progress_dict(self, progress: SessionProgress) -> dict[str, Any]:
        """Build progress summary dictionary."""
        return {
            "session_id": progress.session_id,
            "current_stage": self._determine_stage(progress),
            "completed_steps": self._count_completed_steps(progress),
            "total_expected": 10,  # Approximate total steps
            "completion_rate": f"{progress.completion_rate * 100:.0f}%",
        }
    
    def _build_state_dict(self, progress: SessionProgress) -> dict[str, Any]:
        """Build current state summary dictionary."""
        return {
            "fishbone": {
                "initialized": progress.fishbone_initialized,
                "categories_filled": f"{progress.fishbone_categories_filled}/6",
                "total_causes": progress.fishbone_total_causes,
            },
            "why_tree": {
                "started": progress.why_tree_started,
                "depth": progress.why_tree_depth,
                "branches": progress.why_tree_branches,
            },
            "root_causes": {
                "identified": progress.root_causes_identified,
                "verified": progress.root_causes_verified,
            },
            "hfacs": {
                "causes_tagged": progress.causes_with_hfacs,
            },
        }
    
    def _determine_stage(self, progress: SessionProgress) -> str:
        """Determine current analysis stage."""
        if not progress.fishbone_initialized:
            return "INIT"
        elif progress.fishbone_categories_filled < 3:
            return "GATHER"
        elif not progress.why_tree_started:
            return "ANALYZE_FISHBONE"
        elif progress.why_tree_depth < 3:
            return "WHY_ANALYSIS"
        elif progress.root_causes_identified == 0:
            return "IDENTIFY_ROOT"
        elif progress.root_causes_verified == 0:
            return "VERIFY"
        else:
            return "COMPLETE"
    
    def _count_completed_steps(self, progress: SessionProgress) -> int:
        """Count completed analysis steps."""
        steps = 0
        
        if progress.fishbone_initialized:
            steps += 1
        if progress.fishbone_categories_filled >= 3:
            steps += 1
        if progress.fishbone_categories_filled >= 5:
            steps += 1
        if progress.why_tree_started:
            steps += 1
        if progress.why_tree_depth >= 2:
            steps += 1
        if progress.why_tree_depth >= 4:
            steps += 1
        if progress.root_causes_identified > 0:
            steps += 1
        if progress.root_causes_verified > 0:
            steps += 1
        if progress.causes_with_hfacs > 0:
            steps += 1
        if progress.is_complete:
            steps += 1
        
        return steps
    
    def _suggest_next_action(
        self,
        progress: SessionProgress,
        tool_name: str,
    ) -> NextAction:
        """Suggest the next action based on current progress."""
        
        # Stage 1: Fishbone not started
        if not progress.fishbone_initialized:
            return NextAction(
                required=True,
                tool="create_session",
                question="請先建立分析 Session，並描述要分析的問題是什麼？",
                hint="使用 create_session 工具開始新的 RCA 分析",
            )
        
        # Stage 2: Fishbone incomplete
        if progress.fishbone_categories_filled < 4:
            # Suggest filling more categories
            unfilled = 6 - progress.fishbone_categories_filled
            push_q = self._get_push_question(
                "fishbone_empty" if progress.fishbone_categories_filled < 2 else "fishbone_partial"
            )
            return NextAction(
                required=True,
                tool="add_fishbone_cause",
                question=push_q,
                hint=f"還有 {unfilled} 個類別未填寫，建議至少完成 4 個類別",
            )
        
        # Stage 3: Why Tree not started
        if not progress.why_tree_started:
            return NextAction(
                required=True,
                tool="add_why_node",
                question="從魚骨圖中最可疑的原因開始，問「為什麼會發生？」",
                hint="選擇一個原因作為起點，開始 5-Why 分析",
            )
        
        # Stage 4: Why Tree too shallow
        if progress.why_tree_depth < 3:
            push_q = self._get_push_question("why_shallow")
            return NextAction(
                required=True,
                tool="add_why_node",
                question=push_q,
                hint=f"目前 Why 深度為 {progress.why_tree_depth}，建議追問到至少 3 層",
            )
        
        # Stage 5: No root cause identified
        if progress.root_causes_identified == 0:
            push_q = self._get_push_question("why_deep")
            return NextAction(
                required=True,
                tool="mark_root_cause",
                question=push_q,
                hint="如果已找到根本原因，請標記它",
            )
        
        # Stage 6: Root cause not verified
        if progress.root_causes_verified == 0:
            push_q = self._get_push_question("verification_needed")
            return NextAction(
                required=False,  # Optional but recommended
                tool="verify_causation",
                question=push_q,
                hint="建議驗證因果關係的強度",
            )
        
        # Stage 7: Analysis complete
        return NextAction(
            required=False,
            tool="get_why_summary",
            question="分析已達到基本完成標準，是否需要檢視完整摘要？",
            hint="可以匯出報告或繼續深入分析其他分支",
        )
    
    def _get_push_question(self, category: str) -> str:
        """Get a push question from the category."""
        import random
        questions = self.PUSH_QUESTIONS.get(category, ["請繼續分析"])
        return random.choice(questions)
