"""
ui/app.py
Main WifiSurveyApp window — delegates all network/storage work to modules.
"""
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

class WifiSurveyApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title(APP_TITLE)
        self.geometry("1600x900")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.iperf_path = os.path.join(base_dir, "bin", "iperf3", "iperf3.exe")
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

    def draw_spectrum_on_canvas(self):
        if not hasattr(self, "ax") or not hasattr(self, "canvas"):
            return

        render_spectrum(self.ax, self.wifi_cache, self.ssid_colors)
        self.canvas.draw_idle()

    def update_spectrum_preview(self):
        if self._test_running:
            self.after(3000, self.update_spectrum_preview)
            return

        try:
            scan_wifi_live(self.wifi_cache)
            self.draw_spectrum_on_canvas()
        except Exception:
            pass

        self.after(SPECTRUM_REFRESH_MS, self.update_spectrum_preview)

    # =========================
    # IPERF
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
            hops = parse_winmtr_txt(file_path)

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

            base_dir = os.path.join(SPECTRUM_IMAGE_ROOT, safe_filename(bldg))
            os.makedirs(base_dir, exist_ok=True)

            preferred_file_name = os.path.join(base_dir, f"{safe_filename(bldg)}.xlsx")
            output_file_name = resolve_output_file(preferred_file_name)

            self.set_status("Saving WinMTR to Excel...", "cyan")
            save_to_excel(output_file_name, "WinMTR", df_winmtr)

            self.set_status("Saving WinMTR to traceroute_hops...", "cyan")
            db_success, db_msg = save_winmtr_to_supabase(df_winmtr)

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
        wlan = get_wlan_info()

        self.set_status("Measuring noise floor and SNR...", "cyan")
        noise_floor_dbm, snr_db, snr_quality = measure_noise_snr(wlan["RSSI_dBm"])

        self.set_status("Resolving default gateway...", "cyan")
        gateway = get_default_gateway()

        self.set_status("Pinging gateway...", "cyan")
        ping_gw_ms, ping_gw_loss = ping_host(gateway, PING_COUNT)

        self.set_status("Pinging iPerf server...", "cyan")
        ping_srv_ms, ping_srv_loss = ping_host(server_ip, PING_COUNT)

        tcp_up_data = run_iperf(self.iperf_path, server_ip, ["-t", str(IPERF_DURATION)], "TCP Upload")
        upload_mbps = parse_iperf_tcp_upload(tcp_up_data)

        tcp_down_data = run_iperf(self.iperf_path, server_ip, ["-t", str(IPERF_DURATION), "-R"], "TCP Download")
        download_mbps = parse_iperf_tcp_download(tcp_down_data)

        udp_mbps = None
        jitter_ms = None
        packet_loss_pct = None
        udp_error = None
        try:
            udp_data = run_iperf(self.iperf_path, 
                server_ip,
                ["-u", "-b", UDP_BANDWIDTH, "-t", str(IPERF_DURATION)],
                "UDP Jitter/Loss",
            )
            udp_mbps, jitter_ms, packet_loss_pct = parse_iperf_udp(udp_data)
        except Exception as exc:
            udp_error = str(exc)

        self.set_status("Scanning nearby Wi-Fi for spectrum...", "cyan")
        scan_wifi_live(self.wifi_cache)
        self.run_on_ui(self.draw_spectrum_on_canvas)

        try:
            connected_channel = int(str(wlan["Channel"]).strip())
            channel_quality = analyze_channel_quality(self.wifi_cache, connected_channel)
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
        base_dir = os.path.join(SPECTRUM_IMAGE_ROOT, safe_filename(bldg))
        img_dir = os.path.join(base_dir, SPECTRUM_IMAGE_DIRNAME)
        os.makedirs(base_dir, exist_ok=True)
        os.makedirs(img_dir, exist_ok=True)

        preferred_file_name = os.path.join(base_dir, f"{safe_filename(bldg)}.xlsx")
        output_file_name = resolve_output_file(preferred_file_name)

        image_name = f"{safe_filename(bldg)}_{safe_filename(floor)}_{safe_filename(room)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        image_path = os.path.join(img_dir, image_name)

        self.set_status("Saving spectrum image to local disk...", "cyan")
        draw_spectrum_to_file(image_path, self.wifi_cache, self.ssid_colors)

        ap_vendor = lookup_ap_vendor(wlan["BSSID"])

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
        save_to_excel(output_file_name, DEFAULT_SHEET_NAME, df)

        self.set_status("Saving to Supabase Database...", "cyan")
        db_success, db_msg = save_to_supabase(df)
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
            "- iperf3.exe exists in bin/iperf3\n"
            "- Wi-Fi is connected\n"
            "- Firewall is not blocking iPerf\n"
            "- The output Excel file is not locked by another program\n"
        )
        self.set_result_text(message)

