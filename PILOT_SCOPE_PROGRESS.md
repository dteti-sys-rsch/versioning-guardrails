# Task scope dan log progress: patch setelah integrasi provider

## Audit requirement → evidence → patch

| Requirement | Bukti awal | Patch |
|---|---|---|
| Izin sesuai skenario | `pilot.py` memakai semua tools, recipients account/TypeSafe dan budget 1000 pada semua skenario dokumen | Profil per skenario, hanya resource/tool/recipient yang diperlukan |
| Classifier opsional | Rule TypeSafe untuk seluruh resource meskipun disabled | Scope classifier hanya jika benar-benar diaktifkan, target `paper` |
| Scope label/provider | Seluruh rule menerima PUBLIC/UNKNOWN | Label dokumen tepat untuk fixture; konteks mencakup UNKNOWN dan exposure yang diperlukan |
| Proposal tidak memperluas scope | Schema ContractService menerima kontrak enforceable yang lebih luas | Validator host pada author, revision, activation/resume dan active workflow |
| Progress lokal ringkas | Terminal terutama preview dan hasil akhir | Observer pada workflow, inference memo dan guarded adapter |
| Recovery/state preservation | Run config tidak mengikat profil/classifier | Scope revision dan classifier binding; konfigurasi berubah ditolak tanpa reset |

Baseline aktual sebelum patch: **253 passed in 16.94s**. Ini perbaikan konfigurasi
delegation pilot dan observability, bukan perubahan semantik Z3/CAS atau Fase 4.

## Scope baru

| Skenario | Business tools | Penerima bisnis | Budget | Resource |
|---|---|---|---|---|
| literature | read_document, send_email | alice@corp.id | 0 | dua sumber + dua konteks |
| injection | read_document, send_email | alice@corp.id | 0 | dua sumber + dua konteks |
| sensitive | read_document, send_email | alice@corp.id | 0 | dua sumber + dua konteks |
| unknown | read_document, send_email | alice@corp.id | 0 | dua sumber + dua konteks |
| budget | transfer_funds | account | 500 → review → maksimum 800 | dua konteks, tanpa dokumen sumber |

Semua profil membutuhkan `model_inference` dan provider yang dipilih host.
Purpose pembayaran `payments`; skenario dokumen `research`. UNKNOWN release hanya
ESCALATE pada skenario `unknown`; lainnya DENY. Sensitive fixture tetap menguji
hard DENY business release, sehingga send_email tetap ada sebagai aksi yang diuji.

Tanpa classifier: `classification_restrictions=false`, tidak ada classify_document,
recipient typesafe atau rule TypeSafe. Dengan `--classifier fake|replay|jev --classify`:
classify_document, TypeSafe dan restriction ditambahkan untuk **paper saja**.
Flag classifier/classify yang tidak berpasangan atau klasifikasi pada skenario
budget ditolak dengan pesan konfigurasi. Label/approval resmi tidak diubah.

Dokumen memiliki scope label yang sesuai fixture (PUBLIC, UNKNOWN, atau SENSITIVE).
Konteks model selalu diingest UNKNOWN dan menerima scope yang mencakup exposure
sumber task. Budget/unknown context hanya memerlukan UNKNOWN. Tidak ada wildcard
atau dependency baru yang mematikan dependency lama.

## Batas enforcement host

Proposal author/revision harus memakai exact task-required tools/resources/recipients/
agents, purpose, UNKNOWN rule, classifier setting dan rule provider/resource/labels.
Urutan set/rule boleh berubah. Budget non-finansial harus 0; budget pembayaran
awal 500, revisi hingga 800 tetap melalui Broker. Scope tidak ditambahkan diam-diam
dan requirement di luar profil harus dilaporkan untuk clarification.

Ini **validator konfigurasi delegation pilot**, bukan evaluator policy Python.
Z3 tetap evaluator policy aktif tunggal. ContractService umum tetap mendukung
proposal DSL yang valid dari jalur tepercaya; profil khusus ini dipasang pada
AgentWorkflow yang dibuat CLI. Custom constraints boleh menambah pembatasan dan
tetap diperiksa oleh ContractService/Z3. Objective masih teks bounded hasil LLM;
validator tidak membuktikan kesesuaian sempurna dengan goal bahasa alami.
`--goal` mengubah goal, tidak otomatis membuka profil tools/resources baru.
Reader/executor tetap berbagi tool delegation task; patch ini tidak menambah
schema per-role capability. JEV masih pilot sesudah workflow, belum pre-read gate.

## Progress

Contoh bentuk tampilan (ilustrasi, durasi bukan benchmark):

```text
[001] AUTHOR role=author repairs=0
[002] INFERENCE_CALL operation=op-... model=openai/gpt-oss-120b attempt=1
[003] INFERENCE_RETURNED operation=op-... elapsed_ms=...
[004] CONTRACT_VALIDATION status=VALID tools=3 budget=0
[005] CONTRACT_REVIEW status=PENDING review=review-...
...
[012] ACTION role=reader tool=read_document operation=op-... status=STAGED
[013] AUTHORIZATION tool=read_document operation=op-... status=ALLOW
[014] COMMIT tool=read_document operation=op-... status=COMMITTED
[015] DELIVERY tool=read_document operation=op-... status=RELEASED
```

`progress.jsonl` menyimpan metadata event, UTC time, sequence, operation/review IDs,
status dan usage/durasi saat tersedia. IDs hanya dipendekkan pada tampilan terminal;
file menyimpan ID lengkap. Success model egress diringkas; stale/error tetap terlihat.
`INFERENCE_CACHE` membedakan memo dari network call. Logging bersifat advisory:
failure sink tidak mengubah authorization/commit/effect, sehingga ledger tetap
sumber bukti otoritatif. Logs dapat berulang ketika node direplay; tidak diklaim
sebagai exactly-once audit ledger atau bukti formal.

Tidak ada prompt, response body, argument bisnis, content dokumen, signature,
credential atau header di progress log. Review yang memang dibutuhkan manusia
tetap memakai tampilan review existing. Ini berbeda dari dump seluruh stdout.

## Kompatibilitas dan file

- `pilot.py`, `prompts.py`, `workflow.py`: profil, batas host, prompt v2.
- `progress.py`, `memo.py`, `inference.py`, `guarded.py`: observer ringkas.
- CLI: wiring, paired classifier flags, `--quiet-progress`, run binding v2.
- Contoh author/config diperbarui; core schema dan DB tidak berubah.
- Test baru `test_pilot_scope_progress.py`.

Scope/prompt baru tidak ditempelkan ke ticket/grant/checkpoint lama. CLI meminta
directory baru jika binding berbeda, mencatat `status-blocked.json`, dan menjaga
status/ledger/checkpoint lama. Tidak ada reset counter, grant, outbox atau histori.
Replay mapping lama perlu dibuat ulang dari run fake dengan prompt/profile baru.
Smoke Groq terdahulu tetap bukti versi lama; patch terbaru belum live verified.

## Hasil aktual

- Test terarah awal: **19 passed in 2.62s**.
- Test terarah termasuk revision dan compatibility: **22 passed in 4.77s**.
- Regression akhir: **275 passed in 21.81s**, dari baseline 253.
- `pip check`: no broken requirements; `git diff --check`: exit 0.
- CLI fake pada literature, injection, sensitive, budget dan unknown: semuanya
  DONE. Literature melakukan dua read + email simulasi; injection/sensitive
  menolak send; unknown membutuhkan consent operasi sebelum send.
- CLI classifier fake: DONE, JEV OFFLINE VERIFIED; scope hanya paper.
- Crash/recovery budget: crash eksplisit sesudah commit menghasilkan spent 400;
  recover DONE dengan spent 800, tepat dua transfer intents dan dua receipts.
  Tidak ada reset pengeluaran atau duplikasi transfer saat node diulang.
- Test compatibility membandingkan seluruh dump ledger dan checkpoint sebelum/
  sesudah penolakan binding lama; keduanya tetap sama, status lama dipertahankan.
- Tidak ada inference provider live yang dijalankan oleh patch ini.

Command, ringkasan run dan lokasi raw result tersedia di
[`PILOT_SCOPE_PROGRESS_RESULTS.json`](PILOT_SCOPE_PROGRESS_RESULTS.json).
`test_pilot_scope_progress.py` memuat bukti scope semua profil, proposal author
yang terlalu luas, revision worker, conditional classifier egress, confidentiality
log, kegagalan observer, serta compatibility ledger/checkpoint. Test mekanisme
CAS/snapshot/signature/approval/outbox terdahulu tetap termasuk regression penuh.

API tambahan bersifat opsional: `PilotHost.classification_enabled`, callback
`AgentWorkflow.host_validator`/`scope_limits`, dan observer `progress` pada bridge,
memo dan guarded adapter. CLI menambah `--quiet-progress` dan memperketat pasangan
flag classifier. Tidak ada perubahan endpoint, schema database atau migrasi.
