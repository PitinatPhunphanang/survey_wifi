"""
network/spectrum.py
Wi-Fi spectrum scanning, channel quality analysis, and matplotlib rendering.
"""
import os
import re
import time

import matplotlib.pyplot as plt

from utils.helpers import run_command
from config import SPECTRUM_CACHE_TIMEOUT, COLOR_CYCLE, SPECTRUM_REFRESH_MS


# =========================
# WIFI SCAN
# =========================
def scan_wifi_live(wifi_cache: dict) -> dict:
    """
    Scan nearby Wi-Fi networks and update the shared cache dict in-place.
    Returns the updated cache.
    """
    now = time.time()

    try:
        run_command(["netsh", "wlan", "scan"], timeout=10)
        time.sleep(1.5)

        result = run_command(
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

                band_val = float(band) if band else (5.0 if ch_int > 14 else 2.4)
                rssi = round((int(sig) / 2) - 100, 1)

                wifi_cache[mac.lower()] = {
                    "ssid": ssid if ssid else "Hidden",
                    "band": band_val,
                    "ch": ch_int,
                    "rssi": rssi,
                    "updated": now,
                }

        # Evict stale entries
        for key in list(wifi_cache.keys()):
            if now - wifi_cache[key]["updated"] > SPECTRUM_CACHE_TIMEOUT:
                del wifi_cache[key]

    except Exception:
        pass

    return wifi_cache


# =========================
# CHANNEL QUALITY
# =========================
def analyze_channel_quality(wifi_cache: dict, connected_channel: int) -> dict:
    """Count co-channel / adjacent APs and find strongest neighbor RSSI."""
    same_channel = 0
    overlap_channel = 0
    strongest_neighbor = -100

    for ap in wifi_cache.values():
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


# =========================
# SPECTRUM RENDERING
# =========================
def render_spectrum(ax, wifi_cache: dict, ssid_colors: dict):
    """Draw the Wi-Fi spectrum on the given matplotlib Axes."""
    ax.clear()
    ax.set_facecolor("#0d1117")

    active_wifi = [n for n in wifi_cache.values() if n["rssi"] > -90]
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

        if ssid not in ssid_colors:
            ssid_colors[ssid] = COLOR_CYCLE[len(ssid_colors) % len(COLOR_CYCLE)]

        color = ssid_colors[ssid]
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


def draw_spectrum_to_file(save_path: str, wifi_cache: dict, ssid_colors: dict):
    """Render the spectrum and save it as a PNG image file."""
    fig, ax = plt.subplots(figsize=(10, 6), dpi=120)
    fig.patch.set_facecolor("#0d1117")
    render_spectrum(ax, wifi_cache, ssid_colors)

    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    fig.savefig(save_path, facecolor="#0d1117", bbox_inches="tight", dpi=120)
    plt.close(fig)
