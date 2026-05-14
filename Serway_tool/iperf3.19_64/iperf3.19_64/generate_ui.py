"""
generate_ui.py  —  run once to create ui/app.py and the new survey_wifi.py
"""
import os, textwrap

BASE = os.path.dirname(os.path.abspath(__file__))
BACKUP = os.path.join(BASE, "survey_wifi_backup.py")

# Read the backup
with open(BACKUP, encoding="utf-8") as f:
    lines = f.readlines()

# ── helpers ───────────────────────────────────────────────
def line_range(start, end):
    """1-based inclusive."""
    return lines[start - 1 : end]

# ── NEW IMPORTS for ui/app.py ─────────────────────────────
HEADER = textwrap.dedent("""\
    \"\"\"
    ui/app.py
    Main WifiSurveyApp window — delegates all network/storage work to modules.
    \"\"\"
    import os
    import threading
    from datetime import datetime

    import customtkinter as ctk
    import matplotlib.pyplot as plt
    import pandas as pd
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from tkinter import filedialog

    from config import (
        APP_TITLE, SERVER_IP, IPERF_PORT, IPERF_DURATION,
        UDP_BANDWIDTH, PING_COUNT, DEFAULT_SHEET_NAME,
        SPECTRUM_IMAGE_ROOT, SPECTRUM_IMAGE_DIRNAME, SPECTRUM_REFRESH_MS,
    )
    from utils.helpers import safe_filename, sanitize_db_value
    from network.wlan import get_wlan_info, measure_noise_snr, lookup_ap_vendor
    from network.ping import get_default_gateway, ping_host
    from network.iperf import run_iperf, parse_iperf_tcp_upload, parse_iperf_tcp_download, parse_iperf_udp
    from network.spectrum import scan_wifi_live, analyze_channel_quality, render_spectrum, draw_spectrum_to_file
    from storage.excel import resolve_output_file, save_to_excel
    from storage.supabase_db import (
        parse_winmtr_txt, save_to_supabase, save_winmtr_to_supabase,
    )

""")

# ── Extract the class body from backup (lines 64-1624) ───
# Replace self.* calls with module-level calls where needed.
CLASS_LINES = line_range(64, 1624)

# Patch method calls inside execute_test / import_winmtr_txt
# so they use module functions instead of self.*
REPLACEMENTS = [
    (
        'self.iperf_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "iperf3.exe")',
        'base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))\n        self.iperf_path = os.path.join(base_dir, "bin", "iperf3", "iperf3.exe")',
    ),
    ("self.get_wlan_info()",             "get_wlan_info()"),
    ("self.measure_noise_snr(",          "measure_noise_snr("),
    ("self.get_default_gateway()",       "get_default_gateway()"),
    ("self.ping_host(",                  "ping_host("),
    ("self.ping_for_stats(",             "ping_for_stats("),
    ("self.run_iperf(",                  "run_iperf(self.iperf_path, "),
    ("self.parse_iperf_tcp_upload(",     "parse_iperf_tcp_upload("),
    ("self.parse_iperf_tcp_download(",   "parse_iperf_tcp_download("),
    ("self.parse_iperf_udp(",            "parse_iperf_udp("),
    ("self.scan_wifi_live()",            "scan_wifi_live(self.wifi_cache)"),
    ("self.analyze_channel_quality(",    "analyze_channel_quality(self.wifi_cache, "),
    ("self._render_spectrum(self.ax)",   "render_spectrum(self.ax, self.wifi_cache, self.ssid_colors)"),
    ("self._render_spectrum(ax)",        "render_spectrum(ax, self.wifi_cache, self.ssid_colors)"),
    ("self.draw_spectrum_to_file(image_path)", "draw_spectrum_to_file(image_path, self.wifi_cache, self.ssid_colors)"),
    ("self.lookup_ap_vendor(",           "lookup_ap_vendor("),
    ("self.resolve_output_file(",        "resolve_output_file("),
    ("self.save_to_excel(",              "save_to_excel("),
    ("self.safe_filename(",              "safe_filename("),
    ("self.sanitize_db_value(",          "sanitize_db_value("),
    ("self.parse_winmtr_txt(",           "parse_winmtr_txt("),
    ("self.save_to_supabase(df, None)",  "save_to_supabase(df)"),
    ("self.save_winmtr_to_supabase(",    "save_winmtr_to_supabase("),
    ("self.run_command(",                "_run_cmd("),
    ("self._creation_flags()",           "_creation_flags_flag()"),
    ("self.powershell_escape(",          "_ps_escape("),
    ("self.run_powershell_json(",        "_run_ps_json("),
    ("self.normalize_band(",             "normalize_band("),
    ("self.infer_band_from_channel(",    "infer_band_from_channel("),
    ("self.rate_result(",                "self.rate_result("),   # keep this one
    ("self.normalize_key(",              "_normalize_key("),
    ("self.find_interface_value(",       "_find_value("),
    ("self.find_mac_address(",           "_find_mac("),
    ("self.parse_percent(",              "parse_percent_value("),
    ("self.parse_float(",                "parse_float_value("),
    ("self.get_or_create_trace_survey_id(", "get_or_create_trace_survey_id("),
]

# Methods that are now fully in modules — skip them from the class body
SKIP_METHOD_NAMES = {
    "normalize_key", "find_interface_value", "find_mac_address",
    "parse_percent", "parse_float", "get_wlan_info", "measure_noise_snr",
    "infer_band_from_channel", "normalize_band", "lookup_ap_vendor",
    "get_default_gateway", "ping_host", "ping_for_stats",
    "_creation_flags", "run_command", "powershell_escape", "run_powershell_json",
    "run_iperf", "parse_iperf_tcp_upload", "parse_iperf_tcp_download", "parse_iperf_udp",
    "scan_wifi_live", "analyze_channel_quality", "_render_spectrum", "draw_spectrum_to_file",
    "resolve_output_file", "save_to_excel",
    "read_text_file_safely", "is_ipv4_address", "resolve_winmtr_host_to_ip",
    "parse_winmtr_txt", "save_winmtr_to_supabase", "get_or_create_trace_survey_id",
    "save_to_supabase", "sanitize_db_value", "safe_filename",
}

import re

def method_name_at(line):
    """If line starts a def inside the class, return the method name, else None."""
    m = re.match(r"    def (\w+)\(", line)
    return m.group(1) if m else None

def patch(line):
    for old, new in REPLACEMENTS:
        line = line.replace(old, new)
    return line

# ── Filter + patch class lines ───────────────────────────
out_lines = []
skip = False
i = 0
while i < len(CLASS_LINES):
    raw = CLASS_LINES[i]
    mname = method_name_at(raw)
    if mname and mname in SKIP_METHOD_NAMES:
        skip = True
        i += 1
        continue
    if skip:
        # End of skipped method when we hit next def or class ends
        if re.match(r"    def |\nclass ", raw):
            skip = False
        else:
            i += 1
            continue
    out_lines.append(patch(raw))
    i += 1

# ── Write ui/app.py ──────────────────────────────────────
ui_dir = os.path.join(BASE, "ui")
os.makedirs(ui_dir, exist_ok=True)
with open(os.path.join(ui_dir, "app.py"), "w", encoding="utf-8") as f:
    f.write(HEADER)
    f.writelines(out_lines)
print("[OK] ui/app.py written")

# ── Write new survey_wifi.py (entry point) ───────────────
ENTRY = textwrap.dedent("""\
    \"\"\"
    survey_wifi.py  —  entry point
    \"\"\"
    from ui.app import WifiSurveyApp

    if __name__ == "__main__":
        app = WifiSurveyApp()
        app.mainloop()
""")
with open(os.path.join(BASE, "survey_wifi.py"), "w", encoding="utf-8") as f:
    f.write(ENTRY)
print("[OK] survey_wifi.py written")
print("Done.")
