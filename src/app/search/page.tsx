"use client";

import React, { useState, useEffect, useMemo } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { SurveyEntry, DEFAULT_THRESHOLDS } from "@/types";
import { evaluateEntry } from "@/lib/evaluation";
import { normalizeBand, getBandColor } from "@/lib/utils";
import { Search, RefreshCw, Download, ArrowUpDown } from "lucide-react";
import Link from "next/link";

const safeNum = (val: any) => (isNaN(Number(val)) || val === "" || val === null ? 0 : Number(val));

type RawSurveyEntry = SurveyEntry & { point: string };

const mapSurveyRow = (row: any): RawSurveyEntry => ({
  id: String(row.id ?? ""),
  createdAt: row.created_at ? new Date(row.created_at).getTime() : 0,
  timestamp: row.survey_timestamp ?? row.created_at ?? "",
  building: row.building ?? "",
  floor: String(row.floor ?? ""),
  // room_point = ห้อง, note/point = จุดสำรวจในห้องนั้น
  room: String(row.room_point ?? ""),
  point: String(row.point ?? row.point_no ?? row.survey_point ?? row.note ?? ""),
  note: row.note ?? "",
  ssid: row.ssid ?? "",
  apVendor: row.ap_vendor ?? "",
  bssid: row.bssid ?? "",
  band: row.band ?? null,
  radioType: row.radio_type ?? "",
  channel: String(row.channel ?? ""),
  signalPercent: safeNum(row.signal_percent),
  rssi: safeNum(row.rssi_dbm),
  rxRate: safeNum(row.receive_rate_mbps),
  txRate: safeNum(row.transmit_rate_mbps),
  gatewayIp: row.gateway_ip ?? "",
  pingGatewayMs: safeNum(row.ping_gateway_ms),
  pingGatewayLoss: safeNum(row.ping_gateway_loss_pct),
  pingServerMs: safeNum(row.ping_server_ms),
  pingLoss: safeNum(row.ping_server_loss_pct),
  tcpUpload: safeNum(row.tcp_upload_mbps),
  tcpDownload: safeNum(row.tcp_download_mbps),
  udpTarget: row.udp_target_bandwidth ?? "",
  udpActual: safeNum(row.udp_actual_mbps),
  udpJitter: safeNum(row.udp_jitter_ms),
  udpLoss: safeNum(row.udp_packetloss_pct),
});

type SortField =
  | "timestamp"
  | "building"
  | "floor"
  | "room"
  | "point"
  | "note"
  | "rssi"
  | "tcpDownload"
  | "tcpUpload"
  | "udpJitter"
  | "udpLoss";
type SortOrder = "asc" | "desc";

export default function SearchPage() {
  const [allData, setAllData] = useState<RawSurveyEntry[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isClient, setIsClient] = useState(false);

  // Search filters
  const [searchBuilding, setSearchBuilding] = useState("");
  const [searchFloor, setSearchFloor] = useState("");
  const [searchRoom, setSearchRoom] = useState("");
  const [searchPoint, setSearchPoint] = useState("");
  const [searchSSID, setSearchSSID] = useState("");
  const [searchBand, setSearchBand] = useState<"All" | "2.4GHz" | "5GHz" | "6GHz">("All");
  const [searchRating, setSearchRating] = useState<"All" | "GOOD" | "FAIR" | "POOR">("All");
  const [searchDateFrom, setSearchDateFrom] = useState("");
  const [searchDateTo, setSearchDateTo] = useState("");

  // Sorting
  const [sortField, setSortField] = useState<SortField>("timestamp");
  const [sortOrder, setSortOrder] = useState<SortOrder>("desc");

  const fetchData = async () => {
    setIsLoading(true);
    try {
      const res = await fetch("/api/survey");
      if (res.ok) {
        const data = await res.json();
        setAllData(Array.isArray(data) ? data.map(mapSurveyRow) : []);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    setIsClient(true);
  }, []);

  useEffect(() => {
    if (isClient) {
      fetchData();
    }
  }, [isClient]);

  // Filter data
  const filteredData = useMemo(() => {
    return allData.filter((entry) => {
      const matchBuilding = !searchBuilding || entry.building.toLowerCase().includes(searchBuilding.toLowerCase());
      const matchFloor = !searchFloor || entry.floor.toLowerCase().includes(searchFloor.toLowerCase());
      const matchRoom = !searchRoom || entry.room.toLowerCase().includes(searchRoom.toLowerCase());
      const matchPoint = !searchPoint || entry.point.toLowerCase().includes(searchPoint.toLowerCase());
      const matchSSID = !searchSSID || entry.ssid.toLowerCase().includes(searchSSID.toLowerCase());
      const entryRating = evaluateEntry(entry, DEFAULT_THRESHOLDS).overallRating;
      const matchRating = searchRating === "All" || entryRating === searchRating;
      
      let matchBand = true;
      if (searchBand !== "All") {
        matchBand = normalizeBand(entry.band) === searchBand;
      }

      let matchDate = true;
      if (searchDateFrom) {
        const entryDate = new Date(entry.timestamp);
        const fromDate = new Date(searchDateFrom);
        matchDate = entryDate >= fromDate;
      }
      if (searchDateTo) {
        const entryDate = new Date(entry.timestamp);
        const toDate = new Date(searchDateTo);
        toDate.setHours(23, 59, 59, 999);
        matchDate = matchDate && entryDate <= toDate;
      }

      return matchBuilding && matchFloor && matchRoom && matchPoint && matchSSID && matchBand && matchRating && matchDate;
    });
  }, [allData, searchBuilding, searchFloor, searchRoom, searchPoint, searchSSID, searchBand, searchRating, searchDateFrom, searchDateTo]);

  // Sort data
  const sortedData = useMemo(() => {
    const sorted = [...filteredData];
    sorted.sort((a, b) => {
      let aVal: any = a[sortField];
      let bVal: any = b[sortField];

      if (sortField === "timestamp") {
        aVal = new Date(a.timestamp).getTime();
        bVal = new Date(b.timestamp).getTime();
      }

      if (["floor", "note"].includes(sortField)) {
        const aNum = Number(aVal);
        const bNum = Number(bVal);
        if (!Number.isNaN(aNum) && !Number.isNaN(bNum)) {
          aVal = aNum;
          bVal = bNum;
        }
      }

      if (typeof aVal === "string" && typeof bVal === "string") {
        const result = aVal.localeCompare(bVal, undefined, { numeric: true, sensitivity: "base" });
        return sortOrder === "asc" ? result : -result;
      }

      if (aVal < bVal) return sortOrder === "asc" ? -1 : 1;
      if (aVal > bVal) return sortOrder === "asc" ? 1 : -1;
      return 0;
    });
    return sorted;
  }, [filteredData, sortField, sortOrder]);

  const toggleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortOrder("desc");
    }
  };

  const getSortIcon = (field: SortField) => {
    if (sortField !== field) return <ArrowUpDown className="w-4 h-4 opacity-40" />;
    return <ArrowUpDown className={`w-4 h-4 ${sortOrder === "asc" ? "rotate-180" : ""}`} />;
  };

  if (!isClient) return null;

  return (
    <div className="flex min-h-screen bg-gray-50 dark:bg-gray-950 text-gray-900 dark:text-gray-100 font-sans">
      {/* Sidebar */}
      <aside className="w-64 flex-shrink-0 border-r border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 flex flex-col p-4">
        <div className="flex items-center gap-2 mb-6">
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center shadow-sm">
            <span className="text-white font-bold text-sm">W</span>
          </div>
          <h1 className="text-lg font-bold tracking-tight">Survey Pro</h1>
        </div>

        <nav className="space-y-2 mb-6">
          <Link href="/">
            <Button variant="ghost" className="w-full justify-start text-sm">
               Dashboard
            </Button>
          </Link>
          <Button variant="secondary" className="w-full justify-start text-sm">
            Raw Data / Search
          </Button>
        </nav>

        <hr className="my-4 border-gray-200 dark:border-gray-800" />

        <div>
          <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">เครื่องมือ</h2>
          <Button
            onClick={fetchData}
            variant="default"
            className="w-full bg-blue-600 hover:bg-blue-700 text-white shadow-md text-sm"
            disabled={isLoading}
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${isLoading ? "animate-spin" : ""}`} />
            {isLoading ? "กำลังโหลด..." : "รีเฟรช"}
          </Button>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        <header className="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 px-8 py-4">
          <h2 className="text-2xl font-bold">ค้นหาข้อมูลดิบ (Raw Data)</h2>
          <p className="text-sm text-gray-500 mt-1">ค้นหา filter และเรียงลำดับข้อมูลการสำรวจ Wi-Fi ทั้งหมด</p>
        </header>

        <main className="flex-1 overflow-y-auto p-8 space-y-6">
          {/* Search Filters */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Search className="w-5 h-5" />
                ตัวกรองค้นหา
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                <div>
                  <label className="text-sm font-medium mb-1 block">ตึก (Building)</label>
                  <input
                    type="text"
                    placeholder="เช่น ตึก A, ตึก 110916..."
                    value={searchBuilding}
                    onChange={(e) => setSearchBuilding(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-gray-50 dark:bg-gray-900 focus:ring-2 focus:ring-blue-500 outline-none"
                  />
                </div>

                <div>
                  <label className="text-sm font-medium mb-1 block">ชั้น (Floor)</label>
                  <input
                    type="text"
                    placeholder="เช่น 1, 2, 3..."
                    value={searchFloor}
                    onChange={(e) => setSearchFloor(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-gray-50 dark:bg-gray-900 focus:ring-2 focus:ring-blue-500 outline-none"
                  />
                </div>

                <div>
                  <label className="text-sm font-medium mb-1 block">ห้อง (Room)</label>
                  <input
                    type="text"
                    placeholder="เช่น 101, 200..."
                    value={searchRoom}
                    onChange={(e) => setSearchRoom(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-gray-50 dark:bg-gray-900 focus:ring-2 focus:ring-blue-500 outline-none"
                  />
                </div>

                <div>
                  <label className="text-sm font-medium mb-1 block">จุด (Point)</label>
                  <input
                    type="text"
                    placeholder="เช่น 1, 2, หน้าโต๊ะ, มุมห้อง..."
                    value={searchPoint}
                    onChange={(e) => setSearchPoint(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-gray-50 dark:bg-gray-900 focus:ring-2 focus:ring-blue-500 outline-none"
                  />
                </div>

                <div>
                  <label className="text-sm font-medium mb-1 block">SSID</label>
                  <input
                    type="text"
                    placeholder="ชื่อเครือข่าย Wi-Fi..."
                    value={searchSSID}
                    onChange={(e) => setSearchSSID(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-gray-50 dark:bg-gray-900 focus:ring-2 focus:ring-blue-500 outline-none"
                  />
                </div>

                <div>
                  <label className="text-sm font-medium mb-1 block">แถบความถี่ (Band)</label>
                  <select
                    value={searchBand}
                    onChange={(e) => setSearchBand(e.target.value as any)}
                    className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-gray-50 dark:bg-gray-900 focus:ring-2 focus:ring-blue-500 outline-none"
                  >
                    <option value="All">ทั้งหมด</option>
                    <option value="2.4GHz">2.4 GHz</option>
                    <option value="5GHz">5 GHz</option>
                    <option value="6GHz">6 GHz</option>
                  </select>
                </div>

                <div>
                  <label className="text-sm font-medium mb-1 block">Rating</label>
                  <select
                    value={searchRating}
                    onChange={(e) => setSearchRating(e.target.value as any)}
                    className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-gray-50 dark:bg-gray-900 focus:ring-2 focus:ring-blue-500 outline-none"
                  >
                    <option value="All">ทั้งหมด</option>
                    <option value="GOOD">GOOD</option>
                    <option value="FAIR">FAIR</option>
                    <option value="POOR">POOR</option>
                  </select>
                </div>

                <div>
                  <label className="text-sm font-medium mb-1 block">วันที่เริ่มต้น</label>
                  <input
                    type="datetime-local"
                    value={searchDateFrom}
                    onChange={(e) => setSearchDateFrom(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-gray-50 dark:bg-gray-900 focus:ring-2 focus:ring-blue-500 outline-none text-sm"
                  />
                </div>

                <div>
                  <label className="text-sm font-medium mb-1 block">วันที่สิ้นสุด</label>
                  <input
                    type="datetime-local"
                    value={searchDateTo}
                    onChange={(e) => setSearchDateTo(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-gray-50 dark:bg-gray-900 focus:ring-2 focus:ring-blue-500 outline-none text-sm"
                  />
                </div>

                <div className="flex items-end">
                  <Button
                    onClick={() => {
                      setSearchBuilding("");
                      setSearchFloor("");
                      setSearchRoom("");
                      setSearchPoint("");
                      setSearchSSID("");
                      setSearchBand("All");
                      setSearchRating("All");
                      setSearchDateFrom("");
                      setSearchDateTo("");
                    }}
                    variant="outline"
                    className="w-full"
                  >
                    ล้างการค้นหา
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Results */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>ผลลัพธ์ ({sortedData.length} รายการ)</CardTitle>
                <Button variant="outline" size="sm">
                  <Download className="w-4 h-4 mr-2" />
                  ส่งออก Excel
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-left whitespace-nowrap">
                  <thead className="text-xs text-gray-500 bg-gray-50 dark:bg-gray-900/80 dark:text-gray-400 uppercase border-b dark:border-gray-800">
                    <tr>
                      <th className="px-4 py-3 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800">
                        <button
                          onClick={() => toggleSort("timestamp")}
                          className="flex items-center gap-2"
                        >
                          เวลา {getSortIcon("timestamp")}
                        </button>
                      </th>
                      <th className="px-4 py-3 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800">
                        <button
                          onClick={() => toggleSort("building")}
                          className="flex items-center gap-2"
                        >
                          ตึก {getSortIcon("building")}
                        </button>
                      </th>
                      <th className="px-4 py-3 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800">
                        <button
                          onClick={() => toggleSort("floor")}
                          className="flex items-center gap-2"
                        >
                          ชั้น {getSortIcon("floor")}
                        </button>
                      </th>
                      <th className="px-4 py-3 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800">
                        <button
                          onClick={() => toggleSort("room")}
                          className="flex items-center gap-2"
                        >
                          ห้อง {getSortIcon("room")}
                        </button>
                      </th>
                      <th className="px-4 py-3 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800">
                        <button
                          onClick={() => toggleSort("point")}
                          className="flex items-center gap-2"
                        >
                          จุด {getSortIcon("point")}
                        </button>
                      </th>
                      <th className="px-4 py-3 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800">
                        <button
                          onClick={() => toggleSort("note")}
                          className="flex items-center gap-2"
                        >
                          Note {getSortIcon("note")}
                        </button>
                      </th>
                      <th className="px-4 py-3">SSID</th>
                      <th className="px-4 py-3">AP Vendor</th>
                      <th className="px-4 py-3">Band</th>
                      <th className="px-4 py-3 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800">
                        <button
                          onClick={() => toggleSort("rssi")}
                          className="flex items-center gap-2"
                        >
                          RSSI {getSortIcon("rssi")}
                        </button>
                      </th>
                      <th className="px-4 py-3 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800">
                        <button
                          onClick={() => toggleSort("tcpDownload")}
                          className="flex items-center gap-2"
                        >
                          Down {getSortIcon("tcpDownload")}
                        </button>
                      </th>
                      <th className="px-4 py-3 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800">
                        <button
                          onClick={() => toggleSort("tcpUpload")}
                          className="flex items-center gap-2"
                        >
                          Up {getSortIcon("tcpUpload")}
                        </button>
                      </th>
                      <th className="px-4 py-3">Ping</th>
                      <th className="px-4 py-3 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800">
                        <button
                          onClick={() => toggleSort("udpJitter")}
                          className="flex items-center gap-2"
                        >
                          Jitter {getSortIcon("udpJitter")}
                        </button>
                      </th>
                      <th className="px-4 py-3 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800">
                        <button
                          onClick={() => toggleSort("udpLoss")}
                          className="flex items-center gap-2"
                        >
                          Loss {getSortIcon("udpLoss")}
                        </button>
                      </th>
                      <th className="px-4 py-3">Rating</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sortedData.length === 0 ? (
                      <tr>
                        <td colSpan={16} className="px-4 py-8 text-center text-gray-500">
                          ไม่พบข้อมูลที่ตรงกับเกณฑ์การค้นหา
                        </td>
                      </tr>
                    ) : (
                      sortedData.map((entry) => {
                        const report = evaluateEntry(entry, DEFAULT_THRESHOLDS);
                        const rating = report.overallRating;
                        const ratingBgClass =
                          rating === "GOOD"
                            ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300"
                            : rating === "FAIR"
                            ? "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300"
                            : "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300";
                        const bandColor = getBandColor(entry.band);

                        return (
                          <tr key={entry.id} className="border-b dark:border-gray-800 hover:bg-gray-50/50 dark:hover:bg-gray-800/50">
                            <td className="px-4 py-3 text-xs text-gray-500">{entry.timestamp || "-"}</td>
                            <td className="px-4 py-3 font-medium">{entry.building || "-"}</td>
                            <td className="px-4 py-3">{entry.floor || "-"}</td>
                            <td className="px-4 py-3 font-medium">{entry.room || "-"}</td>
                            <td className="px-4 py-3 font-medium">{entry.point || "-"}</td>
                            <td className="px-4 py-3 text-xs">{entry.note || "-"}</td>
                            <td className="px-4 py-3 text-xs">{entry.ssid || "-"}</td>
                            <td className="px-4 py-3 text-xs">{(entry as any).apVendor || "-"}</td>
                            <td className="px-4 py-3">
                              <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-semibold ${bandColor.bg} ${bandColor.text}`}>
                                {normalizeBand(entry.band)}
                              </span>
                            </td>
                            <td className={`px-4 py-3 font-medium ${safeNum(entry.rssi) < -75 ? "text-red-500" : safeNum(entry.rssi) < -67 ? "text-amber-500" : "text-emerald-500"}`}>
                              {safeNum(entry.rssi).toFixed(1)} dBm
                            </td>
                            <td className="px-4 py-3">{safeNum(entry.tcpDownload).toFixed(1)}</td>
                            <td className="px-4 py-3">{safeNum(entry.tcpUpload).toFixed(1)}</td>
                            <td className="px-4 py-3">{safeNum(entry.pingServerMs).toFixed(1)}</td>
                            <td className="px-4 py-3">{safeNum(entry.udpJitter).toFixed(1)}</td>
                            <td className="px-4 py-3">{safeNum(entry.udpLoss).toFixed(1)}%</td>
                            <td className="px-4 py-3">
                              <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium ${ratingBgClass}`}>
                                {rating}
                              </span>
                            </td>
                          </tr>
                        );
                      })
                    )}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </main>
      </div>
    </div>
  );
}