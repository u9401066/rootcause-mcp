"""
Session Progress Tracker.

Tracks RCA session progress across all tools:
- Fishbone completion (6M categories)
- Why Tree depth
- Root causes identified
- Verification status
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from rootcause_mcp.domain.entities.fishbone import Fishbone
    from rootcause_mcp.domain.entities.why_node import WhyChain


@dataclass
class SessionProgress:
    """Current progress state of an RCA session."""
    
    # Session info
    session_id: str
    current_stage: str = "GATHER"
    
    # Fishbone progress
    fishbone_initialized: bool = False
    fishbone_categories_filled: int = 0
    fishbone_total_categories: int = 6  # 6M
    fishbone_total_causes: int = 0
    
    # Why Tree progress
    why_tree_started: bool = False
    why_tree_depth: int = 0
    why_tree_max_depth: int = 5
    why_tree_branches: int = 0
    
    # Root cause progress
    root_causes_identified: int = 0
    root_causes_verified: int = 0
    
    # HFACS progress
    causes_with_hfacs: int = 0
    
    @property
    def completion_rate(self) -> float:
        """Calculate overall completion rate (0.0 - 1.0)."""
        scores = []
        
        # Fishbone score (weight: 30%)
        if self.fishbone_total_categories > 0:
            fb_score = self.fishbone_categories_filled / self.fishbone_total_categories
            scores.append(fb_score * 0.3)
        
        # Why Tree score (weight: 40%)
        if self.why_tree_started:
            # At least 3 levels for meaningful analysis
            why_score = min(self.why_tree_depth / 3.0, 1.0)
            scores.append(why_score * 0.4)
        
        # Root cause score (weight: 30%)
        if self.root_causes_identified > 0:
            rc_score = 1.0 if self.root_causes_verified > 0 else 0.5
            scores.append(rc_score * 0.3)
        
        return sum(scores) if scores else 0.0
    
    @property
    def completion_criteria(self) -> list[str]:
        """Get list of completion criteria with status."""
        criteria = []
        
        # Fishbone criteria
        if self.fishbone_categories_filled >= 4:
            criteria.append(f"✅ Fishbone: {self.fishbone_categories_filled}/6 類別已填寫")
        else:
            criteria.append(f"❌ Fishbone: 至少填寫 4/6 類別 (目前: {self.fishbone_categories_filled})")
        
        # Why Tree criteria
        if self.why_tree_depth >= 3:
            criteria.append(f"✅ Why 分析: 深度 {self.why_tree_depth} (建議 ≥3)")
        else:
            criteria.append(f"❌ Why 分析: 深度不足 (目前: {self.why_tree_depth}, 建議 ≥3)")
        
        # Root cause criteria
        if self.root_causes_identified > 0:
            criteria.append(f"✅ 已標記 {self.root_causes_identified} 個根本原因")
        else:
            criteria.append("❌ 尚未標記任何根本原因")
        
        # Verification criteria
        if self.root_causes_verified > 0:
            criteria.append(f"✅ 已驗證 {self.root_causes_verified} 個因果關係")
        elif self.root_causes_identified > 0:
            criteria.append("⚠️ 建議驗證已識別的根本原因")
        
        return criteria
    
    @property
    def is_complete(self) -> bool:
        """Check if analysis meets minimum completion criteria."""
        return (
            self.fishbone_categories_filled >= 4
            and self.why_tree_depth >= 3
            and self.root_causes_identified > 0
        )


class SessionProgressTracker:
    """
    Tracks and manages RCA session progress.
    
    Provides:
    - Progress calculation across all analysis components
    - Completion criteria checking
    - Next action suggestions
    """
    
    def __init__(self) -> None:
        """Initialize tracker."""
        self._progress_cache: dict[str, SessionProgress] = {}
    
    def get_progress(self, session_id: str) -> SessionProgress:
        """Get or create progress for a session."""
        if session_id not in self._progress_cache:
            self._progress_cache[session_id] = SessionProgress(session_id=session_id)
        return self._progress_cache[session_id]
    
    def update_from_fishbone(
        self,
        session_id: str,
        fishbone: Fishbone | None,
    ) -> SessionProgress:
        """Update progress from fishbone state."""
        progress = self.get_progress(session_id)
        
        if fishbone is None:
            progress.fishbone_initialized = False
            return progress
        
        progress.fishbone_initialized = True
        
        # Count filled categories
        filled = 0
        total_causes = 0
        for category in fishbone.categories:
            if fishbone.categories[category]:
                filled += 1
                total_causes += len(fishbone.categories[category])
        
        progress.fishbone_categories_filled = filled
        progress.fishbone_total_causes = total_causes
        
        return progress
    
    def update_from_why_tree(
        self,
        session_id: str,
        why_chain: WhyChain | None,
    ) -> SessionProgress:
        """Update progress from why tree state."""
        progress = self.get_progress(session_id)
        
        if why_chain is None:
            progress.why_tree_started = False
            return progress
        
        progress.why_tree_started = True
        progress.why_tree_depth = why_chain.depth
        progress.why_tree_branches = len(why_chain.nodes)
        
        # Count root causes
        root_causes = sum(1 for node in why_chain.nodes.values() if node.is_root_cause)
        progress.root_causes_identified = root_causes
        
        return progress
    
    def update_root_cause_verified(self, session_id: str) -> SessionProgress:
        """Mark that a root cause has been verified."""
        progress = self.get_progress(session_id)
        progress.root_causes_verified += 1
        return progress
    
    def update_hfacs_added(self, session_id: str) -> SessionProgress:
        """Mark that HFACS code was added to a cause."""
        progress = self.get_progress(session_id)
        progress.causes_with_hfacs += 1
        return progress
    
    def clear(self, session_id: str) -> None:
        """Clear progress cache for a session."""
        self._progress_cache.pop(session_id, None)
