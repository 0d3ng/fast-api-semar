# FAST API SEMAR SERVER
Implement IoT Platform system using FastAPI

## How to run
To run the application using `uvicorn`
### Install dependency first
Please type command `pip install -r requirements.txt`

### Running application
Using command uvicorn `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`

### Running inside single container 
`docker run --network host --name fast-api-semar --env-file .env -v logs:/app/logs -p 8001:8001 0d3ng/fast-api-semar:v1`

### Generate Key Secret Token
The python file in `ecc_tools.py`, type `export PYTHONPATH=$(pwd)` first

### Build image
`docker build -t fast-api-semar:ota .`

### Build image and push to docker hub
`docker build -t 0d3ng/fast-api-semar:ota --push .`

---

## AI-Assisted Firmware Security Assessment & OTA Gate

Fitur ini mengintegrasikan analisis keamanan firmware otomatis sebelum firmware didistribusikan melalui OTA (Over-The-Air). Penilaian menggabungkan:
1. **SBOM Generation & CVE Scanning:** Mengidentifikasi pustaka dependensi (SPDX 2.2) dan mencocokkan kerentanan CVE via NVD & Grype, diperkaya skor exploitability EPSS dan CISA KEV.
2. **Static Code & Secret Analysis:** Mendeteksi fungsi memori tidak aman (`strcpy`, `sprintf`), plaintext HTTP, skip verifikasi sertifikat TLS via Semgrep & Flawfinder, serta kredensial/token bocor via Gitleaks.
3. **Configuration Checker:** Memeriksa kepatuhan konfigurasi bootloader/keamanan ESP-IDF (`sdkconfig`) seperti Secure Boot, Flash Encryption, dan App Rollback.
4. **Local AI Security Analyzer:** Model LLM lokal (Ollama / Qwen2.5-Coder) di server SEMAR yang menafsirkan temuan, memetakan korelasi skenario serangan, melakukan validasi grounding temuan, dan merekomendasikan mitigasi teknis.
5. **OTA Security Gate & 1-Step Human Review:** Menahan perintah broadcast jika firmware belum memenuhi syarat keamanan, dengan opsi *Approve*, *Block*, atau *Request Fix* (otomatis membuat issue di GitHub repository firmware).

---

### Konfigurasi Environment (`.env`)

Tambahkan properti berikut ke file `.env` di root project:

| Properti | Tipe / Pilihan Nilai | Default | Deskripsi & Fungsi |
|---|---|---|---|
| `SECURITY_GATE_MODE` | `monitor` \| `enforce` \| `off` | `monitor` | Mode gerbang saat broadcast OTA. <br>• `monitor`: Menilai & mencatat status tanpa memblokir broadcast.<br>• `enforce`: Memblokir broadcast (HTTP 409) jika belum `PASS` atau belum di-`Approve`.<br>• `off`: Mematikan fungsi security gate. |
| `SECURITY_POLICY_PROFILE` | `lab` \| `production` | `lab` | Memilih profil aturan pada `app/security_policies/`. <br>• `lab`: Menonaktifkan Secure Boot/Flash Encryption hanya memicu *warning* (tetap lolos).<br>• `production`: Wajib Secure Boot, Flash Encryption, dan TLS penuh (insecure flag memicu `BLOCKED`/`REVIEW_REQUIRED`). |
| `LLM_BASE_URL` | URL string | `http://localhost:11434` | Endpoint layanan Ollama lokal di server SEMAR (mendukung akselerasi GPU). |
| `LLM_MODEL` | String nama model | `qwen2.5-coder:14b` | Model LLM lokal yang digunakan. Disarankan `qwen2.5-coder:14b` (GPU VRAM 12GB+) atau `qwen2.5-coder:7b` untuk pengujian lebih hemat resource. |
| `LLM_TIMEOUT_S` | Integer (detik) | `120` | Batas waktu inferensi Ollama. Jika timeout/Ollama tidak aktif, sistem otomatis *fallback* aman ke keputusan Policy Engine (`ai_unavailable`). |
| `LLM_NUM_CTX` | Integer (token) | `16384` | Panjang context window model Ollama agar dapat menampung daftar temuan dan diff rilis. |
| `SECURITY_ENRICH_NETWORK` | `true` \| `false` | `true` | Mengaktifkan pengambilan skor exploitability (EPSS) dari FIRST dan status eksploitasi aktif CISA KEV secara online (di-cache di MongoDB selama 24 jam). |
| `NVD_API_KEY` | String (opsional) | *(kosong)* | API Key NVD jika ingin limit request ke NVD API lebih longgar. |
| `SEMAR_WEB_URL` | URL string | `https://web.sinaungoding.com` | Base URL frontend web SEMAR (`web-semar-iot`), dicantumkan pada GitHub Issue otomatis saat reviewer meminta perbaikan. |

#### Properti Integrasi GitHub (Sudah ada di SEMAR):
* `GITHUB_DISPATCH_TOKEN`: Token Personal Access Token (PAT) GitHub dengan izin akses repo (issues/workflow dispatch). Digunakan saat aksi **Request Fix** untuk membuat GitHub Issue otomatis di repo firmware.
* `GITHUB_REPO_OWNER`: Pemilik repository firmware (misal: `0d3ng`).
* `GITHUB_REPO_NAMES` / `GITHUB_REPO_NAME`: Nama repository firmware (misal: `firmware-ota-rolling-key`).
* `SEMAR_API_TOKEN`: Token autentikasi CI/CD GitHub Actions saat mem-posting bukti hasil scan ke endpoint `/api/v1/security-assessments`.

---

### Profil Evaluasi (`lab` vs `production`)

| Kondisi Temuan | Mode `lab` | Mode `production` |
|---|---|---|
| Hardcoded secret / API Token (Gitleaks) | `BLOCKED` | `BLOCKED` |
| CVE Kritis (CVSS ≥ 9.0) atau terdaftar di CISA KEV | `BLOCKED` | `BLOCKED` |
| TLS Insecure / Skip cert check / Plain HTTP OTA | `REVIEW_REQUIRED` | `BLOCKED` |
| High SAST (`strcpy` buffer tidak aman) / High CVE | `REVIEW_REQUIRED` | `REVIEW_REQUIRED` |
| Secure Boot / Flash Encryption / Rollback nonaktif | `PASS` *(Warning)* | `REVIEW_REQUIRED` |

*Catatan:* AI Security Analyzer menerapkan aturan **Monotonic Escalation**. AI hanya dapat menaikkan kewaspadaan (misal dari `PASS` ke `REVIEW_REQUIRED` jika menemukan korelasi berisiko tinggi), dan **tidak pernah menurunkan** keputusan yang sudah diblokir oleh Policy Engine.

---

### Menjalankan Unit Test

Untuk memverifikasi normalizer, policy engine, AI parser/grounding validator, dan security gate:
```bash
pytest app/tests/test_security_assessment.py app/tests/test_cicd_endpoints.py -v
```
