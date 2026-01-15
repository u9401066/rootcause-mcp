"""
Learned Rules Service - 管理 HFACS 學習規則.

負責學習規則的 CRUD 操作，包括：
- 新增已確認的規則
- 管理待審核規則
- 記錄被拒絕的規則
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


@dataclass
class LearnedRule:
    """已學習的規則."""
    
    keyword: str
    code: str
    confidence: float
    reason: str
    source_type: str = "agent"  # agent | session | manual
    source_session: str | None = None
    confirmed_by: str = "user"
    confirmed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    hit_count: int = 0


@dataclass
class PendingRule:
    """待審核的規則."""
    
    keyword: str
    code: str
    confidence: float
    reason: str
    source_session: str | None = None
    suggested_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "pending"  # pending | approved | rejected


@dataclass
class RejectedRule:
    """被拒絕的規則."""
    
    keyword: str
    code: str
    rejected_reason: str
    rejected_by: str = "user"
    rejected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class LearnedRulesService:
    """
    管理學習規則的 Domain Service.
    
    提供對 learned_rules.yaml 的 CRUD 操作。
    """
    
    def __init__(self, config_dir: Path | str | None = None):
        """
        初始化服務.
        
        Args:
            config_dir: config/hfacs 目錄路徑
        """
        self.config_dir = self._resolve_config_dir(config_dir)
        self.rules_file = self.config_dir / "learned_rules.yaml"
        self._data: dict[str, Any] = {}
        self._load()
    
    def _resolve_config_dir(self, config_dir: Path | str | None) -> Path:
        """解析設定目錄路徑."""
        if config_dir:
            return Path(config_dir)
        
        current_file = Path(__file__)
        for parent in current_file.parents:
            candidate = parent / "config" / "hfacs"
            if candidate.exists():
                return candidate
        
        return Path("config/hfacs")
    
    def _load(self) -> None:
        """載入學習規則檔案."""
        if self.rules_file.exists():
            with open(self.rules_file, "r", encoding="utf-8") as f:
                self._data = yaml.safe_load(f) or {}
        else:
            self._data = {
                "metadata": {
                    "version": "1.0.0",
                    "updated": datetime.now(timezone.utc).isoformat(),
                    "stats": {
                        "total_rules": 0,
                        "from_agent": 0,
                        "from_session": 0,
                        "from_manual": 0,
                    }
                },
                "learned_rules": [],
                "pending_rules": [],
                "rejected_rules": [],
            }
    
    def _save(self) -> None:
        """儲存學習規則檔案."""
        # 更新 metadata
        self._data["metadata"]["updated"] = datetime.now(timezone.utc).isoformat()
        self._update_stats()
        
        # 確保目錄存在
        self.rules_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.rules_file, "w", encoding="utf-8") as f:
            yaml.dump(
                self._data,
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )
    
    def _update_stats(self) -> None:
        """更新統計資訊."""
        learned = self._data.get("learned_rules", [])
        stats = {
            "total_rules": len(learned),
            "from_agent": sum(1 for r in learned if r.get("source_type") == "agent"),
            "from_session": sum(1 for r in learned if r.get("source_type") == "session"),
            "from_manual": sum(1 for r in learned if r.get("source_type") == "manual"),
        }
        self._data["metadata"]["stats"] = stats
    
    # ═══════════════════════════════════════════════════════════════
    # Learned Rules CRUD
    # ═══════════════════════════════════════════════════════════════
    
    def add_learned_rule(self, rule: LearnedRule) -> bool:
        """
        新增已學習的規則.
        
        Args:
            rule: 要新增的規則
            
        Returns:
            是否成功新增（若關鍵字已存在則返回 False）
        """
        learned = self._data.setdefault("learned_rules", [])
        
        # 檢查是否已存在相同 keyword + code 的規則
        for existing in learned:
            if existing["keyword"] == rule.keyword and existing["code"] == rule.code:
                # 更新 hit_count
                existing["hit_count"] = existing.get("hit_count", 0) + 1
                self._save()
                return False
        
        # 新增規則
        learned.append({
            "keyword": rule.keyword,
            "code": rule.code,
            "confidence": rule.confidence,
            "reason": rule.reason,
            "source_type": rule.source_type,
            "source_session": rule.source_session,
            "confirmed_by": rule.confirmed_by,
            "confirmed_at": rule.confirmed_at.isoformat(),
            "hit_count": rule.hit_count,
        })
        
        self._save()
        return True
    
    def get_learned_rules(self) -> list[dict[str, Any]]:
        """取得所有已學習的規則."""
        return self._data.get("learned_rules", [])
    
    def remove_learned_rule(self, keyword: str, code: str) -> bool:
        """
        移除已學習的規則.
        
        Args:
            keyword: 關鍵字
            code: HFACS 代碼
            
        Returns:
            是否成功移除
        """
        learned = self._data.get("learned_rules", [])
        original_len = len(learned)
        
        self._data["learned_rules"] = [
            r for r in learned
            if not (r["keyword"] == keyword and r["code"] == code)
        ]
        
        if len(self._data["learned_rules"]) < original_len:
            self._save()
            return True
        return False
    
    # ═══════════════════════════════════════════════════════════════
    # Pending Rules CRUD
    # ═══════════════════════════════════════════════════════════════
    
    def add_pending_rule(self, rule: PendingRule) -> bool:
        """新增待審核規則."""
        pending = self._data.setdefault("pending_rules", [])
        
        # 檢查是否已在 pending 或 rejected
        for existing in pending:
            if existing["keyword"] == rule.keyword and existing["code"] == rule.code:
                return False
        
        for rejected in self._data.get("rejected_rules", []):
            if rejected["keyword"] == rule.keyword and rejected["code"] == rule.code:
                return False  # 已被拒絕過，不再建議
        
        pending.append({
            "keyword": rule.keyword,
            "code": rule.code,
            "confidence": rule.confidence,
            "reason": rule.reason,
            "source_session": rule.source_session,
            "suggested_at": rule.suggested_at.isoformat(),
            "status": rule.status,
        })
        
        self._save()
        return True
    
    def get_pending_rules(self) -> list[dict[str, Any]]:
        """取得所有待審核的規則."""
        return self._data.get("pending_rules", [])
    
    def approve_pending_rule(
        self,
        keyword: str,
        code: str,
        confirmed_by: str = "user",
    ) -> bool:
        """
        核准待審核規則，轉為已學習規則.
        
        Args:
            keyword: 關鍵字
            code: HFACS 代碼
            confirmed_by: 確認者
            
        Returns:
            是否成功核准
        """
        pending = self._data.get("pending_rules", [])
        
        for i, rule in enumerate(pending):
            if rule["keyword"] == keyword and rule["code"] == code:
                # 轉移到 learned_rules
                learned_rule = LearnedRule(
                    keyword=rule["keyword"],
                    code=rule["code"],
                    confidence=rule["confidence"],
                    reason=rule["reason"],
                    source_type="agent",
                    source_session=rule.get("source_session"),
                    confirmed_by=confirmed_by,
                )
                self.add_learned_rule(learned_rule)
                
                # 從 pending 移除
                pending.pop(i)
                self._save()
                return True
        
        return False
    
    def reject_pending_rule(
        self,
        keyword: str,
        code: str,
        reason: str,
        rejected_by: str = "user",
    ) -> bool:
        """
        拒絕待審核規則.
        
        Args:
            keyword: 關鍵字
            code: HFACS 代碼
            reason: 拒絕原因
            rejected_by: 拒絕者
            
        Returns:
            是否成功拒絕
        """
        pending = self._data.get("pending_rules", [])
        
        for i, rule in enumerate(pending):
            if rule["keyword"] == keyword and rule["code"] == code:
                # 轉移到 rejected_rules
                rejected = self._data.setdefault("rejected_rules", [])
                rejected.append({
                    "keyword": rule["keyword"],
                    "code": rule["code"],
                    "rejected_reason": reason,
                    "rejected_by": rejected_by,
                    "rejected_at": datetime.now(timezone.utc).isoformat(),
                })
                
                # 從 pending 移除
                pending.pop(i)
                self._save()
                return True
        
        return False
    
    # ═══════════════════════════════════════════════════════════════
    # Utility Methods
    # ═══════════════════════════════════════════════════════════════
    
    def is_keyword_rejected(self, keyword: str, code: str) -> bool:
        """檢查關鍵字+代碼是否曾被拒絕."""
        rejected = self._data.get("rejected_rules", [])
        return any(
            r["keyword"] == keyword and r["code"] == code
            for r in rejected
        )
    
    def get_stats(self) -> dict[str, int]:
        """取得統計資訊."""
        return self._data.get("metadata", {}).get("stats", {})
    
    def reload(self) -> None:
        """重新載入規則檔案."""
        self._load()
    
    def confirm_classification(
        self,
        description: str,
        hfacs_code: str,
        reason: str,
        session_id: str | None = None,
        confidence: float = 0.85,
    ) -> dict[str, Any]:
        """
        確認 HFACS 分類並學習.
        
        這是給 MCP Tool 呼叫的主要方法。
        
        Args:
            description: 原因描述（將提取關鍵字）
            hfacs_code: 確認的 HFACS 代碼
            reason: 分類原因
            session_id: 來源 Session ID
            confidence: 信心度
            
        Returns:
            操作結果
        """
        # 提取關鍵字（簡單策略：使用整個描述或前 20 字）
        keyword = description[:50] if len(description) > 50 else description
        
        # 檢查是否已被拒絕
        if self.is_keyword_rejected(keyword, hfacs_code):
            return {
                "success": False,
                "message": f"此分類組合 ({keyword} → {hfacs_code}) 曾被拒絕",
                "action": "skipped",
            }
        
        # 新增學習規則
        rule = LearnedRule(
            keyword=keyword,
            code=hfacs_code,
            confidence=confidence,
            reason=reason,
            source_type="agent",
            source_session=session_id,
        )
        
        is_new = self.add_learned_rule(rule)
        
        return {
            "success": True,
            "message": "已新增學習規則" if is_new else "已更新現有規則的使用次數",
            "action": "created" if is_new else "updated",
            "rule": {
                "keyword": keyword,
                "code": hfacs_code,
                "confidence": confidence,
            }
        }
