import re
from pathlib import Path

import yaml

SOP_PATH = Path("config/protocols/clinical_reasoning_sop.yaml")
TEMPLATE_PATH = Path("config/templates/clinician_ddx_discussion_zh_tw.md")
LEGACY_TEMPLATE_PATH = Path("config/templates/clinical_reasoning_report_template.md")
SPECIALTY_TEMPLATE_PATHS = (
    Path("config/templates/anesthesia_mm_rca_report_template.md"),
    Path("config/templates/near_miss_adverse_event_rca_template.md"),
)
TIMELINE_PATTERNS_PATH = Path("config/protocols/timeline_patterns.yaml")
ANESTHESIA_PROTOCOL_PATH = Path("config/protocols/anesthesia_mm_rca_protocol.yaml")


def _sop() -> dict[str, object]:
    loaded = yaml.safe_load(SOP_PATH.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def test_sop_defines_zh_tw_clinician_communication_contract() -> None:
    communication = _sop()["communication_contract"]
    assert communication["default_locale"] == "zh-TW"
    assert communication["default_audience"] == "clinician"
    assert communication["prose_language"] == "Traditional Chinese"
    assert communication["medical_terminology"] == "English"
    assert communication["certainty_display"] == "qualitative"


def test_sop_requires_bounded_broad_differential() -> None:
    breadth = _sop()["differential_breadth"]
    assert len(breadth["candidate_qualifiers"]) >= 4
    assert "distinct mechanism" in breadth["stop_rule"]
    assert breadth["final_minimum_unique_diagnoses"] == 3
    assert breadth["final_minimum_non_unknown_mechanisms"] >= 2

    required = " ".join(breadth["required_per_active_candidate"])
    for expected in (
        "why this diagnosis is plausible",
        "evidence for, against",
        "unknowns",
        "DISCRIMINATE",
        "qualitative certainty",
    ):
        assert expected in required


def test_sop_does_not_supply_canned_numeric_likelihood_ratios() -> None:
    policy = _sop()["likelihood_ratio_policy"]
    assert policy["quantitatively_unknown_value"] == 1.0
    assert (
        "citation or locally approved calibration source"
        in policy["non_neutral_requires"]
    )
    assert "not genuine" in policy["neutral_semantics"]
    assert set(policy) == {
        "quantitatively_unknown_value",
        "non_neutral_requires",
        "neutral_semantics",
        "prohibited",
    }


def test_zh_tw_clinician_template_exposes_required_discussion_fields() -> None:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    for expected in (
        "繁體中文",
        "English medical terminology",
        "Differential diagnosis discussion",
        "Evidence for",
        "Evidence against",
        "Unknown / alternative explanation",
        "Discriminating test",
        "Must-not-miss",
        "differential_breadth_audit_section",
        "Medical root-process / system RCA",
        "Conformance",
    ):
        assert expected in template


def test_legacy_template_does_not_present_placeholder_probability_or_orders() -> None:
    template = LEGACY_TEMPLATE_PATH.read_text(encoding="utf-8")
    assert "Posterior Probability" not in template
    assert "Recommended Clinical Action Plan" not in template
    assert "not patient-specific treatment orders" in template
    assert "Qualitative certainty" in template
    assert "provenance-state true inside the registered-source boundary" in template


def test_specialty_templates_do_not_embed_patient_specific_actions() -> None:
    prohibited = (
        "top_probability",
        "後驗機率",
        "Epinephrine",
        "Phenylephrine",
        "Esmolol",
        "mg/kg",
        "立即停用",
    )
    for path in SPECIALTY_TEMPLATE_PATHS:
        template = path.read_text(encoding="utf-8")
        assert "qualified" in template
        assert "unknown" in template.lower()
        for term in prohibited:
            assert term not in template, f"{path} contains {term!r}"


def test_timeline_pattern_keywords_do_not_embed_benchmark_times_or_answers() -> None:
    catalog = yaml.safe_load(TIMELINE_PATTERNS_PATH.read_text(encoding="utf-8"))
    assert len(catalog["safety_contract"]) >= 3
    for pattern in catalog["patterns"].values():
        for phase in pattern["phases"]:
            for keyword in phase["keywords"]:
                assert re.fullmatch(r"\d{1,2}:\d{2}", str(keyword)) is None
            assert "misinterpretation" not in phase["name"].casefold()
            assert "corrective rescue" not in phase["name"].casefold()


def test_anesthesia_framework_requires_unknown_cells_without_prefilled_causality() -> (
    None
):
    protocol = yaml.safe_load(ANESTHESIA_PROTOCOL_PATH.read_text(encoding="utf-8"))
    assert protocol["status"] == "non_normative_retrospective_framework"
    assert len(protocol["safety_contract"]) >= 3
    rules = " ".join(rule["description"] for rule in protocol["rules"])
    assert "missing data 必須標 unknown" in protocol["tiers"][1]["focus"]
    assert "不得以三項作為展開上限" in rules
    assert "response本身不證明" in rules
