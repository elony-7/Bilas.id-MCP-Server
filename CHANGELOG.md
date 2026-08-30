# Changelog

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
