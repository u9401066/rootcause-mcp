"""Debug keyword matching."""

from rootcause_mcp.domain.services.hfacs_suggester import HFACSSuggester

suggester = HFACSSuggester()

# 測試描述
desc = "困難插管導致病人缺氧"
print(f"Description: {desc}")
print()

# 列出有 '插管' 的規則
matching_rules = [r for r in suggester.rules if "插管" in r.keyword]
print(f"Rules containing '插管': {len(matching_rules)}")
for r in matching_rules[:10]:
    keyword_lower = r.keyword.lower()
    desc_lower = desc.lower()
    is_match = keyword_lower in desc_lower
    print(f"  - keyword=\"{r.keyword}\", code={r.code}")
    print(f"    Match check: \"{keyword_lower}\" in \"{desc_lower}\" = {is_match}")
print()

# 直接測試關鍵字匹配
print("=== Direct Matching Test ===")
test_keywords = ["困難插管", "插管", "插管失敗", "氣道"]
for kw in test_keywords:
    in_rules = any(kw in r.keyword for r in suggester.rules)
    in_desc = kw in desc
    print(f"Keyword '{kw}':")
    print(f"  In rules: {in_rules}")
    print(f"  In desc:  {in_desc}")
    print(f"  Should match: {in_rules and in_desc}")
print()

# 執行實際 suggest
print("=== Actual Suggestions ===")
results = suggester.suggest(desc)
print(f"Suggestions count: {len(results)}")
for s in results[:5]:
    print(f"  - {s.code.code}: {s.confidence:.2f} - {s.reason}")
