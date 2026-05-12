import concurrent.futures
import json
import os
import re
import socket
import subprocess
import ipaddress
from tkinter import filedialog
import threading
import time
from datetime import datetime

from dotenv import load_dotenv

import customtkinter as ctk
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from supabase import Client, create_client


# Load .env from parent directories
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
# CONFIG
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

# SUPABASE CONFIG
SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SECRET_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ ERROR: Supabase credentials not found in .env.local")
    print("Make sure NEXT_PUBLIC_SUPABASE_URL and SUPABASE_SECRET_KEY are set")


class WifiSurveyApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title(APP_TITLE)
        self.geometry("1600x900")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.iperf_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "iperf3.exe")
        self._test_running = False

        # Spectrum-related cache
        self.wifi_cache = {}
        self.ssid_colors = {}

        self._build_ui()
        self.after(1000, self.update_spectrum_preview)

    # =========================
    # UI
    # =========================
    def _build_ui(self):
        top_wrap = ctk.CTkFrame(self, fg_color="transparent")
        top_wrap.pack(fill="both", expand=True, padx=20, pady=15)

        left_panel = ctk.CTkFrame(top_wrap)
        left_panel.pack(side="left", fill="both", padx=(0, 10))
        left_panel.pack_propagate(False)
        left_panel.configure(width=500)

        right_panel = ctk.CTkFrame(top_wrap)
        right_panel.pack(side="left", fill="both", expand=True, padx=(10, 0))

        # LEFT SIDE
        ctk.CTkLabel(left_panel, text="Wi-Fi Survey Pro", font=("Arial", 24, "bold")).pack(pady=(20, 2))
        ctk.CTkLabel(
            left_panel,
            text=f"iPerf Duration: {IPERF_DURATION}s | Port: {IPERF_PORT}",
            font=("Arial", 11),
            text_color="gray",
        ).pack(pady=(0, 10))

        net_frame = ctk.CTkFrame(left_panel)
        net_frame.pack(padx=20, pady=5, fill="x")

        ctk.CTkLabel(net_frame, text="Network Settings", font=("Arial", 13, "bold")).pack(pady=(10, 0))

        ip_inner = ctk.CTkFrame(net_frame, fg_color="transparent")
        ip_inner.pack(pady=5, fill="x", padx=5)

        ctk.CTkLabel(ip_inner, text="iPerf Server:").grid(row=0, column=0, padx=(3, 2), pady=5, sticky="e")
        self.entry_server_ip = ctk.CTkEntry(ip_inner, width=100)
        self.entry_server_ip.insert(0, SERVER_IP)
        self.entry_server_ip.grid(row=0, column=1, padx=2, pady=5)

        ctk.CTkLabel(ip_inner, text="WinMTR Target:").grid(row=0, column=2, padx=(0, 2), pady=5, sticky="e")
        self.entry_trace_ip = ctk.CTkEntry(ip_inner, width=100)
        self.entry_trace_ip.insert(0, SERVER_IP)
        self.entry_trace_ip.grid(row=0, column=3, padx=2, pady=5)

        input_frame = ctk.CTkFrame(left_panel)
        input_frame.pack(padx=20, pady=5, fill="x")

        ctk.CTkLabel(input_frame, text="Survey Details", font=("Arial", 13, "bold")).pack(pady=(10, 5))

        self.entry_bldg = ctk.CTkEntry(input_frame, placeholder_text="Building (e.g. COE)", width=520)
        self.entry_bldg.pack(pady=5)

        self.entry_floor = ctk.CTkEntry(input_frame, placeholder_text="Floor (e.g. 2)", width=520)
        self.entry_floor.pack(pady=5)

        self.entry_room = ctk.CTkEntry(input_frame, placeholder_text="Room / Test Point (e.g. 201)", width=520)
        self.entry_room.pack(pady=5)

        self.entry_note = ctk.CTkEntry(
            input_frame,
            placeholder_text="Note (optional)",
            width=520,
        )
        self.entry_note.pack(pady=(5, 12))

        btn_frame = ctk.CTkFrame(left_panel)
        btn_frame.pack(padx=20, pady=8, fill="x")

        self.btn_test = ctk.CTkButton(
            btn_frame,
            text="START TEST & SAVE",
            command=self.run_test,
            fg_color="#1f538d",
            hover_color="#14375e",
            height=45,
            font=("Arial", 14, "bold"),
        )
        self.btn_test.pack(side="left", padx=10, pady=10, expand=True, fill="x")

        self.btn_clear = ctk.CTkButton(
            btn_frame,
            text="CLEAR",
            command=self.clear_fields,
            fg_color="#444444",
            hover_color="#333333",
            height=45,
            font=("Arial", 14, "bold"),
        )
        self.btn_clear.pack(side="left", padx=10, pady=10, expand=True, fill="x")

        self.btn_import_winmtr = ctk.CTkButton(
            btn_frame,
            text="IMPORT WINMTR",
            command=self.import_winmtr_txt,
            fg_color="#6b4fbb",
            hover_color="#4c378a",
            height=45,
            font=("Arial", 14, "bold"),
        )
        self.btn_import_winmtr.pack(side="left", padx=10, pady=10, expand=True, fill="x")

        self.status_label = ctk.CTkLabel(left_panel, text="Ready", text_color="gray", font=("Arial", 12))
        self.status_label.pack(pady=2)

        self.result_box = ctk.CTkTextbox(left_panel, width=560, height=300, font=("Courier New", 12))
        self.result_box.pack(pady=10, padx=20, fill="both", expand=True)

        ctk.CTkLabel(
            left_panel,
            text="One building = one workbook. Raw data and WinMTR imports are saved in separate sheets.",
            font=("Arial", 10),
            text_color="gray",
        ).pack(pady=(0, 12))

        # RIGHT SIDE - SPECTRUM
        ctk.CTkLabel(right_panel, text="Spectrum Preview", font=("Arial", 20, "bold")).pack(pady=(20, 6))
        ctk.CTkLabel(
            right_panel,
            text="Live nearby Wi-Fi channels and signal levels",
            font=("Arial", 11),
            text_color="gray",
        ).pack(pady=(0, 8))

        self.spectrum_frame = ctk.CTkFrame(right_panel)
        self.spectrum_frame.pack(padx=15, pady=10, fill="both", expand=True)

        self.fig, self.ax = plt.subplots(figsize=(11, 8), dpi=100)
        self.fig.patch.set_facecolor("#0d1117")

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.spectrum_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

    # =========================
    # UI HELPERS
    # =========================
    def run_on_ui(self, callback, *args, **kwargs):
        if threading.current_thread() is threading.main_thread():
            callback(*args, **kwargs)
        else:
            self.after(0, lambda: callback(*args, **kwargs))

    def set_status(self, text, color="gray"):
        self.run_on_ui(self._set_status_ui, text, color)

    def _set_status_ui(self, text, color):
        self.status_label.configure(text=text, text_color=color)
        self.update_idletasks()

    def set_result_text(self, text):
        self.run_on_ui(self._set_result_text_ui, text)

    def _set_result_text_ui(self, text):
        self.result_box.delete("0.0", "end")
        self.result_box.insert("0.0", text)

    def append_result_text(self, text):
        self.run_on_ui(self._append_result_text_ui, text)

    def _append_result_text_ui(self, text):
        self.result_box.insert("end", text)
        self.result_box.see("end")

    def set_testing_state(self, running):
        self.run_on_ui(self._set_testing_state_ui, running)

    def _set_testing_state_ui(self, running):
        self._test_running = running
        if running:
            self.btn_test.configure(state="disabled", text="Testing...")
        else:
            self.btn_test.configure(state="normal", text="START TEST & SAVE")

    def clear_fields(self):
        if self._test_running:
            self.set_status("A test is running. Please wait until it finishes.", "yellow")
            return
        self.entry_bldg.delete(0, "end")
        self.entry_floor.delete(0, "end")
        self.entry_room.delete(0, "end")
        self.entry_note.delete(0, "end")
        self.result_box.delete("0.0", "end")
        self.set_status("Ready", "gray")

    def safe_filename(self, name: str) -> str:
        cleaned = re.sub(r'[\\/:*?"<>|]', "_", name.strip())
        return cleaned if cleaned else "wifi_survey"

    # =========================
    # COMMAND HELPERS
    # =========================
    def _creation_flags(self):
        if os.name == "nt" and hasattr(subprocess, "CREATE_NO_WINDOW"):
            return subprocess.CREATE_NO_WINDOW
        return 0

    def run_command(self, args, timeout=20):
        return subprocess.run(
            args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=timeout,
            creationflags=self._creation_flags(),
        )

    def powershell_escape(self, value):
        return str(value).replace("'", "''")

    def run_powershell_json(self, script, timeout=20):
        result = self.run_command(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
            timeout=timeout,
        )

        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        if result.returncode != 0 and not stdout:
            raise RuntimeError(stderr or "PowerShell command failed.")
        if not stdout:
            return None

        try:
            return json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Failed to parse PowerShell JSON output: {stdout[:200]}") from exc

    # =========================
    # WLAN INFO
    # =========================
    def get_wlan_info(self):
        info = {
            "SSID": "Unknown",
            "BSSID": "Unknown",
            "Band": "Unknown",
            "Channel": "Unknown",
            "Radio_Type": "Unknown",
            "Receive_Rate_Mbps": None,
            "Transmit_Rate_Mbps": None,
            "Signal_%": None,
            "RSSI_dBm": None,
        }

        try:
            result = self.run_command(["netsh", "wlan", "show", "interfaces"], timeout=8)
            text = result.stdout
            pairs = []

            for raw_line in text.splitlines():
                line = raw_line.strip()
                if ":" not in line:
                    continue
                key, value = line.split(":", 1)
                pairs.append((self.normalize_key(key), value.strip()))

            info["SSID"] = self.find_interface_value(pairs, ["ssid"]) or info["SSID"]
            info["BSSID"] = self.find_interface_value(pairs, ["apbssid", "bssid"]) or info["BSSID"]
            info["Band"] = self.find_interface_value(pairs, ["band"]) or info["Band"]
            info["Channel"] = self.find_interface_value(pairs, ["channel"]) or info["Channel"]
            info["Radio_Type"] = self.find_interface_value(pairs, ["radiotype"]) or info["Radio_Type"]

            rx_rate = self.find_interface_value(pairs, ["receiveratembps", "receiverate(mbps)"])
            tx_rate = self.find_interface_value(pairs, ["transmitratembps", "transmitrate(mbps)"])
            signal = self.find_interface_value(pairs, ["signal"])
            rssi = self.find_interface_value(pairs, ["rssi"])

            info["Receive_Rate_Mbps"] = self.parse_float(rx_rate)
            info["Transmit_Rate_Mbps"] = self.parse_float(tx_rate)
            info["Signal_%"] = self.parse_percent(signal)
            info["RSSI_dBm"] = self.parse_float(rssi)

            if info["BSSID"] == "Unknown":
                info["BSSID"] = self.find_mac_address(text) or info["BSSID"]

            if info["RSSI_dBm"] is None and info["Signal_%"] is not None:
                info["RSSI_dBm"] = round((info["Signal_%"] / 2) - 100, 1)

            if info["Band"] == "Unknown":
                info["Band"] = self.infer_band_from_channel(info["Channel"])
        except Exception:
            pass

        return info

    def normalize_key(self, value):
        return re.sub(r"[^a-z0-9()%]", "", str(value).strip().lower())

    def find_interface_value(self, pairs, aliases):
        alias_set = set(aliases)
        for key, value in pairs:
            if key in alias_set and value:
                return value
        return None

    def find_mac_address(self, text):
        matches = re.findall(r"(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}", text)
        return matches[0] if matches else None

    def parse_percent(self, value):
        if not value:
            return None
        match = re.search(r"(\d+)", str(value))
        if not match:
            return None
        return int(match.group(1))

    def parse_float(self, value):
        if value is None:
            return None
        match = re.search(r"-?\d+(?:\.\d+)?", str(value))
        if not match:
            return None
        return float(match.group(0))

    # =========================
    # NOISE / SNR MEASUREMENT
    # =========================
    def measure_noise_snr(self, rssi_dbm):
        """
        วัด Noise Floor และ SNR จาก netsh wlan show interfaces
        - ถ้า Windows รายงาน noise ตรงๆ ก็ใช้เลย
        - ถ้าไม่มี field noise ให้คำนวณจาก RSSI - link quality estimate
        - ถ้าวัดไม่ได้เลย คืน None ทั้งหมด (ไม่ใส่ค่าจำลอง)
        """
        noise_floor = None
        snr_db = None
        snr_quality = None

        try:
            result = self.run_command(["netsh", "wlan", "show", "interfaces"], timeout=8)
            text = result.stdout

            # Step 1: หาค่า Noise / Noise Floor จาก netsh โดยตรง
            for raw_line in text.splitlines():
                line = raw_line.strip().lower()
                if "noise" in line and ":" in line:
                    _, val = line.split(":", 1)
                    parsed = self.parse_float(val.strip())
                    if parsed is not None and parsed < 0:
                        noise_floor = round(parsed, 1)
                        break

            # Step 2: ถ้ายังไม่ได้ noise → ลอง wlanreport (Windows 10+)
            if noise_floor is None:
                try:
                    ps_script = (
                        "(Get-NetAdapter | Where-Object {$_.MediaType -eq '802.3' -or $_.PhysicalMediaType -eq 'NativeWifi'} "
                        "| Select-Object -First 1 | Get-NetAdapterStatistics).ReceivedPackets"
                    )
                    # ไม่ใช้ wlanreport เพราะช้า — ข้ามไป Step 3
                    pass
                except Exception:
                    pass

            # Step 3: คำนวณ SNR ถ้ามีทั้ง RSSI และ noise
            if rssi_dbm is not None and noise_floor is not None:
                snr_db = round(rssi_dbm - noise_floor, 1)

                if snr_db >= 40:
                    snr_quality = "Excellent"
                elif snr_db >= 25:
                    snr_quality = "Good"
                elif snr_db >= 15:
                    snr_quality = "Fair"
                else:
                    snr_quality = "Poor"

        except Exception:
            pass

        return noise_floor, snr_db, snr_quality

    def infer_band_from_channel(self, channel):
        try:
            ch = int(str(channel).strip())
            if 1 <= ch <= 14:
                return "2.4 GHz"
            if 36 <= ch <= 177:
                return "5 GHz"
            return "Unknown"
        except Exception:
            return "Unknown"

    def normalize_band(self, band):
        """Normalize band string to standard format: '2.4 GHz' or '5 GHz'."""
        if not band:
            return "Unknown"
        b = str(band).strip().lower().replace(" ", "")
        if "2.4" in b:
            return "2.4 GHz"
        if "5" in b:
            return "5 GHz"
        return "Unknown"

    def lookup_ap_vendor(self, bssid):
        """Look up AP vendor/brand from BSSID using macvendors API."""
        if not bssid or bssid == "Unknown":
            return "Unknown"
        try:
            oui = bssid.replace("-", ":").upper()[:8]
            import urllib.request
            url = f"https://api.macvendors.com/{oui}"
            req = urllib.request.Request(url, headers={"User-Agent": "WifiSurveyApp/1.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.read().decode("utf-8").strip()
        except Exception:
            return "Unknown"

    # =========================
    # ROUTING / PING
    # =========================
    def get_default_gateway(self):
        try:
            result = self.run_command(["route", "print", "-4"], timeout=8)
            best_gateway = None
            best_metric = None

            for raw_line in result.stdout.splitlines():
                line = raw_line.strip()
                match = re.match(
                    r"^0\.0\.0\.0\s+0\.0\.0\.0\s+(\d{1,3}(?:\.\d{1,3}){3})\s+(\d{1,3}(?:\.\d{1,3}){3})\s+(\d+)$",
                    line,
                )
                if not match:
                    continue

                gateway = match.group(1)
                metric = int(match.group(3))

                if best_metric is None or metric < best_metric:
                    best_gateway = gateway
                    best_metric = metric

            return best_gateway or "Unknown"
        except Exception:
            return "Unknown"

    def ping_host(self, host, count=4):
        stats = self.ping_for_stats(host, count=count)
        return stats["Avg"], stats["Loss_%"]

    def ping_for_stats(self, host, count=10):
        if not host or host in ("Unknown", "Timeout", "Unreachable"):
            return {"Min": None, "Max": None, "Avg": None, "Loss_%": None}

        host_escaped = self.powershell_escape(host)
        script = (
            "$ProgressPreference='SilentlyContinue'; "
            f"$r = Test-Connection -Count {int(count)} -ComputerName '{host_escaped}' -ErrorAction SilentlyContinue | "
            "Select-Object ResponseTime; "
            "if ($r) { $r | ConvertTo-Json -Compress }"
        )

        try:
            data = self.run_powershell_json(script, timeout=max(10, count * 3))
            if not data:
                return {"Min": None, "Max": None, "Avg": None, "Loss_%": 100}

            if isinstance(data, dict):
                data = [data]

            times = [int(item["ResponseTime"]) for item in data if item.get("ResponseTime") is not None]
            success_count = len(times)
            loss_pct = round(((count - success_count) / count) * 100) if count else None

            if not times:
                return {"Min": None, "Max": None, "Avg": None, "Loss_%": 100}

            return {
                "Min": min(times),
                "Max": max(times),
                "Avg": round(sum(times) / len(times)),
                "Loss_%": loss_pct,
            }
        except Exception:
            return {"Min": None, "Max": None, "Avg": None, "Loss_%": 100}

    # =========================
    # SPECTRUM / WIFI SCAN
    # =========================
    def scan_wifi_live(self):
        """
        Scan nearby Wi-Fi and cache nearby AP info for spectrum drawing.
        Saved locally only. Not sent to Supabase.
        """
        now = time.time()

        try:
            self.run_command(["netsh", "wlan", "scan"], timeout=10)
            time.sleep(1.5)

            result = self.run_command(
                ["netsh", "wlan", "show", "networks", "mode=bssid"],
                timeout=15,
            )
            out = result.stdout

            blocks = re.findall(r"SSID\s+\d+\s*:.*?(?=\nSSID|\Z)", out, re.S)

            for block in blocks:
                ssid_match = re.search(r"SSID\s+\d+\s*:\s*(.*)", block)
                ssid = ssid_match.group(1).strip() if ssid_match else "Hidden"

                bss_list = re.findall(
                    r"BSSID\s+\d+\s*:\s*([0-9a-f:]+).*?"
                    r"Signal\s*:\s*(\d+)%.*?"
                    r"(?:Band\s*:\s*([\d.]+)\s*GHz)?.*?"
                    r"Channel\s*:\s*(\d+)",
                    block,
                    re.S | re.I,
                )

                for mac, sig, band, ch in bss_list:
                    try:
                        ch_int = int(ch)
                    except Exception:
                        continue

                    if band:
                        band_val = float(band)
                    else:
                        band_val = 5.0 if ch_int > 14 else 2.4

                    rssi = round((int(sig) / 2) - 100, 1)

                    self.wifi_cache[mac.lower()] = {
                        "ssid": ssid if ssid else "Hidden",
                        "band": band_val,
                        "ch": ch_int,
                        "rssi": rssi,
                        "updated": now,
                    }

            for key in list(self.wifi_cache.keys()):
                if now - self.wifi_cache[key]["updated"] > SPECTRUM_CACHE_TIMEOUT:
                    del self.wifi_cache[key]

        except Exception:
            pass

        return self.wifi_cache

    def analyze_channel_quality(self, connected_channel):
        same_channel = 0
        overlap_channel = 0
        strongest_neighbor = -100

        for ap in self.wifi_cache.values():
            ch = ap["ch"]
            rssi = ap["rssi"]

            if rssi > strongest_neighbor:
                strongest_neighbor = rssi

            if ch == connected_channel:
                same_channel += 1

            if connected_channel <= 14:
                if abs(ch - connected_channel) <= 2 and ch != connected_channel:
                    overlap_channel += 1

        return {
            "CoChannel_AP_Count": same_channel,
            "Adjacent_AP_Count": overlap_channel,
            "Strongest_Neighbor_RSSI": strongest_neighbor,
        }

    def _render_spectrum(self, ax):
        ax.clear()
        ax.set_facecolor("#0d1117")

        active_wifi = [n for n in self.wifi_cache.values() if n["rssi"] > -90]
        real_max_ch = max([n["ch"] for n in active_wifi], default=14)
        display_max = max(32, real_max_ch + 5)

        ax.set_xlim(0, display_max)
        ax.set_ylim(-90, -10)
        ax.grid(True, alpha=0.15, color="white", linestyle=":")
        ax.tick_params(colors="white", labelsize=9)
        ax.set_title("Wi-Fi Spectrum Analyzer", color="white", fontsize=12, weight="bold")
        ax.set_xlabel("Channel", color="white")
        ax.set_ylabel("Signal (dBm)", color="white")

        for spine in ax.spines.values():
            spine.set_color("#666666")

        rssi_levels = {}

        for net in sorted(active_wifi, key=lambda x: x["rssi"]):
            ssid = net["ssid"]
            rssi = net["rssi"]
            ch = net["ch"]
            band = net["band"]

            if ssid not in self.ssid_colors:
                self.ssid_colors[ssid] = COLOR_CYCLE[len(self.ssid_colors) % len(COLOR_CYCLE)]

            color = self.ssid_colors[ssid]

            width = 2.2 if band < 3.0 else 5.0
            x_pts = [ch - width, ch - width / 2, ch + width / 2, ch + width]
            y_pts = [-90, rssi, rssi, -90]

            ax.plot(x_pts, y_pts, color=color, linewidth=2, alpha=0.85)
            ax.fill_between(x_pts, -90, y_pts, color=color, alpha=0.15)

            offset = rssi_levels.get(ch, 0)
            label_ssid = ssid if ssid else "Hidden"
            ax.text(
                ch,
                rssi + 1 + offset,
                f"{label_ssid}\n{rssi}dBm",
                color=color,
                fontsize=8,
                ha="center",
                va="bottom",
                weight="bold",
            )
            rssi_levels[ch] = offset + 8

        if display_max > 20:
            ax.text(display_max * 0.10, -15, "2.4GHz Zone", color="gray", alpha=0.6, ha="center", weight="bold")
            ax.text(display_max * 0.70, -15, "5GHz Zone", color="gray", alpha=0.6, ha="center", weight="bold")

        if not active_wifi:
            ax.text(
                0.5,
                0.5,
                "No nearby Wi-Fi data yet",
                transform=ax.transAxes,
                color="gray",
                fontsize=12,
                ha="center",
                va="center",
            )

    def draw_spectrum_on_canvas(self):
        if not hasattr(self, "ax") or not hasattr(self, "canvas"):
            return

        self._render_spectrum(self.ax)
        self.canvas.draw_idle()

    def draw_spectrum_to_file(self, save_path):
        fig, ax = plt.subplots(figsize=(10, 6), dpi=120)
        fig.patch.set_facecolor("#0d1117")
        self._render_spectrum(ax)

        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        fig.savefig(save_path, facecolor="#0d1117", bbox_inches="tight", dpi=120)
        plt.close(fig)

    def update_spectrum_preview(self):
        if self._test_running:
            self.after(3000, self.update_spectrum_preview)
            return

        try:
            self.scan_wifi_live()
            self.draw_spectrum_on_canvas()
        except Exception:
            pass

        self.after(SPECTRUM_REFRESH_MS, self.update_spectrum_preview)

    # =========================
    # IPERF
    # =========================
    def run_iperf(self, server_ip, args, label):
        self.set_status(f"Running {label}...", "yellow")

        if not os.path.exists(self.iperf_path):
            raise FileNotFoundError(f"iperf3.exe was not found at: {self.iperf_path}")

        try:
            proc = self.run_command(
                [self.iperf_path, "-c", server_ip, "-p", str(IPERF_PORT), "-4"] + args + ["--json"],
                timeout=max(40, IPERF_DURATION + 20),
            )

            stdout = proc.stdout.strip()
            stderr = proc.stderr.strip()

            if proc.returncode != 0 and not stdout:
                raise RuntimeError(
                    f"iPerf3 ({label}) failed.\n"
                    f"Command: iperf3.exe -c {server_ip} -p {IPERF_PORT} -4 {' '.join(args)} --json\n"
                    f"stderr: {stderr or '-'}"
                )

            if not stdout:
                raise RuntimeError(f"iPerf3 ({label}) returned no data.")

            try:
                data = json.loads(stdout)
            except json.JSONDecodeError as exc:
                preview = stdout[:500]
                raise RuntimeError(
                    f"iPerf3 ({label}) returned invalid JSON.\n"
                    f"Command: iperf3.exe -c {server_ip} -p {IPERF_PORT} -4 {' '.join(args)} --json\n"
                    f"stdout preview: {preview}"
                ) from exc

            if "error" in data:
                raise RuntimeError(f"iPerf3 ({label}): {data['error']}")

            return data
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"iPerf3 ({label}) timed out.") from exc

    def parse_iperf_tcp_upload(self, data):
        try:
            return round(data["end"]["sum_sent"]["bits_per_second"] / 1e6, 2)
        except Exception:
            return None

    def parse_iperf_tcp_download(self, data):
        try:
            return round(data["end"]["sum_received"]["bits_per_second"] / 1e6, 2)
        except Exception:
            return None

    def parse_iperf_udp(self, data):
        udp_mbps = None
        jitter = None
        loss = None
    
        udp_summary = data.get("end", {}).get("sum_received")

        if not udp_summary:
            udp_summary = data.get("end", {}).get("sum")

        try:
            udp_mbps = round(udp_summary["bits_per_second"] / 1e6, 2)
        except Exception:
            pass

        try:
            jitter = round(udp_summary["jitter_ms"], 2)
        except Exception:
            pass

        try:
            loss = round(udp_summary["lost_percent"], 2)
        except Exception:
            pass

        return udp_mbps, jitter, loss

    # =========================
    # RATING
    # =========================
    def rate_result(self, signal_dbm, upload, download, loss, ping_server):
        try:
            if (
                signal_dbm is not None
                and signal_dbm >= -67
                and upload is not None
                and upload >= 50
                and download is not None
                and download >= 50
                #and loss is not None
                #and loss < 1
                and ping_server is not None
                and ping_server <= 20
            ):
                return "Good"

            if (
                signal_dbm is not None
                and signal_dbm >= -75
                and upload is not None
                and upload >= 20
                and download is not None
                and download >= 20
                and loss is not None
                and loss < 5
            ):
                return "Fair"

            return "Poor"
        except Exception:
            return "Unknown"

    # =========================
    # EXCEL
    # =========================
    def resolve_output_file(self, preferred_file):
        if not os.path.exists(preferred_file):
            return preferred_file

        try:
            with open(preferred_file, "a+b"):
                return preferred_file
        except PermissionError:
            base, ext = os.path.splitext(preferred_file)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            return f"{base}_autosave_{timestamp}{ext}"

    def save_to_excel(self, file_name, sheet_name, df):
        try:
            if not os.path.exists(file_name):
                with pd.ExcelWriter(file_name, engine="openpyxl") as writer:
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
                return

            try:
                existing_df = pd.read_excel(file_name, sheet_name=sheet_name)
                # Keep only columns that exist in the new df (removes stale/removed columns)
                existing_df = existing_df[[c for c in existing_df.columns if c in df.columns]]
                updated_df = pd.concat([existing_df, df], ignore_index=True)
            except ValueError:
                updated_df = df

            with pd.ExcelWriter(
                file_name,
                engine="openpyxl",
                mode="a",
                if_sheet_exists="replace",
            ) as writer:
                updated_df.to_excel(writer, sheet_name=sheet_name, index=False)
        except PermissionError as exc:
            raise PermissionError(
                f"Cannot write to '{file_name}'. Please close the Excel file and try again."
            ) from exc

    # =========================
    # WINMTR TXT IMPORT
    # =========================
    def read_text_file_safely(self, file_path):
        """Read exported WinMTR TXT files with common Windows encodings."""
        encodings = ("utf-8-sig", "utf-16", "cp874", "cp1252", "latin-1")

        last_error = None
        for encoding in encodings:
            try:
                with open(file_path, "r", encoding=encoding, errors="strict") as f:
                    return f.read()
            except UnicodeError as exc:
                last_error = exc

        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()

        if not text and last_error:
            raise RuntimeError(f"Unable to read text file: {last_error}")

        return text

    def is_ipv4_address(self, value):
        try:
            ipaddress.ip_address(str(value).strip())
            return True
        except Exception:
            return False

    def resolve_winmtr_host_to_ip(self, host):
        """Return only an IP-like value for WinMTR rows.

        WinMTR sometimes exports a real IP address and sometimes a hostname,
        for example nperf.psu.ac.th. The database now keeps only the ip column,
        so this function resolves hostnames to IPv4 when possible.
        """
        host_text = str(host or "").strip()
        if not host_text:
            return "Unknown"

        # Handle forms such as: example.com [192.168.1.1]
        bracket_ip = re.search(r"\[(\d{1,3}(?:\.\d{1,3}){3})\]", host_text)
        if bracket_ip:
            return bracket_ip.group(1)

        # Handle plain IP address.
        if self.is_ipv4_address(host_text):
            return host_text

        # Handle hostnames by DNS resolution.
        try:
            return socket.gethostbyname(host_text)
        except Exception:
            # Keep the value instead of dropping the hop. This should be rare,
            # and the visible database schema still has only one column: ip.
            return host_text

    def parse_winmtr_txt(self, file_path):
        """
        Parse WinMTR exported .TXT file.

        Expected WinMTR line format:
        | host - loss | sent | recv | best | avrg | wrst | last |
        """
        rows = []
        text = self.read_text_file_safely(file_path)
        hop_no = 0

        for raw_line in text.splitlines():
            line = raw_line.strip()

            if not line.startswith("|"):
                continue
            if " - " not in line:
                continue

            cleaned = line.strip("|").strip()

            match = re.match(
                r"(.+?)\s+-\s+(\d+)\s*\|\s*"
                r"(\d+)\s*\|\s*"
                r"(\d+)\s*\|\s*"
                r"(\d+)\s*\|\s*"
                r"(\d+)\s*\|\s*"
                r"(\d+)\s*\|\s*"
                r"(\d+)",
                cleaned,
            )

            if not match:
                continue

            hop_no += 1
            host = match.group(1).strip()
            ip = self.resolve_winmtr_host_to_ip(host)

            rows.append(
                {
                    "Hop": hop_no,
                    "IP": ip,
                    "Loss_%": int(match.group(2)),
                    "Sent": int(match.group(3)),
                    "Recv": int(match.group(4)),
                    "Best_ms": int(match.group(5)),
                    "Avg_ms": int(match.group(6)),
                    "Worst_ms": int(match.group(7)),
                    "Last_ms": int(match.group(8)),
                }
            )

        return rows

    def save_winmtr_to_supabase(self, df_winmtr):
        """Upsert WinMTR hop data into public.traceroute_hops."""
        try:
            if not SUPABASE_URL or not SUPABASE_KEY:
                return False, "❌ Supabase credentials not configured. Check .env.local file."

            if df_winmtr is None or df_winmtr.empty:
                return False, "❌ No WinMTR data to save."

            supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

            first_row = df_winmtr.iloc[0]
            survey_id = self.get_or_create_trace_survey_id(
                supabase,
                self.sanitize_db_value(first_row.get("Timestamp")),
                self.sanitize_db_value(first_row.get("Building")),
                self.sanitize_db_value(first_row.get("Floor")),
                self.sanitize_db_value(first_row.get("Room_Point")),
                self.sanitize_db_value(first_row.get("Note")),
                self.sanitize_db_value(first_row.get("Trace_Target")),
            )

            rows = []

            for _, row in df_winmtr.iterrows():
                floor_value = self.sanitize_db_value(row.get("Floor"))
                room_value = self.sanitize_db_value(row.get("Room_Point"))
                ip_value = self.sanitize_db_value(row.get("IP"))
                ip_text = str(ip_value).strip() if ip_value is not None else "Unknown"

                rows.append(
                    {
                        "source": "winmtr",
                        "survey_id": survey_id,
                        "survey_timestamp": self.sanitize_db_value(row.get("Timestamp")),
                        "building": self.sanitize_db_value(row.get("Building")),
                        "floor": str(floor_value) if floor_value is not None else None,
                        "room_point": str(room_value) if room_value is not None else None,
                        "note": self.sanitize_db_value(row.get("Note")),
                        "trace_target": self.sanitize_db_value(row.get("Trace_Target")),
                        "hop_no": int(row.get("Hop")),
                        "ip": ip_text,
                        "loss_pct": self.sanitize_db_value(row.get("Loss_%")),
                        "sent": self.sanitize_db_value(row.get("Sent")),
                        "recv": self.sanitize_db_value(row.get("Recv")),
                        "best_ms": self.sanitize_db_value(row.get("Best_ms")),
                        "avg_ms": self.sanitize_db_value(row.get("Avg_ms")),
                        "worst_ms": self.sanitize_db_value(row.get("Worst_ms")),
                        "last_ms": self.sanitize_db_value(row.get("Last_ms")),
                        "source_file": self.sanitize_db_value(row.get("Source_File")),
                        "updated_at": datetime.now().isoformat(),
                    }
                )

            response = (
                supabase.table("traceroute_hops")
                .upsert(
                    rows,
                    on_conflict="building,floor,room_point,trace_target,hop_no,ip",
                )
                .execute()
            )

            if getattr(response, "data", None) is None:
                return False, f"❌ Failed to save WinMTR data into traceroute_hops: {response}"

            return True, "✅ Saved to Supabase table: traceroute_hops"
        except Exception as e:
            print("WINMTR SUPABASE ERROR:", e)
            return False, f"❌ Supabase Error: {str(e)}"

    def import_winmtr_txt(self):
        """Import a WinMTR TXT export, save it to Excel, then upsert it to Supabase."""
        if self._test_running:
            self.set_status("A test is running. Please wait until it finishes.", "yellow")
            return

        bldg = self.entry_bldg.get().strip()
        floor = self.entry_floor.get().strip()
        room = self.entry_room.get().strip()
        note = self.entry_note.get().strip()
        trace_target = self.entry_trace_ip.get().strip() or self.entry_server_ip.get().strip() or SERVER_IP

        if not bldg or not floor or not room:
            self.set_status("Please fill Building, Floor, and Room/Test Point before importing WinMTR.", "red")
            return

        file_path = filedialog.askopenfilename(
            title="Select WinMTR TXT file",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )

        if not file_path:
            return

        try:
            self.set_status("Importing WinMTR TXT...", "cyan")
            hops = self.parse_winmtr_txt(file_path)

            if not hops:
                self.set_status("No WinMTR hop data found in selected file.", "red")
                self.set_result_text(
                    "No WinMTR hop data found.\n\n"
                    "Please export from WinMTR using Export TEXT and try again."
                )
                return

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            data = []

            for hop in hops:
                data.append(
                    {
                        "Timestamp": timestamp,
                        "Building": bldg,
                        "Floor": floor,
                        "Room_Point": room,
                        "Note": note,
                        "Trace_Target": trace_target,
                        "Hop": hop["Hop"],
                        "IP": hop["IP"],
                        "Loss_%": hop["Loss_%"],
                        "Sent": hop["Sent"],
                        "Recv": hop["Recv"],
                        "Best_ms": hop["Best_ms"],
                        "Avg_ms": hop["Avg_ms"],
                        "Worst_ms": hop["Worst_ms"],
                        "Last_ms": hop["Last_ms"],
                        "Source_File": os.path.basename(file_path),
                    }
                )

            df_winmtr = pd.DataFrame(data)

            base_dir = os.path.join(SPECTRUM_IMAGE_ROOT, self.safe_filename(bldg))
            os.makedirs(base_dir, exist_ok=True)

            preferred_file_name = os.path.join(base_dir, f"{self.safe_filename(bldg)}.xlsx")
            output_file_name = self.resolve_output_file(preferred_file_name)

            self.set_status("Saving WinMTR to Excel...", "cyan")
            self.save_to_excel(output_file_name, "WinMTR", df_winmtr)

            self.set_status("Saving WinMTR to traceroute_hops...", "cyan")
            db_success, db_msg = self.save_winmtr_to_supabase(df_winmtr)

            result_text = (
                f"Imported WinMTR TXT into traceroute_hops successfully\n"
                f"{'-' * 58}\n"
                f"File       : {file_path}\n"
                f"Excel      : {output_file_name}\n"
                f"Rows       : {len(df_winmtr)} hops\n"
                f"Database   : {db_msg}\n"
                f"{'-' * 58}\n"
            )

            for _, row in df_winmtr.iterrows():
                result_text += (
                    f"Hop {int(row['Hop']):<2} | {str(row['IP'])[:24]:<24} | "
                    f"Loss {row['Loss_%']}% | "
                    f"Sent {row['Sent']} | Recv {row['Recv']} | "
                    f"Avg {row['Avg_ms']} ms | Worst {row['Worst_ms']} ms | Last {row['Last_ms']} ms\n"
                )

            self.set_result_text(result_text)

            if db_success:
                self.set_status("WinMTR imported and saved successfully.", "green")
            else:
                self.set_status("WinMTR imported to Excel, but database save failed.", "yellow")
        except Exception as exc:
            self.set_status("WinMTR import failed.", "red")
            self.set_result_text(f"ERROR\n\n{str(exc)}")

    # =========================
    # DATABASE
    # =========================
    def sanitize_db_value(self, value):
        if pd.isna(value):
            return None
        return value

    def get_or_create_trace_survey_id(self, supabase, timestamp, building, floor, room_point, note, trace_target):
        """Find or create a minimal survey row, then return surveys.id for traceroute_hops.survey_id."""
        building_value = str(building or "").strip()
        floor_value = str(floor or "").strip()
        room_value = str(room_point or "").strip()
        note_value = str(note or "").strip()
        trace_target_value = str(trace_target or "").strip()

        existing = (
            supabase.table("surveys")
            .select("id")
            .eq("building", building_value)
            .eq("floor", floor_value)
            .eq("room_point", room_value)
            .eq("note", note_value)
            .eq("trace_target", trace_target_value)
            .limit(1)
            .execute()
        )

        if getattr(existing, "data", None):
            return existing.data[0]["id"]

        survey_data = {
            "survey_timestamp": timestamp,
            "building": building_value,
            "floor": floor_value,
            "room_point": room_value,
            "note": note_value,
            "trace_target": trace_target_value,
        }

        response = supabase.table("surveys").insert(survey_data).execute()
        if not getattr(response, "data", None):
            raise RuntimeError(f"Failed to create survey row for WinMTR import: {response}")

        return response.data[0]["id"]

    def save_to_supabase(self, df_survey, df_trace=None):
        """Save survey data to Supabase. Traceroute is intentionally disabled; WinMTR imports handle hop data."""
        try:
            if not SUPABASE_URL or not SUPABASE_KEY:
                return False, "❌ Supabase credentials not configured. Check .env.local file."

            supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
            final_messages = []

            for _, row in df_survey.iterrows():
                floor_value = self.sanitize_db_value(row.get("Floor"))
                room_value = self.sanitize_db_value(row.get("Room_Point"))
                channel_value = self.sanitize_db_value(row.get("Channel"))

                survey_data = {
                    "survey_timestamp": self.sanitize_db_value(row.get("Timestamp")),
                    "building": self.sanitize_db_value(row.get("Building")),
                    "floor": str(floor_value) if floor_value is not None else None,
                    "room_point": str(room_value) if room_value is not None else None,
                    "note": self.sanitize_db_value(row.get("Note")),
                    "ssid": self.sanitize_db_value(row.get("SSID")),
                    "bssid": self.sanitize_db_value(row.get("BSSID")),
                    "band": self.normalize_band(self.sanitize_db_value(row.get("Band"))),
                    "radio_type": self.sanitize_db_value(row.get("Radio_Type")),
                    "channel": str(channel_value) if channel_value is not None else None,
                    "signal_percent": self.sanitize_db_value(row.get("Signal_%")),
                    "rssi_dbm": self.sanitize_db_value(row.get("RSSI_dBm")),
                    "receive_rate_mbps": self.sanitize_db_value(row.get("Receive_Rate_Mbps")),
                    "transmit_rate_mbps": self.sanitize_db_value(row.get("Transmit_Rate_Mbps")),
                    "gateway_ip": self.sanitize_db_value(row.get("Gateway_IP")),
                    "ping_gateway_ms": self.sanitize_db_value(row.get("Ping_Gateway_ms")),
                    "ping_gateway_loss_pct": self.sanitize_db_value(row.get("Ping_Gateway_Loss_%")),
                    "server_ip": self.sanitize_db_value(row.get("Server_IP")),
                    "trace_target": self.sanitize_db_value(row.get("Trace_Target")),
                    "ping_server_ms": self.sanitize_db_value(row.get("Ping_Server_ms")),
                    "ping_server_loss_pct": self.sanitize_db_value(row.get("Ping_Server_Loss_%")),
                    "tcp_upload_mbps": self.sanitize_db_value(row.get("TCP_Upload_Mbps")),
                    "tcp_download_mbps": self.sanitize_db_value(row.get("TCP_Download_Mbps")),
                    "udp_target_bandwidth": self.sanitize_db_value(row.get("UDP_Target_Bandwidth")),
                    "udp_actual_mbps": self.sanitize_db_value(row.get("UDP_Actual_Mbps")),
                    "udp_jitter_ms": self.sanitize_db_value(row.get("UDP_Jitter_ms")),
                    "udp_packetloss_pct": self.sanitize_db_value(row.get("UDP_PacketLoss_%")),
                    "noise_floor_dbm": self.sanitize_db_value(row.get("Noise_Floor_dBm")),
                    "snr_db": self.sanitize_db_value(row.get("SNR_dB")),
                    "snr_quality": self.sanitize_db_value(row.get("SNR_Quality")),
                    "rating": self.sanitize_db_value(row.get("Rating")),
                    "ap_vendor": self.sanitize_db_value(row.get("AP_Vendor")),
                }

                # Keep the existing duplicate check for the survey row.
                existing = (
                    supabase.table("surveys")
                    .select("id")
                    .eq("building", survey_data["building"] or "")
                    .eq("floor", survey_data["floor"] or "")
                    .eq("room_point", survey_data["room_point"] or "")
                    .eq("note", survey_data["note"] or "")
                    .eq("band", survey_data["band"] or "")
                    .eq("ssid", survey_data["ssid"] or "")
                    .execute()
                )

                if existing.data:
                    survey_id = existing.data[0]["id"]
                    final_messages.append("Survey already exists; survey data was not duplicated.")
                else:
                    response = supabase.table("surveys").insert(survey_data).execute()

                    if not getattr(response, "data", None):
                        return False, f"❌ Failed to insert survey data: {response}"

                    survey_id = response.data[0]["id"]
                    final_messages.append("Survey saved.")

            message = "✅ Saved to Supabase successfully! " + " ".join(final_messages)
            return True, message
        except Exception as e:
            print("SUPABASE ERROR:", e)
            return False, f"❌ Supabase Error: {str(e)}"

    # =========================
    # MAIN TEST FLOW
    # =========================
    def run_test(self):
        if self._test_running:
            self.set_status("A test is already running.", "yellow")
            return

        payload = {
            "server_ip": self.entry_server_ip.get().strip() or SERVER_IP,
            # Kept only as metadata for WinMTR imports / Raw_Data.
            "trace_ip": self.entry_trace_ip.get().strip() or (self.entry_server_ip.get().strip() or SERVER_IP),
            "bldg": self.entry_bldg.get().strip(),
            "floor": self.entry_floor.get().strip(),
            "room": self.entry_room.get().strip(),
            "note": self.entry_note.get().strip(),
        }

        if not payload["server_ip"] or not payload["bldg"] or not payload["floor"] or not payload["room"]:
            self.set_status("Please fill in Server IP, Building, Floor, and Room/Test Point.", "red")
            return

        self.set_testing_state(True)
        self.set_result_text("")
        self.set_status("Starting test...", "cyan")

        worker = threading.Thread(target=self._run_test_worker, args=(payload,), daemon=True)
        worker.start()

    def _run_test_worker(self, payload):
        try:
            result = self.execute_test(payload)
            self.run_on_ui(self._handle_test_success, result)
        except Exception as exc:
            self.run_on_ui(self._handle_test_error, str(exc), payload["server_ip"])
        finally:
            self.set_testing_state(False)

    def execute_test(self, payload):
        server_ip = payload["server_ip"]
        trace_ip = payload["trace_ip"]
        bldg = payload["bldg"]
        floor = payload["floor"]
        room = payload["room"]
        note = payload["note"]
        self.set_status("Collecting Wi-Fi interface details...", "cyan")
        wlan = self.get_wlan_info()

        self.set_status("Measuring noise floor and SNR...", "cyan")
        noise_floor_dbm, snr_db, snr_quality = self.measure_noise_snr(wlan["RSSI_dBm"])

        self.set_status("Resolving default gateway...", "cyan")
        gateway = self.get_default_gateway()

        self.set_status("Pinging gateway...", "cyan")
        ping_gw_ms, ping_gw_loss = self.ping_host(gateway, PING_COUNT)

        self.set_status("Pinging iPerf server...", "cyan")
        ping_srv_ms, ping_srv_loss = self.ping_host(server_ip, PING_COUNT)

        tcp_up_data = self.run_iperf(server_ip, ["-t", str(IPERF_DURATION)], "TCP Upload")
        upload_mbps = self.parse_iperf_tcp_upload(tcp_up_data)

        tcp_down_data = self.run_iperf(server_ip, ["-t", str(IPERF_DURATION), "-R"], "TCP Download")
        download_mbps = self.parse_iperf_tcp_download(tcp_down_data)

        udp_mbps = None
        jitter_ms = None
        packet_loss_pct = None
        udp_error = None
        try:
            udp_data = self.run_iperf(
                server_ip,
                ["-u", "-b", UDP_BANDWIDTH, "-t", str(IPERF_DURATION)],
                "UDP Jitter/Loss",
            )
            udp_mbps, jitter_ms, packet_loss_pct = self.parse_iperf_udp(udp_data)
        except Exception as exc:
            udp_error = str(exc)

        self.set_status("Scanning nearby Wi-Fi for spectrum...", "cyan")
        self.scan_wifi_live()
        self.run_on_ui(self.draw_spectrum_on_canvas)

        try:
            connected_channel = int(str(wlan["Channel"]).strip())
            channel_quality = self.analyze_channel_quality(connected_channel)
        except Exception:
            channel_quality = {
                "CoChannel_AP_Count": 0,
                "Adjacent_AP_Count": 0,
                "Strongest_Neighbor_RSSI": -100,
            }

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Save outputs under the building folder:
        # Excel: Survey_Data/<Building>/<Building>.xlsx
        # Images: Survey_Data/<Building>/Spectrum_Images/<image>.png
        base_dir = os.path.join(SPECTRUM_IMAGE_ROOT, self.safe_filename(bldg))
        img_dir = os.path.join(base_dir, SPECTRUM_IMAGE_DIRNAME)
        os.makedirs(base_dir, exist_ok=True)
        os.makedirs(img_dir, exist_ok=True)

        preferred_file_name = os.path.join(base_dir, f"{self.safe_filename(bldg)}.xlsx")
        output_file_name = self.resolve_output_file(preferred_file_name)

        image_name = f"{self.safe_filename(bldg)}_{self.safe_filename(floor)}_{self.safe_filename(room)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        image_path = os.path.join(img_dir, image_name)

        self.set_status("Saving spectrum image to local disk...", "cyan")
        self.draw_spectrum_to_file(image_path)

        ap_vendor = self.lookup_ap_vendor(wlan["BSSID"])

        rating = self.rate_result(
            wlan["RSSI_dBm"],
            upload_mbps,
            download_mbps,
            #packet_loss_pct,
            None,
            ping_srv_ms,
        )

        new_data = {
            "Timestamp": [timestamp],
            "Building": [bldg],
            "Floor": [floor],
            "Room_Point": [room],
            "Note": [note],
            "SSID": [wlan["SSID"]],
            "BSSID": [wlan["BSSID"]],
            "Band": [wlan["Band"]],
            "Radio_Type": [wlan["Radio_Type"]],
            "Channel": [wlan["Channel"]],
            "Signal_%": [wlan["Signal_%"]],
            "RSSI_dBm": [wlan["RSSI_dBm"]],
            "Receive_Rate_Mbps": [wlan["Receive_Rate_Mbps"]],
            "Transmit_Rate_Mbps": [wlan["Transmit_Rate_Mbps"]],
            "Gateway_IP": [gateway],
            "Ping_Gateway_ms": [ping_gw_ms],
            "Ping_Gateway_Loss_%": [ping_gw_loss],
            "Server_IP": [server_ip],
            "Trace_Target": [trace_ip],
            "Ping_Server_ms": [ping_srv_ms],
            "Ping_Server_Loss_%": [ping_srv_loss],
            "TCP_Upload_Mbps": [upload_mbps],
            "TCP_Download_Mbps": [download_mbps],
            "UDP_Target_Bandwidth": [UDP_BANDWIDTH],
            "UDP_Actual_Mbps": [udp_mbps],
            "UDP_Jitter_ms": [jitter_ms],
            "UDP_PacketLoss_%": [packet_loss_pct],
            "CoChannel_AP_Count": [channel_quality["CoChannel_AP_Count"]],
            "Adjacent_AP_Count": [channel_quality["Adjacent_AP_Count"]],
            "Strongest_Neighbor_RSSI": [channel_quality["Strongest_Neighbor_RSSI"]],
            "Noise_Floor_dBm": [noise_floor_dbm],
            "SNR_dB": [snr_db],
            "SNR_Quality": [snr_quality],
            "Spectrum_Image": [image_name],
            "Spectrum_Image_Path": [image_path],
            "Rating": [rating],
            "AP_Vendor": [ap_vendor],
        }
        df = pd.DataFrame(new_data)

        self.set_status(f"Saving {DEFAULT_SHEET_NAME} to Excel...", "cyan")
        self.save_to_excel(output_file_name, DEFAULT_SHEET_NAME, df)

        self.set_status("Saving to Supabase Database...", "cyan")
        db_success, db_msg = self.save_to_supabase(df, None)
        db_status_text = db_msg if not db_success else "✅ Saved to Supabase"

        return {
            "timestamp": timestamp,
            "room": room,
            "note": note,
            "wlan": wlan,
            "gateway": gateway,
            "ping_gw_ms": ping_gw_ms,
            "ping_gw_loss": ping_gw_loss,
            "server_ip": server_ip,
            "trace_ip": trace_ip,
            "ping_srv_ms": ping_srv_ms,
            "ping_srv_loss": ping_srv_loss,
            "upload_mbps": upload_mbps,
            "download_mbps": download_mbps,
            "udp_mbps": udp_mbps,
            "jitter_ms": jitter_ms,
            "packet_loss_pct": packet_loss_pct,
            "udp_error": udp_error,
            "noise_floor_dbm": noise_floor_dbm,
            "snr_db": snr_db,
            "snr_quality": snr_quality,
            "rating": rating,
            "ap_vendor": ap_vendor,
            "file_name": output_file_name,
            "db_status": db_status_text,
            "image_name": image_name,
            "image_path": image_path,
            "channel_quality": channel_quality,
        }

    def _handle_test_success(self, result):
        wlan = result["wlan"]
        udp_error = result.get("udp_error")
        udp_actual_display = result["udp_mbps"] if result["udp_mbps"] is not None else "N/A"
        udp_jitter_display = result["jitter_ms"] if result["jitter_ms"] is not None else "N/A"
        udp_loss_display = (
            f"{result['packet_loss_pct']}%" if result["packet_loss_pct"] is not None else "N/A"
        )
        cq = result.get("channel_quality", {})

        result_text = (
            f"{'=' * 58}\n"
            f"  Saved file      : {result['file_name']}\n"
            f"  Timestamp       : {result['timestamp']}\n"
            f"{'=' * 58}\n"
            f"  Room / Point    : {result['room']}\n"
            f"  Note            : {result['note'] if result['note'] else '-'}\n"
            f"{'-' * 58}\n"
            f"  SSID            : {wlan['SSID']}\n"
            f"  BSSID           : {wlan['BSSID']}\n"
            f"  AP Vendor       : {result.get('ap_vendor', 'Unknown')}\n"
            f"  Band            : {wlan['Band']}\n"
            f"  Radio Type      : {wlan['Radio_Type']}\n"
            f"  Channel         : {wlan['Channel']}\n"
            f"  Signal          : {wlan['Signal_%']}%\n"
            f"  RSSI            : {wlan['RSSI_dBm']} dBm\n"
            f"  RX / TX Rate    : {wlan['Receive_Rate_Mbps']} / {wlan['Transmit_Rate_Mbps']} Mbps\n"
            f"{'-' * 58}\n"
            f"  Gateway         : {result['gateway']}\n"
            f"  Ping Gateway    : {result['ping_gw_ms']} ms | Loss {result['ping_gw_loss']}%\n"
            f"  Ping Server     : {result['ping_srv_ms']} ms | Loss {result['ping_srv_loss']}%\n"
            f"{'-' * 58}\n"
            f"  TCP Upload      : {result['upload_mbps']} Mbps\n"
            f"  TCP Download    : {result['download_mbps']} Mbps\n"
            f"  UDP Actual      : {udp_actual_display}\n"
            f"  UDP Jitter      : {udp_jitter_display}\n"
            f"  UDP Loss        : {udp_loss_display}\n"
            f"{'-' * 58}\n"
            f"  Noise Floor     : {result.get('noise_floor_dbm', 'N/A')} dBm\n"
            f"  SNR             : {result.get('snr_db', 'N/A')} dB ({result.get('snr_quality', 'N/A')})\n"
            f"{'-' * 58}\n"
            f"  Co-Channel APs  : {cq.get('CoChannel_AP_Count', 0)}\n"
            f"  Adjacent APs    : {cq.get('Adjacent_AP_Count', 0)}\n"
            f"  Strongest AP    : {cq.get('Strongest_Neighbor_RSSI', -100)} dBm\n"
            f"  Spectrum Image  : {result.get('image_path', '-')}\n"
            f"{'-' * 58}\n"
            f"  Rating          : {result['rating']}\n"
            f"  Database        : {result.get('db_status', 'Unknown')}\n"
            f"{'=' * 58}\n"
        )

        if udp_error:
            result_text += f"\nUDP Warning:\n{udp_error}\n"

        self.set_result_text(result_text)
        # Keep Building / Floor / Room / Note after a test so the same survey point
        # can be reused for WinMTR import without typing it again.

        if result["file_name"].endswith(".xlsx") and "_autosave_" in result["file_name"]:
            self.set_status("Test finished. Original workbook was busy, so data was saved to an autosave file.", "yellow")
        else:
            self.set_status("Test finished and data saved successfully.", "green")

    def _handle_test_error(self, error_text, server_ip):
        self.set_status("Test failed.", "red")
        message = (
            "ERROR\n\n"
            f"{error_text}\n\n"
            "Please check:\n"
            f"- Server {server_ip} is reachable\n"
            "- iperf3.exe exists in the same folder as Wifi.py\n"
            "- Wi-Fi is connected\n"
            "- Firewall is not blocking iPerf\n"
            "- The output Excel file is not locked by another program\n"
        )
        self.set_result_text(message)


if __name__ == "__main__":
    app = WifiSurveyApp()
    app.mainloop()