# Laporan Kerentanan — Captcha Bypass (Broken Anti-Automation)

## Informasi Umum

**Judul Laporan**
Captcha Bypass / Broken Anti-Automation pada `captcha.php` Aplikasi SIMPADAN TANGKAP

**Jenis kerentanan dan nama Sistem Elektronik**
Broken Access Control / Insufficient Anti-Automation (Captcha Bypass) — SIMPADAN TANGKAP, Dinas Peternakan dan Perikanan Kabupaten Situbondo (`perikanantangkap.situbondokab.go.id`)

**Jenis Kerentanan**
Broken Access Control / Insufficient Anti-Automation

**Path URL**
https://perikanantangkap.situbondokab.go.id/simpadan/captcha.php

**IP Address Penguji**
`<diisi IP penguji>`

**Tingkat Severity**
Medium

---

## Detail Temuan

### Deskripsi Temuan

Endpoint `captcha.php?action=generate` mengirimkan **seluruh data yang dibutuhkan untuk menjawab tantangan captcha** ke sisi klien, termasuk jawaban tantangan itu sendiri. Untuk tantangan bertipe `count_items`, respons berisi `target` (emoji yang harus dihitung) dan `grid` (daftar emoji), sehingga jumlah kemunculan `target` di dalam `grid` dapat dihitung secara otomatis tanpa interaksi manusia.

Akibatnya kontrol anti-otomatisasi (captcha) yang melindungi alur login (`login.php`) dan pendaftaran (`api.php?action=submit_inbox`) dapat dilewati sepenuhnya secara terprogram. Sesi/CSRF token yang valid pun langsung diberikan setelah tantangan dijawab.

Captcha adalah satu-satunya mekanisme anti-otomatisasi yang teramati pada alur tersebut; tidak ditemukan rate limiting yang berarti pada endpoint terkait.

### Langkah-langkah POC

1. Ambil sesi dan CSRF token:
   - `GET /simpadan/`
   - `GET /simpadan/api.php?action=get_csrf_token`

2. Ambil tantangan captcha. Tambahkan parameter `type=count_items` agar tipe tantangan dapat diprediksi:
   - `GET /simpadan/captcha.php?action=generate&type=count_items`
   - Respons:
     ```json
     {
       "grid": ["🐡","🍎","🍿","🐶","🐡","🐡","🍇","🐡","🍓","🐹","🐡","🔆","🔆","💫","🍕","🐡"],
       "grid_size": 4,
       "target": "🐡",
       "prompt": "Ada berapa 🐡 di grid?",
       "type": "count_items",
       "success": true,
       "expires_in": 180
     }
     ```

3. Hitung jawaban secara otomatis: jumlah `target` di dalam `grid` = **6**.

4. Kirim jawaban tanpa interaksi manusia:
   - `POST /simpadan/captcha.php?action=verify`
   - Body:
     ```json
     {"count": 6, "csrf_token": "<csrf>", "website": "", "email_alt": ""}
     ```
   - Respons:
     ```json
     {"success": true, "message": "Verifikasi berhasil"}
     ```
   - Server menandai sesi sebagai terverifikasi dan mengeluarkan `Set-Cookie: SIMPADAN_SESSID=...`.

5. Sesi hasil bypass dapat langsung digunakan untuk memanggil endpoint yang seharusnya berada di balik captcha (mis. `login.php`, `api.php?action=submit_inbox`). Pada pengujian ini hanya dilakukan satu permintaan `check_nik` sebagai bukti sesi valid dan **tidak ada data pribadi yang diambil**.

Skrip PoC: `poc/captcha_bypass_poc.py` (single-shot, throttled, tanpa enumerasi).

---

## Dampak Temuan

1. **Otomatisasi login (`login.php`)** — penyerang dapat melakukan percobaan kredensial (brute force / password spraying) secara otomatis terhadap akun admin/staf tanpa hambatan captcha.
2. **Otomatisasi pendaftaran (`submit_inbox`)** — pengiriman pendaftaran massal secara otomatis, menimbulkan polusi data dan penyalahgunaan sumber daya.
3. **Pelewatan kontrol keamanan secara umum** — setiap fungsi yang hanya dilindungi captcha menjadi dapat diautomasi; ini memperbesar dampak dari kelemahan lain (mis. enumerasi data) yang bergantung pada kontrol yang sama.
4. **Penyalahgunaan sumber daya berulang** — memperbanyak permintaan otomatis ke server.

Tidak ada data pribadi yang dieksfiltrasi pada pengujian ini; temuan dibuktikan sampai tahap sesi terverifikasi berhasil diperoleh.

---

## Rekomendasi Temuan

1. **Jangan mengirim jawaban ke klien.** Untuk tipe tantangan seperti `count_items`, jangan sertakan nilai jawaban (`target`/`grid`) yang memungkinkan perhitungan otomatis; simpan status dan jawaban tantangan di sisi server (session) dan verifikasi di server.
2. **State satu kali pakai dan kedaluwarsa** — tantangan hanya dapat dipakai sekali dan otomatis kedaluwarsa; simpan nonce tantangan di sesi.
3. **Rate limiting & backoff** per IP/sesi di `captcha.php`, `login.php`, dan `api.php?action=submit_inbox` (percobaan gagal berulang → backoff/lockout).
4. **Gunakan solusi bot-management** (mis. Cloudflare Turnstile) alih-alih captcha buatan sendiri yang jawabannya dikirim ke klien.
5. **Audit menyeluruh** terhadap semua endpoint yang hanya dilindungi captcha dan tambahkan kontrol server-side yang independen.
6. **Logging & monitoring** percobaan otomatis yang mencurigakan.

---

## Data Dukung

- `poc/captcha_bypass_poc.py` — skrip PoC.
- Log HTTP permintaan/respons di atas (get_csrf_token → generate → verify).
- Lampirkan bukti tambahan bila diperlukan.
