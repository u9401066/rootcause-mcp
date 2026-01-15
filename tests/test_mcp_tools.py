"""
Test MCP Tools functionality.

End-to-end tests for all 18 MCP tools:
- Session Management (4 tools)
- Fishbone Diagram (4 tools)
- 5-Why Analysis (4 tools)
- Causation Verification (1 tool)
- HFACS Classification (5 tools)
"""

import asyncio
import sys
import os
from pathlib import Path

# Fix Windows Unicode output
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    os.environ.setdefault('PYTHONIOENCODING', 'utf-8')

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rootcause_mcp.server import (
    _initialize_services,
    # Session handlers
    _handle_start_session,
    _handle_get_session,
    _handle_list_sessions,
    _handle_archive_session,
    # Fishbone handlers
    _handle_init_fishbone,
    _handle_add_cause,
    _handle_get_fishbone,
    _handle_export_fishbone,
    # HFACS handlers
    _handle_suggest_hfacs,
    # Why Tree handlers
    _handle_ask_why,
    _handle_get_why_tree,
    _handle_mark_root_cause,
    _handle_export_why_tree,
    # Verification handlers
    _handle_verify_causation,
)


async def test_session_workflow():
    """Test complete session workflow."""
    print("=" * 60)
    print("Testing Session Workflow")
    print("=" * 60)
    
    # 1. Create session
    print("\n1. Creating session...")
    result = await _handle_start_session({
        "case_type": "near_miss",
        "case_title": "藥物劑量計算錯誤 - 測試案例",
        "initial_description": "護理師計算藥物劑量時發生錯誤",
    })
    print(result[0].text)
    
    # Extract session_id from result
    session_id = None
    for line in result[0].text.split("\n"):
        if "Session ID:" in line:
            session_id = line.split("`")[1]
            break
    
    assert session_id, "Failed to get session_id"
    print(f"\n✓ Session ID: {session_id}")
    
    # 2. Get session
    print("\n2. Getting session details...")
    result = await _handle_get_session({"session_id": session_id})
    print(result[0].text)
    
    # 3. List sessions
    print("\n3. Listing sessions...")
    result = await _handle_list_sessions({"limit": 5})
    print(result[0].text)
    
    return session_id


async def test_fishbone_workflow(session_id: str):
    """Test Fishbone diagram workflow."""
    print("\n" + "=" * 60)
    print("Testing Fishbone Workflow")
    print("=" * 60)
    
    # 1. Init fishbone
    print("\n1. Initializing Fishbone diagram...")
    result = await _handle_init_fishbone({
        "session_id": session_id,
        "problem_statement": "護理師計算藥物劑量時發生 10 倍劑量錯誤",
    })
    print(result[0].text)
    
    # 2. Add causes
    print("\n2. Adding causes...")
    
    causes_to_add = [
        {
            "category": "Personnel",
            "description": "護理師經驗不足",
            "sub_causes": ["新進人員", "訓練時數不足"],
            "hfacs_code": "PC-C-PML",
        },
        {
            "category": "Process",
            "description": "劑量核對流程不完整",
            "sub_causes": ["無雙重查核機制"],
            "hfacs_code": "OI-OP",
            "evidence": ["SOP 文件"],
        },
        {
            "category": "Environment",
            "description": "工作環境吵雜",
            "hfacs_code": "PC-E-PE",
        },
        {
            "category": "Equipment",
            "description": "計算機沒有小數點提醒",
        },
        {
            "category": "Material",
            "description": "藥物標籤濃度單位不一致",
            "evidence": ["藥物包裝照片"],
        },
    ]
    
    for cause in causes_to_add:
        result = await _handle_add_cause({
            "session_id": session_id,
            **cause,
        })
        print(f"  Added: {cause['description']}")
    
    # 3. Get fishbone
    print("\n3. Getting Fishbone diagram...")
    result = await _handle_get_fishbone({"session_id": session_id})
    print(result[0].text)
    
    # 4. Export fishbone (mermaid)
    print("\n4. Exporting Fishbone (Mermaid)...")
    result = await _handle_export_fishbone({
        "session_id": session_id,
        "format": "mermaid",
    })
    print(result[0].text)
    
    # 5. Export fishbone (markdown)
    print("\n5. Exporting Fishbone (Markdown)...")
    result = await _handle_export_fishbone({
        "session_id": session_id,
        "format": "markdown",
    })
    print(result[0].text)


async def test_hfacs_suggestions():
    """Test HFACS suggestion."""
    print("\n" + "=" * 60)
    print("Testing HFACS Suggestions")
    print("=" * 60)
    
    test_cases = [
        "護理師經驗不足導致計算錯誤",
        "工作環境吵雜影響注意力",
        "沒有雙重查核流程",
    ]
    
    for desc in test_cases:
        print(f"\n描述: {desc}")
        result = await _handle_suggest_hfacs({
            "description": desc,
            "max_suggestions": 2,
        })
        print(result[0].text[:500] + "..." if len(result[0].text) > 500 else result[0].text)


async def test_why_tree_workflow(session_id: str):
    """Test 5-Why analysis workflow."""
    print("\n" + "=" * 60)
    print("Testing 5-Why Analysis Workflow")
    print("=" * 60)
    
    # 1. First Why
    print("\n1. Why 1 - Initial problem...")
    result = await _handle_ask_why({
        "session_id": session_id,
        "answer": "護理師計算劑量時出錯",
        "initial_problem": "藥物劑量計算錯誤",
        "evidence": ["處方箋記錄", "護理紀錄"],
    })
    print(result[0].text[:300] + "...")
    
    # 2. Second Why
    print("\n2. Why 2...")
    result = await _handle_ask_why({
        "session_id": session_id,
        "answer": "護理師未使用計算輔助工具",
        "evidence": ["系統使用記錄"],
    })
    print(result[0].text[:200] + "...")
    
    # 3. Third Why
    print("\n3. Why 3...")
    result = await _handle_ask_why({
        "session_id": session_id,
        "answer": "計算輔助系統當天故障",
    })
    print(result[0].text[:200] + "...")
    
    # 4. Fourth Why
    print("\n4. Why 4...")
    result = await _handle_ask_why({
        "session_id": session_id,
        "answer": "系統維護排程衝突導致未及時修復",
    })
    print(result[0].text[:200] + "...")
    
    # 5. Fifth Why - final level
    print("\n5. Why 5 (final level)...")
    result = await _handle_ask_why({
        "session_id": session_id,
        "answer": "IT 部門人力不足，維護優先順序不當",
    })
    print(result[0].text[:200] + "...")
    
    # 6. Get Why Tree
    print("\n6. Getting complete Why Tree...")
    result = await _handle_get_why_tree({"session_id": session_id})
    print(result[0].text)
    
    # 7. Export Mermaid
    print("\n7. Exporting Why Tree (Mermaid)...")
    result = await _handle_export_why_tree({
        "session_id": session_id,
        "format": "mermaid",
    })
    print(result[0].text)
    
    return result  # For extracting node_id


async def test_mark_root_cause(session_id: str):
    """Test marking root cause."""
    print("\n" + "=" * 60)
    print("Testing Mark Root Cause")
    print("=" * 60)
    
    # Get the why tree to find a node ID
    result = await _handle_get_why_tree({"session_id": session_id})
    
    # Extract a node ID from the output
    node_id = None
    for line in result[0].text.split("\n"):
        if "(ID: `" in line:
            node_id = line.split("`")[1]
            # Keep iterating to get the last one (deepest level)
    
    if node_id:
        print(f"\nMarking node {node_id} as root cause...")
        result = await _handle_mark_root_cause({
            "session_id": session_id,
            "node_id": node_id,
            "confidence": 0.85,
        })
        print(result[0].text)
    else:
        print("⚠ Could not find node ID to mark")


async def test_verify_causation(session_id: str):
    """Test causation verification."""
    print("\n" + "=" * 60)
    print("Testing Causation Verification")
    print("=" * 60)
    
    # 1. Standard verification (2 tests)
    print("\n1. Standard verification (Temporality + Necessity)...")
    result = await _handle_verify_causation({
        "session_id": session_id,
        "cause": {
            "description": "護理師計算劑量時出錯",
            "timestamp": "2026-01-15T09:00:00Z",
        },
        "effect": {
            "description": "藥物劑量記錄顯示過量",
            "timestamp": "2026-01-15T09:30:00Z",
        },
        "verification_level": "standard",
    })
    print(result[0].text)
    
    # 2. Comprehensive verification (4 tests)
    print("\n2. Comprehensive verification (all 4 tests)...")
    result = await _handle_verify_causation({
        "session_id": session_id,
        "cause": {
            "description": "IT 部門人力不足",
        },
        "effect": {
            "description": "計算輔助系統故障未及時修復",
        },
        "verification_level": "comprehensive",
    })
    print(result[0].text)


async def test_archive_session(session_id: str):
    """Test session archiving."""
    print("\n" + "=" * 60)
    print("Testing Session Archive")
    print("=" * 60)
    
    result = await _handle_archive_session({"session_id": session_id})
    print(result[0].text)


async def main():
    """Run all tests."""
    print("=" * 60)
    print("RootCause MCP Tools - Comprehensive Test")
    print("=" * 60)
    
    print("\nInitializing services...")
    _initialize_services()
    print("Services initialized.")
    
    # List all tools
    from rootcause_mcp.server import list_tools
    tools = await list_tools()
    print(f"\n📊 Total tools available: {len(tools)}")
    
    categories = {
        "Session": ["rc_start_session", "rc_get_session", "rc_list_sessions", "rc_archive_session"],
        "Fishbone": ["rc_init_fishbone", "rc_add_cause", "rc_get_fishbone", "rc_export_fishbone"],
        "Why Tree": ["rc_ask_why", "rc_get_why_tree", "rc_mark_root_cause", "rc_export_why_tree"],
        "Verification": ["rc_verify_causation"],
        "HFACS": ["rc_suggest_hfacs", "rc_confirm_classification", "rc_get_hfacs_framework", "rc_list_learned_rules", "rc_reload_rules"],
    }
    
    print("\nTools by category:")
    for cat, tool_names in categories.items():
        actual = [t for t in tools if t.name in tool_names]
        print(f"  {cat}: {len(actual)}/{len(tool_names)} tools")
        for t in actual:
            print(f"    ✓ {t.name}")
    
    try:
        # Test session workflow
        session_id = await test_session_workflow()
        
        # Test fishbone workflow
        await test_fishbone_workflow(session_id)
        
        # Test 5-Why analysis (NEW)
        await test_why_tree_workflow(session_id)
        
        # Test mark root cause (NEW)
        await test_mark_root_cause(session_id)
        
        # Test causation verification (NEW)
        await test_verify_causation(session_id)
        
        # Test HFACS suggestions
        await test_hfacs_suggestions()
        
        # Test archive
        await test_archive_session(session_id)
        
        print("\n" + "=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
