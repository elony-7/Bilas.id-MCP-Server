# Changelog

## [1.8.0] - 2026-08-30

### Added
- **Order Status Updates ()**: Move orders between production stages (*Antrian* → *Proses* → *Setrika* → *Siap Ambil* → *Selesai*) and assign operators, machines, or progress notes.
- **Real-Time Live Cashbox Balances ()**: Calculate actual current cashbox net balances and inflow/outflow per channel (*Tunai*, *BCA*, *QRIS*) from live ledger entries.
- **Order Creation ()**: Create new regular laundry transactions directly with customer info, service items, amount, and payment method.
- **Customer Management ()**: View customer profiles, phone numbers, total order counts, lifetime spend, and last order dates.

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
