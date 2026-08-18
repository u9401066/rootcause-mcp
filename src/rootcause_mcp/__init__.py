"""
RootCause MCP - evidence ledger and conservative medical RCA harness.

本套件透過 Model Context Protocol 保存與驗證 host Agent 提交的臨床證據、
DDx 與 RCA 產物；它本身不會思考、診斷、開立治療或證明 clinical causality。
"""

__version__ = "2.0.0a2"

from rootcause_mcp.domain.services import (
    CausationValidator,
    HFACSSuggester,
    LearnedRulesService,
)

__all__ = [
    "CausationValidator",
    "HFACSSuggester",
    "LearnedRulesService",
    "__version__",
]
