"""Durable inference memo and bounded attempts. Provider billing is not exactly once."""
import asyncio
import json
from atomicroot.authority.ticket import args_hash, freeze_json
from atomicroot.framework.storage import dumps, uid


class InferenceInProgress(RuntimeError): pass


class InferenceMemo:
    def __init__(self, store):
        self.store = store
        with store._lock:
            store._conn.executescript("""
                CREATE TABLE IF NOT EXISTS inference_jobs (
                    id TEXT PRIMARY KEY, binding TEXT NOT NULL, data TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS inference_memo (
                    id TEXT PRIMARY KEY, binding TEXT NOT NULL, response TEXT);
                CREATE TABLE IF NOT EXISTS inference_attempts (
                    id TEXT PRIMARY KEY, call_id TEXT NOT NULL, budget TEXT NOT NULL,
                    kind TEXT NOT NULL, model TEXT NOT NULL, started REAL NOT NULL,
                    status TEXT NOT NULL, usage TEXT, error TEXT,
                    reserved_tokens INTEGER NOT NULL, reserved_cost REAL NOT NULL);
            """)

    def job(self, key):
        with self.store._lock:
            row = self.store.row(self.store._conn, "SELECT data FROM inference_jobs WHERE id=?", (key,))
        return json.loads(row["data"]) if row else None

    def save_job(self, key, data):
        binding = args_hash(data)
        with self.store.transaction() as conn:
            row = self.store.row(conn, "SELECT binding FROM inference_jobs WHERE id=?", (key,))
            if row and row["binding"] != binding: raise ValueError("inference job binding mismatch")
            conn.execute("INSERT OR IGNORE INTO inference_jobs(id,binding,data) VALUES (?,?,?)", (key, binding, dumps(data)))
        return data

    async def run(self, key, budget, kind, model, payload, limits, invoke):
        payload = freeze_json(payload)
        binding = args_hash({"kind": kind, "model": model, "payload": payload})
        # Byte count is a conservative pilot input allowance, not reported usage.
        allowance = len(dumps(payload).encode("utf-8")) + limits.max_output_tokens
        price = ((allowance - limits.max_output_tokens) * (limits.input_price_per_million or 0)
                 + limits.max_output_tokens * (limits.output_price_per_million or 0)) / 1_000_000
        for _ in range(limits.max_retries + 1):
            with self.store.transaction() as conn:
                row = self.store.row(conn, "SELECT * FROM inference_memo WHERE id=?", (key,))
                if row and row["binding"] != binding: raise ValueError("memo payload/model/scope mismatch")
                if row and row["response"]: return json.loads(row["response"])
                active = self.store.row(conn, "SELECT id,started FROM inference_attempts WHERE call_id=? AND status='STARTED' ORDER BY rowid DESC LIMIT 1", (key,))
                if active:
                    if active["started"] + limits.timeout + 1 > self.store.now():
                        raise InferenceInProgress("inference already in progress; reconcile after bounded deadline")
                    conn.execute("UPDATE inference_attempts SET status='UNKNOWN',error='abandoned attempt; outcome ambiguous' WHERE id=?", (active["id"],))
                conn.execute("INSERT OR IGNORE INTO inference_memo(id,binding) VALUES (?,?)", (key, binding))
                attempts, tokens, cost = conn.execute("SELECT count(*),coalesce(sum(reserved_tokens),0),coalesce(sum(reserved_cost),0) "
                                                     "FROM inference_attempts WHERE budget=? AND kind=?", (budget, kind)).fetchone()
                per_call = conn.execute("SELECT count(*) FROM inference_attempts WHERE call_id=?", (key,)).fetchone()[0]
                if per_call >= limits.max_retries + 1 or attempts >= limits.max_calls or tokens + allowance > limits.max_tokens:
                    raise ValueError("inference call/token/retry cap reached")
                if limits.spend_cap_usd is not None and cost + price > limits.spend_cap_usd:
                    raise ValueError("inference spend cap reached")
                attempt = uid("attempt")
                conn.execute("INSERT INTO inference_attempts VALUES (?,?,?,?,?,?,'STARTED',NULL,NULL,?,?)",
                             (attempt, key, budget, kind, model, self.store.now(), allowance, price))
            try:
                # No SQLite transaction/lock crosses this await.
                async with asyncio.timeout(limits.timeout): response = freeze_json(await invoke())
            except Exception as exc:
                with self.store.transaction() as conn:
                    # Avoid provider exception bodies that might contain credentials/input.
                    conn.execute("UPDATE inference_attempts SET status='UNKNOWN',error=? WHERE id=?", (type(exc).__name__, attempt))
                if _ == limits.max_retries: raise RuntimeError("inference failed/ambiguous: " + type(exc).__name__) from None
                continue
            with self.store.transaction() as conn:
                usage = response.get("usage")
                reported = sum(v for v in usage.values() if type(v) is int and v >= 0) if type(usage) is dict else 0
                conn.execute("UPDATE inference_attempts SET status='RETURNED',usage=?,reserved_tokens=max(reserved_tokens,?) WHERE id=?", (dumps(usage), reported, attempt))
                conn.execute("UPDATE inference_memo SET response=? WHERE id=? AND binding=?", (dumps(response), key, binding))
            return response

    def attempts(self):
        with self.store._lock:
            return [dict(zip(("kind", "model", "status", "usage", "error"), row)) for row in self.store._conn.execute(
                "SELECT kind,model,status,usage,error FROM inference_attempts ORDER BY rowid")]
