import re
from pathlib import Path
from typing import Any

import yaml

DOMAIN_DIR = Path("config/domains")
PROHIBITED_KEYS = {
    "expert_level_truth",
    "pathognomonic_findings",
    "primary_mechanism",
    "recommended_rescue",
    "rescue",
    "strictly_contraindicated",
    "treatment_protocol",
}
PROHIBITED_ASSERTION_PATTERNS = (
    re.compile(r"\bconfirms?\b", re.IGNORECASE),
    re.compile(r"\bcannot be explained\b", re.IGNORECASE),
    re.compile(r"\bclassic hallmark\b", re.IGNORECASE),
    re.compile(r"\border stat\b", re.IGNORECASE),
    re.compile("確診"),
)


def _mapping_keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        keys = {str(key) for key in value}
        for nested in value.values():
            keys.update(_mapping_keys(nested))
        return keys
    if isinstance(value, list):
        keys: set[str] = set()
        for nested in value:
            keys.update(_mapping_keys(nested))
        return keys
    return set()


def test_domain_playbooks_are_retrospective_and_non_prescriptive() -> None:
    paths = sorted(DOMAIN_DIR.glob("*.yaml"))
    assert paths

    for path in paths:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert document["status"] == "non_normative_retrospective_differential_aid"
        assert len(document["safety_contract"]) >= 3
        assert not (PROHIBITED_KEYS & _mapping_keys(document)), path


def test_clinical_playbooks_rename_overstated_pathognomonic_lists() -> None:
    for path in sorted(DOMAIN_DIR.glob("*.yaml")):
        text = path.read_text(encoding="utf-8")
        assert "pathognomonic_findings:" not in text
        if "candidate_findings_requiring_confirmation:" in text:
            assert "management_boundary:" in text or "candidate_system_actions" in text


def test_domain_playbooks_do_not_publish_diagnostic_certainty_or_active_orders() -> (
    None
):
    """A disclaimer cannot neutralize an absolute claim in the same resource."""
    for path in sorted(DOMAIN_DIR.glob("*.yaml")):
        text = path.read_text(encoding="utf-8")
        for pattern in PROHIBITED_ASSERTION_PATTERNS:
            assert pattern.search(text) is None, (path, pattern.pattern)
