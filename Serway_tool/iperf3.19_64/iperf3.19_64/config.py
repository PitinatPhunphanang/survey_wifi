import os

import matplotlib.colors as mcolors
from dotenv import load_dotenv


# =========================
# LOAD .env
# =========================
def find_and_load_env():
    """Search for .env.local in parent directories and load it."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    for _ in range(5):  # Check up to 5 parent directories
        env_path = os.path.join(current_dir, ".env.local")
        if os.path.exists(env_path):
            load_dotenv(env_path)
            return
        current_dir = os.path.dirname(current_dir)


find_and_load_env()

# =========================
# APP CONFIG
# =========================
SERVER_IP = "10.8.1.93"
IPERF_PORT = 5202
IPERF_DURATION = 10
UDP_BANDWIDTH = "10G"
PING_COUNT = 4
APP_TITLE = "Wi-Fi Survey Excel Pro v6 - WinMTR Import"
DEFAULT_SHEET_NAME = "Raw_Data"

# Spectrum / image config
SPECTRUM_IMAGE_ROOT = "Survey_Data"
SPECTRUM_IMAGE_DIRNAME = "Spectrum_Images"
SPECTRUM_CACHE_TIMEOUT = 60
SPECTRUM_REFRESH_MS = 10000
COLOR_CYCLE = list(mcolors.TABLEAU_COLORS.values()) + list(mcolors.CSS4_COLORS.values())

# =========================
# SUPABASE CONFIG
# =========================
SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SECRET_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ ERROR: Supabase credentials not found in .env.local")
    print("Make sure NEXT_PUBLIC_SUPABASE_URL and SUPABASE_SECRET_KEY are set")
