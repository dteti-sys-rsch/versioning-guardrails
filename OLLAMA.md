# Integrasi langsung Ollama — pembaruan setelah Fase 3.5

## Audit requirement → bukti → perubahan

| Requirement | Bukti sebelum patch | Implementasi / test |
|---|---|---|
| Pilihan local provider | MODEL_PROVIDERS hanya OpenAI/Groq/9Router | OllamaModel, factory/configuration, selector CLI |
| Key lokal tidak diperlukan | CLI mewajibkan key setiap provider live | key_environment=None; bootstrap consent tetap wajib |
| Tujuan lokal tetap | Groq/router memiliki transport dibatasi | Fixed localhost:11434/api, no redirects/proxy/credentials; native HTTP mock test |
| Payload JSON, caps, no fallback | Interface generate/memo sudah tersedia | Native format=json, think=false, num_predict cap, exact response model; malformed/length/error ditolak |
| Scope sebelum worker call | ModelBridge + Z3 provider_scope + Gateway/outbox | Pilot existing memilih ollama; test missing scope zero calls, accepted intent sebelum HTTP |
| Replay/configuration binding | CLI/memo/checkpoint binding existing | Tambahan config lokal/options; test fake→live ditolak tanpa mengubah checkpoint/status |
| Model/classifier terpisah | ClassificationProvider terpisah dari generative provider | JEV tidak berubah; tidak ada classifier Qwen atau dependency baru |

File: `integration/providers.py`, `phase35_cli.py`, `.env.example`, README/provider
docs, dan `tests/test_ollama_provider.py`. Tidak ada endpoint AtomicRoot baru,
schema/migration DB atau perubahan field ticket/policy/approval/outbox.
Baseline aktual sebelum patch: **275 passed in 11.60s**.

## Menjalankan

Ollama server harus berjalan dengan model lokal sudah tersedia. Metadata model:

```powershell
.\.venv\Scripts\python.exe phase35_cli.py --directory .runs/ollama-models --provider ollama --list-models
```

Workflow nyata dengan review manusia, hanya source/efek sintetis pilot:

```powershell
.\.venv\Scripts\python.exe phase35_cli.py --directory .runs/ollama-live-v3 --provider ollama --model qwen3:8b --model-mode live --authorize-model-usage --timeout 120 --max-calls 12 --max-tokens 200000 --max-output-tokens 1600 --max-retries 0
```

Default tetap mode fake jika `--model-mode live` tidak diberikan. Fake success
bukan Ollama inference. Override default model dengan `--model` atau `OLLAMA_MODEL`.
CLI tidak memuat `.env` otomatis. Tidak memakai `--prompt-api-key` untuk Ollama.

Pada review, approve/reject/pause berasal dari manusia tepercaya. Pause dapat
dilanjutkan dengan command konfigurasi yang sama dan `--resume`; setelah crash
gunakan `--recover`. Berpindah provider/model/mode memakai directory baru.
Logging ringkas sama seperti provider lain, termasuk cache vs inference aktual.
Email/transfer tetap simulasi. Budget kontrak berbeda dari allowance token.

## Keputusan dan asumsi

- Memakai API **native** `/api/chat`, bukan `/v1/chat/completions`, untuk mengikat
  `think=false`, `format=json`, `num_ctx=16384`, `temperature=0` dan batas
  `num_predict` secara eksplisit. Menggunakan HTTP library yang sudah terpasang;
  tidak menginstal SDK Ollama atau mengubah server pengguna.
- Endpoint fixed loopback. OLLAMA_BASE_URL/OPENAI_BASE_URL dan API keys tidak
  mengubah tujuan. Tidak ada redirect, environment proxy, hidden retry, pull,
  provider tools, atau fallback. Daftar model adalah metadata saja.
- Model tag harus eksplisit; `:latest`, cloud tags dan URL ditolak. Daemon,
  resolusi localhost, konfigurasi model serta administrator host dipercaya untuk
  menjalankan bobot lokal yang dipilih dan mempertahankan tag sepanjang run.
  Adapter tidak membuktikan isi daemon atau mem-pin weights secara atomik.
  Digest/version yang diamati dicatat pada hasil, bukan CAS key runtime.
- Jika operator membutuhkan server local-only, Ollama mendokumentasikan
  `OLLAMA_NO_CLOUD=1` pada environment **server**, lalu restart Ollama. Patch ini
  tidak mengubah konfigurasi atau restart daemon yang sudah berjalan.
- Qwen dapat mengeluarkan JSON valid tetapi kontrak/action tidak valid. Validator
  host/schema dan Z3 tetap memeriksa; error/timeout/partial output tidak diganti
  oleh fake response dan tidak otomatis mendapatkan approval.
- Context 16K adalah pengaturan adapter, bukan bukti tidak ada truncation pada
  setiap input arbitrer. Pilot memakai source sintetis kecil dan batas existing;
  dokumen panjang, tokenizer budgeting, kualitas model dan performance benchmark
  di luar pengujian ini. Latency smoke bukan estimasi semua workload.
- Local inference tetap memerlukan scope provider/resource/purpose. Author awal
  memerlukan explicit host bootstrap usage consent; worker melewati Gateway dan
  accepted immutable outbox sebelum HTTP. Tidak ada DB lock melintasi inference.
- JEV tetap opsional TypeSafe terpisah. Memakai Qwen lokal tidak membuat JEV lokal.

## Verifikasi aktual

Hasil akhir dan command disimpan di `OLLAMA_RESULTS.json`. Default tests seluruhnya
offline. Satu live adapter probe memakai input sintetis, satu call maksimum,
128 output tokens, zero retries dan timeout 120 detik. Full live workflow dengan
aksi bisnis dibedakan dari adapter/author probes.

- Regression: **294 passed in 15.53s**; 19 test baru di file Ollama.
- Test provider terarah awal: **40 passed in 2.01s** sebelum tambahan positive
  guarded-dispatch test. Tidak ada assertion regression yang dilemahkan.
- `pip check`: no broken requirements; `git diff --check`: exit 0.
- Ollama **0.32.13**, local tag `qwen3:8b`, digest
  `500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41`.
- Live adapter probe: RETURNED JSON `{"status":"ok"}`, reported usage 42 input /
  6 output tokens, observed total 9.39 detik (termasuk load; bukan benchmark).
- Live CLI author probe: satu attempt RETURNED, proposal lolos host/schema
  validation dan sampai contract review. Input `pause` mempertahankan review;
  workflow PAUSED, nol outbox intent sebelum approval. JEV DISABLED.
- Probe author awal dengan allowance 20000 ditolak oleh caps existing sebelum
  inference (nol attempts); byte-based allowance prompt+output memerlukan 21711.
  Run baru dengan cap eksplisit 200000 berhasil. Kegagalan awal tetap dicatat.
- **Full workflow live Qwen sampai efek worker: NOT RUN.** Fake full workflow dan
  native HTTP integration mock lulus; keduanya bukan bukti full live workflow.

Sumber resmi: [API chat](https://docs.ollama.com/api/chat),
[Thinking](https://docs.ollama.com/capabilities/thinking),
[FAQ konfigurasi/local-only](https://docs.ollama.com/faq).

## Patch worker-v3 setelah run pengguna STEP_LIMIT

Audit ledger `.runs/ollama-live` membuktikan dua read berhasil, lalu enam respons
worker memilih `model_inference`. GuardedTools menolak semuanya sebelum business
authorization; tidak ada email. Ini kegagalan pemilihan aksi, bukan solver/CAS
failure. Hasil run lama dipertahankan.

| Gap aktual | Patch / evidence |
|---|---|
| Task contract memuat host inference, sehingga worker memilihnya | Prompt v3: available_actions eksplisit; infer/classify host-managed; summary ditulis langsung dalam email body |
| JSON mode tidak membatasi pilihan tool | Schema action/done/contract berdasarkan intersection capability worker dan allowed_tools, hanya untuk native Ollama worker |
| Schema generation dapat dipalsukan/berubah | Schema masuk immutable context dan memo binding; Authority membandingkannya dengan schema tepercaya dari snapshot kontrak yang sama |
| Canonicalization menaruh args sebelum discriminator pada grammar | Native serializer mengembalikan property order sesuai required array yang terikat context: kind/tool/args |
| Schema ganda memperbesar context sampai batas ingest 8192 bytes | Schema disimpan sekali dalam context; prompt memuat daftar aksi ringkas. Limit ingest tetap sama |
| Resume/cache dari versi lama | Prompt versions sekarang terikat cli-config; perubahan ditolak tanpa reset ledger/checkpoint |

Schema adalah pembatas **generation**, bukan otoritas permission. Daemon yang
mengabaikan schema tetap ditolak host; test mereproduksi aksi model_inference asli
dan membuktikan tidak ada nested call/business effect. Schema revision tetap
tersedia; ContractService/host validator/Broker memeriksa proposal penuh. Tidak ada
fallback evaluator, remapping inference menjadi email, hardcoded summary atau
perluasan tools. Z3/CAS/ticket/approval tetap menjadi jalur enforcement.

Author tetap prompt v2 dan JSON mode; worker memakai v3. Fake/replay/cloud adapter
memakai prompt yang diperjelas, tetapi tidak diklaim memiliki native constrained
decoding baru. Context format menerima tambahan response_schema hanya jika schema
tepercaya cocok; key dan dependency lama tidak dinonaktifkan. Tidak ada migrasi DB.

File patch: `prompts.py`, `providers.py`, `inference.py`, `egress.py`, `guarded.py`,
CLI run binding, example config, docs dan `test_worker_output_schema.py`.
Baseline aktual sebelum patch: **294 passed in 10.51s**. Hasil patch serta seluruh
percobaan live (termasuk kegagalan selama perbaikan) dicatat terpisah pada
`OLLAMA_WORKER_RESULTS.json`. Rujukan fitur: [Ollama structured outputs](https://docs.ollama.com/capabilities/structured-outputs).

### Hasil patch aktual

- Test terarah: **7 passed in 1.15s**. Regression akhir: **301 passed in 20.83s**.
- Percobaan live schema awal tetap STEP_LIMIT karena mengulang proposal kontrak.
  Percobaan berikutnya membaca ulang satu source dan mencapai batas ingest context
  8192 bytes. Keduanya dipertahankan pada raw result; limit tidak dinaikkan.
- Variant final: **DONE / LIVE VERIFIED**, **6/6 calls RETURNED**, dua resource
  berbeda dibaca dan satu `send_email` ke `alice@corp.id` RELEASED. Body hasil Qwen
  merangkum kedua observasi: atomic authorization/versioned state serta replay
  prevention/durable operation identity. Bukan body template/scripted.
- Run terakhir memakai **explicit trusted synthetic fixture approval**, bukan
  persetujuan manusia interaktif. JEV DISABLED, seluruh email/transfer simulasi.
- Satu workflow final (1/1) menunjukkan Qwen3:8b dapat menjalankan pilot setelah
  perbaikan protocol/prompt. Ini bukan jaminan untuk semua model, dokumen atau
  workload. Smoke tidak menguji stale race; regression mekanisme tetap terpisah.
- Tidak ada perubahan dependency, schema DB, budget/label/grant/ticket enforcement.
  `git diff --check` exit 0. Gunakan directory baru (`ollama-live-v3`) agar run
  v2 yang gagal tetap tersedia sebagai bukti dan tidak tercampur prompt baru.
