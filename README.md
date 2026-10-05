# AtomicRoot — Phase 3 research prototype

AtomicRoot binds an ALLOW ticket to the versions of the policy state it read. A
Gateway accepts the ticket only if `Fresh(ticket, state)` holds inside the same
SQLite transaction that consumes the ticket, appends an event, updates policy
state, and bumps the write set. Tool effects remain simulated.

**Z3 remains the only policy evaluator.** Phase 3 extends the same AST, signing
format and SQLite Trace Store with reviewed contracts, a trusted fact/tool
registry, explicit labels, selective operation consent and a transactional
outbox. COMMITTED accepts an immutable intent; RELEASED records a durable
simulated receiver receipt. No real email, money transfer or deployment occurs.

See [PHASE3.md](PHASE3.md) for the API, grammar, source/update matrix, state
machines, actual test results and assumptions. Examples are in
[examples/phase3](examples/phase3). The manual CLI is [phase3_cli.py](phase3_cli.py).
The earlier audit and migration record remains in [PHASE2_UPDATE.md](PHASE2_UPDATE.md).

The conditional Phase 3 compatibility patch records classifier evidence
separately from authoritative labels and adds explicit provider ingestion scope
through the existing Gateway/outbox, with an offline simulator only. See
[PHASE3_COMPAT_AUDIT.md](PHASE3_COMPAT_AUDIT.md) for the requirement matrix,
additive migration, API changes and actual test results.

## Run

Python 3.11+:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[test]"
.\.venv\Scripts\python.exe -m pytest atomicroot/tests -q
.\.venv\Scripts\python.exe demo.py
.\.venv\Scripts\python.exe phase3_cli.py demo
.\.venv\Scripts\python.exe phase3_cli.py schema
```

For Phase 3 integrations use `FrameworkRuntime` and `create_phase3_app` from
`atomicroot.framework.app`. Supply a trusted identity resolver; worker bodies
cannot set their identity or role. The demo uses explicit named identity and
approval fixtures. The runtime never auto-approves.

The existing Phase 2 entry points and tests remain available for reproducible
baseline comparisons. Legacy direct-effect Commit rejects any activated Phase 3
task. Existing Phase 2 task data needs a reviewed explicit migration; it is not
silently relabelled or reset by the new Contract Service.

## Historical Phase 2 design (retained regression interface)

- `atomicroot/authority/policy_engine.py` defines a small typed AST (`Ref`,
  `Const`, `RequestAmount`, `Add`, `Le`, `Not`, `And`, `If`). Unknown nodes or
  unresolved identities fail with `EVALUATION_ERROR`, without a ticket. A
  static pass visits **every** branch. The same AST is encoded into Z3.
- `StatusReader` is the only policy-state read path. It reads values and
  versions from one pinned SQLite read transaction and records dynamic reads.
  The ticket Footprint is the union of static dependencies and dynamic reads;
  every key gets its version from that same snapshot. A newly registered task
  has explicit `taint=[]` and `budget=0` rows at version zero. A missing fact
  without such a definition is an error; no empty/zero/free-symbol fallback is
  used. The low-level version-vector CAS still treats absent keys as version
  zero, independently of policy fact validation. There are no wildcard CAS keys.
- Z3 facts bind validated request values and snapshot state. The violation
  query is `facts AND NOT(safe)`: SAT yields DENY and a model witness; UNSAT
  yields ALLOW; UNKNOWN, timeout, inconsistent facts, and encoding errors yield
  `EVALUATION_ERROR` without a ticket. Witness provenance comes from actual
  trace events in the same snapshot. The native production evaluators were
  removed; tests assert concrete expected decisions, boundaries, witnesses,
  dependencies and security regressions. There is no Python fallback.
- Each applicable policy has its own violation query on the same pinned
  snapshot. For validated concrete facts this is equivalent to
  `facts AND NOT(all_applicable_constraints)`: ALLOW requires every individual
  query to be UNSAT. All policies are evaluated even after an earlier DENY;
  any incomplete/error result prevents issuance. A separate consistency check
  prevents contradictory facts from making the violation query vacuously UNSAT.
- Trusted configuration changes to `contract:<task_id>` and `class:<doc_id>`
  increment their version. `budget:<task_id>` holds integer smallest-unit
  cumulative spend; `taint:<task_id>` holds observed classes. A sensitive
  document read records taint in the Commit before its simulated result is
  available. Worker-supplied `data_class` must match trusted classification.
  The active policy membership lives at `policies:<tool>` and is included in
  every authorization Footprint. The trusted `configure_tool_policies` method
  changes membership with a version bump; adding a rule invalidates pending
  tickets. Initialization by another authority preserves existing membership.
  Default tool/policy mappings and fact-source descriptors are immutable;
  external tool definitions are copied into a frozen service context. Those
  definitions are fixed for the service lifetime. Hot code/definition changes
  and deployment key management require a later integration design.
- The supported DSL is extensible through trusted node types and immutable
  `FactSource` descriptors (scope, type, decoder, conflict-key prefix). It is
  not limited to a permanent domain catalog. Unknown nodes/sources and type
  errors fail explicitly. No arbitrary natural-language policies, Python
  `eval`, worker SQL or worker/LLM-supplied Z3 scripts are executed.
- Limits: 256 AST nodes, depth 32, 64 KiB canonical request/argument/ticket
  payloads, 16 KiB per state fact, and a solver timeout of at most 1,000 ms
  per check with resource limit 100,000. Money is an integer from 0 to
  `2^63-1`; examples use one unit = one IDR. The current state machine checks
  committed cumulative spend plus the proposed amount; it has no reservation
  or external-effect state. Solver UNKNOWN/timeout is `EVALUATION_ERROR`.
  A confidentiality label `UNKNOWN` is also unsupported, for a different
  reason: it is not an established fact in this prototype.
- External document content is always untrusted as instructions. Its
  confidentiality is independently supplied by the trusted class fact:
  `public`/`internal` reads do not automatically create sensitive taint.
- `atomicroot/sim/harness.py` records `(step, action_id, stage)` and can pause
  at `snapshot_authorization`, `ticket_issued`, `before_cas`, and
  `after_commit`. `recorded_schedule()` can be supplied to a new harness as
  `replay=...` to enforce the same checkpoint order. It supports explicit
  interleavings; it is not the Phase 4
  adversarial scheduler. The FastAPI adapter in `atomicroot/api.py` requires a
  host-supplied trusted caller identity resolver. The `SimulatedWorker` identity
  is a test fixture identity, not a production authentication system.

### Soundness target and limits

For a fixed request and fixed definition of one of the two supported policies,
changes only outside its Footprint must not change its decision. Every change
to a state value inside the Footprint must bump that key's version. This is a
design obligation for the supported DSL, not a general proof for arbitrary
Python or SMT. Static analysis can over-approximate: `read_document` includes
`taint:<task_id>` even though its current branch does not inspect taint. A
taint change can therefore abort that read conservatively. Collection
enumeration is not supported; a future collection policy would need a
membership/version key to avoid phantom dependencies.

SQLite WAL allows readers alongside one writer, but only **one physical writer
transaction at a time**. The key-separation acceptance criterion is that both
commits succeed without a false stale result, not simultaneous writes.

## What the race tests show

In the exfiltration scenario, an email and a finance-document read both get
ALLOW against the original state. The read commits first and taints the task.
With the deliberately configured baseline Gateway that skips Fresh, the email
executes. With AtomicRoot, its ticket is a Stale ticket and no email effect is
recorded. The budget race similarly permits two individual 700,000-unit
transfers against a 1,000,000-unit cap at authorization, then rejects the
second Commit as stale. Unrelated keys do not invalidate each other.

## Phase 1 audit corrections

- Policy values previously lived in a separate mutable dictionary and were
  manually changed **after** Commit in tests. They could be paired with a
  newer SQLite version, and sensitive data could become visible before taint.
  They now live in the versioned SQLite row and change in Commit.
- `ticket_id` and nonce were not consumed; a ticket with an empty write set
  could execute repeatedly. Unique constraints now reject replay atomically.
- Caller identity, trusted document classification, and ticket time bounds
  were not checked. The Gateway now checks those, signature, and the full
  SHA-256 canonical argument hash. Caller-owned ticket and argument containers
  are frozen before verification, and expiry is checked again inside Commit.
  Baseline bypass is enabled only in explicit test fixtures.
- Contract caps were mutable without version tracking; they now use
  `contract:<task_id>` as a versioned dependency. The Fase 1 race tests no
  longer manually add taint/spend after Commit because Commit owns those
  updates. No valid ALLOW/DENY case for the two original policies changed.

The historical Phase 2 interface ends here. Phase 3 adds the simulated outbox
and approval workflow in `atomicroot/framework`; the four full policy benchmark
templates, full adversarial scheduler, agent frameworks/LLMs, and large
benchmarks remain outside the current scope.
