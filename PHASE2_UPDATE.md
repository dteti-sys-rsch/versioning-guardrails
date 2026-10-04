# AtomicRoot — audit and Phase 2 update, 2026-10-04

Scope: the updated user brief in this chat replaces the earlier requirement
to maintain a native policy oracle. No AGENTS.md or additional phase brief was
found in the workspace. No persistent SQLite database was found. The directory
has no `.git`, so changes are delivered as workspace files without Git commits.

Baseline actually run: `python -m pytest atomicroot/tests -q` — **35 passed**.

## Audit matrix

| Requirement | Source / test evidence | Audit before patch | Final status |
|---|---|---|---|
| Z3 only | `policies/*.py`; expected budget/taint tests | Active path correct; native oracle obsolete | Aligned: native functions removed; no fallback or differential requirement |
| Consistent values/versions/provenance | `snapshot`, `StatusReader`; mixed snapshot test | Correct | Preserved |
| Atomic CAS/state/event/versions/single use | `TraceStore.commit`; rollback/nonce/concurrent replay | Correct | Preserved |
| Signature/caller/expiry/immutable args | `ticket.py`, `gateway.py`; signed-field and argument mutation tests | Commit path correct; authorization alias unsafe | Patched: freeze request at authority entrance with the same canonical JSON rule |
| Trusted Footprint/write set/class/effect kind | Policy modules; worker tampering and label tests | Write set correct; unknown label treated nonsensitive | Patched: unsupported labels fail; all effects remain simulated |
| All policies/versioned membership | `configure_tool_policies`; changed membership and concurrent snapshot membership tests | Membership lacked version | Patched: `policies:<tool>` read in same snapshot and included in every ticket |
| Monotone mutations/frozen definitions | `set_state`, `register_task_state`, immutable defaults test | Mutable policy map; test setter could lower version | Patched: immutable tables/context; membership versioned; setter rejects decreases |
| Taint before sensitive result release | Commit then effect; `test_sensitive_result_waits_for_committed_taint` | Correct | Preserved and explicitly tested at `after_commit` barrier |
| Hooks/connection concurrency | Existing harness, real two-connection CAS/replay/mixed snapshot | Correct | Preserved; membership interleaving added without sleeps |
| Shared typed AST/static dependency pass | `ast_type`, `dependencies`, `encode`; branch/type/limit tests | Missing explicit complexity/type checks | Patched: all branches checked; node/depth/input/fact limits |
| Missing facts vs official initial state | `register_task_state`, `StatusReader`; missing registered/unregistered fact tests | Implicit empty/zero defaults | Patched: explicit initial rows at version zero; absent facts error |
| Integer cumulative money | Budget AST; expected exact/one-unit/cumulative/malformed/max tests | Cumulative integer semantics correct | Preserved; 63-bit input bounds added |
| Query convention/consistency/failure handling | `solve`; actual contradictory-facts injection, UNKNOWN/timeout/exception/UNSAT/witness tests | Convention correct | Preserved; finite timeout/resource limits and explicit error diagnostics |
| Instruction trust separate from confidentiality | Public/internal/finance/sensitive content tests | Needs explicit validation/docs | Aligned: content never determines trusted label; unsupported label is an error |

## Reproduction before patch

`test_phase2_update.py` was added and run before implementation changes:
**4 failed**. It reproduced issuance for an unregistered task, issuance for a
document with unsupported `UNKNOWN` classification, an argument hash bound to
999 after evaluating 50, and a successful commit after active policy membership
was changed. Security assertions will be preserved; the membership mutation
test will use the new trusted versioned configuration API after patching.

## Migration notes

1. The public `evaluate(task_context, trace_snapshot, request) -> PolicyResult`,
   authorization/commit response fields, signed ticket field names, FastAPI,
   SQLite WAL and PyNaCl remain. Canonical signature/hash bytes use the same
   sorted-key JSON, compact separators, UTF-8, `ensure_ascii=False`, no NaN,
   and full SHA-256 rule. The helper now also freezes caller-owned input.
2. Policy membership is an additive dependency. The immutable defaults seed
   version-zero `policies:<tool>` rows without overwriting existing membership.
   Only trusted service configuration can change the list; the two current
   policy names are validated and default guards cannot be removed. This is
   a small membership/version mechanism, not a general registry or authoring UI.
3. Newly registered tasks atomically get `taint=[]`, `budget=0` at version
   zero and a contract row. Re-registering an existing task never resets spend
   or taint. An older database with missing task facts must be explicitly
   migrated using verified stored state/trace; this patch does not silently
   reconstruct zero. No persistent database in this workspace required migration.
4. Old signed tickets without the membership dependency must be reauthorized
   once the service has initialized that tool's policy membership. Commit rejects
   them even if an old signing key is reused. Low-level trusted signing fixtures
   without a service registry still test CAS mechanics independently.
5. Native functions and their duplicate result classes were removed from the
   two production policy modules. Existing differential tests were replaced by
   explicit expected outcomes and dependency assertions. There is no second
   policy backend to maintain. Solver failure cannot select an alternative backend.
6. Valid registered-task policy outcomes remain the same. Unregistered/missing
   facts, unsupported labels, malformed or oversized values now fail with
   `EVALUATION_ERROR`. Python still performs validation/compiler/orchestration;
   Z3 alone evaluates the compiled safety constraints.
7. One physical SQLite writer remains. Independent task state may share the
   read-only membership dependency; ordinary commits do not change it, so both
   tasks still succeed without making the other's ticket stale.

## Soundness obligation and extension boundary

For a fixed request and policy definition, changing state only outside the
Footprint must not change the decision. Every mutation of a relevant fact must
bump its version. Static and dynamic dependencies, membership and provenance
use the same pinned snapshot. Small-domain tests inspect this obligation;
they are not a general proof. Conservative dependencies can still cause extra
aborts. Only trusted AST node types and fact-source descriptors are supported;
unsupported collections/enumerations fail. Future enumeration must include a
membership version to catch newly added members.

The implementation retains separate per-policy violation queries. On complete,
consistent concrete facts their all-UNSAT requirement is equivalent to querying
`facts AND NOT(all_applicable_constraints)`. All policies run; any evaluation
failure blocks issuance. No SAT/UNSAT inversion or evaluator migration was needed.

Limits: 256 AST nodes, depth 32, 64 KiB canonical JSON input, 16 KiB per fact;
up to 1,000 ms per solver check and Z3 resource limit 100,000. UNKNOWN from the
solver is an operational failure, distinct from an unsupported confidentiality
label called UNKNOWN. No ordinary approval can turn either into an ALLOW.

## Deferred to Phase 3

- Full registry and richer trusted fact/contract/label provenance.
- Authoring/compilation and identity resolution for more supported fact sources,
  including collection membership/version rules.
- An explicit design for versioning policy definitions across deployments and
  integrating caller authentication with a real host runtime.

Four additional policies, outbox, approval broker, full adversarial scheduler,
agent frameworks/LLMs, Redis and large benchmarks remain outside this patch.

## Files changed

- `atomicroot/authority/authority.py`: frozen request/configuration and versioned policy selection.
- `atomicroot/authority/policy_engine.py`: strict facts, source descriptors, typed/limited AST and solver diagnostics.
- `atomicroot/authority/policies/{budget_monotone,no_exfil_after_sensitive}.py`: only Z3 wrappers; obsolete native code removed.
- `atomicroot/authority/ticket.py`, `atomicroot/gateway/gateway.py`: shared canonical freezing and input limits.
- `atomicroot/store/trace_store.py`: atomic official initial task facts, preserved membership initialization and monotone versions.
- `atomicroot/sim/worker.py`: preserves operational evaluation errors without calling Commit.
- `atomicroot/tests/test_phase2_policy.py`: explicit outcomes and valid witness assertions.
- `atomicroot/tests/test_phase2_update.py`: targeted update regressions and fault injection.
- `atomicroot/tests/test_parallel_disjoint.py`: clarification of read-only shared membership; security assertions unchanged.
- `README.md`, `PHASE2_UPDATE.md`: updated semantics, audit and migration notes.

## Actual final verification

Latest full test run: `python -m pytest atomicroot/tests -q` — **84 passed**.
`python -m compileall -q atomicroot` completed without compilation errors.
`python demo.py` completed successfully: the sensitive read committed, the email
ticket returned `STALE_TICKET` after the taint version changed, and the email
effect was not executed.
