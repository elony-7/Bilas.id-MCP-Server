"""Bilas.id MCP Server — shared constants and configuration."""
import os
from pathlib import Path

VERSION = "1.9.23"

USER_HOME = Path.home()
CONFIG_DIR = USER_HOME / ".bilas_id"
STATE_FILE = CONFIG_DIR / "token_state.json"

# Bilas identifies the calling application via two static headers
# (`x-access-token`, `x-access-web-token`) in addition to the user JWT.
# They can be overridden at runtime with the BILAS_ACCESS_TOKEN and
# BILAS_WEB_TOKEN environment variables, but default values are required
# for the dashboard report endpoints to authorize requests at all.
APP_TOKENS = {
    "x-access-token": os.environ.get("BILAS_ACCESS_TOKEN", "sjgyfne73592643gedudney3628465hgrdt"),
    "x-access-web-token": os.environ.get("BILAS_WEB_TOKEN", "UD1P6jZ0XKErPm5hQ4dKSXu5MQv6h8oOGeT78CVpXXAxC7H4LrtEZtj2BnwHKKcnuLfRtZYvne3Qlb2aUVg"),
    "Content-Type": "application/json",
}

# ── API Endpoints ──────────────────────────────────────────────────────────
ARUSKAS_URL = "https://laporan.apibilas.com/v1/laporanoutlet/keuangan/aruskas"
ARUSKAS_NERACA_URL = "https://laporan.apibilas.com/v1/laporanoutlet/keuangan/aruskasneraca"
PEMINDAHAN_URL = "https://laporan.apibilas.com/v1/laporanoutlet/keuangan/pemindahansaldo"

REPORT_ENDPOINTS = {
    "ringkasan_outlet": "https://laporan.apibilas.com/v1/laporanoutlet/ringkasan",
    "pendapatan_transaksi": "https://laporan.apibilas.com/v1/laporanoutlet/keuangan/pendapatan",
    "pengeluaran_transaksi": "https://laporan.apibilas.com/v1/laporanoutlet/keuangan/pengeluaran",
    "topup_paket": "https://laporan.apibilas.com/v1/laporanoutlet/keuangan/pendapatanpaket",
    "topup_deposit": "https://laporan.apibilas.com/v1/laporanoutlet/keuangan/pendapatanemoney",
    "self_service_income": "https://laporan.apibilas.com/v1/qris/pendapatanselfservice",
    "other_income": "https://laporan.apibilas.com/v1/laporanoutlet/keuangan/pendapatanlain",
    "piutang": "https://laporan.apibilas.com/v1/laporanoutlet/keuangan/piutang",
    "pembulatan": "https://laporan.apibilas.com/v1/laporanoutlet/keuangan/pembulatan",
    "merchant_fees": "https://laporan.apibilas.com/v1/laporanoutlet/keuangan/biayalayanan",
    "customer_growth": "https://laporan.apibilas.com/v1/laporanoutlet/pelanggan/pertumbuhan",
    "top_customers": "https://laporan.apibilas.com/v1/laporanoutlet/pelanggan/toppelanggan",
    "package_quota": "https://laporan.apibilas.com/v1/laporanoutlet/pelanggan/sisakuota",
    "deposit_balance": "https://laporan.apibilas.com/v1/laporanoutlet/pelanggan/sisaemoney",
    "kasbon_history": "https://laporan.apibilas.com/v1/laporanoutlet/pelanggan/riwayatbon",
}

APIWEB_BASE = "https://apiweb.bilas.id"
