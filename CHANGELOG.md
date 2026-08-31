# Changelog

## [1.9.19] - 2026-08-31

### Security
- Replace the literal Firestore outlet document ID in the README `--outlet`
  example with a `#example_outlet_id` placeholder. The previous value was
  the user's production outlet (Sovéra Laundry) and was visible on every
  prior release. This release scrubs the README; older tags/releases were
  retracted and are no longer downloadable from the public release list.

## [1.9.18] - 2026-08-31

### Added
- `bilas-mcp --update` (alias `--upgrade`) for one-command self-update from
  GitHub. Resolves the running Python interpreter via `sys.executable` and
  runs `pip install --upgrade --force-reinstall --no-deps
  git+https://github.com/elony-7/Bilas.id-MCP-Server.git`, so the update
  always targets the same install location regardless of whether the user
  invoked `bilas-mcp`, `python -m bilas_id_mcp.server`, or a virtualenv
  script. No credentials are touched. New `update_from_github()` helper
  plus two unit tests (help-text contract and mocked pip success path).

### Usage
```
bilas-mcp --update         # pull and reinstall latest from main
bilas-mcp --upgrade        # alias
```

## [1.9.17] - 2026-08-30

### Added
- `bilas_get_ringkasan_outlet` now returns a parsed `summary` block at the top
  of the response, surfaced directly from the `result[0].semua[0]` KPI payload
  the dashboard's Keuangan and Transaksi tabs read. Key fields surfaced:
  - `kiloan` (total KG processed)
  - `satuan` (total piece-count items)
  - `meter` (total meters, e.g. curtains)
  - `omzet`, `pendapatan`, `pengeluaran`, `labarugi`
  - `trxmasuk` (orders received), `trxbatal` (cancelled)
  - `trxemoney`, `trxselfservice`, `biaya_merchant`
  - `graph` (daily chart array, carried verbatim)
- New helper `_summarize_ringkasan(api_response)` extracts the summary block,
  handling both the `semua` and per-outlet key shapes. Used internally by
  `bilas_get_ringkasan_outlet` and available for future tools.
- Two new unit tests covering the summarizer (happy path + empty response).

This means "how many KG was processed in August?" can now be answered by
`bilas_get_ringkasan_outlet("2026/08/01","2026/08/30")` reading
`summary.kiloan` — no per-order line-item summation needed.

## [1.9.16] - 2026-08-30

### Fixed
- `bilas_get_cashbox_report` now sends the dashboard's full request body
  (`pemilik`, `dibuat_tgl`, `user`, `mode`, `tipe`, `send_data`) instead of
  the minimal `{id, tgl_awal, tgl_akhir, req_id}` body. The minimal body
  was silently returning `saldo_sebelum = 0` for every cashbox, dropping
  the stored opening baseline the dashboard Cashbox tab displays
  (e.g. Tunai 800,000 / BCA 620,746 / QRIS 41,802 for the August range).
  With the full body, the per-cashbox `saldo_awal` now matches the
  dashboard's value exactly. This also restores the live behavior that
  v1.9.12 last exhibited before the Bilas endpoint tightened its body
  requirements.

## [1.9.15] - 2026-08-30

### Fixed
- Map the 14 dashboard report tools to the live Bilas endpoints, not the
  speculative ones captured in the v1.9.13 review. Verified paths:
  - `pendapatan_transaksi` -> `/v1/laporanoutlet/keuangan/pendapatan`
  - `topup_paket` -> `/v1/laporanoutlet/keuangan/pendapatanpaket`
  - `topup_deposit` -> `/v1/laporanoutlet/keuangan/pendapatanemoney`
  - `self_service_income` -> `/v1/qris/pendapatanselfservice`
  - `other_income` -> `/v1/laporanoutlet/keuangan/pendapatanlain`
  - `merchant_fees` -> `/v1/laporanoutlet/keuangan/biayalayanan`
  - `top_customers` -> `/v1/laporanoutlet/pelanggan/toppelanggan`
  - `package_quota` -> `/v1/laporanoutlet/pelanggan/sisakuota`
  - `deposit_balance` -> `/v1/laporanoutlet/pelanggan/sisaemoney`
  - `kasbon_history` -> `/v1/laporanoutlet/pelanggan/riwayatbon`
- Send the dashboard's full request body (`pemilik`, `user`, `mode`, `tipe`,
  `send_data`) — the simple `{id, tgl_awal, tgl_akhir, req_id}` body was
  being silently dropped. `ringkasan_outlet` additionally expects `id` to
  be a JSON-encoded array of `{id_outlet, dibuat_tgl}` descriptors.
- Surface underlying transport error class in error messages instead of
  returning a generic "could not be retrieved" string.

## [1.9.14] - 2026-08-30

### Fixed
- Restore the `x-access-token` and `x-access-web-token` default values that
  the Bilas API requires on dashboard report requests. v1.9.13 dropped them
  to a strictly env-driven model, which caused every authenticated call to
  return `HTTP 401 Unauthorized`. The defaults now match the values shipped
  before v1.9.13 while the `BILAS_ACCESS_TOKEN` and `BILAS_WEB_TOKEN`
  environment variables continue to override them for deployments that
  inject their own application credentials.

## [1.9.13] - 2026-08-30

### Added
- 14 read-only dashboard report tools covering the Bilas sidebar matrix:
  - `bilas_get_ringkasan_outlet` (Ringkasan Outlet)
  - `bilas_get_pendapatan_transaksi` (Pendapatan Transaksi / Omzet)
  - `bilas_get_topup_paket` (Topup Paket)
  - `bilas_get_topup_deposit` (Topup Deposit / e-money)
  - `bilas_get_self_service_income`
  - `bilas_get_other_income`
  - `bilas_get_piutang` (Kasbon & Piutang)
  - `bilas_get_pembulatan`
  - `bilas_get_merchant_fees` (Biaya Layanan)
  - `bilas_get_customer_growth`
  - `bilas_get_top_customers`
  - `bilas_get_package_quota`
  - `bilas_get_deposit_balance`
  - `bilas_get_kasbon_history`
- Shared `_validate_report_dates` and `_post_report` helpers that reject
  malformed or reversed date ranges locally and preserve the raw API response
  alongside normalized metadata (endpoint, period, request_id, outlet_id,
  http status). The same validator is now applied to the existing
  `bilas_get_cashbox_report` path so its input contract matches the rest of
  the dashboard family.
- Behavior tests in `tests/test_dashboard_reports.py` covering the date
  validator, endpoint selection, row normalization, network error contract,
  and MCP tool registration.

### Security
- Replaced the previously hardcoded `x-access-token` and `x-access-web-token`
  defaults in `APP_TOKENS` with optional `BILAS_ACCESS_TOKEN` and
  `BILAS_WEB_TOKEN` environment variables, restoring the README's "zero
  hardcoded credentials" guarantee while preserving behavior when those
  env vars are provided at runtime.

## [1.9.12] - 2026-08-30

### Fixed
- Use Bilas's `aruskasneraca` endpoint for exact per-cashbox opening, debit, credit, and closing balances.
- Remove manual opening-balance inputs and zero-balance fallbacks from Cashbox-tab reports.

## [1.9.11] - 2026-08-30

### Fixed
- Match Cashbox-tab balances by requiring explicit per-cashbox opening balances and returning `saldo_awal` and `saldo_akhir`.
- Prevent movement-only totals from being mislabeled as current cashbox balances.

## [1.9.9] - 2026-08-30

### Fixed
- Include all required `waktu_*` timestamp fields in flat forward and backward production payloads.
- Preserve existing correction timestamps and normalize missing or serialized `None` values to empty strings.

## [1.9.8] - 2026-08-30

### Fixed
- Send forward production updates as flat detail-item payloads matching the dashboard API.
- Clear later station assignments when advancing an item so stale workflow fields cannot block persistence.

## [1.9.7] - 2026-08-30

### Fixed
- Match the Bilas dashboard Koreksi/Riwayat detail payload for backward production corrections.
- Preserve existing station assignments while changing only the selected item `proses` value.


## [1.9.6] - 2026-08-30

### Release
- Packaged the verified production update and backward-stage correction tools as the v1.9.6 release.

## [1.9.5] - 2026-08-30

### Fixed
- Preserve top-level order status during detail updates and verify mutations after API acknowledgement.

### Added
- Added `bilas_revert_item_stage` for one-item backward production corrections using the dashboard Koreksi/Riwayat payload.


## [1.9.4] - 2026-08-30

### Fixed
- **Production Stage Update Payload (`bilas_update_order_status`)**: Discovered that Bilas's `/web/transaksi/produksi/update` endpoint expects the full order object wrapped in `dataTransaksi` along with `id_layanan`, `id_paket`, and `id_operator` at the top level. Previously tried variants were missing the `id_layanan` and `id_paket` fields. Stage transitions are now accepted by the server and logged properly.

## [1.9.3] - 2026-08-30

### Fixed
- **Joblist Workflow Guard (`bilas_update_order_status`)**: Prevent sending invalid *Setrika* API calls to non-ironing services (e.g., *Cuci Lipat* with `joblist: 110`). The tool now gracefully skips the call with an informative message.
- **Robust Response Parser**: Added protection against non-JSON or `undefined` backend responses from production endpoints so JSONDecodeError is never raised.
- **Clear Item & Stage Logging**: Returned structured breakdown showing status for each line item processed in multi-service orders.

## [1.9.2] - 2026-08-30

### Enhanced
- **Multi-Service & Per-Item Production Updates (`bilas_update_order_status`)**:
  - Support granular per-item targeting by `item_index` (1, 2...) or `item_name` for invoices containing multiple service types.
  - Automatically routes stage updates to dedicated production endpoints (`/web/transaksi/produksi/setrika`, `/cuci`, `/pengeringan`, `/selesai`, `/ambil`).
  - Validates `joblist` workflow constraints per service item (e.g. automatically handles services without an ironing station).

## [1.9.1] - 2026-08-30

### Changed / Performance Fix
- **Native Fast Customer Directory (`bilas_list_customers`)**: Replaced slow full-order transaction table scan with Bilas native dedicated customer profile endpoint (`/web/pelanggan/list`). Execution time drops from ~25s to **< 0.6s**.

## [1.9.0] - 2026-08-30

### Added
- **Order Item & Service Breakdown (`bilas_get_order_details`)**: Retrieve line-by-line *Detail Layanan* for any transaction (Package/Service name, weight/piece quantity with unit *Kg/Satuan*, unit price, total price, perfume, line item notes, and image URL).
- **Order Pipeline Status Filtering (`bilas_list_orders_by_status`)**: List and filter active orders directly by production stage (*Antrian*, *Proses*, *Setrika*, *Siap Ambil*, *Selesai*, or *all*).

## [1.8.0] - 2026-08-30

### Added
- **Order Status Updates (`bilas_update_order_status`)**: Move orders between production stages (*Antrian* → *Proses* → *Setrika* → *Siap Ambil* → *Selesai*) and assign operators, machines, or progress notes.
- **Real-Time Live Cashbox Balances (`bilas_get_live_cashbox_balances`)**: Calculate actual current cashbox net balances and inflow/outflow per channel (*Tunai*, *BCA*, *QRIS*) from live ledger entries.
- **Order Creation (`bilas_create_order`)**: Create new regular laundry transactions directly with customer info, service items, amount, and payment method.
- **Customer Management (`bilas_list_customers`)**: View customer profiles, phone numbers, total order counts, lifetime spend, and last order dates.

All notable changes to the **Bilas.id MCP Server** project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.7.0] - 2026-08-30

### Added
- **Complete MCP Protocol Exposure**: Full docstrings, parameter schemas, usage guidelines, and read/write labels exposed across all 11 MCP tools via `tools/list`.
- **JSON Payload Bookmarklet Transfer**: 1-Click Bookmarklet now extracts and copies a complete JSON payload containing both `jwt` token and `outlet_id` to system clipboard while transferring to `127.0.0.1:8765`.
- **Flexible `--token` Input Parsing**: CLI argument `bilas-mcp --token` can now parse either raw JWT strings or full JSON payload dumps (`{"jwt": "...", "outlet_id": "..."}`) automatically.
- **Built-in CLI Help Command**: `--help` and `-h` flags output a structured CLI & MCP tool reference menu.
- **Dedicated CHANGELOG.md**: Documented version history and release milestones.

### Fixed
- **NameError Fix in Onboarding Menu**: Fixed broken function reference on choice `1` in `interactive_onboarding_menu()`.
- **Sanitized Outlet ID Parsing**: Automatically strips full JSON object dumps stored as string literals in `save_state()` down to clean raw Firestore document IDs (`outlet_id`).

### Security
- **Purged Hardcoded Credentials**: Removed all hardcoded default outlet IDs and sensitive fallback constants from codebase to guarantee 100% per-user session isolation in `~/.bilas_id/token_state.json`.

---

## [1.6.0] - 2026-08-30

### Added
- **Official GitHub Release Assets**: First tagged production release (`v1.6.0`).
- **Comprehensive Tool Registry**: Added detailed agent guidance to MCP tool descriptions and authentication error messages.

---

## [1.5.0] - 2026-08-30

### Added
- **Direct CLI Token Onboarding**: Added `bilas-mcp --token <JWT> [--outlet <ID>]` CLI command.

---

## [1.4.0] - 2026-08-29

### Added
- **5-Column Cashbox Accounting Matrix**: Added `bilas_get_cashbox_report` combining Arus Kas and Pemindahan Saldo.
- **System Default Browser Bridge**: Native `webbrowser.open()` integration to bypass Google OAuth bot detection.
