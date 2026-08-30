# Changelog

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
