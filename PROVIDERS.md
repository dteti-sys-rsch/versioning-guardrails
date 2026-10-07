# Provider selection: Groq, OpenAI, Ollama, local 9Router

Pembaruan terarah setelah Fase 3.5; bukan Fase 4. Z3, tiket, CAS, approval,
label, outbox dan classifier JEV mempertahankan semantik sebelumnya.

## Ollama lokal

Pilihan `--provider ollama` memakai `qwen3:8b` secara default, tanpa API key.
Endpoint tetap `http://localhost:11434/api`; tidak memakai 9Router. JSON object,
thinking off, timeout/call/token caps, provider scope dan persisted run binding
tetap diperiksa. Tidak ada fallback cloud atau pull model otomatis dari adapter.
Model/tag lokal dan daemon dikelola oleh host tepercaya. Setup, audit serta
status verifikasi terpisah tercatat di [OLLAMA.md](OLLAMA.md).

## Audit sebelum patch

| Requirement | Bukti awal | Gap / patch minimum |
|---|---|---|
| Pilihan provider host | `providers.py`: protocol, OpenAI/fake/replay; CLI hardcode OpenAI | `--provider`, `--model`, factory; OpenAI default kompatibel |
| Groq SDK/API | OpenAI SDK sudah terpasang | Endpoint resmi kompatibel, parameter JSON/output cap; tidak menambah dependency |
| Scope sebelum worker inference | `ModelBridge.worker`, Gateway, Z3 `provider_scope` | Pilot memilih scope provider host; tidak otomatis menambah provider ke kontrak aktif |
| Binding memo/checkpoint | Context sudah mengikat provider/model | Groq scope sendiri; router scope hash endpoint/model/upstream/revision; directory lama menolak perubahan binding |
| 9Router | Tidak ada adapter; user memberi `http://localhost:20128/v1` | Adapter lokal bersyarat: route tetap dan konfigurasi tepercaya eksplisit |
| Secrets / limits | Environment, durable memo, limits sudah ada | Key terpisah per provider; opsi prompt tersembunyi; tidak ada fallback SDK/provider |
| Tests | Baseline aktual **231 passed, 12.23s** | SDK mock dan integration graph/scope/regression; hasil akhir di bawah |

## Groq

```powershell
# Default fake, kontrak/graph yang sama dengan scope Groq; tidak ada network.
.\.venv\Scripts\python.exe phase35_cli.py --directory .runs/groq-offline --provider groq --fixture-approve

# Live interaktif: key dimasukkan lewat terminal tanpa echo.
.\.venv\Scripts\python.exe phase35_cli.py --directory .runs/groq-live --provider groq --model-mode live --prompt-api-key --authorize-model-usage --max-calls 12 --max-tokens 200000 --max-output-tokens 1600 --timeout 30 --max-retries 0

# Alternatif: GROQ_API_KEY sudah diexport secara lokal.
.\.venv\Scripts\python.exe phase35_cli.py --directory .runs/groq-models --provider groq --list-models
```

Default model `openai/gpt-oss-120b`, sesuai pilihan pengguna. Override menggunakan
`GROQ_MODEL` atau `--model openai/gpt-oss-20b`. Nama model OpenAI GPT-OSS di sini
dijalankan di Groq, bukan endpoint OpenAI. API key untuk satu provider tidak
dipakai ke provider lain. `.env.example` hanya template; CLI tidak memuat `.env`.

Request memakai JSON object mode, bukan jaminan schema. Validator host tetap
memeriksa proposal/action. Respons model berbeda, output bukan object, JSON
malformed, refusal/incomplete atau usage invalid gagal tanpa fallback. Error 429
tidak mengganti model atau provider; retry dibatasi memo. Kuota free tier adalah
kuota provider di luar allowance token lokal; prompt author/worker panjang
dapat mencapai TPM sebelum batas call lokal. Tidak ada klaim gratis tanpa batas.

Tidak ada builtin provider tools/search, penerima langsung, atau admin tool baru.
Gunakan fixture sintetis/publik. `--fixture-approve` adalah approval fixture
eksplisit; default live menunggu review manusia.

## 9Router bersyarat

```powershell
.\.venv\Scripts\python.exe phase35_cli.py --directory .runs/router-models --provider 9router --list-models
```

Metadata listing lokal berhasil pada 2026-10-06. Daftar memuat route `cx/...`,
`ag/...` dan `atria/...`; **tidak ada DeepSeek** pada listing yang diamati.
Listing bukan bukti availability inference, kuota gratis, atau keberhasilan model.

Sebelum live, operator harus memilih **direct provider/model route** dari dashboard,
mematikan combo/fallback dan compression, memverifikasi upstream dan exact
`model` yang dilaporkan router, lalu mengatur:

```powershell
$env:NINEROUTER_BASE_URL = 'http://localhost:20128/v1'
$env:NINEROUTER_MODEL = 'YOUR_DIRECT_PROVIDER_MODEL_ROUTE'
$env:NINEROUTER_UPSTREAM_PROVIDER = 'YOUR_APPROVED_UPSTREAM_PROVIDER'
$env:NINEROUTER_RESPONSE_MODEL = 'YOUR_EXACT_RESPONSE_MODEL_ID'
$env:NINEROUTER_ROUTE_REVISION = 'route-v1'
.\.venv\Scripts\python.exe phase35_cli.py --directory .runs/router-live --provider 9router --model-mode live --prompt-api-key --authorize-model-usage --trust-router-route
```

`NINEROUTER_API_KEY` adalah key router lokal, bukan key upstream. Token saver
dibypass memakai `X-9Router-Token-Saver: off`. Endpoint terbatas loopback HTTP
dengan port dan path `/v1`; credentials di URL, remote hosts, query/fragment
dan redirect tidak diizinkan. Environment proxy tidak dipakai oleh transport
Groq/router. CLI tidak menginstal atau mengubah konfigurasi 9Router.

**Asumsi tambahan untuk opsi router:** router dan administrator routing dipercaya
untuk mempertahankan route revision dan tujuan upstream yang disahkan. Hash scope
`router9-...` mengikat konfigurasi endpoint/request model/upstream/response model/
revision dalam kontrak dan immutable context. Perubahan konfigurasi membutuhkan
scope baru, directory baru dan review baru; key/provider lama tidak dinonaktifkan.
Tidak ada migrasi/reset ledger.

`--trust-router-route` adalah attestasi host tentang konfigurasi upstream, bukan
approval bisnis dari worker. AtomicRoot tidak mengaudit internal router atau
membuktikan upstream dari response. Pemeriksaan `response.model` mendeteksi mismatch
setelah respons, **tidak dapat mencegah egress fallback yang dilakukan router
sebelumnya**. Jika router tidak dapat menjamin route tetap, gunakan Groq langsung.
Jangan menganggap provider/model fallback otomatis sudah mendapat otorisasi.

## API/file/state

- `integration/providers.py`: GroqModel, RouterRoute, NineRouterModel,
  configuration/factory dan metadata discovery; Fake/Replay menerima scope provider.
- `integration/pilot.py`: kontrak fixture hanya mendelegasikan provider terpilih
  dan TypeSafe; kontrak lama tetap butuh review perubahan resmi.
- `phase35_cli.py`: selector, model override, secret prompt, bounded model listing,
  router trust gate, non-secret reports dan persisted provider binding.
- `tests/test_model_providers.py`, `.env.example`, README, dokumen ini.
- Tidak ada perubahan schema/migration DB, field tiket, registry admin atau JEV.
  Tabel inference yang sudah ada menyimpan binding baru secara normal.

## Verifikasi aktual

- Baseline sebelum patch: `python -m pytest atomicroot/tests -q`: **231 passed in 12.23s**.
- Test terarah awal: provider + SDK Fase 3.5: **20 passed in 2.19s**.
- Regression akhir: `python -m pytest atomicroot/tests -q`: **253 passed in 10.79s**
  (22 test tambahan; seluruh 231 regression awal tetap lulus).
- CLI `--provider groq --fixture-approve`: **OFFLINE VERIFIED / DONE**, dua read
  dan satu simulated send, actual model `offline-script-v1`; bukan Groq inference.
- CLI `--provider groq --model-mode live --authorize-model-usage`: **BLOCKED**,
  hanya `GROQ_API_KEY` yang kurang; default model sudah benar.
- CLI `--provider 9router --list-models`: berhasil membaca **42 model IDs** dari
  endpoint pengguna; metadata saja, tidak mengirim prompt/content atau inference.
- `pip check`: **No broken requirements found**. `git diff --check`: tidak ada
  whitespace error (hanya warning LF/CRLF). Command/config/snapshot listing tersimpan
  di [PROVIDER_RESULTS.json](PROVIDER_RESULTS.json); artefak CLI di `.runs/` diabaikan Git.
- Saat patch diverifikasi agent, **inference live Groq/9Router: NOT RUN**:
  `GROQ_API_KEY` tidak tersedia di environment agent dan route/model/upstream
  9Router belum dikonfigurasi. Ini hasil historis, bukan status run pengguna berikutnya.

### Smoke live pengguna: 2026-10-06

Artefak `.runs/groq-live-01/{status.json,transcript.json,ledger.sqlite}` kemudian
diperiksa setelah pengguna menjalankan CLI dan menyetujui kontrak secara interaktif:

- Groq `openai/gpt-oss-120b`, scenario `literature`, mode `live`, workflow **DONE**.
- **6/6 attempts RETURNED**, model aktual sesuai konfigurasi, tidak ada error tercatat.
- Dua `read_document` dan satu `send_email` semuanya **RELEASED**. Isi email simulasi
  merangkum kedua observasi sintetis: atomic authorization/versioned state dan
  replay prevention/durable operation identity. Tidak ada email sungguhan.
- Reported usage: **10.546 input + 2.754 output tokens**. Pricing tidak dikonfigurasi;
  biaya tetap unknown. Token ini bukan ukuran latency atau benchmark ketepatan.
- Satu contract review; JEV **DISABLED**.

Status: **Groq literature smoke LIVE VERIFIED**, dengan scope satu workflow
sintetis. Skenario serangan, contention/race, recovery live, kualitas model pada
dataset lebih luas, JEV live dan 9Router inference belum divalidasi oleh run ini.
Keberhasilan smoke menunjukkan integrasi provider/graph/approval/guarded effects
berjalan bersama; bukti stale authorization tetap berasal dari test deterministik
baseline vs AtomicRoot. Entri awal BLOCKED dipertahankan, hasil baru tersimpan di
`PROVIDER_RESULTS.json/live_runs`. Exact shell command tidak tersimpan pada artefak;
config dan versi aktual tersedia. API key tidak dibaca atau disalin ke laporan.

Referensi implementasi resmi:
[Groq OpenAI compatibility](https://console.groq.com/docs/openai),
[Groq JSON mode](https://console.groq.com/docs/structured-outputs),
[9Router README/API/token-saver](https://github.com/decolua/9router).
