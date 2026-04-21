import concurrent.futures
import json
import os
import re
import subprocess
import threading
from datetime import datetime

import customtkinter as ctk
import pandas as pd
import psycopg2


# =========================
# CONFIG
# =========================
SERVER_IP = "10.8.1.93"
IPERF_PORT = 5202
IPERF_DURATION = 10
UDP_BANDWIDTH = "20M"
PING_COUNT = 4
MAX_HOPS = 15
TRACERT_TIMEOUT = 500
APP_TITLE = "Wi-Fi Survey Excel Pro v6"
DEFAULT_SHEET_NAME = "Raw_Data"

# DB CONFIG
DB_HOST = "127.0.0.1"
DB_PORT = 5432
DB_NAME = "wifisurvey"
DB_USER = "wifi_admin"
DB_PASS = "V7!mQ2#pL9@xR4$kN8zT6c"


class WifiSurveyApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title(APP_TITLE)
        self.geometry("640x950")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.iperf_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "iperf3.exe")
        self._test_running = False

        self._build_ui()

    # =========================
    # UI
    # =========================
    def _build_ui(self):
        ctk.CTkLabel(self, text="Wi-Fi Survey Pro", font=("Arial", 24, "bold")).pack(pady=(20, 2))
        ctk.CTkLabel(
            self,
            text=f"iPerf: {IPERF_DURATION}s | UDP: {UDP_BANDWIDTH} | Port: {IPERF_PORT}",
            font=("Arial", 11),
            text_color="gray",
        ).pack(pady=(0, 10))

        net_frame = ctk.CTkFrame(self)
        net_frame.pack(padx=20, pady=5, fill="x")

        ctk.CTkLabel(net_frame, text="Network Settings", font=("Arial", 13, "bold")).pack(pady=(10, 0))

        ip_inner = ctk.CTkFrame(net_frame, fg_color="transparent")
        ip_inner.pack(pady=5, fill="x", padx=10)

        ctk.CTkLabel(ip_inner, text="iPerf Server:").grid(row=0, column=0, padx=(5, 2), pady=5, sticky="e")
        self.entry_server_ip = ctk.CTkEntry(ip_inner, width=150)
        self.entry_server_ip.grid(row=0, column=1, padx=2, pady=5)

        ctk.CTkLabel(ip_inner, text="Traceroute Target:").grid(row=0, column=2, padx=(15, 2), pady=5, sticky="e")
        self.entry_trace_ip = ctk.CTkEntry(ip_inner, width=150)
        self.entry_trace_ip.grid(row=0, column=3, padx=2, pady=5)

        ctk.CTkLabel(ip_inner, text="Diag Mode:").grid(row=1, column=0, padx=(5, 2), pady=5, sticky="e")
        self.combo_diag_mode = ctk.CTkComboBox(
            ip_inner,
            values=["Quick (IP, 5 Pings)", "Detailed (Host, 10 Pings)"],
            width=150,
        )
        self.combo_diag_mode.set("Quick (IP, 5 Pings)")
        self.combo_diag_mode.grid(row=1, column=1, padx=2, pady=5)

        input_frame = ctk.CTkFrame(self)
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

        btn_frame = ctk.CTkFrame(self)
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

        self.status_label = ctk.CTkLabel(self, text="Ready", text_color="gray", font=("Arial", 12))
        self.status_label.pack(pady=2)

        self.result_box = ctk.CTkTextbox(self, width=560, height=450, font=("Courier New", 12))
        self.result_box.pack(pady=10, padx=20)

        ctk.CTkLabel(
            self,
            text="One building = one workbook. Raw data and traceroute are saved in separate sheets.",
            font=("Arial", 10),
            text_color="gray",
        ).pack(pady=(0, 12))

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
    # TRACEROUTE
    # =========================
    def run_traceroute(self, host, max_hops=10, timeout_ms=500, resolve_hostname=False):
        hops = []

        try:
            cmd = ["tracert", "-h", str(max_hops), "-w", str(timeout_ms)]
            if not resolve_hostname:
                cmd.append("-d")
            cmd.append(host)

            result = self.run_command(cmd, timeout=max(20, max_hops * 6))

            for raw_line in result.stdout.splitlines():
                line = raw_line.strip()
                hop_match = re.match(r"^(\d+)\s+(.*)$", line)
                if not hop_match:
                    continue

                hop_num = hop_match.group(1)
                rest = hop_match.group(2)

                ip = "Unknown"
                hostname = ""

                ip_bracket = re.search(r"([^\s]+)\s+\[(\d{1,3}(?:\.\d{1,3}){3})\]", rest)
                if ip_bracket:
                    hostname = ip_bracket.group(1)
                    ip = ip_bracket.group(2)
                else:
                    ip_match = re.search(r"(\d{1,3}(?:\.\d{1,3}){3})", rest)
                    if ip_match:
                        ip = ip_match.group(1)
                    elif rest.count("*") >= 3:
                        ip = "Timeout"

                times = re.findall(r"((?:<\s*1|\d+)\s*ms|\*)", rest, re.IGNORECASE)
                t1 = times[0] if len(times) > 0 else "*"
                t2 = times[1] if len(times) > 1 else "*"
                t3 = times[2] if len(times) > 2 else "*"

                hops.append(
                    {
                        "Hop": hop_num,
                        "RTT1": t1.replace(" ", ""),
                        "RTT2": t2.replace(" ", ""),
                        "RTT3": t3.replace(" ", ""),
                        "IP": ip,
                        "Hostname": hostname,
                    }
                )
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

        try:
            udp_mbps = round(data["end"]["sum"]["bits_per_second"] / 1e6, 2)
        except Exception:
            pass

        try:
            jitter = round(data["end"]["sum"]["jitter_ms"], 2)
        except Exception:
            pass

        try:
            loss = round(data["end"]["sum"]["lost_percent"], 2)
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
                and loss is not None
                and loss < 1
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
    # DATABASE
    # =========================
    def save_to_postgres(self, df_survey, df_trace):
        try:
            conn = psycopg2.connect(
                host=DB_HOST,
                port=DB_PORT,
                dbname=DB_NAME,
                user=DB_USER,
                password=DB_PASS
            )
            conn.autocommit = True
            cursor = conn.cursor()

            # Create tables if not exist
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS survey_results (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP,
                    building VARCHAR(255),
                    floor VARCHAR(50),
                    room_point VARCHAR(255),
                    note TEXT,
                    ssid VARCHAR(255),
                    bssid VARCHAR(50),
                    band VARCHAR(50),
                    radio_type VARCHAR(50),
                    channel VARCHAR(50),
                    signal_percent INT,
                    rssi_dbm REAL,
                    rx_rate_mbps REAL,
                    tx_rate_mbps REAL,
                    gateway_ip VARCHAR(50),
                    ping_gateway_ms REAL,
                    ping_gateway_loss_percent REAL,
                    server_ip VARCHAR(50),
                    trace_target VARCHAR(50),
                    ping_server_ms REAL,
                    ping_server_loss_percent REAL,
                    tcp_upload_mbps REAL,
                    tcp_download_mbps REAL,
                    udp_target_bandwidth VARCHAR(50),
                    udp_actual_mbps REAL,
                    udp_jitter_ms REAL,
                    udp_packetloss_percent REAL,
                    rating VARCHAR(50)
                );
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trace_hops (
                    id SERIAL PRIMARY KEY,
                    survey_id INT,
                    hop INT,
                    hostname VARCHAR(255),
                    ip VARCHAR(50),
                    loss_percent REAL,
                    rtt1 VARCHAR(50),
                    rtt2 VARCHAR(50),
                    rtt3 VARCHAR(50),
                    min_ms REAL,
                    max_ms REAL,
                    avg_ms REAL
                );
            ''')

            # Insert survey data
            for index, row in df_survey.iterrows():
                cursor.execute('''
                    INSERT INTO survey_results (
                        timestamp, building, floor, room_point, note, ssid, bssid, band, radio_type, channel,
                        signal_percent, rssi_dbm, rx_rate_mbps, tx_rate_mbps, gateway_ip, ping_gateway_ms,
                        ping_gateway_loss_percent, server_ip, trace_target, ping_server_ms, ping_server_loss_percent,
                        tcp_upload_mbps, tcp_download_mbps, udp_target_bandwidth, udp_actual_mbps, udp_jitter_ms,
                        udp_packetloss_percent, rating
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s,
                        %s, %s
                    ) RETURNING id;
                ''', (
                    row.get('Timestamp'), row.get('Building'), row.get('Floor'), row.get('Room_Point'), row.get('Note'),
                    row.get('SSID'), row.get('BSSID'), row.get('Band'), row.get('Radio_Type'), row.get('Channel'),
                    row.get('Signal_%'), row.get('RSSI_dBm'), row.get('Receive_Rate_Mbps'), row.get('Transmit_Rate_Mbps'),
                    row.get('Gateway_IP'), row.get('Ping_Gateway_ms'), row.get('Ping_Gateway_Loss_%'),
                    row.get('Server_IP'), row.get('Trace_Target'), row.get('Ping_Server_ms'), row.get('Ping_Server_Loss_%'),
                    row.get('TCP_Upload_Mbps'), row.get('TCP_Download_Mbps'), row.get('UDP_Target_Bandwidth'),
                    row.get('UDP_Actual_Mbps'), row.get('UDP_Jitter_ms'), row.get('UDP_PacketLoss_%'), row.get('Rating')
                ))
                survey_id = cursor.fetchone()[0]

                # Insert trace data for this survey
                if df_trace is not None and not df_trace.empty:
                    for t_idx, t_row in df_trace.iterrows():
                        cursor.execute('''
                            INSERT INTO trace_hops (
                                survey_id, hop, hostname, ip, loss_percent,
                                rtt1, rtt2, rtt3, min_ms, max_ms, avg_ms
                            ) VALUES (
                                %s, %s, %s, %s, %s,
                                %s, %s, %s, %s, %s, %s
                            );
                        ''', (
                            survey_id, t_row.get('Hop'), t_row.get('Hostname'), t_row.get('IP'), t_row.get('Loss_%'),
                            str(t_row.get('RTT1')), str(t_row.get('RTT2')), str(t_row.get('RTT3')), 
                            t_row.get('Min_ms'), t_row.get('Max_ms'), t_row.get('Avg_ms')
                        ))
            
            cursor.close()
            conn.close()
            return True, "Saved to PostgreSQL successfully."
        except Exception as e:
            return False, f"PostgreSQL Error: {e}"

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

        rating = self.rate_result(
            wlan["RSSI_dBm"],
            upload_mbps,
            download_mbps,
            packet_loss_pct,
            ping_srv_ms,
        )

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        preferred_file_name = f"{self.safe_filename(bldg)}.xlsx"
        output_file_name = self.resolve_output_file(preferred_file_name)

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
            "Rating": [rating],
        }
        df = pd.DataFrame(new_data)

        self.set_status(f"Saving {DEFAULT_SHEET_NAME} to Excel...", "cyan")
        self.save_to_excel(output_file_name, DEFAULT_SHEET_NAME, df)

        df_trace = None
        if tracert_hops:
            tracert_data = []
            for hop in tracert_hops:
                tracert_data.append(
                    {
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
                    }
                )
            df_trace = pd.DataFrame(tracert_data)
            self.set_status("Saving TraceRoute to Excel...", "cyan")
            self.save_to_excel(output_file_name, "TraceRoute", df_trace)

        self.set_status("Saving to PostgreSQL Database...", "cyan")
        db_success, db_msg = self.save_to_postgres(df, df_trace)
        db_status_text = db_msg if not db_success else "Saved to DB"

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
            "rating": rating,
            "tracert_hops": tracert_hops,
            "file_name": output_file_name,
            "db_status": db_status_text,
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
        udp_error = result.get("udp_error")
        udp_actual_display = result["udp_mbps"] if result["udp_mbps"] is not None else "N/A"
        udp_jitter_display = result["jitter_ms"] if result["jitter_ms"] is not None else "N/A"
        udp_loss_display = (
            f"{result['packet_loss_pct']}%" if result["packet_loss_pct"] is not None else "N/A"
        )
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
            f"{trace_str}"
            f"  Rating          : {result['rating']}\n"
            f"  Database        : {result.get('db_status', 'Unknown')}\n"
            f"{'=' * 58}\n"
        )

        if udp_error:
            result_text += f"\nUDP Warning:\n{udp_error}\n"

        self.set_result_text(result_text)
        self.entry_room.delete(0, "end")
        self.entry_note.delete(0, "end")

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
