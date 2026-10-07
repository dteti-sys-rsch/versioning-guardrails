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
.\.venv\Scripts\python.exe phase35_cli.py --directory .runs/ollama-live --provider ollama --model qwen3:8b --model-mode live --authorize-model-usage --timeout 120 --max-calls 12 --max-tokens 200000 --max-output-tokens 1600 --max-retries 0
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
