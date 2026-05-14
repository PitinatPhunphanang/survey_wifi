"""
storage/supabase_db.py
Supabase database operations:
  - save_to_supabase        : insert Wi-Fi survey rows
  - save_winmtr_to_supabase : insert WinMTR traceroute hops
  - get_or_create_trace_survey_id : find-or-create a surveys row for WinMTR imports
  - parse_winmtr_txt        : parse WinMTR exported .TXT files
  - read_text_file_safely   : decode WinMTR text with common Windows encodings
  - resolve_winmtr_host_to_ip: resolve hostnames to IPv4 for WinMTR rows
"""
import ipaddress
import re
import socket
from datetime import datetime

import pandas as pd
from supabase import Client, create_client

from config import SUPABASE_URL, SUPABASE_KEY
from network.wlan import normalize_band
from utils.helpers import sanitize_db_value


# =========================
# WINMTR FILE PARSING
# =========================
def read_text_file_safely(file_path: str) -> str:
    """Read WinMTR exported TXT files with common Windows encodings."""
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


def _is_ipv4(value: str) -> bool:
    try:
        ipaddress.ip_address(str(value).strip())
        return True
    except Exception:
        return False


def resolve_winmtr_host_to_ip(host: str) -> str:
    """
    Return an IPv4 string for a WinMTR hop host field.
    Handles: plain IP, 'hostname [IP]', and hostname-only (resolved via DNS).
    """
    host_text = str(host or "").strip()
    if not host_text:
        return "Unknown"

    bracket_ip = re.search(r"\[(\d{1,3}(?:\.\d{1,3}){3})\]", host_text)
    if bracket_ip:
        return bracket_ip.group(1)

    if _is_ipv4(host_text):
        return host_text

    try:
        return socket.gethostbyname(host_text)
    except Exception:
        return host_text


def parse_winmtr_txt(file_path: str) -> list:
    """
    Parse a WinMTR exported .TXT file.

    Expected line format:
    | host - loss | sent | recv | best | avrg | wrst | last |
    """
    rows = []
    text = read_text_file_safely(file_path)
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
        ip = resolve_winmtr_host_to_ip(host)

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


# =========================
# SUPABASE — SURVEY
# =========================
def save_to_supabase(df_survey: pd.DataFrame):
    """
    Insert Wi-Fi survey rows into the 'surveys' Supabase table.
    Skips duplicates with the same (building, floor, room_point, note, band, ssid).

    Returns (success: bool, message: str)
    """
    try:
        if not SUPABASE_URL or not SUPABASE_KEY:
            return False, "❌ Supabase credentials not configured. Check .env.local file."

        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        final_messages = []

        for _, row in df_survey.iterrows():
            floor_value = sanitize_db_value(row.get("Floor"))
            room_value = sanitize_db_value(row.get("Room_Point"))
            channel_value = sanitize_db_value(row.get("Channel"))

            survey_data = {
                "survey_timestamp": sanitize_db_value(row.get("Timestamp")),
                "building": sanitize_db_value(row.get("Building")),
                "floor": str(floor_value) if floor_value is not None else None,
                "room_point": str(room_value) if room_value is not None else None,
                "note": sanitize_db_value(row.get("Note")),
                "ssid": sanitize_db_value(row.get("SSID")),
                "bssid": sanitize_db_value(row.get("BSSID")),
                "band": normalize_band(sanitize_db_value(row.get("Band"))),
                "radio_type": sanitize_db_value(row.get("Radio_Type")),
                "channel": str(channel_value) if channel_value is not None else None,
                "signal_percent": sanitize_db_value(row.get("Signal_%")),
                "rssi_dbm": sanitize_db_value(row.get("RSSI_dBm")),
                "receive_rate_mbps": sanitize_db_value(row.get("Receive_Rate_Mbps")),
                "transmit_rate_mbps": sanitize_db_value(row.get("Transmit_Rate_Mbps")),
                "gateway_ip": sanitize_db_value(row.get("Gateway_IP")),
                "ping_gateway_ms": sanitize_db_value(row.get("Ping_Gateway_ms")),
                "ping_gateway_loss_pct": sanitize_db_value(row.get("Ping_Gateway_Loss_%")),
                "server_ip": sanitize_db_value(row.get("Server_IP")),
                "trace_target": sanitize_db_value(row.get("Trace_Target")),
                "ping_server_ms": sanitize_db_value(row.get("Ping_Server_ms")),
                "ping_server_loss_pct": sanitize_db_value(row.get("Ping_Server_Loss_%")),
                "tcp_upload_mbps": sanitize_db_value(row.get("TCP_Upload_Mbps")),
                "tcp_download_mbps": sanitize_db_value(row.get("TCP_Download_Mbps")),
                "udp_target_bandwidth": sanitize_db_value(row.get("UDP_Target_Bandwidth")),
                "udp_actual_mbps": sanitize_db_value(row.get("UDP_Actual_Mbps")),
                "udp_jitter_ms": sanitize_db_value(row.get("UDP_Jitter_ms")),
                "udp_packetloss_pct": sanitize_db_value(row.get("UDP_PacketLoss_%")),
                "noise_floor_dbm": sanitize_db_value(row.get("Noise_Floor_dBm")),
                "snr_db": sanitize_db_value(row.get("SNR_dB")),
                "snr_quality": sanitize_db_value(row.get("SNR_Quality")),
                "rating": sanitize_db_value(row.get("Rating")),
                "ap_vendor": sanitize_db_value(row.get("AP_Vendor")),
            }

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
                final_messages.append("Survey already exists; survey data was not duplicated.")
            else:
                response = supabase.table("surveys").insert(survey_data).execute()
                if not getattr(response, "data", None):
                    return False, f"❌ Failed to insert survey data: {response}"
                final_messages.append("Survey saved.")

        message = "✅ Saved to Supabase successfully! " + " ".join(final_messages)
        return True, message

    except Exception as e:
        print("SUPABASE ERROR:", e)
        return False, f"❌ Supabase Error: {str(e)}"


# =========================
# SUPABASE — WINMTR
# =========================
def get_or_create_trace_survey_id(
    supabase,
    timestamp,
    building,
    floor,
    room_point,
    note,
    trace_target,
) -> int:
    """
    Find or create a surveys row for WinMTR imports and return its id.
    Each unique (building, floor, room_point, note) creates a separate record.
    """
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


def save_winmtr_to_supabase(df_winmtr: pd.DataFrame):
    """
    Insert WinMTR hop data into public.traceroute_hops.
    Deletes old matching records before inserting to prevent duplicates.

    Returns (success: bool, message: str)
    """
    try:
        if not SUPABASE_URL or not SUPABASE_KEY:
            return False, "❌ Supabase credentials not configured. Check .env.local file."

        if df_winmtr is None or df_winmtr.empty:
            return False, "❌ No WinMTR data to save."

        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

        first_row = df_winmtr.iloc[0]
        survey_id = get_or_create_trace_survey_id(
            supabase,
            sanitize_db_value(first_row.get("Timestamp")),
            sanitize_db_value(first_row.get("Building")),
            sanitize_db_value(first_row.get("Floor")),
            sanitize_db_value(first_row.get("Room_Point")),
            sanitize_db_value(first_row.get("Note")),
            sanitize_db_value(first_row.get("Trace_Target")),
        )

        building_val = sanitize_db_value(first_row.get("Building"))
        floor_val = sanitize_db_value(first_row.get("Floor"))
        room_val = sanitize_db_value(first_row.get("Room_Point"))
        trace_target_val = sanitize_db_value(first_row.get("Trace_Target"))

        rows = []
        for _, row in df_winmtr.iterrows():
            floor_value = sanitize_db_value(row.get("Floor"))
            room_value = sanitize_db_value(row.get("Room_Point"))
            ip_value = sanitize_db_value(row.get("IP"))
            ip_text = str(ip_value).strip() if ip_value is not None else "Unknown"

            rows.append(
                {
                    "source": "winmtr",
                    "survey_id": survey_id,
                    "survey_timestamp": sanitize_db_value(row.get("Timestamp")),
                    "building": sanitize_db_value(row.get("Building")),
                    "floor": str(floor_value) if floor_value is not None else None,
                    "room_point": str(room_value) if room_value is not None else None,
                    "note": sanitize_db_value(row.get("Note")),
                    "trace_target": sanitize_db_value(row.get("Trace_Target")),
                    "hop_no": int(row.get("Hop")),
                    "ip": ip_text,
                    "loss_pct": sanitize_db_value(row.get("Loss_%")),
                    "sent": sanitize_db_value(row.get("Sent")),
                    "recv": sanitize_db_value(row.get("Recv")),
                    "best_ms": sanitize_db_value(row.get("Best_ms")),
                    "avg_ms": sanitize_db_value(row.get("Avg_ms")),
                    "worst_ms": sanitize_db_value(row.get("Worst_ms")),
                    "last_ms": sanitize_db_value(row.get("Last_ms")),
                    "source_file": sanitize_db_value(row.get("Source_File")),
                    "updated_at": datetime.now().isoformat(),
                }
            )

        # Delete old records with same key fields before re-inserting
        for _, row in df_winmtr.iterrows():
            hop_no_val = int(row.get("Hop"))
            ip_val = sanitize_db_value(row.get("IP"))
            ip_text = str(ip_val).strip() if ip_val is not None else "Unknown"
            note_val = sanitize_db_value(row.get("Note"))

            supabase.table("traceroute_hops").delete()\
                .eq("building", building_val or "")\
                .eq("floor", floor_val or "")\
                .eq("room_point", room_val or "")\
                .eq("note", note_val or "")\
                .eq("trace_target", trace_target_val or "")\
                .eq("hop_no", hop_no_val)\
                .eq("ip", ip_text)\
                .execute()

        response = supabase.table("traceroute_hops").insert(rows).execute()

        if getattr(response, "data", None) is None:
            return False, f"❌ Failed to save WinMTR data into traceroute_hops: {response}"

        return True, "✅ Saved to Supabase table: traceroute_hops"

    except Exception as e:
        print("WINMTR SUPABASE ERROR:", e)
        return False, f"❌ Supabase Error: {str(e)}"
