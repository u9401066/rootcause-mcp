# Active Context - RootCause MCP

> Last updated: 2026-08-18

## Accepted Product Boundary

RootCause MCP is an engineering-alpha reasoning ledger for controlled,
retrospective clinical evaluation. A host agent inventories and extracts supplied
records; the MCP persists source-grounded atomic findings, differential diagnoses,
typed evidence relations, cognitive audit, system RCA, and deterministic standardized
reports. It is not a raw binary document parser, autonomous diagnostic system,
medical device, or substitute for qualified clinical review.

The canonical workflow is:

1. Pin a versioned multi-source manifest with stable document IDs and whole-file
   SHA-256 digests.
2. Append allowlisted source review/de-identification/independence events without
   mutating the pinned manifest identity or digest.
3. Register atomic evidence with exact source spans, location, typed source-faithful
   time, and an explicit verification state.
4. Build a mechanism-based breadth audit, maintain at least three unique hypotheses,
   explicitly select the leading item, and preserve applicable must-not-miss items.
5. Use direct LR only when distinct verified literature evidence establishes its
   calibration; otherwise retain a neutral qualitative relationship and typed tests.
6. Record uncertainty, alternatives, missing data, and cognitive-bias review.
7. Build Fishbone and 5-Why artifacts, obtain authorized per-cause HFACS review, and persist a
   conservative causation audit for each proposed root with exact root/evidence
   ledger identity.
8. Run readiness/conflict checks, preview the unified report, then require an
   operator-authorized human before a content-hashed final snapshot.

## Release-blocking Invariants

- Refuting evidence never raises the posterior through server-side LR inversion.
- File or location existence alone never verifies clinical content.
- Every final report has at least two reviewed, de-identified independent source
  roots backed by append-only authorized adjudication; duplicate bytes, derivatives,
  undeclared evidence, and unresolved processing block release.
- Date/range/relative/unknown time stays unpositioned; only source-aware instants may
  establish chronology or causation temporality.
- Array order and compatibility numbers never choose the leading diagnosis. A
  non-neutral LR needs verified case-local literature calibration evidence.
- Every Fishbone cause has a ledger-exact authorized HFACS CONFIRMED or
  NOT_APPLICABLE review.
- Final conclusions exclude ruled-out/on-hold hypotheses and distinguish proposed
  roots, contributing factors, correlation, and insufficient causal evidence.
- Rejected causal claims are absent from the root bucket; insufficient-data roots
  remain proposed, and audit passes never claim clinical causality established.
- The final boundary recomputes machine-readable conformance checks, requires an
  authorized reviewer/time/hash, and recursively rejects nested mutation.
- The unified output contains source inventory, DDx/evidence, timeline, cognitive
  audit, Fishbone/Why/HFACS, persisted causation results, gaps/readiness, approval,
  and integrity hashes.
- Codex, Claude, Cline, and Copilot guidance use the same stage order and safety
  boundary. Live MCP schemas override copied examples.

## Current Engineering State

- The native acceptance test exercises the public MCP callback/lifespan across
  three physical text sources from manifest creation through authorized final
  output.
- The 2.0.0a3 release exposes 46 all-profile tools, 25 clinical tools,
  24 RCA tools, 8 condensed facades, 19 resources, 4 resource templates, and 5 prompts.
- The frozen release run passes 486 tests with 84.59% branch coverage plus Ruff,
  Mypy, Bandit, Vulture, dependency audit, build/Twine, installed-wheel stdio, and
  desktop/mobile browser QA. GitHub CI remains authoritative after push.
- The six-case script is a synthetic `PRELIMINARY` regression/demo. It intentionally
  does not claim finalization, release acceptance, or clinical correctness.
- The neutral public Agent-eval corpus and runner are engineering references only.
  Formal 3-runtime × 6-case × 2-repeat evaluation, repository-external private
  cases and private-gold isolation, trusted MCP traces, and blinded two-clinician
  review remain
  `AGENT_EVAL_NOT_ESTABLISHED`.
- Packaged configuration and MCP resources work from an installed wheel. Runtime
  data defaults to the platform user-data directory; exports and checkpoints use
  confined, integrity-checked paths with restrictive permissions where supported.
- CI covers Python 3.12/3.13 lint, format, strict typing, branch coverage,
  ResourceWarning enforcement, low-severity Bandit scanning, frozen dependency
  audit, package metadata, and clean installed-wheel smoke tests.
- Current test counts, coverage, typing, security, dependency, and packaging results
  are taken from the active CI/release run rather than copied into this context file.

## Known Production Gaps

1. No built-in PDF/DOCX/image/EHR batch parser; the host must use an approved
   extractor and preserve citation-ready spans.
2. Protocol/domain YAML is exposed to agents, but readiness, gap, and timeline
   behavior is not yet driven by a versioned runtime PolicyCatalog pinned to each
   session.
3. Reviewer allowlisting is an operator identity check, not full authentication,
   trusted RBAC, tenant isolation, or authorization federation.
4. Encryption-at-rest, deployment-specific PHI controls, retention enforcement,
   audit-log custody, and WORM records storage remain deployment responsibilities.
5. No formal database migration framework exists for multi-version production
   upgrades.
6. The conservative MVP causation validator records an audit outcome but does not
   independently prove clinical causation; insufficient evidence remains explicit.
7. Corrective-action ownership, due dates, and effectiveness follow-up may be
   supplied in host handoff supplements but are not yet first-class persisted
   domain entities in the canonical report.
8. The v1 source manifest identity is pinned at session creation and has no source
   append/amend API. Review state can advance through `rc_adjudicate_source`, but late
   sources still require a controlled superseding-session replay with prior-session
   lineage in the host handoff.
9. Historical tracked `data/`, example records, editor configuration, and hook
   state are excluded from new source distributions but remain in Git. A
   maintainer must classify example provenance, add compliant fixture manifests,
   and approve any removal/history-cleanup operation.

## Entry Points

- CLI / stdio: `uv run rootcause-mcp`
- Python: `rootcause_mcp.server_v2:main`
- Data root: `ROOTCAUSE_DATA_DIR`, otherwise the OS user-data directory
- Source allowlist: `ROOTCAUSE_SOURCE_ROOTS`
- Manual/final reviewer allowlist: `ROOTCAUSE_AUTHORIZED_REVIEWERS`
