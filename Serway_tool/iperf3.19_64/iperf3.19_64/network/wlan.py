"""
network/wlan.py
Wi-Fi interface information: SSID, BSSID, band, channel, RSSI, noise/SNR,
AP vendor lookup, and band helpers.
"""
import re
import urllib.request

from utils.helpers import run_command, parse_float_value, parse_percent_value


# =========================
# WLAN INFO
# =========================
def get_wlan_info():
    """Return a dict of the currently connected Wi-Fi interface details."""
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
        result = run_command(["netsh", "wlan", "show", "interfaces"], timeout=8)
        text = result.stdout
        pairs = []

        for raw_line in text.splitlines():
            line = raw_line.strip()
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            pairs.append((_normalize_key(key), value.strip()))

        info["SSID"] = _find_value(pairs, ["ssid"]) or info["SSID"]
        info["BSSID"] = _find_value(pairs, ["apbssid", "bssid"]) or info["BSSID"]
        info["Band"] = _find_value(pairs, ["band"]) or info["Band"]
        info["Channel"] = _find_value(pairs, ["channel"]) or info["Channel"]
        info["Radio_Type"] = _find_value(pairs, ["radiotype"]) or info["Radio_Type"]

        rx_rate = _find_value(pairs, ["receiveratembps", "receiverate(mbps)"])
        tx_rate = _find_value(pairs, ["transmitratembps", "transmitrate(mbps)"])
        signal = _find_value(pairs, ["signal"])
        rssi = _find_value(pairs, ["rssi"])

        info["Receive_Rate_Mbps"] = parse_float_value(rx_rate)
        info["Transmit_Rate_Mbps"] = parse_float_value(tx_rate)
        info["Signal_%"] = parse_percent_value(signal)
        info["RSSI_dBm"] = parse_float_value(rssi)

        if info["BSSID"] == "Unknown":
            info["BSSID"] = _find_mac(text) or info["BSSID"]

        if info["RSSI_dBm"] is None and info["Signal_%"] is not None:
            info["RSSI_dBm"] = round((info["Signal_%"] / 2) - 100, 1)

        if info["Band"] == "Unknown":
            info["Band"] = infer_band_from_channel(info["Channel"])

    except Exception:
        pass

    return info


def _normalize_key(value):
    return re.sub(r"[^a-z0-9()%]", "", str(value).strip().lower())


def _find_value(pairs, aliases):
    alias_set = set(aliases)
    for key, value in pairs:
        if key in alias_set and value:
            return value
    return None


def _find_mac(text):
    matches = re.findall(r"(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}", text)
    return matches[0] if matches else None


# =========================
# NOISE / SNR
# =========================
def measure_noise_snr(rssi_dbm):
    """
    วัด Noise Floor และ SNR จาก netsh wlan show interfaces
    คืน (noise_floor_dbm, snr_db, snr_quality) — None ถ้าวัดไม่ได้
    """
    noise_floor = None
    snr_db = None
    snr_quality = None

    try:
        result = run_command(["netsh", "wlan", "show", "interfaces"], timeout=8)
        text = result.stdout

        for raw_line in text.splitlines():
            line = raw_line.strip().lower()
            if "noise" in line and ":" in line:
                _, val = line.split(":", 1)
                parsed = parse_float_value(val.strip())
                if parsed is not None and parsed < 0:
                    noise_floor = round(parsed, 1)
                    break

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


# =========================
# BAND / CHANNEL HELPERS
# =========================
def infer_band_from_channel(channel):
    """Guess 2.4/5 GHz band from channel number."""
    try:
        ch = int(str(channel).strip())
        if 1 <= ch <= 14:
            return "2.4 GHz"
        if 36 <= ch <= 177:
            return "5 GHz"
        return "Unknown"
    except Exception:
        return "Unknown"


def normalize_band(band):
    """Normalize band string to '2.4 GHz' or '5 GHz'."""
    if not band:
        return "Unknown"
    b = str(band).strip().lower().replace(" ", "")
    if "2.4" in b:
        return "2.4 GHz"
    if "5" in b:
        return "5 GHz"
    return "Unknown"


# =========================
# AP VENDOR LOOKUP
# =========================
def lookup_ap_vendor(bssid):
    """Look up AP vendor/brand from BSSID OUI via macvendors API."""
    if not bssid or bssid == "Unknown":
        return "Unknown"
    try:
        oui = bssid.replace("-", ":").upper()[:8]
        url = f"https://api.macvendors.com/{oui}"
        req = urllib.request.Request(url, headers={"User-Agent": "WifiSurveyApp/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.read().decode("utf-8").strip()
    except Exception:
        return "Unknown"
