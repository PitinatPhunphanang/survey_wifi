import concurrent.futures
import json
import os
import re
import subprocess
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
    for _ in range(5):
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
# UDP_BANDWIDTH = "20M"   # ปิด UDP เหมือน Windows version
PING_COUNT = 4
MAX_HOPS = 15
TRACERT_TIMEOUT = 500
APP_TITLE = "Wi-Fi Survey Excel Pro v6 (Linux)"
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
        self._test_running = False
        self.iperf_path = "iperf3"  # Linux: ใช้ system iperf3

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
        ctk.CTkLabel(left_panel, text="Wi-Fi Survey Pro (Linux)", font=("Arial", 24, "bold")).pack(pady=(20, 2))
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

        ctk.CTkLabel(ip_inner, text="Traceroute Target:").grid(row=0, column=2, padx=(0, 2), pady=5, sticky="e")
        self.entry_trace_ip = ctk.CTkEntry(ip_inner, width=100)
        self.entry_trace_ip.insert(0, SERVER_IP)
        self.entry_trace_ip.grid(row=0, column=3, padx=2, pady=5)

        ctk.CTkLabel(ip_inner, text="Diag Mode:").grid(row=1, column=0, padx=(5, 2), pady=5, sticky="e")
        self.combo_diag_mode = ctk.CTkComboBox(
            ip_inner,
            values=["Quick Network Trace (IP, 5 Pings)", "Detailed Network Trace (Host, 10 Pings)"],
            width=150,
        )
        self.combo_diag_mode.set("Quick Network Trace (IP, 5 Pings)")
        self.combo_diag_mode.grid(row=1, column=1, padx=2, pady=5)

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

        self.status_label = ctk.CTkLabel(left_panel, text="Ready", text_color="gray", font=("Arial", 12))
        self.status_label.pack(pady=2)

        self.result_box = ctk.CTkTextbox(left_panel, width=560, height=300, font=("Courier New", 12))
        self.result_box.pack(pady=10, padx=20, fill="both", expand=True)

        ctk.CTkLabel(
            left_panel,
            text="One building = one workbook. Raw data and traceroute are saved in separate sheets.",
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
        # Linux ไม่ต้องการ creationflags
        return 0

    def run_command(self, args, timeout=20):
        return subprocess.run(
            args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=timeout,
        )

    # =========================
    # WLAN INFO (Linux)
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
            # ดึงข้อมูล Wi-Fi ที่เชื่อมต่ออยู่ด้วย nmcli
            res = self.run_command(
                ["nmcli", "-t", "-f", "ACTIVE,SSID,BSSID,CHAN,RATE,SIGNAL", "device", "wifi"],
                timeout=8,
            )
            for line in res.stdout.splitlines():
                if line.startswith("yes"):
                    # BSSID มี ':' ใน nmcli -t จะถูก escape เป็น '\:'
                    p = line.replace("\\:", "++").split(":")
                    if len(p) >= 6:
                        info["SSID"] = p[1] if p[1] else "Hidden"
                        info["BSSID"] = p[2].replace("++", ":").lower()
                        info["Channel"] = p[3]
                        rate_match = re.search(r"\d+", p[4])
                        if rate_match:
                            info["Receive_Rate_Mbps"] = float(rate_match.group())
                            info["Transmit_Rate_Mbps"] = info["Receive_Rate_Mbps"]
                        try:
                            sig_val = int(p[5].strip())
                            info["Signal_%"] = sig_val
                        except Exception:
                            pass
                        try:
                            info["Band"] = "5 GHz" if int(p[3]) > 14 else "2.4 GHz"
                        except Exception:
                            pass
                    break

            # คำนวณ RSSI จาก Signal %
            if info["RSSI_dBm"] is None and info["Signal_%"] is not None:
                info["RSSI_dBm"] = round((info["Signal_%"] / 2) - 100, 1)

        except Exception as e:
            print(f"Error in get_wlan_info: {e}")

        return info

    def normalize_key(self, value):
        return re.sub(r"[^a-z0-9()%]", "", str(value).strip().lower())

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
    # NOISE / SNR MEASUREMENT (Linux)
    # =========================
    def measure_noise_snr(self, rssi_dbm):
        """
        วัด Noise Floor และ SNR บน Linux โดยใช้ iw dev <iface> survey dump เท่านั้น
        ซึ่งเป็นค่าที่วัดได้จริงจาก hardware radio survey

        หมายเหตุ: ต้องการสิทธิ์ CAP_NET_ADMIN (หรือ sudo) และไดรเวอร์ต้องรองรับ
        ถ้าวัดไม่ได้ → คืน None ทั้งหมด ไม่ประมาณหรือคำนวณจากค่าอื่น
        """
        noise_floor = None
        snr_db = None
        snr_quality = None

        # หา wireless interface ที่ใช้งานอยู่
        iface = self._get_active_wifi_iface()
        if not iface:
            return None, None, None

        # ─── iw dev survey dump ────────────────────────────────────────────────
        try:
            result = self.run_command(["iw", "dev", iface, "survey", "dump"], timeout=10)
            if result.returncode == 0 and result.stdout:
                in_use_block = False
                for raw_line in result.stdout.splitlines():
                    line = raw_line.strip().lower()
                    if "in use" in line:
                        in_use_block = True
                    if in_use_block and "noise" in line and ":" in line:
                        _, val = line.split(":", 1)
                        val = val.strip().replace("dbm", "").strip()
                        parsed = self.parse_float(val)
                        if parsed is not None and parsed < 0:
                            noise_floor = round(parsed, 1)
                        break  # พบ noise line แล้ว หยุดได้เลยไม่ว่าจะได้ค่าหรือไม่
        except Exception:
            pass

        # ─── คำนวณ SNR (เฉพาะเมื่อวัด noise ได้จริงจาก iw survey เท่านั้น) ──
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

        return noise_floor, snr_db, snr_quality

    def _get_active_wifi_iface(self):
        """หา wireless interface ที่กำลังเชื่อมต่ออยู่"""
        try:
            # วิธี 1: nmcli
            result = self.run_command(
                ["nmcli", "-t", "-f", "DEVICE,TYPE,STATE", "device"],
                timeout=5,
            )
            for line in result.stdout.splitlines():
                parts = line.split(":")
                if len(parts) >= 3 and "wifi" in parts[1].lower() and "connected" in parts[2].lower():
                    return parts[0]
        except Exception:
            pass

        try:
            # วิธี 2: iw dev
            result = self.run_command(["iw", "dev"], timeout=5)
            ifaces = re.findall(r"Interface\s+(\S+)", result.stdout)
            if ifaces:
                return ifaces[0]
        except Exception:
            pass

        try:
            # วิธี 3: หาจาก /sys/class/net
            for iface in os.listdir("/sys/class/net"):
                wireless_path = f"/sys/class/net/{iface}/wireless"
                if os.path.isdir(wireless_path):
                    return iface
        except Exception:
            pass

        return None

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
        if not bssid or bssid in ("Unknown", "unknown"):
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

    # =========================
    # ROUTING / PING (Linux)
    # =========================
    def get_default_gateway(self):
        try:
            result = self.run_command(["ip", "route", "show", "default"], timeout=5)
            match = re.search(r"default via ([\d.]+)", result.stdout)
            return match.group(1) if match else "Unknown"
        except Exception:
            return "Unknown"

    def ping_host(self, host, count=4):
        stats = self.ping_for_stats(host, count=count)
        return stats["Avg"], stats["Loss_%"]

    def ping_for_stats(self, host, count=10):
        if not host or host in ("Unknown", "Timeout", "Unreachable"):
            return {"Min": None, "Max": None, "Avg": None, "Loss_%": 100}
        try:
            res = self.run_command(["ping", "-c", str(count), host], timeout=max(15, count * 2))
            stats = re.search(r"rtt min/avg/max/mdev = ([\d.]+)/([\d.]+)/([\d.]+)", res.stdout)
            loss = re.search(r"(\d+)% packet loss", res.stdout)
            if stats:
                return {
                    "Min": float(stats.group(1)),
                    "Avg": float(stats.group(2)),
                    "Max": float(stats.group(3)),
                    "Loss_%": int(loss.group(1)) if loss else 100,
                }
        except Exception:
            pass
        return {"Min": None, "Max": None, "Avg": None, "Loss_%": 100}

    # =========================
    # TRACEROUTE (Linux)
    # =========================
    def run_traceroute(self, host, max_hops=10, timeout_ms=500, resolve_hostname=False):
        hops = []
        try:
            cmd = ["traceroute", "-m", str(max_hops), "-w", "1"]
            if not resolve_hostname:
                cmd.append("-n")
            cmd.append(host)

            result = self.run_command(cmd, timeout=max(30, max_hops * 4))

            for line in result.stdout.splitlines():
                hop_match = re.match(r"^\s*(\d+)\s+(.*)", line)
                if not hop_match:
                    continue

                hop_num = hop_match.group(1)
                rest = hop_match.group(2)

                ip = "Unknown"
                hostname = ""

                # หา IP/hostname
                ip_match = re.search(r"(\d{1,3}(?:\.\d{1,3}){3})", rest)
                host_bracket = re.search(r"([^\s(]+)\s+\((\d{1,3}(?:\.\d{1,3}){3})\)", rest)
                if host_bracket:
                    hostname = host_bracket.group(1)
                    ip = host_bracket.group(2)
                elif ip_match:
                    ip = ip_match.group(1)
                elif rest.count("*") >= 3:
                    ip = "Timeout"

                # หา RTT times
                times = re.findall(r"([\d.]+)\s*ms|\*", rest)
                t1 = times[0] if len(times) > 0 else "*"
                t2 = times[1] if len(times) > 1 else "*"
                t3 = times[2] if len(times) > 2 else "*"

                def fmt_t(t):
                    return f"{t}ms" if t != "*" else "*"

                hops.append({
                    "Hop": hop_num,
                    "RTT1": fmt_t(t1),
                    "RTT2": fmt_t(t2),
                    "RTT3": fmt_t(t3),
                    "IP": ip,
                    "Hostname": hostname,
                })

        except Exception:
            pass
        return hops

    def run_pingplotter_style(self, host, max_hops=10, timeout_ms=500, ping_count=10, resolve_hostname=False):
        hops = self.run_traceroute(
            host,
            max_hops=max_hops,
            timeout_ms=timeout_ms,
            resolve_hostname=resolve_hostname,
        )

        if not hops:
            return hops

        worker_count = min(max(1, len(hops)), 6)
        with concurrent.futures.ThreadPoolExecutor(max_workers=worker_count) as executor:
            future_to_hop = {}
            for hop in hops:
                ip = hop["IP"]
                if ip not in ("Unknown", "Timeout", "Unreachable"):
                    future = executor.submit(self.ping_for_stats, ip, ping_count)
                    future_to_hop[future] = hop
                else:
                    hop["Min"] = None
                    hop["Max"] = None
                    hop["Avg"] = None
                    hop["Loss_%"] = None

            for future in concurrent.futures.as_completed(future_to_hop):
                hop = future_to_hop[future]
                try:
                    stats = future.result()
                except Exception:
                    stats = {"Min": None, "Max": None, "Avg": None, "Loss_%": None}
                hop["Min"] = stats["Min"]
                hop["Max"] = stats["Max"]
                hop["Avg"] = stats["Avg"]
                hop["Loss_%"] = stats["Loss_%"]

        return hops

    # =========================
    # SPECTRUM / WIFI SCAN (Linux)
    # =========================
    def scan_wifi_live(self):
        now = time.time()
        try:
            subprocess.run(["nmcli", "device", "wifi", "rescan"], stderr=subprocess.DEVNULL, timeout=5)
            time.sleep(1.0)

            result = subprocess.run(
                ["nmcli", "-t", "-f", "SSID,BSSID,CHAN,SIGNAL,FREQ", "device", "wifi"],
                capture_output=True, text=True, encoding="utf-8", timeout=10,
            )
            out = result.stdout

            for line in out.strip().split("\n"):
                if not line:
                    continue
                try:
                    parts = line.replace("\\:", "++").split(":")
                    if len(parts) < 5:
                        continue
                    ssid = parts[0]
                    mac = parts[1].replace("++", ":").lower()
                    channel = int(parts[2])
                    signal = int(parts[3])
                    freq_str = parts[4]
                    freq_match = re.search(r"\d+", freq_str)
                    freq_val = int(freq_match.group()) if freq_match else 2400

                    rssi_dbm = (signal / 2) - 100

                    self.wifi_cache[mac] = {
                        "ssid": ssid if ssid else "Hidden",
                        "ch": channel,
                        "rssi": rssi_dbm,
                        "band": 5.0 if freq_val > 3000 else 2.4,
                        "updated": now,
                    }
                except Exception:
                    continue

            for key in list(self.wifi_cache.keys()):
                if now - self.wifi_cache[key]["updated"] > SPECTRUM_CACHE_TIMEOUT:
                    del self.wifi_cache[key]

        except Exception as e:
            print(f"Scan error: {e}")

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
                f"{label_ssid}\n{rssi:.0f}dBm",
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
                0.5, 0.5,
                "No nearby Wi-Fi data yet",
                transform=ax.transAxes,
                color="gray", fontsize=12, ha="center", va="center",
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
    # IPERF (Linux)
    # =========================
    def run_iperf(self, server_ip, args, label):
        self.set_status(f"Running {label}...", "yellow")

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
                    f"Command: {self.iperf_path} -c {server_ip} -p {IPERF_PORT} -4 {' '.join(args)} --json\n"
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
                    f"stdout preview: {preview}"
                ) from exc

            if "error" in data:
                raise RuntimeError(f"iPerf3 ({label}): {data['error']}")

            return data

        except FileNotFoundError:
            raise RuntimeError(
                f"ไม่พบคำสั่ง '{self.iperf_path}' กรุณาติดตั้งด้วย: sudo apt install iperf3"
            )
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

    # UDP ปิดใช้งาน เหมือน Windows version
    # def parse_iperf_udp(self, data): ...

    # =========================
    # RATING
    # =========================
    def rate_result(self, signal_dbm, upload, download, loss, ping_server):
        try:
            if (
                signal_dbm is not None and signal_dbm >= -67
                and upload is not None and upload >= 50
                and download is not None and download >= 50
                # and loss is not None and loss < 1
                and ping_server is not None and ping_server <= 20
            ):
                return "Good"

            if (
                signal_dbm is not None and signal_dbm >= -75
                and upload is not None and upload >= 20
                and download is not None and download >= 20
                and loss is not None and loss < 5
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
        os.makedirs(os.path.dirname(file_name), exist_ok=True)
        try:
            if not os.path.exists(file_name):
                with pd.ExcelWriter(file_name, engine="openpyxl") as writer:
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
                return

            try:
                existing_df = pd.read_excel(file_name, sheet_name=sheet_name)
                # ลบ column ที่ไม่มีใน df ปัจจุบัน
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
                f"Cannot write to '{file_name}'. Please close the file and try again."
            ) from exc

    # =========================
    # DATABASE
    # =========================
    def sanitize_db_value(self, value):
        try:
            if pd.isna(value):
                return None
        except Exception:
            pass
        return value

    def save_to_supabase(self, df_survey, df_trace):
        """Save survey and traceroute data to Supabase."""
        try:
            if not SUPABASE_URL or not SUPABASE_KEY:
                return False, "❌ Supabase credentials not configured. Check .env.local file."

            supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

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
                    # UDP ปิดใช้งาน
                    # "udp_target_bandwidth": ...,
                    # "udp_actual_mbps": ...,
                    # "udp_jitter_ms": ...,
                    # "udp_packetloss_pct": ...,
                    "noise_floor_dbm": self.sanitize_db_value(row.get("Noise_Floor_dBm")),
                    "snr_db": self.sanitize_db_value(row.get("SNR_dB")),
                    "snr_quality": self.sanitize_db_value(row.get("SNR_Quality")),
                    "rating": self.sanitize_db_value(row.get("Rating")),
                    "ap_vendor": self.sanitize_db_value(row.get("AP_Vendor")),
                }

                # ตรวจสอบก่อนว่ามีข้อมูลซ้ำไหม
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
                    self.set_status("⚠️ ข้อมูลนี้มีอยู่แล้ว ไม่บันทึกซ้ำ", "yellow")
                    return True, "⚠️ ข้อมูลนี้มีอยู่แล้ว ไม่บันทึกซ้ำ"

                response = supabase.table("surveys").insert(survey_data).execute()

                if not getattr(response, "data", None):
                    return False, f"❌ Failed to insert survey data: {response}"

                survey_id = response.data[0]["id"]

                if df_trace is not None and not df_trace.empty:
                    trace_rows = []
                    for _, t_row in df_trace.iterrows():
                        trace_floor = self.sanitize_db_value(t_row.get("Floor"))
                        trace_room = self.sanitize_db_value(t_row.get("Room_Point"))
                        hop_value = self.sanitize_db_value(t_row.get("Hop"))

                        trace_rows.append({
                            "survey_id": survey_id,
                            "survey_timestamp": self.sanitize_db_value(t_row.get("Timestamp")),
                            "building": self.sanitize_db_value(t_row.get("Building")),
                            "floor": str(trace_floor) if trace_floor is not None else None,
                            "room_point": str(trace_room) if trace_room is not None else None,
                            "hop": int(hop_value) if hop_value is not None else None,
                            "ip": self.sanitize_db_value(t_row.get("IP")),
                            "loss_pct": self.sanitize_db_value(t_row.get("Loss_%")),
                            "min_ms": self.sanitize_db_value(t_row.get("Min_ms")),
                            "max_ms": self.sanitize_db_value(t_row.get("Max_ms")),
                            "avg_ms": self.sanitize_db_value(t_row.get("Avg_ms")),
                        })

                    if trace_rows:
                        trace_response = supabase.table("traceroute_hops").insert(trace_rows).execute()
                        if getattr(trace_response, "data", None) is None:
                            return False, f"❌ Failed to insert trace data: {trace_response}"

            return True, "✅ Saved to Supabase successfully!"

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
            "trace_ip": self.entry_trace_ip.get().strip() or (self.entry_server_ip.get().strip() or SERVER_IP),
            "bldg": self.entry_bldg.get().strip(),
            "floor": self.entry_floor.get().strip(),
            "room": self.entry_room.get().strip(),
            "note": self.entry_note.get().strip(),
            "diag_mode": self.combo_diag_mode.get(),
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
        diag_mode = payload["diag_mode"]

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

        # UDP ปิดใช้งาน เหมือน Windows version
        # udp_mbps = None
        # jitter_ms = None
        # packet_loss_pct = None

        if "Detailed" in diag_mode:
            resolve_hostname = True
            ping_count = 10
        else:
            resolve_hostname = False
            ping_count = 5

        self.set_status(f"Collecting traceroute snapshot to {trace_ip}...", "cyan")
        try:
            tracert_hops = self.run_pingplotter_style(
                trace_ip,
                max_hops=MAX_HOPS,
                timeout_ms=TRACERT_TIMEOUT,
                ping_count=ping_count,
                resolve_hostname=resolve_hostname,
            )
        except Exception:
            tracert_hops = []

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

        self.set_status("Looking up AP vendor...", "cyan")
        ap_vendor = self.lookup_ap_vendor(wlan["BSSID"])

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # ── เก็บ Excel ใน Survey_Data/<Building>/<Building>.xlsx ──────────────
        base_dir = os.path.join(SPECTRUM_IMAGE_ROOT, self.safe_filename(bldg))
        img_dir = os.path.join(base_dir, SPECTRUM_IMAGE_DIRNAME)
        os.makedirs(base_dir, exist_ok=True)
        os.makedirs(img_dir, exist_ok=True)

        preferred_file_name = os.path.join(base_dir, f"{self.safe_filename(bldg)}.xlsx")
        output_file_name = self.resolve_output_file(preferred_file_name)

        # ── รูป Spectrum แยกไว้ใน Spectrum_Images/ ───────────────────────────
        image_name = (
            f"{self.safe_filename(bldg)}_{self.safe_filename(floor)}_"
            f"{self.safe_filename(room)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        )
        image_path = os.path.join(img_dir, image_name)

        self.set_status("Saving spectrum image to local disk...", "cyan")
        self.draw_spectrum_to_file(image_path)

        rating = self.rate_result(
            wlan["RSSI_dBm"],
            upload_mbps,
            download_mbps,
            None,  # UDP packet loss ปิดใช้งาน
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
            # UDP ปิดใช้งาน
            # "UDP_Target_Bandwidth": [UDP_BANDWIDTH],
            # "UDP_Actual_Mbps": [udp_mbps],
            # "UDP_Jitter_ms": [jitter_ms],
            # "UDP_PacketLoss_%": [packet_loss_pct],
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

        df_trace = None
        if tracert_hops:
            tracert_data = []
            for hop in tracert_hops:
                tracert_data.append({
                    "Timestamp": timestamp,
                    "Building": bldg,
                    "Floor": floor,
                    "Room_Point": room,
                    "Hop": hop["Hop"],
                    "Hostname": hop.get("Hostname", ""),
                    "IP": hop["IP"],
                    "Loss_%": hop.get("Loss_%"),
                    "RTT1": hop.get("RTT1", "*"),
                    "RTT2": hop.get("RTT2", "*"),
                    "RTT3": hop.get("RTT3", "*"),
                    "Min_ms": hop.get("Min"),
                    "Max_ms": hop.get("Max"),
                    "Avg_ms": hop.get("Avg"),
                })
            df_trace = pd.DataFrame(tracert_data)
            self.set_status("Saving TraceRoute to Excel...", "cyan")
            self.save_to_excel(output_file_name, "TraceRoute", df_trace)

        self.set_status("Saving to Supabase Database...", "cyan")
        db_success, db_msg = self.save_to_supabase(df, df_trace)
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
            # "udp_mbps": udp_mbps,
            # "jitter_ms": jitter_ms,
            # "packet_loss_pct": packet_loss_pct,
            # "udp_error": udp_error,
            "noise_floor_dbm": noise_floor_dbm,
            "snr_db": snr_db,
            "snr_quality": snr_quality,
            "ap_vendor": ap_vendor,
            "rating": rating,
            "tracert_hops": tracert_hops,
            "file_name": output_file_name,
            "db_status": db_status_text,
            "image_name": image_name,
            "image_path": image_path,
            "channel_quality": channel_quality,
        }

    def _handle_test_success(self, result):
        trace_str = ""
        tracert_hops = result["tracert_hops"]

        if tracert_hops:
            trace_str = "  [PingPlotter-style Snapshot]\n"
            trace_str += "   Hop | IP              | Hostname        | Loss% | Min/Max/Avg (ms)\n"
            for hop in tracert_hops:
                loss = f"{hop['Loss_%']}%" if hop.get("Loss_%") is not None else "-"
                min_ms = hop.get("Min") if hop.get("Min") is not None else "-"
                max_ms = hop.get("Max") if hop.get("Max") is not None else "-"
                avg_ms = hop.get("Avg") if hop.get("Avg") is not None else "-"
                host_disp = (hop.get("Hostname") or "")[:15]
                trace_str += (
                    f"   {hop['Hop']:<3} | {hop['IP']:<15} | {host_disp:<15} | "
                    f"{loss:<5} | {min_ms}/{max_ms}/{avg_ms}\n"
                )
            trace_str += f"{'-' * 74}\n"

        wlan = result["wlan"]
        cq = result.get("channel_quality", {})

        noise_disp = f"{result.get('noise_floor_dbm')} dBm" if result.get("noise_floor_dbm") is not None else "N/A"
        snr_disp = f"{result.get('snr_db')} dB ({result.get('snr_quality', 'N/A')})" if result.get("snr_db") is not None else "N/A"

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
            f"{'-' * 58}\n"
            f"  Noise Floor     : {noise_disp}\n"
            f"  SNR             : {snr_disp}\n"
            f"{'-' * 58}\n"
            f"  Co-Channel APs  : {cq.get('CoChannel_AP_Count', 0)}\n"
            f"  Adjacent APs    : {cq.get('Adjacent_AP_Count', 0)}\n"
            f"  Strongest AP    : {cq.get('Strongest_Neighbor_RSSI', -100)} dBm\n"
            f"  Spectrum Image  : {result.get('image_path', '-')}\n"
            f"{'-' * 58}\n"
            f"{trace_str}"
            f"  Rating          : {result['rating']}\n"
            f"  Database        : {result.get('db_status', 'Unknown')}\n"
            f"{'=' * 58}\n"
        )

        self.set_result_text(result_text)
        self.entry_room.delete(0, "end")
        self.entry_note.delete(0, "end")

        if result["file_name"].endswith(".xlsx") and "_autosave_" in result["file_name"]:
            self.set_status("Test finished. Saved to autosave file (original was busy).", "yellow")
        else:
            self.set_status("Test finished and data saved successfully.", "green")

    def _handle_test_error(self, error_text, server_ip):
        self.set_status("Test failed.", "red")
        message = (
            "ERROR\n\n"
            f"{error_text}\n\n"
            "Please check:\n"
            f"- Server {server_ip} is reachable\n"
            "- iperf3 is installed: sudo apt install iperf3\n"
            "- Wi-Fi is connected\n"
            "- Firewall is not blocking iPerf\n"
            "- traceroute is installed: sudo apt install traceroute\n"
        )
        self.set_result_text(message)


if __name__ == "__main__":
    app = WifiSurveyApp()
    app.mainloop()