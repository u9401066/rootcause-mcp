"""
Root Cause Analysis MCP Server (SDK 2.0).

MCP Server entry point for medical reasoning and differential diagnosis.
Uses SDK 2.0 callback-based API.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from collections.abc import AsyncIterator, Awaitable, Callable, Iterator
from contextlib import asynccontextmanager, contextmanager, suppress
from dataclasses import dataclass
from functools import partial
from importlib import resources as package_resources
from pathlib import Path
from typing import Any

from mcp.server import Server, ServerRequestContext
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolRequestParams,
    CallToolResult,
    GetPromptRequestParams,
    GetPromptResult,
    ListPromptsResult,
    ListResourcesResult,
    ListResourceTemplatesResult,
    ListToolsResult,
    ReadResourceRequestParams,
    ReadResourceResult,
    TextContent,
)

# Application layer
from rootcause_mcp.application.server_state import ServerState
from rootcause_mcp.application.session_progress import SessionProgressTracker

# Domain and Infrastructure
from rootcause_mcp.domain.services import HFACSSuggester, LearnedRulesService
from rootcause_mcp.infrastructure.persistence.database import Database
from rootcause_mcp.infrastructure.persistence.evidence_repository import (
    SQLiteEvidenceRepository,
)
from rootcause_mcp.infrastructure.persistence.fishbone_repository import (
    SQLiteFishboneRepository,
)
from rootcause_mcp.infrastructure.persistence.hypothesis_repository import (
    SQLiteHypothesisRepository,
)
from rootcause_mcp.infrastructure.persistence.reasoning_chain_repository import (
    SQLiteReasoningChainRepository,
)
from rootcause_mcp.infrastructure.persistence.session_repository import (
    SQLiteSessionRepository,
)
from rootcause_mcp.infrastructure.persistence.thinking_chain_repository import (
    SQLiteThinkingChainRepository,
)
from rootcause_mcp.infrastructure.persistence.why_tree_repository import (
    SQLiteWhyTreeRepository,
)
from rootcause_mcp.infrastructure.runtime_paths import get_user_data_root

# Handlers
from rootcause_mcp.interface.handlers import (
    ContractHandlers,
    DDHandlers,
    EvidenceHandlers,
    FacadeHandlers,
    FishboneHandlers,
    HFACSHandlers,
    ReasoningHandlers,
    SessionHandlers,
    ThinkingHandlers,
    VerificationHandlers,
    WhyTreeHandlers,
)

# Prompts and Resources
from rootcause_mcp.interface.prompts import get_all_prompts, get_prompt_result
from rootcause_mcp.interface.resources import (
    get_resource_templates,
    get_static_resources,
    read_clinical_resource,
)

# Tool definitions
from rootcause_mcp.interface.tools import get_all_tools

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ServerRuntime:
    """Mutable resources owned by one MCP server lifespan."""

    tool_profile: str | None = None
    response_mode: str | None = None
    server_state: ServerState | None = None
    thinking_handlers: ThinkingHandlers | None = None
    evidence_handlers: EvidenceHandlers | None = None
    dd_handlers: DDHandlers | None = None
    reasoning_handlers: ReasoningHandlers | None = None
    contract_handlers: ContractHandlers | None = None
    hfacs_handlers: HFACSHandlers | None = None
    session_handlers: SessionHandlers | None = None
    fishbone_handlers: FishboneHandlers | None = None
    why_tree_handlers: WhyTreeHandlers | None = None
    verification_handlers: VerificationHandlers | None = None
    facade_handlers: FacadeHandlers | None = None
    database: Database | None = None

    def clear(self) -> None:
        """Release references after lifespan shutdown."""
        for field_name in self.__dataclass_fields__:
            setattr(self, field_name, None)


_runtime = ServerRuntime()


def _get_direct_config_path() -> Path | None:
    """Return an explicit/editable-checkout config path when one is available."""
    env_config = os.environ.get("ROOTCAUSE_CONFIG_DIR")
    if env_config:
        return Path(env_config).expanduser().resolve()

    project_root = Path(__file__).resolve().parent.parent.parent
    source_config = project_root / "config"
    if (project_root / "pyproject.toml").is_file() and source_config.is_dir():
        return source_config
    return None


def _get_config_path() -> Path:
    """Get config from an override, editable checkout, or installed package."""
    direct_path = _get_direct_config_path()
    if direct_path is not None:
        return direct_path

    packaged = package_resources.files("rootcause_mcp").joinpath("config")
    if isinstance(packaged, Path) and packaged.is_dir():
        return packaged
    raise FileNotFoundError(
        "Packaged RootCause configuration is unavailable; reinstall rootcause-mcp "
        "or set ROOTCAUSE_CONFIG_DIR"
    )


@contextmanager
def _expose_config_path(config_path: Path) -> Iterator[Path]:
    """Expose the resolved path to legacy config readers for one lifespan."""
    existing = os.environ.get("ROOTCAUSE_CONFIG_DIR")
    if existing is None:
        os.environ["ROOTCAUSE_CONFIG_DIR"] = str(config_path)
    try:
        yield config_path
    finally:
        if existing is None:
            os.environ.pop("ROOTCAUSE_CONFIG_DIR", None)


@contextmanager
def _config_path_context() -> Iterator[Path]:
    """Keep extracted package resources alive for the server lifespan."""
    direct_path = _get_direct_config_path()
    if direct_path is not None:
        if not direct_path.is_dir():
            raise FileNotFoundError(
                f"ROOTCAUSE_CONFIG_DIR is not a directory: {direct_path}"
            )
        with _expose_config_path(direct_path) as exposed:
            yield exposed
        return

    packaged = package_resources.files("rootcause_mcp").joinpath("config")
    if not packaged.is_dir():
        raise FileNotFoundError(
            "Packaged RootCause configuration is unavailable; reinstall "
            "rootcause-mcp or set ROOTCAUSE_CONFIG_DIR"
        )
    with (
        package_resources.as_file(packaged) as extracted,
        _expose_config_path(extracted) as exposed,
    ):
        yield exposed


def _get_data_path() -> Path:
    """Get the configured or platform-appropriate writable data directory."""
    return get_user_data_root()


def _get_tool_profile() -> str:
    """Return the configured MCP schema/dispatch profile."""
    return os.environ.get("ROOTCAUSE_TOOL_PROFILE", "all").strip().lower()


def _get_response_mode() -> str:
    """Return compact SDK 2.0 output mode or verbose compatibility mode."""
    mode = os.environ.get("ROOTCAUSE_RESPONSE_MODE", "compact").strip().lower()
    if mode not in {"compact", "verbose"}:
        raise ValueError(
            "ROOTCAUSE_RESPONSE_MODE must be either 'compact' or 'verbose'"
        )
    return mode


def _freeze_runtime_configuration() -> None:
    """Validate and freeze context-affecting settings for one lifespan."""
    tool_profile = _get_tool_profile()
    response_mode = _get_response_mode()
    get_all_tools(tool_profile)
    _runtime.tool_profile = tool_profile
    _runtime.response_mode = response_mode
    logger.info(
        "MCP tool profile=%s response mode=%s",
        tool_profile,
        response_mode,
    )
    if response_mode == "compact":
        logger.info(
            "Compact responses require host structuredContent support; "
            "set ROOTCAUSE_RESPONSE_MODE=verbose otherwise"
        )


@asynccontextmanager
async def lifespan(_server: Server) -> AsyncIterator[None]:  # noqa: PLR0915
    """
    Lifespan context manager for SDK 2.0.

    Initializes all handlers and repositories on startup.
    """
    logger.info("Initializing RootCause MCP Server (SDK 2.0)...")
    _freeze_runtime_configuration()

    # Setup paths
    config_context = _config_path_context()
    config_path = config_context.__enter__()
    data_path = _get_data_path()
    data_path.mkdir(parents=True, exist_ok=True, mode=0o700)

    # Initialize database
    db_path = data_path / "rca_sessions.db"
    database = Database(db_path)
    database.create_tables()

    # Initialize repositories
    session_repo = SQLiteSessionRepository(database)
    fishbone_repo = SQLiteFishboneRepository(database)
    why_tree_repo = SQLiteWhyTreeRepository(database)
    evidence_repo = SQLiteEvidenceRepository(database)
    hypothesis_repo = SQLiteHypothesisRepository(database)
    thinking_repo = SQLiteThinkingChainRepository(database)
    reasoning_repo = SQLiteReasoningChainRepository(database)

    # Initialize services
    baseline_hfacs_path = config_path / "hfacs"
    writable_hfacs_path = data_path / "hfacs"
    learned_rules_service = LearnedRulesService(
        writable_hfacs_path,
        baseline_file=baseline_hfacs_path / "learned_rules.yaml",
    )
    hfacs_suggester = HFACSSuggester(
        baseline_hfacs_path,
        learned_rules_path=learned_rules_service.rules_file,
        fallback_learned_rules_path=baseline_hfacs_path / "learned_rules.yaml",
    )

    # Initialize application layer
    progress_tracker = SessionProgressTracker()

    # Initialize ServerState (shared across handlers)
    server_state = ServerState(
        evidence_repository=evidence_repo,
        hypothesis_repository=hypothesis_repo,
        thinking_repository=thinking_repo,
        reasoning_repository=reasoning_repo,
    )

    # Initialize handlers
    # NEW in 2.0: Cognitive layer + Medical reasoning handlers (use ServerState)
    thinking_handlers = ThinkingHandlers(server_state)
    evidence_handlers = EvidenceHandlers(
        server_state,
        session_repository=session_repo,
    )
    dd_handlers = DDHandlers(server_state)
    reasoning_handlers = ReasoningHandlers(server_state)
    contract_handlers = ContractHandlers(
        server_state,
        session_repository=session_repo,
        fishbone_repository=fishbone_repo,
        why_tree_repository=why_tree_repo,
        template_root=config_path / "templates",
    )

    # Existing RCA handlers
    hfacs_handlers = HFACSHandlers(
        hfacs_suggester,
        learned_rules_service,
        fishbone_repository=fishbone_repo,
    )
    session_handlers = SessionHandlers(session_repo, progress_tracker)
    fishbone_handlers = FishboneHandlers(
        fishbone_repo,
        session_repo,
        progress_tracker,
    )
    why_tree_handlers = WhyTreeHandlers(
        why_tree_repo,
        session_repo,
        progress_tracker,
    )
    verification_handlers = VerificationHandlers(
        progress_tracker=progress_tracker,
        server_state=server_state,
        session_repository=session_repo,
        why_tree_repository=why_tree_repo,
    )
    facade_handlers = FacadeHandlers(
        evidence_handlers=evidence_handlers,
        dd_handlers=dd_handlers,
        thinking_handlers=thinking_handlers,
        reasoning_handlers=reasoning_handlers,
        contract_handlers=contract_handlers,
        verification_handlers=verification_handlers,
        session_handlers=session_handlers,
        fishbone_handlers=fishbone_handlers,
        why_tree_handlers=why_tree_handlers,
        hfacs_handlers=hfacs_handlers,
    )

    _runtime.server_state = server_state
    _runtime.thinking_handlers = thinking_handlers
    _runtime.evidence_handlers = evidence_handlers
    _runtime.dd_handlers = dd_handlers
    _runtime.reasoning_handlers = reasoning_handlers
    _runtime.contract_handlers = contract_handlers
    _runtime.hfacs_handlers = hfacs_handlers
    _runtime.session_handlers = session_handlers
    _runtime.fishbone_handlers = fishbone_handlers
    _runtime.why_tree_handlers = why_tree_handlers
    _runtime.verification_handlers = verification_handlers
    _runtime.facade_handlers = facade_handlers
    _runtime.database = database

    # Keep startup logs ASCII-safe for Windows remote extension-host pipes.
    logger.info("All handlers initialized")

    try:
        yield
    finally:
        logger.info("Shutting down RootCause MCP Server...")
        database.close()
        _runtime.clear()
        config_context.__exit__(None, None, None)


async def on_list_tools(_ctx: ServerRequestContext, _params: Any) -> ListToolsResult:
    """
    List all available MCP tools (SDK 2.0 callback).

    Returns:
        ListToolsResult with all tool definitions
    """
    profile = _runtime.tool_profile or _get_tool_profile()
    return ListToolsResult(tools=get_all_tools(profile))


ToolHandler = Callable[[dict[str, Any]], Awaitable[Any]]


async def _call_without_arguments(
    method: Callable[[], Awaitable[Any]], _arguments: dict[str, Any]
) -> Any:
    """Adapt a no-argument legacy handler to the common tool signature."""
    return await method()


def _build_tool_dispatch(profile: str | None = None) -> dict[str, ToolHandler]:
    """Build the explicit tool-to-handler registry for every advertised tool."""
    _thinking_handlers = _runtime.thinking_handlers
    _evidence_handlers = _runtime.evidence_handlers
    _dd_handlers = _runtime.dd_handlers
    _reasoning_handlers = _runtime.reasoning_handlers
    _contract_handlers = _runtime.contract_handlers
    _hfacs_handlers = _runtime.hfacs_handlers
    _session_handlers = _runtime.session_handlers
    _fishbone_handlers = _runtime.fishbone_handlers
    _why_tree_handlers = _runtime.why_tree_handlers
    _verification_handlers = _runtime.verification_handlers
    handlers = (
        _thinking_handlers,
        _evidence_handlers,
        _dd_handlers,
        _reasoning_handlers,
        _contract_handlers,
        _hfacs_handlers,
        _session_handlers,
        _fishbone_handlers,
        _why_tree_handlers,
        _verification_handlers,
    )
    if any(handler is None for handler in handlers):
        raise RuntimeError("Server handlers are not initialized")

    assert _thinking_handlers is not None
    assert _evidence_handlers is not None
    assert _dd_handlers is not None
    assert _reasoning_handlers is not None
    assert _contract_handlers is not None
    assert _hfacs_handlers is not None
    assert _session_handlers is not None
    assert _fishbone_handlers is not None
    assert _why_tree_handlers is not None
    assert _verification_handlers is not None

    dispatch: dict[str, ToolHandler] = {
        name: partial(_thinking_handlers.handle, name)
        for name in (
            "rc_think_aloud",
            "rc_reflect",
            "rc_identify_gaps",
            "rc_challenge_assumption",
            "rc_get_thinking_chain",
        )
    }
    dispatch.update(
        {
            name: partial(_evidence_handlers.handle, name)
            for name in (
                "rc_add_evidence",
                "rc_get_evidence",
                "rc_verify_evidence",
            )
        }
    )
    dispatch.update(
        {
            name: partial(_dd_handlers.handle, name)
            for name in (
                "rc_propose_hypothesis",
                "rc_audit_differential_breadth",
                "rc_link_evidence_to_hypothesis",
                "rc_select_leading_hypothesis",
                "rc_get_differential_diagnosis",
                "rc_exclude_hypothesis",
            )
        }
    )
    dispatch.update(
        {
            name: partial(_reasoning_handlers.handle, name)
            for name in (
                "rc_get_reasoning_chain",
                "rc_export_reasoning_chain",
                "rc_audit_reasoning_state",
                "rc_detect_conflicts",
                "rc_create_checkpoint",
                "rc_restore_checkpoint",
                "rc_list_checkpoints",
            )
        }
    )
    dispatch["rc_generate_contract_report"] = partial(
        _contract_handlers.handle, "rc_generate_contract_report"
    )
    dispatch.update(
        {
            "rc_suggest_hfacs": _hfacs_handlers.handle_suggest_hfacs,
            "rc_confirm_classification": (
                _hfacs_handlers.handle_confirm_classification
            ),
            "rc_get_hfacs_framework": _hfacs_handlers.handle_get_framework,
            "rc_get_6m_hfacs_mapping": (_hfacs_handlers.handle_get_6m_hfacs_mapping),
            "rc_list_learned_rules": _hfacs_handlers.handle_list_learned_rules,
            "rc_reload_rules": partial(
                _call_without_arguments, _hfacs_handlers.handle_reload_rules
            ),
            "rc_start_session": _session_handlers.handle_start_session,
            "rc_adjudicate_source": _session_handlers.handle_adjudicate_source,
            "rc_get_session": _session_handlers.handle_get_session,
            "rc_list_sessions": _session_handlers.handle_list_sessions,
            "rc_archive_session": _session_handlers.handle_archive_session,
            "rc_init_fishbone": _fishbone_handlers.handle_init_fishbone,
            "rc_add_cause": _fishbone_handlers.handle_add_cause,
            "rc_get_fishbone": _fishbone_handlers.handle_get_fishbone,
            "rc_export_fishbone": _fishbone_handlers.handle_export_fishbone,
            "rc_ask_why": _why_tree_handlers.handle_ask_why,
            "rc_get_why_tree": _why_tree_handlers.handle_get_why_tree,
            "rc_mark_root_cause": _why_tree_handlers.handle_mark_root_cause,
            "rc_add_causal_link": _why_tree_handlers.handle_add_causal_link,
            "rc_export_why_tree": _why_tree_handlers.handle_export_why_tree,
            "rc_build_teaching_case": _why_tree_handlers.handle_build_teaching_case,
            "rc_verify_causation": (_verification_handlers.handle_verify_causation),
            "rc_validate_diagram": (_verification_handlers.handle_validate_diagram),
            "rc_render_timeline": (_verification_handlers.handle_render_timeline),
        }
    )
    _facade_handlers = _runtime.facade_handlers
    if _facade_handlers is not None:
        dispatch.update(
            {
                "rc_evidence": _facade_handlers.handle_evidence,
                "rc_hypothesis": _facade_handlers.handle_hypothesis,
                "rc_thinking": _facade_handlers.handle_thinking,
                "rc_audit": _facade_handlers.handle_audit,
                "rc_report": _facade_handlers.handle_report,
                "rc_diagram": _facade_handlers.handle_diagram,
                "rc_checkpoint": _facade_handlers.handle_checkpoint,
                "rc_rca": _facade_handlers.handle_rca,
            }
        )
    active_profile = profile or _runtime.tool_profile or _get_tool_profile()
    visible_tool_names = {tool.name for tool in get_all_tools(active_profile)}
    return {
        name: handler
        for name, handler in dispatch.items()
        if name in visible_tool_names
    }


def _compact_structured_text(result: dict[str, Any]) -> str:
    """Build a bounded text fallback without duplicating structured content."""
    summary: dict[str, Any] = {}
    preferred_keys = (
        "status",
        "message",
        "session_id",
        "report_id",
        "evidence_id",
        "hypothesis_id",
        "thinking_step_id",
        "reflection_id",
        "gap_id",
        "challenge_id",
        "format",
        "output_path",
        "finalized",
        "verified",
        "probability_semantics",
        "clinical_probability_established",
        "quality_score",
    )
    for key in preferred_keys:
        value = result.get(key)
        if isinstance(value, str):
            summary[key] = value if len(value) <= 240 else f"{value[:237]}..."
        elif key in result and (isinstance(value, int | float | bool) or value is None):
            summary[key] = value

    for key, value in result.items():
        is_count = key.startswith("total_") or key.endswith(
            ("_count", "_steps", "_nodes", "_edges")
        )
        if is_count and isinstance(value, int | float):
            summary.setdefault(key, value)

    if "guidance" in result and isinstance(result["guidance"], dict):
        g = result["guidance"]
        if "current_stage" in g:
            summary["stage"] = g["current_stage"]
        if "completeness_score" in g:
            with suppress(ValueError, TypeError):
                summary["completeness"] = f"{float(g['completeness_score']):.0%}"
        if g.get("next_recommended_actions") and isinstance(
            g["next_recommended_actions"], list
        ):
            summary["next_prompt"] = str(g["next_recommended_actions"][0])[:180]

    summary.setdefault("status", "success")
    summary["detail"] = "structuredContent"
    summary["fallback"] = (
        "Set ROOTCAUSE_RESPONSE_MODE=verbose if structuredContent is unavailable"
    )
    return json.dumps(summary, ensure_ascii=False, separators=(",", ":"), default=str)


def _to_call_tool_result(result: Any) -> CallToolResult:
    """Normalize modern dict and legacy content responses for MCP SDK 2.0."""
    if isinstance(result, CallToolResult):
        return result
    if isinstance(result, dict):
        response_mode = _runtime.response_mode or _get_response_mode()
        text = (
            json.dumps(result, ensure_ascii=False, indent=2, default=str)
            if response_mode == "verbose"
            else _compact_structured_text(result)
        )
        return CallToolResult(
            content=[TextContent(type="text", text=text)],
            structured_content=result,
            is_error=str(result.get("status", "success")).lower() == "error",
        )
    if isinstance(result, (list, tuple)):
        content: list[Any] = [
            item
            if isinstance(item, TextContent)
            else TextContent(type="text", text=str(item))
            for item in result
        ]
        text_content = [
            item.text if isinstance(item, TextContent) else str(item)
            for item in content
        ]
        error_text = next(
            (
                text
                for text in text_content
                if text.lstrip().startswith(("Error:", "❌"))
            ),
            None,
        )
        structured_content: dict[str, Any] = {
            "status": "error" if error_text else "success",
            "content": text_content,
        }
        session_id = _extract_legacy_markdown_value(
            text_content,
            markers=("**Session ID:** `", "**Session:** `"),
        )
        if session_id is not None:
            structured_content["session_id"] = session_id
        return CallToolResult(
            content=content,
            structured_content=structured_content,
            is_error=error_text is not None,
        )
    return CallToolResult(content=[TextContent(type="text", text=str(result))])


def _extract_legacy_markdown_value(
    text_content: list[str],
    *,
    markers: tuple[str, ...],
) -> str | None:
    """Expose key legacy Markdown identifiers in structured MCP responses."""
    for text in text_content:
        for marker in markers:
            if marker not in text:
                continue
            value = text.split(marker, 1)[1].split("`", 1)[0].strip()
            if value:
                return value
    return None


def _argument_matches_type(value: Any, expected: str) -> bool:
    """Check the JSON primitive types used by the public tool schemas."""
    checks = {
        "string": lambda: isinstance(value, str),
        "boolean": lambda: isinstance(value, bool),
        "integer": lambda: isinstance(value, int) and not isinstance(value, bool),
        "number": lambda: isinstance(value, int | float)
        and not isinstance(value, bool),
        "array": lambda: isinstance(value, list | tuple),
        "object": lambda: isinstance(value, dict),
    }
    check = checks.get(expected)
    return check() if check is not None else True


def _validate_argument_value(
    key: str,
    value: Any,
    definition: dict[str, Any],
) -> str | None:
    """Validate one value against the basic constraints advertised to clients."""
    expected = definition.get("type")
    if isinstance(expected, str) and not _argument_matches_type(value, expected):
        return f"argument '{key}' must be {expected}"

    allowed = definition.get("enum")
    if isinstance(allowed, list) and value not in allowed:
        return f"argument '{key}' must be one of {allowed}"

    if not isinstance(value, int | float) or isinstance(value, bool):
        return None
    minimum = definition.get("minimum")
    maximum = definition.get("maximum")
    if minimum is not None and value < minimum:
        return f"argument '{key}' must be >= {minimum}"
    if maximum is not None and value > maximum:
        return f"argument '{key}' must be <= {maximum}"
    return None


def _normalize_and_validate_arguments(
    tool_name: str,
    arguments: dict[str, Any],
) -> tuple[dict[str, Any], str | None]:
    """Apply advertised top-level defaults and reject invalid basic arguments."""
    profile = _runtime.tool_profile or _get_tool_profile()
    tool = next(
        (item for item in get_all_tools(profile) if item.name == tool_name), None
    )
    normalized = dict(arguments)
    validation_error: str | None = None
    if tool is not None:
        schema = tool.input_schema
        properties = schema.get("properties", {})
        for key, definition in properties.items():
            if key not in normalized and "default" in definition:
                default = definition["default"]
                if default is not None:
                    normalized[key] = default

        missing = [key for key in schema.get("required", []) if key not in normalized]
        if missing:
            validation_error = f"missing required argument(s): {', '.join(missing)}"

        for key, value in normalized.items():
            if validation_error is not None:
                break
            definition = properties.get(key)
            if not isinstance(definition, dict):
                continue
            validation_error = _validate_argument_value(key, value, definition)
    return normalized, validation_error


async def on_call_tool(
    _ctx: ServerRequestContext, params: CallToolRequestParams
) -> CallToolResult:
    """
    Handle tool calls (SDK 2.0 callback).

    Routes tool calls to appropriate handlers based on tool name prefix.

    Args:
        ctx: Server request context
        params: Tool call parameters (name + arguments)

    Returns:
        CallToolResult with tool execution result
    """
    tool_name = params.name
    arguments = params.arguments or {}

    try:
        handler = _build_tool_dispatch().get(tool_name)
        if handler is None:
            return CallToolResult(
                content=[
                    TextContent(type="text", text=f"Error: Unknown tool '{tool_name}'")
                ],
                is_error=True,
            )
        arguments, validation_error = _normalize_and_validate_arguments(
            tool_name,
            arguments,
        )
        if validation_error is not None:
            payload = {
                "status": "error",
                "error_code": "INVALID_ARGUMENT",
                "message": validation_error,
            }
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error: {validation_error}")],
                structured_content=payload,
                is_error=True,
            )
        return _to_call_tool_result(await handler(arguments))
    except Exception:
        logger.exception("Error executing tool %s", tool_name)
        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=(
                        f"Error executing {tool_name}: internal tool failure. "
                        "Inspect the server log for details."
                    ),
                )
            ],
            structured_content={
                "status": "error",
                "error_code": "TOOL_EXECUTION_FAILED",
            },
            is_error=True,
        )


async def on_list_resources(
    _ctx: ServerRequestContext, _params: Any
) -> ListResourcesResult:
    """List available static clinical resources (playbooks, protocols, templates)."""
    return ListResourcesResult(resources=get_static_resources())


async def on_list_resource_templates(
    _ctx: ServerRequestContext, _params: Any
) -> ListResourceTemplatesResult:
    """List dynamic case session resource templates."""
    return ListResourceTemplatesResult(resource_templates=get_resource_templates())


async def on_read_resource(
    _ctx: ServerRequestContext, params: ReadResourceRequestParams
) -> ReadResourceResult:
    """Read clinical resource or dynamic session state by URI."""
    return await read_clinical_resource(
        str(params.uri),
        server_state=_runtime.server_state,
        contract_handler=_runtime.contract_handlers,
    )


async def on_list_prompts(
    _ctx: ServerRequestContext, _params: Any
) -> ListPromptsResult:
    """List predefined clinical investigation prompts."""
    return ListPromptsResult(prompts=get_all_prompts())


async def on_get_prompt(
    _ctx: ServerRequestContext, params: GetPromptRequestParams
) -> GetPromptResult:
    """Get structured prompt messages for clinical investigation."""
    return get_prompt_result(params.name, params.arguments)


# Create server instance with SDK 2.0 API, resources, prompts, and instructions
server = Server(
    "rootcause-mcp",
    version="2.0.0a2",
    title="RootCause MCP: Clinical Reasoning & Medical RCA Harness",
    description=(
        "Auditable evidence ledger, broad differential-diagnosis workflow, "
        "provenance checks, and conservative medical root-cause analysis."
    ),
    instructions=(
        "RootCause MCP does not reason, diagnose, or prove clinical causality. It persists and validates the host "
        "Agent's evidence-linked case model for qualified-clinician review. Use Traditional Chinese prose for "
        "clinician-facing discussion while keeping medical terminology in English. Separate exact observations, "
        "clinical inferences, unknowns, planned tests, and causal claims. First anchor atomic evidence to source "
        "snippets, locations, hashes, and time precision. Then select a syndrome-appropriate mechanism framework "
        "such as 5H5T, VINDICATE, anatomic/system localization, or medication/device/exposure review. Expand the "
        "DDx beyond the minimum three until another candidate adds no distinct mechanism, safety risk, or "
        "discriminating test; avoid unprioritized rare-disease lists. For every active DDx record why it is plausible, "
        "evidence for and against, neutral context, case-specific unknowns, a typed rule-out/disconfirm/discriminate "
        "plan when evidence is incomplete, and qualitative certainty. Apply only justified direct likelihood ratios; "
        "LR=1.0 is neutral and cannot satisfy support or disconfirmation. Keep medical DDx separate from Fishbone, "
        "5-Why, HFACS, and conservative causation audit. Preview reports before finalization. A final report requires "
        "all hard conformance checks plus an authorized named human reviewer and remains decision support, not a "
        "validated diagnosis or treatment recommendation. Inspect clinical:// contracts at runtime; bundled domain "
        "playbooks are non-normative retrospective DDx prompts and never patient-specific management guidance."
    ),
    lifespan=lifespan,
    on_list_tools=on_list_tools,
    on_call_tool=on_call_tool,
    on_list_resources=on_list_resources,
    on_list_resource_templates=on_list_resource_templates,
    on_read_resource=on_read_resource,
    on_list_prompts=on_list_prompts,
    on_get_prompt=on_get_prompt,
)


async def _run_stdio_server() -> None:
    """Run the asynchronous stdio transport."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def main() -> None:
    """Synchronous console-script entry point."""
    asyncio.run(_run_stdio_server())


if __name__ == "__main__":
    main()
