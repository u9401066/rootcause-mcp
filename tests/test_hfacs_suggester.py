"""Test HFACSSuggester with YAML rules."""

from rootcause_mcp.domain.services import HFACSSuggester


def test_suggester_loads_rules():
    """Test that suggester loads rules from YAML files."""
    suggester = HFACSSuggester()
    summary = suggester.get_loaded_rules_summary()
    
    print("=== HFACSSuggester Rules Summary ===")
    print(f"Total rules: {summary['total_rules']}")
    print(f"By source: {summary['by_source']}")
    print(f"By domain: {summary['by_domain']}")
    print()
    
    assert summary["total_rules"] > 0, "Should have loaded some rules"


def test_suggester_suggests_anesthesia():
    """Test suggestions for anesthesia-related descriptions."""
    suggester = HFACSSuggester()
    
    test_cases = [
        ("護理師因疲勞而給錯藥，發生 syringe swap", "藥物錯誤+疲勞"),
        ("困難插管導致病人缺氧", "呼吸道相關"),
        ("術中心跳停止，急救後恢復", "心血管相關"),
        ("交班時未傳達病人過敏史", "溝通問題"),
        ("alarm fatigue 導致監測器警報被忽略", "設備相關"),
    ]
    
    print("=== Anesthesia Suggestion Tests ===")
    for desc, scenario in test_cases:
        print(f"\n[{scenario}]")
        print(f"Description: {desc}")
        suggestions = suggester.suggest(desc, max_suggestions=3)
        print(f"Suggestions ({len(suggestions)}):")
        for s in suggestions:
            print(f"  - {s.code.code}: {s.reason}")
            print(f"    confidence: {float(s.confidence):.2f}, source: {s.source}")


def test_guiding_questions():
    """Test guiding questions for each HFACS level."""
    from rootcause_mcp.domain.value_objects.hfacs import HFACSLevel
    
    suggester = HFACSSuggester()
    
    print("\n=== Guiding Questions by Level ===")
    for level in HFACSLevel:
        questions = suggester.get_guiding_questions(level)
        print(f"\n{level.name}:")
        for q in questions:
            print(f"  - {q}")


if __name__ == "__main__":
    test_suggester_loads_rules()
    test_suggester_suggests_anesthesia()
    test_guiding_questions()
    print("\n✅ All tests passed!")
