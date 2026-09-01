"""Bilas.id MCP Server — constants and configuration defaults."""
from pathlib import Path

VERSION = "1.9.24"

# User config & state paths (NEVER write tokens to workspace root)
CONFIG_DIR = Path.home() / ".bilas_id"
STATE_FILE = CONFIG_DIR / "token_state.json"

# Fixed application-level tokens required by Bilas backend
APP_TOKENS = {
    "x-access-token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjYxOWM2NmY5MGY5YjU3MDAxOGEwYmU5YiIsImlhdCI6MTYzNzY1NjMxM30.7m_W1Zg_oE6Tq7mXp9Y_Z9Y_Z9Y_Z9Y_Z9Y_Z9Y_Z9Y",
    "x-access-web-token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
    "Content-Type": "application/json",
}

# Base URLs
ARUSKAS_URL = "https://laporan.apibilas.com/v1/laporanoutlet/keuangan/aruskas"
ARUSKAS_NERACA_URL = "https://laporan.apibilas.com/v1/laporanoutlet/keuangan/aruskasneraca"
APIWEB_BASE = "https://apiweb.bilas.id"

# 15 standard report endpoints on the laporan.apibilas.com domain
REPORT_ENDPOINTS = {
    "ringkasan_outlet": "https://laporan.apibilas.com/v1/laporanoutlet/ringkasan",
    "pendapatan_transaksi": "https://laporan.apibilas.com/v1/laporanoutlet/keuangan/pendapatan",
    "pengeluaran_transaksi": "https://laporan.apibilas.com/v1/laporanoutlet/keuangan/pengeluaran",
    "topup_paket": "https://laporan.apibilas.com/v1/laporanoutlet/keuangan/pendapatanpaket",
    "topup_deposit": "https://laporan.apibilas.com/v1/laporanoutlet/keuangan/pendapatanemoney",
    "self_service_income": "https://laporan.apibilas.com/v1/laporanoutlet/keuangan/pendapatanselfservice",
    "other_income": "https://laporan.apibilas.com/v1/laporanoutlet/keuangan/pendapatanlainnya",
    "piutang": "https://laporan.apibilas.com/v1/laporanoutlet/keuangan/piutang",
    "pembulatan": "https://laporan.apibilas.com/v1/laporanoutlet/keuangan/pembulatan",
    "merchant_fees": "https://laporan.apibilas.com/v1/laporanoutlet/keuangan/biayalayanan",
    "customer_growth": "https://laporan.apibilas.com/v1/laporanoutlet/pelanggan/pertumbuhan",
    "top_customers": "https://laporan.apibilas.com/v1/laporanoutlet/pelanggan/toppelanggan",
    "package_quota": "https://laporan.apibilas.com/v1/laporanoutlet/pelanggan/sisakuotapaket",
    "deposit_balance": "https://laporan.apibilas.com/v1/laporanoutlet/pelanggan/sisaemoney",
    "kasbon_history": "https://laporan.apibilas.com/v1/laporanoutlet/pelanggan/riwayatkasbon",
}
