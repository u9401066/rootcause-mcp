"""
HFACS Suggester Domain Service.

Suggests appropriate HFACS codes based on cause descriptions.
Loads rules from YAML configuration files for flexibility and learning.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from rootcause_mcp.domain.value_objects.enums import FishboneCategoryType
from rootcause_mcp.domain.value_objects.hfacs import (
    HFACSCode,
    HFACSLevel,
    HFACS_CODE_TABLE,
)
from rootcause_mcp.domain.value_objects.scores import ConfidenceScore


@dataclass
class HFACSSuggestion:
    """A suggested HFACS code with confidence score."""

    code: HFACSCode
    confidence: ConfidenceScore
    reason: str
    source: str = "base"  # base | domain | learned


@dataclass
class KeywordRule:
    """A keyword-to-HFACS mapping rule."""
    
    keyword: str
    code: str
    confidence: float
    reason: str
    source: str = "base"
    domain: str | None = None


@dataclass
class MatchingConfig:
    """Configuration for keyword matching."""
    
    min_confidence: float = 0.5
    max_suggestions: int = 5
    matching_mode: str = "substring"  # substring | exact | regex
    case_sensitive: bool = False
    multi_hit_boost: float = 0.05
    domain_priority: bool = True


# 6M to HFACS Level Mapping
CATEGORY_LEVEL_MAPPING: dict[FishboneCategoryType, list[HFACSLevel]] = {
    FishboneCategoryType.PERSONNEL: [HFACSLevel.LEVEL_1, HFACSLevel.LEVEL_2],
    FishboneCategoryType.EQUIPMENT: [HFACSLevel.LEVEL_4],
    FishboneCategoryType.MATERIAL: [HFACSLevel.LEVEL_4],
    FishboneCategoryType.PROCESS: [HFACSLevel.LEVEL_4, HFACSLevel.LEVEL_3],
    FishboneCategoryType.ENVIRONMENT: [HFACSLevel.LEVEL_2, HFACSLevel.LEVEL_4],
    FishboneCategoryType.MONITORING: [HFACSLevel.LEVEL_3, HFACSLevel.LEVEL_4],
}


class HFACSSuggester:
    """
    Domain service for suggesting HFACS codes.

    Loads keyword rules from YAML configuration files and uses
    keyword matching to suggest appropriate HFACS codes.
    
    Rules are loaded from:
    1. Base rules (from HFACS framework YAML files)
    2. Domain rules (from keyword_rules.yaml)
    3. Learned rules (from learned_rules.yaml)
    """

    def __init__(
        self,
        config_dir: Path | str | None = None,
        active_domains: list[str] | None = None,
    ):
        """
        Initialize the suggester.
        
        Args:
            config_dir: Path to config/hfacs directory. If None, auto-detect.
            active_domains: List of active domains (e.g., ["anesthesia"]).
                           If None, all domains are active.
        """
        self.config_dir = self._resolve_config_dir(config_dir)
        self.active_domains = active_domains
        self.rules: list[KeywordRule] = []
        self.config = MatchingConfig()
        # Cache code info from YAML (avoids dependency on HFACS_CODE_TABLE)
        self.code_info_cache: dict[str, dict[str, Any]] = {}
        self._load_rules()
    
    def _resolve_config_dir(self, config_dir: Path | str | None) -> Path:
        """Resolve the config directory path."""
        if config_dir:
            return Path(config_dir)
        
        # Auto-detect: look for config/hfacs relative to this file
        current_file = Path(__file__)
        # Navigate up to find project root
        for parent in current_file.parents:
            candidate = parent / "config" / "hfacs"
            if candidate.exists():
                return candidate
        
        # Fallback: assume current working directory
        return Path("config/hfacs")
    
    def _load_rules(self) -> None:
        """Load all rules from YAML files."""
        self.rules = []
        
        # 1. Load keyword_rules.yaml (domain rules + config)
        keyword_rules_path = self.config_dir / "keyword_rules.yaml"
        if keyword_rules_path.exists():
            self._load_keyword_rules(keyword_rules_path)
        
        # 2. Load base rules from framework YAML files
        self._load_base_rules_from_frameworks()
        
        # 3. Load learned rules
        learned_rules_path = self.config_dir / "learned_rules.yaml"
        if learned_rules_path.exists():
            self._load_learned_rules(learned_rules_path)
    
    def _load_keyword_rules(self, path: Path) -> None:
        """Load domain-specific rules from keyword_rules.yaml."""
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        
        # Load matching config
        if "matching_config" in data:
            mc = data["matching_config"]
            self.config = MatchingConfig(
                min_confidence=mc.get("min_confidence", 0.5),
                max_suggestions=mc.get("max_suggestions", 5),
                matching_mode=mc.get("matching_mode", "substring"),
                case_sensitive=mc.get("case_sensitive", False),
                multi_hit_boost=mc.get("multi_hit_boost", 0.05),
                domain_priority=mc.get("domain_priority", True),
            )
        
        # Load domain rules
        if "domain_rules" in data:
            for domain_name, domain_data in data["domain_rules"].items():
                # Check if domain is active
                if self.active_domains and domain_name not in self.active_domains:
                    continue
                
                if not isinstance(domain_data, dict):
                    continue
                    
                # Iterate through categories in domain
                for category_name, category_data in domain_data.items():
                    if category_name in ("description", "source"):
                        continue
                    
                    if not isinstance(category_data, dict):
                        continue
                    
                    keywords = category_data.get("keywords", [])
                    mappings = category_data.get("mappings", [])
                    
                    # Create rules for each keyword-mapping combination
                    for keyword in keywords:
                        for mapping in mappings:
                            self.rules.append(KeywordRule(
                                keyword=keyword,
                                code=mapping["code"],
                                confidence=mapping["confidence"],
                                reason=mapping["reason"],
                                source="domain",
                                domain=domain_name,
                            ))
    
    def _load_base_rules_from_frameworks(self) -> None:
        """Load base rules from HFACS framework YAML files."""
        # Load HFACS-MES
        hfacs_mes_path = self.config_dir / "hfacs_mes.yaml"
        if hfacs_mes_path.exists():
            self._extract_keywords_from_framework(hfacs_mes_path, "hfacs-mes")
        
        # Load Fishbone 6M
        fishbone_path = self.config_dir / "fishbone_6m.yaml"
        if fishbone_path.exists():
            self._extract_keywords_from_fishbone(fishbone_path)
    
    def _extract_keywords_from_framework(self, path: Path, framework: str) -> None:
        """Extract keyword rules and code info from a framework YAML file."""
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        
        taxonomy = data.get("taxonomy", {})
        
        def extract_from_codes(
            codes: dict[str, Any],
            level_num: int,
            category_name: str,
            base_confidence: float = 0.7,
        ) -> None:
            for code_id, code_data in codes.items():
                if not isinstance(code_data, dict):
                    continue
                keywords = code_data.get("keywords", [])
                name_zh = code_data.get("name_zh", "")
                name = code_data.get("name", "")
                description = code_data.get("description", "")
                
                # Cache code info for later use in suggest()
                self.code_info_cache[code_id] = {
                    "level": level_num,
                    "category": category_name,
                    "subcategory": name_zh or name,
                    "description": description or name_zh or name,
                    "name_zh": name_zh,
                }
                
                for keyword in keywords:
                    self.rules.append(KeywordRule(
                        keyword=keyword,
                        code=code_id,
                        confidence=base_confidence,
                        reason=f"基礎規則: {name_zh}",
                        source="base",
                    ))
        
        # Traverse taxonomy structure
        for level_id, level_data in taxonomy.items():
            if not isinstance(level_data, dict):
                continue
            
            level_num = level_data.get("level", 0)
            level_name_zh = level_data.get("name_zh", level_id)
            
            # Direct codes
            if "codes" in level_data:
                extract_from_codes(level_data["codes"], level_num, level_name_zh)
            
            # Subcategories
            if "subcategories" in level_data:
                for subcat_id, subcat_data in level_data["subcategories"].items():
                    if isinstance(subcat_data, dict) and "codes" in subcat_data:
                        subcat_name = subcat_data.get("name_zh", subcat_id)
                        extract_from_codes(
                            subcat_data["codes"], level_num, subcat_name
                        )
    
    def _extract_keywords_from_fishbone(self, path: Path) -> None:
        """Extract keyword rules from Fishbone 6M YAML."""
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        
        categories = data.get("categories", {})
        
        for cat_id, cat_data in categories.items():
            if not isinstance(cat_data, dict):
                continue
            
            keywords = cat_data.get("keywords", [])
            name_zh = cat_data.get("name_zh", cat_id)
            
            # Map Fishbone categories to HFACS levels
            hfacs_mapping = {
                "MAN": ["UA-SBE", "PP-AMS"],
                "METHOD": ["OF-OP", "US-IP"],
                "MACHINE": ["EF-PMI", "OF-RM"],
                "MATERIAL": ["OF-RM"],
                "MEASUREMENT": ["EF-PMI", "US-IS"],
                "MILIEU": ["EF-PE"],
            }
            
            target_codes = hfacs_mapping.get(cat_id, [])
            
            for keyword in keywords:
                for code in target_codes:
                    self.rules.append(KeywordRule(
                        keyword=keyword,
                        code=code,
                        confidence=0.6,  # Lower confidence for indirect mapping
                        reason=f"Fishbone {name_zh} 對應",
                        source="base",
                    ))
    
    def _load_learned_rules(self, path: Path) -> None:
        """Load learned rules from learned_rules.yaml."""
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        
        if not data:
            return
        
        learned = data.get("learned_rules", [])
        
        for rule in learned:
            if not isinstance(rule, dict):
                continue
            
            self.rules.append(KeywordRule(
                keyword=rule["keyword"],
                code=rule["code"],
                confidence=rule.get("confidence", 0.85),
                reason=rule.get("reason", "已學習規則"),
                source="learned",
            ))

    def suggest(
        self,
        description: str,
        category: FishboneCategoryType | None = None,
        max_suggestions: int | None = None,
    ) -> list[HFACSSuggestion]:
        """
        Suggest HFACS codes for a cause description.

        Args:
            description: The cause description text
            category: Optional 6M category for context
            max_suggestions: Maximum number of suggestions to return

        Returns:
            List of HFACSSuggestions sorted by confidence
        """
        max_suggestions = max_suggestions or self.config.max_suggestions
        suggestions: list[HFACSSuggestion] = []
        
        # Normalize description for matching
        desc_normalized = description if self.config.case_sensitive else description.lower()
        
        # Track keyword hits for multi-hit boost
        code_hits: dict[str, int] = {}
        
        # Match keywords
        for rule in self.rules:
            keyword = rule.keyword if self.config.case_sensitive else rule.keyword.lower()
            
            matched = False
            if self.config.matching_mode == "exact":
                matched = keyword == desc_normalized
            elif self.config.matching_mode == "regex":
                matched = bool(re.search(keyword, desc_normalized))
            else:  # substring
                matched = keyword in desc_normalized
            
            if matched:
                code_hits[rule.code] = code_hits.get(rule.code, 0) + 1
                
                # Try to get code from cache first, then fallback to HFACS_CODE_TABLE
                code_info = self.code_info_cache.get(rule.code)
                if code_info:
                    # Build HFACSCode from cache
                    level_num = code_info.get("level", 1)
                    try:
                        level = HFACSLevel(f"Level {level_num}")
                    except ValueError:
                        level = HFACSLevel.LEVEL_1
                    
                    code = HFACSCode(
                        code=rule.code,
                        level=level,
                        category=str(code_info.get("category", "")),
                        subcategory=str(code_info.get("subcategory", "")),
                        description=str(code_info.get("description", "")),
                    )
                else:
                    # Fallback to HFACS_CODE_TABLE
                    try:
                        code = HFACSCode.from_code(rule.code)
                    except (ValueError, KeyError):
                        continue
                
                # Calculate adjusted confidence
                adjusted_confidence = rule.confidence
                
                # Boost for category match
                if category:
                    expected_levels = CATEGORY_LEVEL_MAPPING.get(category, [])
                    if code.level in expected_levels:
                        adjusted_confidence = min(1.0, adjusted_confidence + 0.1)
                
                # Boost for learned rules (more trusted)
                if rule.source == "learned":
                    adjusted_confidence = min(1.0, adjusted_confidence + 0.05)
                
                # Domain rules get priority if configured
                if self.config.domain_priority and rule.source == "domain":
                    adjusted_confidence = min(1.0, adjusted_confidence + 0.02)
                
                suggestions.append(HFACSSuggestion(
                    code=code,
                    confidence=ConfidenceScore(adjusted_confidence),
                    reason=rule.reason,
                    source=rule.source,
                ))
        
        # Apply multi-hit boost
        for suggestion in suggestions:
            hits = code_hits.get(suggestion.code.code, 1)
            if hits > 1:
                boost = self.config.multi_hit_boost * (hits - 1)
                new_conf = min(1.0, float(suggestion.confidence) + boost)
                suggestion.confidence = ConfidenceScore(new_conf)
        
        # Sort by confidence (descending), then by source priority
        source_priority = {"learned": 0, "domain": 1, "base": 2}
        suggestions.sort(
            key=lambda s: (-float(s.confidence), source_priority.get(s.source, 3))
        )
        
        # Remove duplicates (keep highest confidence)
        seen_codes: set[str] = set()
        unique_suggestions: list[HFACSSuggestion] = []
        for suggestion in suggestions:
            if suggestion.code.code not in seen_codes:
                if float(suggestion.confidence) >= self.config.min_confidence:
                    seen_codes.add(suggestion.code.code)
                    unique_suggestions.append(suggestion)
        
        return unique_suggestions[:max_suggestions]

    def suggest_by_category(
        self,
        category: FishboneCategoryType,
    ) -> list[HFACSSuggestion]:
        """
        Suggest HFACS codes based only on 6M category.

        Returns typical HFACS codes for a given Fishbone category.
        """
        suggestions: list[HFACSSuggestion] = []
        expected_levels = CATEGORY_LEVEL_MAPPING.get(category, [])

        for code_str, info in HFACS_CODE_TABLE.items():
            if info["level"] in expected_levels:
                try:
                    code = HFACSCode.from_code(code_str)
                except (ValueError, KeyError):
                    continue
                    
                suggestions.append(
                    HFACSSuggestion(
                        code=code,
                        confidence=ConfidenceScore(0.5),
                        reason=f"基於 {category.value} 分類建議",
                        source="base",
                    )
                )

        return suggestions[:5]

    def get_guiding_questions(
        self,
        level: HFACSLevel,
    ) -> list[str]:
        """
        Get guiding questions to help identify causes at a specific HFACS level.
        """
        questions: dict[HFACSLevel, list[str]] = {
            HFACSLevel.LEVEL_5: [
                "是否有法規或政策層面的問題？",
                "是否有國家層級的資源限制？",
                "外部監管環境是否存在缺陷？",
            ],
            HFACSLevel.LEVEL_4: [
                "組織的資源配置是否足夠？（人力、設備、預算）",
                "是否存在組織文化或政策問題？",
                "相關的 SOP 或流程是否完善？",
                "近期是否有組織變革影響？",
            ],
            HFACSLevel.LEVEL_3: [
                "主管是否提供足夠的指導和訓練？",
                "任務的規劃和分配是否適當？",
                "是否有已知問題未被處理？",
                "督導者是否有違規行為？",
            ],
            HFACSLevel.LEVEL_2: [
                "工作環境（物理、技術）是否適當？",
                "人員當時的身心狀態如何？",
                "團隊溝通和協調是否良好？",
                "病人本身是否有特殊因素？",
            ],
            HFACSLevel.LEVEL_1: [
                "是否有決策或判斷上的錯誤？",
                "是否有技術或操作上的錯誤？",
                "是否有感知上的錯誤（看錯、聽錯）？",
                "是否有違規或捷徑行為？",
            ],
        }
        return questions.get(level, [])
    
    def get_loaded_rules_summary(self) -> dict[str, Any]:
        """Get a summary of loaded rules for debugging."""
        summary: dict[str, Any] = {
            "total_rules": len(self.rules),
            "by_source": {},
            "by_domain": {},
            "config": {
                "min_confidence": self.config.min_confidence,
                "max_suggestions": self.config.max_suggestions,
                "matching_mode": self.config.matching_mode,
            }
        }
        
        for rule in self.rules:
            # By source
            summary["by_source"][rule.source] = summary["by_source"].get(rule.source, 0) + 1
            
            # By domain
            if rule.domain:
                summary["by_domain"][rule.domain] = summary["by_domain"].get(rule.domain, 0) + 1
        
        return summary
    
    def reload_rules(self) -> None:
        """Reload all rules from YAML files."""
        self._load_rules()
