# AGENTS.md — AtomicRoot

Panduan untuk coding agent yang bekerja pada repository AtomicRoot. Ikuti instruksi tugas pengguna yang terbaru dan aturan yang berlaku pada lingkungan kerja. File ini menetapkan aturan development; enforcement runtime harus diwujudkan dalam kode, database, dan konfigurasi tool.

## 1. Tujuan dan lingkup

- AtomicRoot adalah lapisan authorization runtime untuk mencegah **stale authorization** pada sistem multi-agent concurrent. Fokus: consistent snapshot, policy footprint, one-time ticket, atomic freshness check/CAS, dan effect outbox.
- Threat model mencakup adversarial scheduler yang mengendalikan interleaving dalam batas API/capability yang dimodelkan. Attacker tidak memiliki signing key, trusted approver identity, atau akses administratif langsung ke Trace Store.
- Jangan memperluas klaim menjadi pencegahan semua prompt injection, kebenaran seluruh fakta, atau kesesuaian sempurna dengan maksud pengguna.
- Klaim empiris dibatasi pada pelanggaran policy akibat stale authorization di bawah interleaving yang dieksplorasi dan asumsi enforcement yang dinyatakan. Pisahkan bukti empiris dari pembuktian formal.

## 2. Mulai dari implementasi aktual

- Baca README, konfigurasi dependency, source, tests, dan catatan fase yang relevan sebelum mengubah kode. Periksa instruksi khusus pada direktori yang dikerjakan.
- Jika tersedia, gunakan `AtomicRoot-Prompt-Fase-2-6-Revisi.md` sebagai roadmap, dengan revisi terbaru yang disahkan pengguna. Dokumen blueprint/abstract lama tidak otomatis mengalahkan keputusan terbaru.
- Kerjakan fase/tugas yang diminta. Fase 1–3 telah dilaporkan selesai pada saat panduan ini dibuat; verifikasi status aktual dari kode/test. Jangan mengulang fase atau migrasi hanya karena instruksinya tersedia.
- Untuk integrasi baru, buat audit requirement → bukti file/test → gap. Pertahankan bagian yang benar dan lakukan patch minimum pada gap yang dibuktikan. Jangan refactor besar tanpa kebutuhan tugas.
- Jika desain yang diminta mengubah invariant atau threat model, jelaskan dampaknya kepada pengguna; jangan mengubah asumsi keamanan diam-diam. Keputusan implementasi rutin boleh diselesaikan dan didokumentasikan.

## 3. Stack dan gaya implementasi

- Gunakan Python dan stack yang sudah dipakai repository. Pertahankan SQLite WAL serta library API/kriptografi yang sudah benar; jangan mengganti backend tanpa kebutuhan yang disetujui.
- Gunakan typed schema/data objects, validasi eksplisit, error terstruktur, dan modul kecil. Hindari generic `eval`, SQL dari worker, atau script solver buatan LLM.
- Gunakan integer satuan uang yang disepakati, bukan float untuk nominal finansial. Validasi nilai negatif/malformed, scope, dan ukuran input.
- Gunakan `asyncio`/mekanisme concurrency yang sesuai arsitektur. Jangan menahan lock/transaksi database ketika menunggu manusia, model inference, atau receiver eksternal.
- SQLite hanya memiliki satu writer pada satu waktu. Key independen mengurangi false freshness conflicts; jangan mengklaim parallel physical writes atau distributed lock dari implementasi single-process.
- Komentar menjelaskan invariant, titik linearization, binding versi, serta alasan sinkronisasi; hindari komentar yang hanya mengulang sintaks.

## 4. Invariant authorization dan commit

- Authority, Trace Store, Gateway, Contract Service, Label Manager, dan Approval Broker adalah komponen tepercaya. Worker, proposal LLM, dan isi konten eksternal bukan otoritas.
- Policy state dan versi conflict keys harus berasal dari **snapshot konsisten yang sama**. Jangan membaca nilai dan versi dari waktu berbeda.
- Gunakan footprint per concrete conflict key, bukan satu global version pada mode utama. Global version hanya varian pembanding yang eksplisit.
- Footprint berasal dari static dependency analysis semua cabang AST dan dynamic reads tepercaya. Sertakan dependency policy-set/membership, kontrak, label, approval, dan resource yang relevan; jangan mengambil dependency hanya dari model/unsat core Z3.
- Setiap mutasi policy-relevant state menaikkan versi terkait. Enumeration/membership yang dapat berubah harus mendeteksi phantom additions lewat aggregate/membership version. Wildcard bukan literal key CAS.
- Worker tidak memilih footprint, write set, effect class, identity, capability, versi, atau fakta ledger. Identitas berasal dari trusted runtime/auth context.
- Tiket signed mengikat caller/task/tool, exact canonical payload hash, footprint+versi, nonce, expiry, dan operation binding yang digunakan sistem. Pertahankan single-use bahkan untuk write set kosong.
- Commit melakukan validasi/freshness, state/reservation update, increment versi, event, konsumsi tiket/grant, dan outbox insertion dalam **satu transaksi atomik**. Gagal CAS tidak menghasilkan state parsial atau dispatchable effect.
- Tiket stale memerlukan authorization baru untuk payload/operation yang sama. Jangan memperbarui versi tiket atau membawa approval lama ke business state baru secara diam-diam.
- Fallback contention harus re-read/re-authorize dan tetap memeriksa freshness atomik. Semua writer terkait mengikuti exclusion protocol yang sama; dokumentasikan scope lock, timeout, fairness, dan retry bound.

## 5. Policy, fakta, dan Z3

- **Z3 adalah satu-satunya evaluator policy aktif.** Tidak membangun Python reference evaluator lengkap atau fallback policy evaluator ketika Z3 gagal. Oracle eksperimen memakai invariant spesifik, bukan evaluator kedua.
- Gunakan DSL/typed AST yang dapat diperluas dari operator dan sumber fakta terdaftar. Enam policy benchmark bukan batas permanen DSL. Semua applicable policies diperiksa; hard DENY tidak dikalahkan approval policy lain.
- Pisahkan definisi policy, parameter kontrak, metadata jenis fakta, runtime values, dan immutable request. Fakta hilang tidak dianggap nol dan tidak menjadi simbol bebas untuk keadaan aktual.
- Registry fakta menentukan tipe, scope, trusted source, conflict-key resolver, authorized updater, serta operasi/transisi sah. Worker hanya mengusulkan operasi; service tepercaya memperbarui state.
- Dokumentasikan semantik query. Acuan `facts AND NOT(all_applicable_constraints)`: setelah kelengkapan/konsistensi fakta valid, SAT → DENY; UNSAT → kandidat ALLOW jika semua prasyarat lain valid; UNKNOWN/timeout/error → tanpa tiket.
- Fakta kontradiktif tidak boleh memberi ALLOW karena vacuous UNSAT. Jangan membalik mapping solver tanpa memeriksa encoding aktual atau memanggil `model()` setelah UNSAT.
- Solver failure, invalid DSL, missing facts, atau signature failure tidak dapat dibuka dengan tombol approval. Bukti/provenance harus menunjuk fakta dan event nyata, bukan event yang dikarang dari solver model.

## 6. Kontrak dan approval

- LLM boleh mengusulkan kontrak/policy; validasi struktur, tipe, sumber, dependency, dan dukungan enforcement sebelum preview/aktivasi. Jangan membuang requirement unsupported tanpa menampilkannya.
- Gunakan review selektif: kontrak awal yang relevan, rule baru/berubah, perubahan scope, dan tindakan yang memang memerlukan consent. Counter normal melalui transisi sah tidak memerlukan approval setiap increment.
- Grant mengikat exact proposal/payload, basis versi/footprint yang direview, approver tepercaya, expiry, dan operasi sesuai jenis approval. Periksa freshness saat approve dan final commit; perubahan relevan memerlukan review baru.
- Bedakan contract activation/change approval dari consent satu operasi. Teks “user approved” dari worker, email, atau resume input bukan grant.
- Field read-only/derived tidak otomatis terbuka oleh approval umum. Counter/reservation dikoreksi hanya melalui operasi ledger yang sah. Resume tidak mereset budget atau exposure.

## 7. Konten, label, dan JEV

- Pisahkan instruction trust, confidentiality, dan factual correctness. Email body, web/search, serta lampiran adalah **UNTRUSTED sebagai instruksi**; ini tidak otomatis berarti SENSITIVE atau terbukti malicious.
- Kerahasiaan memakai PUBLIC/SENSITIVE/UNKNOWN yang terikat resource identity, content digest/version, asal penetapan, dan scope penggunaan. PUBLIC bukan izin semua tujuan/semua versi konten.
- Metadata/pemilik/rule ingestion berwenang menetapkan label otoritatif. Rename, move, teks “aman”, atau klaim worker tidak menurunkan label.
- JEV adalah **classifier opsional**, bukan Policy Authority dan bukan pengganti Z3. Integrasikan model siap pakai; jangan melatih/fine-tune classifier atau menambah model lain tanpa tugas eksplisit.
- Pisahkan `ClassificationProposal`, authoritative label, dan effective restriction. Simpan candidate, model ID, criteria version/hash, probabilities/confidence, content binding, serta coverage/error yang relevan.
- Prediksi PUBLIC tidak otomatis mempromosikan UNKNOWN, downgrade SENSITIVE, menghapus task exposure, atau memberi izin external release. Prediksi SENSITIVE boleh menambah restriction konservatif melalui rule tepercaya yang sudah disahkan.
- Acceptance proposal memeriksa content/base-label version secara atomik. Hasil lama ditolak bila konten/label berubah selama inference/review. Effective policy-relevant update menaikkan dependency version dan menginvalidasi release dependency task yang sudah terpapar input terkait.
- Confidence bukan jaminan correctness atau keamanan. Timeout/error/low-confidence/truncation tidak menghasilkan PUBLIC; jangan menghapus label resmi yang masih valid. Dokumentasikan threshold provisional dan abstention.
- Output mengikuti exposure input/shared context secara konservatif. Catat exposure sebelum hasil read tersedia kepada worker; klaim “hanya memakai jurnal publik” tidak menurunkan taint yang sudah tercatat.
- Pemanggilan provider LLM/JEV adalah data egress. Scope provider/resource/tujuan harus sudah diotorisasi **sebelum** input dikirim; jangan menunggu hasil klasifikasi untuk mengizinkan inputnya sendiri. Gunakan jalur Gateway yang sesuai, payload immutable, dan semantik commit yang terdokumentasi.

## 8. Tool adapter, outbox, dan recovery

- Semua protected worker tools melewati guarded adapter/Gateway. Jangan mengekspos receiver langsung, DB/admin writes, approval endpoint, atau unrestricted shell sebagai worker tool.
- Framework mengatur orchestration/checkpoint; ledger/approval/kontrak tepercaya tetap sumber state otoritatif. Jangan overwrite ledger menggunakan checkpoint lama.
- `operation_id` stabil lintas retry/reauthorization/resume dan terikat identity/payload. ID sama dengan payload berbeda ditolak. Rerun operasi committed mengembalikan status tanpa konsumsi budget/efek baru; bukan menerima replay tiket sebagai commit baru.
- Bekukan payload/recipient/resource sebelum authorize. Delivery tidak membaca ulang mutable reference. Outbox berada dalam database/transaksi commit yang sama; receiver call dilakukan di luar transaksi setelah intent committed.
- COMMITTED berbeda dari DELIVERED. Titik linearization adalah penerimaan intent; jangan mengklaim revocation atomik sampai provider delivery. Perubahan policy setelah commit sah tidak otomatis menjadikannya stale violation.
- Gunakan bounded lease/claim/retry dan receiver idempotency yang benar-benar didukung. Lost ack/timeout dapat berarti efek sudah terjadi: pertahankan status UNKNOWN/reconciliation dan reservation sampai outcome pasti.
- Jangan mengklaim exactly-once pada provider arbitrer. Dedupe dummy receiver dan memo inference adalah mekanisme berbeda; provider inference dapat menagih ulang setelah lost response.

## 9. Pengujian dan perintah proyek

- Temukan perintah setup/test/lint dari README, `pyproject.toml`, lockfile, task runner, atau CI aktual. Gunakan perintah repository tersebut; jangan mengarang path, dependency, atau hasil test.
- Jalankan baseline relevan sebelum perubahan, test terarah atas perubahan, lalu regression yang diwajibkan tugas. Jangan melemahkan assertion atau menghapus test untuk membuat suite hijau.
- Core tests default offline: scripted/mock agents serta fake/replay LLM/JEV. Tidak menggunakan real model API untuk menguji CAS/TOCTOU.
- Race tests wajib reproducible memakai `asyncio.Event`, barrier, explicit scheduler steps, atau hook terkontrol. Jangan memakai `sleep` untuk mengasumsikan interleaving tertentu. Seed saja tidak cukup; simpan schedule dan initial state.
- Pertahankan integration tests dengan koneksi DB terpisah, rollback, single-use/replay, signature/identity/payload tampering, relevant/unrelated dependency changes, approval staleness, outbox lost ack, dan checkpoint rerun.
- Test classifier acceptance dengan false PUBLIC, UNKNOWN/error, restrictive update, stale content, cached-response binding, dan blocked provider egress. Test mekanisme tidak bergantung pada model mampu mendeteksi injection.
- Live integration/experiment hanya dalam scope tugas dengan credentials, izin data, dan call/token/spend caps eksplisit. Gunakan PUBLIC atau synthetic fixtures yang diizinkan; rahasia melalui environment, tidak dicetak/di-commit.
- Bila live tidak tersedia, selesaikan offline work/configuration dan laporkan NOT RUN/BLOCKED. Fake/replay success bukan live validation.

## 10. Evaluasi dan penulisan ilmiah

- Pertahankan enam mode pembanding yang didefinisikan roadmap. JEV enable/disable adalah sumbu ablation terpisah, bukan mode guard ketujuh.
- Pisahkan deterministic mechanism runs, real-clock performance, LLM live workflows, dan JEV classification pilot. Pair initial workload/schedule plans serta recorded proposals/responses bila mengisolasi kontribusi CAS.
- Oracle mengacu pada scenario/invariant/events/receipts independen, bukan keputusan guard sebagai ground truth. Bedakan attempted attack, violating accepted intent, delivered effect, dan unknown delivery.
- Bedakan ground-truth confidentiality, candidate classifier, dan effective formal state. Pisahkan classification error, stale proposal acceptance, dan stale authorization failure; laporkan end-to-end leakage terhadap ground truth juga.
- Simpan raw results, actual commands/config/dependency/model versions, seeds/schedules, failures, serta numerator/denominator metrik. Denominator nol → N/A; zero violations pada sejumlah run bukan universal guarantee.
- Jangan mengatribusi dedupe/constraint bersama seluruhnya kepada CAS atau menyembunyikan baseline yang berhasil. Laporkan uncertainty dan keterbatasan sample size serta scope SQLite/lock/provider.
- Gunakan bahasa Indonesia/Inggris mengikuti tugas, nada objektif, dan klaim terukur. Verifikasi isi sumber sebelum menyatakan novelty atau keterbatasan prior work; jangan mengarang kutipan atau hasil eksperimen.

## 11. Penyelesaian tugas

- Laporkan apa yang berubah, alasannya, file/API/migrasi yang terdampak, test yang benar-benar dijalankan, serta blocker/batas material. Dokumentasikan perubahan fase terdahulu secara terpisah.
- Bedakan status implemented, offline verified, live verified, dan belum dijalankan. Jangan mengklaim fase selesai jika kriteria yang diminta belum tercapai.
- Kerjakan tugas yang sudah diotorisasi sampai hasil dapat ditinjau; jangan berhenti pada rencana atau meminta konfirmasi ulang untuk keputusan rutin. Jangan melanjutkan fase berikutnya kecuali diminta.
