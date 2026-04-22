"use client";

import React, { useState, useEffect, useMemo } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { SurveyEntry, DEFAULT_THRESHOLDS } from "@/types";
import { evaluateEntry } from "@/lib/evaluation";
import { LayoutDashboard, RefreshCw, Building2, Map as MapIcon, ChevronDown, ChevronRight, Activity, Printer, Trash2 } from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend, LabelList, ReferenceLine, ComposedChart, Line
} from "recharts";

const safeNum = (val: any) => (isNaN(Number(val)) || val === "" || val === null ? 0 : Number(val));
const mapSurveyRow = (row: any): SurveyEntry => ({
  id: String(row.id ?? ""),
  timestamp: row.survey_timestamp ?? row.created_at ?? "",
  building: row.building ?? "",
  floor: String(row.floor ?? ""),
  room: String(row.room_point ?? ""),
  note: row.note ?? "",
  ssid: row.ssid ?? "",
  bssid: row.bssid ?? "",
  band: row.band ?? "",
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

const mapTraceRow = (row: any) => ({
  survey_id: row.survey_id,
  survey_timestamp: row.survey_timestamp ?? "",
  Building: row.building ?? "",
  Floor: String(row.floor ?? ""),
  Room_Point: String(row.room_point ?? ""),
  Hop: String(row.hop ?? ""),
  IP: row.ip ?? "",
  Hostname: "",
  RTT1: "*",
  RTT2: "*",
  RTT3: "*",
  Min_ms: row.min_ms ?? null,
  Max_ms: row.max_ms ?? null,
  Avg_ms: row.avg_ms ?? null,
  ["Loss_%"]: row.loss_pct ?? 0,
});
export default function Dashboard() {
  const [history, setHistory] = useState<SurveyEntry[]>([]);
  const [traceData, setTraceData] = useState<any[]>([]);
  const [isClient, setIsClient] = useState(false);
  const [isLoadingDB, setIsLoadingDB] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);

  // Filter State
  const [selectedBuilding, setSelectedBuilding] = useState<string | null>(null);
  const [selectedFloor, setSelectedFloor] = useState<string | null>(null);
  const [expandedBuildings, setExpandedBuildings] = useState<Set<string>>(new Set());

  // Traceroute room selection within a floor
  const [selectedTraceRoom, setSelectedTraceRoom] = useState<string>("");

  const fetchFromDatabase = async () => {
    setIsLoadingDB(true);
    try {
      const [resSurvey, resTrace] = await Promise.all([
        fetch('/api/survey'),
        fetch('/api/trace')
      ]);

      if (resSurvey.ok) {
        const data = await resSurvey.json();
        setHistory(Array.isArray(data) ? data.map(mapSurveyRow) : []);
      } else {
        setHistory([]);
      }

      if (resTrace.ok) {
        const data = await resTrace.json();
        setTraceData(Array.isArray(data) ? data.map(mapTraceRow) : []);
      } else {
        setTraceData([]);
      }
    } catch (err) {
      console.error(err);
      setHistory([]);
      setTraceData([]);
    } finally {
      setIsLoadingDB(false);
    }
  };

  useEffect(() => {
    setIsClient(true);
    fetchFromDatabase(); // Fetch newest data on load
  }, []);

  // Compute Hierarchy from DB (Buildings -> Floors)
  const hierarchy = useMemo(() => {
    const map = new Map<string, Set<string>>();
    history.forEach(h => {
      const bldg = h.building?.trim() || 'Unknown';
      const floor = h.floor?.trim() || 'Default';
      if (!map.has(bldg)) map.set(bldg, new Set());
      map.get(bldg)!.add(floor);
    });
    const result: Record<string, string[]> = {};
    for (const [b, fSet] of map.entries()) {
      result[b] = Array.from(fSet).sort((a, b) => {
        const numA = parseInt(a);
        const numB = parseInt(b);
        if (!isNaN(numA) && !isNaN(numB)) return numA - numB;
        return a.localeCompare(b);
      });
    }
    return result;
  }, [history]);

  useEffect(() => {
    if (!selectedBuilding && Object.keys(hierarchy).length > 0) {
      const firstBuilding = Object.keys(hierarchy)[0];
      const firstFloor = hierarchy[firstBuilding]?.[0] ?? null;

      setSelectedBuilding(firstBuilding);
      setSelectedFloor(firstFloor);
      setExpandedBuildings(new Set([firstBuilding]));
    }
  }, [hierarchy, selectedBuilding]);

  // Active entries for the selected floor
  const entries = useMemo(() => {
    if (!selectedBuilding || !selectedFloor) return [];
    return history.filter(h => {
      const bldg = h.building?.trim() || 'Unknown';
      const floor = h.floor?.trim() || 'Default';
      return bldg === selectedBuilding && floor === selectedFloor;
    });
  }, [history, selectedBuilding, selectedFloor]);

  // Auto-select the first room for traceroute when floor changes
  useEffect(() => {
    if (entries.length > 0) {
      setSelectedTraceRoom(entries[0].room);
    } else {
      setSelectedTraceRoom("");
    }
  }, [entries]);

  const toggleBuilding = (bldg: string) => {
    setExpandedBuildings(prev => {
      const next = new Set(prev);
      if (next.has(bldg)) next.delete(bldg);
      else next.add(bldg);
      return next;
    });
  };

  const handleDelete = async ({ building, floor }: { building: string; floor?: string }) => {
    const scope = floor ? "floor" : "building";
    const targetKey = floor ? `${building}::${floor}` : building;
    const targetLabel = floor ? `ชั้น ${floor} ของตึก ${building}` : `ตึก ${building}`;

    if (!window.confirm(`ต้องการลบข้อมูล${targetLabel}ออกจากฐานข้อมูลใช่หรือไม่?`)) {
      return;
    }

    setDeleteTarget(targetKey);
    try {
      const response = await fetch("/api/survey", {
        method: "DELETE",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          scope,
          building,
          floor,
        }),
      });

      const payload = await response.json();

      if (!response.ok) {
        throw new Error(payload?.error || "Delete failed");
      }

      if (selectedBuilding === building && (!floor || selectedFloor === floor)) {
        setSelectedBuilding(null);
        setSelectedFloor(null);
        setSelectedTraceRoom("");
      }

      await fetchFromDatabase();
      window.alert(`ลบข้อมูล${targetLabel}เรียบร้อยแล้ว (${payload.deletedCount ?? 0} รายการ)`);
    } catch (error) {
      console.error(error);
      window.alert("ลบข้อมูลไม่สำเร็จ กรุณาลองใหม่อีกครั้ง");
    } finally {
      setDeleteTarget(null);
    }
  };

  // ============================================
  // Floor Report KPI & Chart Data Calculations
  // ============================================
  const count = entries.length;
  const avgRssi = count > 0 ? entries.reduce((acc, curr) => acc + safeNum(curr.rssi), 0) / count : 0;
  const avgTcpDown = count > 0 ? entries.reduce((acc, curr) => acc + safeNum(curr.tcpDownload), 0) / count : 0;
  const avgTcpUp = count > 0 ? entries.reduce((acc, curr) => acc + safeNum(curr.tcpUpload), 0) / count : 0;
  const avgPing = count > 0 ? entries.reduce((acc, curr) => acc + safeNum(curr.pingServerMs), 0) / count : 0;
  const avgJitter = count > 0 ? entries.reduce((acc, curr) => acc + safeNum(curr.udpJitter), 0) / count : 0;
  const avgLoss = count > 0 ? entries.reduce((acc, curr) => acc + safeNum(curr.udpLoss), 0) / count : 0;

  const evaluated = entries.map(e => ({ ...e, report: evaluateEntry(e, DEFAULT_THRESHOLDS) }));
  const poorCount = evaluated.filter(e => e.report.overallRating === "POOR").length;

  const ratingData = [
    { name: "GOOD", value: evaluated.filter(e => e.report.overallRating === "GOOD").length, color: "#10b981" },
    { name: "FAIR", value: evaluated.filter(e => e.report.overallRating === "FAIR").length, color: "#f59e0b" },
    { name: "POOR", value: poorCount, color: "#ef4444" }
  ].filter(d => d.value > 0);

  const rssiData = [...entries].map(e => ({ name: e.room, rssi: safeNum(e.rssi) })).sort((a, b) => a.rssi - b.rssi);
  const throughputData = entries.map(e => ({ name: e.room, Download: safeNum(e.tcpDownload), Upload: safeNum(e.tcpUpload) }));
  const pingData = entries.map(e => ({ name: e.room, ping: safeNum(e.pingServerMs) }));
  const jitterData = entries.map(e => ({ name: e.room, jitter: safeNum(e.udpJitter) }));
  const lossData = entries.map(e => ({ name: e.room, udpLoss: safeNum(e.udpLoss), pingLoss: safeNum(e.pingLoss) }));

  const bandCounts = entries.reduce((acc, curr) => {
    const band = curr.band ? curr.band.toUpperCase() : "UNKNOWN";
    if (!acc[band]) acc[band] = 0;
    acc[band]++;
    return acc;
  }, {} as Record<string, number>);
  const bandData = Object.keys(bandCounts).map((key, i) => ({
    name: key, value: bandCounts[key], color: ['#8b5cf6', '#ec4899', '#06b6d4', '#f59e0b'][i % 4]
  }));

  const sortedRssi = [...entries].sort((a, b) => safeNum(a.rssi) - safeNum(b.rssi));
  const worstRssi = sortedRssi.slice(0, 3).map(e => ({ room: e.room, val: e.rssi }));
  const worstPing = [...entries].sort((a, b) => safeNum(b.pingServerMs) - safeNum(a.pingServerMs))[0];
  const worstJitter = [...entries].sort((a, b) => safeNum(b.udpJitter) - safeNum(a.udpJitter))[0];
  const worstLoss = [...entries].sort((a, b) => Math.max(safeNum(b.udpLoss), safeNum(b.pingLoss)) - Math.max(safeNum(a.udpLoss), safeNum(a.pingLoss)))[0];

  const generateSummary = () => {
    let summary: string[] = [];
    if (count === 0) return summary;
    if (avgRssi >= -67) summary.push(`สัญญาณ Wi-Fi โดยรวมอยู่ในเกณฑ์ดีมาก (เฉลี่ย ${avgRssi.toFixed(1)} dBm)`);
    else if (avgRssi >= -75) summary.push(`สัญญาณ Wi-Fi โดยรวมอยู่ในเกณฑ์พอใช้ (เฉลี่ย ${avgRssi.toFixed(1)} dBm) แต่มีบางจุดที่ควรปรับปรุง`);
    else summary.push(`สัญญาณ Wi-Fi โดยรวมอยู่ในเกณฑ์อ่อน (เฉลี่ย ${avgRssi.toFixed(1)} dBm) จำเป็นต้องตรวจสอบหรือเพิ่ม Access Point`);

    if (avgLoss === 0) summary.push(`ความเสถียรของเครือข่ายดีเยี่ยม ไม่พบ Packet Loss ในการทดสอบ`);
    else if (avgLoss > 2) summary.push(`พบปัญหา Packet Loss ค่อนข้างสูง (เฉลี่ย ${avgLoss.toFixed(1)}%) อาจทำให้การเชื่อมต่อหลุดบ่อย`);

    if (avgJitter < 30) summary.push(`ค่าความแกว่งของสัญญาณ (Jitter) ต่ำ เหมาะสมกับการใช้งาน VDO Conference และ Voice Call`);
    else summary.push(`ค่า Jitter ค่อนข้างสูง อาจทำให้ภาพหรือเสียงกระตุกระหว่างประชุมออนไลน์`);

    if (avgTcpDown > 100) summary.push(`ความเร็ว Download ทำได้ดีเยี่ยม (เฉลี่ย ${avgTcpDown.toFixed(1)} Mbps) รองรับการใช้งานหนาแน่นได้สบาย`);
    else if (avgTcpDown < 20) summary.push(`ความเร็ว Download ค่อนข้างต่ำ ควรตรวจสอบ Bandwidth ของฝั่ง Gateway หรือข้อจำกัดของอุปกรณ์`);
    return summary;
  };
  const summaryLines = generateSummary();

  const currentTrace = traceData.filter(
    t => t.Building === selectedBuilding && t.Floor === selectedFloor && t.Room_Point === selectedTraceRoom
  );

  if (!isClient) return null;

  return (
    <div className="flex min-h-screen bg-gray-50 dark:bg-gray-950 text-gray-900 dark:text-gray-100 font-sans">

      {/* Sidebar Navigation */}
      <aside className="w-64 flex-shrink-0 border-r border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 flex flex-col print:hidden">
        <div className="p-4 border-b border-gray-200 dark:border-gray-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center shadow-sm">
              <span className="text-white font-bold text-sm">W</span>
            </div>
            <h1 className="text-lg font-bold tracking-tight">Survey Pro</h1>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-6">
          <div className="space-y-2">
            <Button onClick={fetchFromDatabase} variant="default" className="w-full bg-blue-600 hover:bg-blue-700 text-white shadow-md" disabled={isLoadingDB}>
              <RefreshCw className={`w-4 h-4 mr-2 ${isLoadingDB ? 'animate-spin' : ''}`} />
              {isLoadingDB ? "กำลังซิงค์..." : "ดึงข้อมูลล่าสุด"}
            </Button>
          </div>

          <div>
            <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">สถานที่</h2>
            <div className="space-y-1">
              <Button
                variant={!selectedBuilding ? "secondary" : "ghost"}
                className="w-full justify-start text-sm"
                onClick={() => { setSelectedBuilding(null); setSelectedFloor(null); }}
              >
                <LayoutDashboard className="w-4 h-4 mr-2 text-gray-500" />
                ภาพรวมทั้งหมด
              </Button>

              {Object.entries(hierarchy).map(([bldg, floors]) => (
                <div key={bldg} className="pt-1">
                  <div className="flex items-center gap-1">
                    <Button
                      variant="ghost"
                      className="px-2 w-8 h-8"
                      onClick={() => toggleBuilding(bldg)}
                    >
                      {expandedBuildings.has(bldg) ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                    </Button>
                    <Button
                      variant={selectedBuilding === bldg && !selectedFloor ? "secondary" : "ghost"}
                      className="flex-1 justify-start text-sm font-medium px-2 h-8"
                      onClick={() => {
                        setSelectedBuilding(bldg);
                        setSelectedFloor(null);
                        setExpandedBuildings(prev => new Set(prev).add(bldg));
                      }}
                    >
                      <Building2 className="w-4 h-4 mr-2 text-indigo-500" />
                      {bldg}
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 text-red-500 hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-950/40"
                      onClick={() => handleDelete({ building: bldg })}
                      disabled={deleteTarget !== null}
                      aria-label={`Delete building ${bldg}`}
                    >
                      <Trash2 className={`w-4 h-4 ${deleteTarget === bldg ? "animate-pulse" : ""}`} />
                    </Button>
                  </div>

                  {expandedBuildings.has(bldg) && (
                    <div className="ml-8 mt-1 space-y-1 border-l-2 border-gray-100 dark:border-gray-800 pl-2">
                      {floors.map(fl => (
                        <div key={fl} className="flex items-center gap-1">
                          <Button
                            variant={selectedBuilding === bldg && selectedFloor === fl ? "secondary" : "ghost"}
                            className="flex-1 justify-start text-xs h-8 text-gray-600 dark:text-gray-300"
                            onClick={() => {
                              setSelectedBuilding(bldg);
                              setSelectedFloor(fl);
                            }}
                          >
                            <MapIcon className="w-3.5 h-3.5 mr-2 opacity-70" />
                            ชั้น {fl}
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8 text-red-500 hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-950/40"
                            onClick={() => handleDelete({ building: bldg, floor: fl })}
                            disabled={deleteTarget !== null}
                            aria-label={`Delete floor ${fl} in ${bldg}`}
                          >
                            <Trash2 className={`w-3.5 h-3.5 ${deleteTarget === `${bldg}::${fl}` ? "animate-pulse" : ""}`} />
                          </Button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="p-4 border-t border-gray-200 dark:border-gray-800">
          <Button onClick={() => window.print()} variant="outline" className="w-full justify-start text-sm">
            <Printer className="w-4 h-4 mr-2" /> พิมพ์รายงาน
          </Button>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col h-screen overflow-hidden">

        {/* Top Header */}
        <header className="flex-shrink-0 bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 px-8 py-4 flex items-center justify-between print:hidden">
          <div>
            <h2 className="text-xl font-bold">
              {selectedBuilding && selectedFloor ? `รายงานอาคาร: ${selectedBuilding} - ชั้น ${selectedFloor}` : 'ภาพรวม Dashboard'}
            </h2>
            <p className="text-sm text-gray-500 mt-1">
              {selectedBuilding && selectedFloor ? `แสดงข้อมูลจุดทดสอบทั้งหมด ${entries.length} จุดในชั้นนี้` : `กรุณาเลือกตึกและชั้นจากเมนูด้านซ้ายเพื่อดูรายละเอียด`}
            </p>
          </div>
        </header>

        {/* Dashboard Area */}
        <main className="flex-1 overflow-y-auto p-4 md:p-8 space-y-8 bg-gray-50 dark:bg-gray-950">

          {(!selectedBuilding || !selectedFloor) ? (
            <div className="h-full flex flex-col items-center justify-center text-gray-500 space-y-4">
              <Activity className="w-16 h-16 opacity-20" />
              <p>กรุณาเลือกชั้นจากเมนูด้านซ้ายเพื่อดูรายงาน</p>
            </div>
          ) : entries.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-gray-500 space-y-4">
              <Activity className="w-16 h-16 opacity-20" />
              <p>ไม่มีข้อมูลการทดสอบสำหรับสถานที่นี้</p>
            </div>
          ) : (
            <>
              {/* KPI Summary */}
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 print:break-inside-avoid">
                <KpiCard title="Avg RSSI" value={`${avgRssi.toFixed(1)} dBm`} isWarning={avgRssi < -75} />
                <KpiCard title="Avg Download" value={`${avgTcpDown.toFixed(1)} Mbps`} />
                <KpiCard title="Avg Upload" value={`${avgTcpUp.toFixed(1)} Mbps`} />
                <KpiCard title="Avg Ping" value={`${avgPing.toFixed(1)} ms`} isWarning={avgPing > 50} />
                <KpiCard title="Avg Jitter" value={`${avgJitter.toFixed(1)} ms`} isWarning={avgJitter > 30} />
                <KpiCard title="Poor Points" value={`${poorCount} / ${count}`} isWarning={poorCount > 0} highlight />
              </div>

              {/* Smart Summary & Worst Points */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 print:break-inside-avoid">
                <Card className="lg:col-span-2 bg-blue-50/50 dark:bg-blue-900/10 border-blue-200 dark:border-blue-800">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base text-blue-800 dark:text-blue-300">สรุปผลอัตโนมัติ / ข้อเสนอแนะ</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ul className="list-disc pl-5 space-y-2 text-sm text-gray-700 dark:text-gray-300">
                      {summaryLines.map((line, idx) => (
                        <li key={idx}>{line}</li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>

                <Card className="border-red-200 dark:border-red-900/30">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base text-red-600 dark:text-red-400">จุดวิกฤตที่ต้องแก้ไข (Action List)</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3 text-sm">
                      <div className="flex justify-between items-center border-b border-gray-100 dark:border-gray-800 pb-1">
                        <span className="text-gray-500">สัญญาณอ่อนที่สุด (RSSI):</span>
                        <span className="font-semibold text-red-500">{worstRssi.map(r => r.room).join(', ')}</span>
                      </div>
                      <div className="flex justify-between items-center border-b border-gray-100 dark:border-gray-800 pb-1">
                        <span className="text-gray-500">ปิงสูงที่สุด (Ping):</span>
                        <span className="font-medium">{worstPing?.room} ({safeNum(worstPing?.pingServerMs)}ms)</span>
                      </div>
                      <div className="flex justify-between items-center border-b border-gray-100 dark:border-gray-800 pb-1">
                        <span className="text-gray-500">ความแกว่งสูงสุด (Jitter):</span>
                        <span className="font-medium">{worstJitter?.room} ({safeNum(worstJitter?.udpJitter)}ms)</span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-gray-500">สูญหายสูงสุด (Loss):</span>
                        <span className="font-medium">{worstLoss?.room} ({Math.max(safeNum(worstLoss?.udpLoss), safeNum(worstLoss?.pingLoss))}%)</span>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Traceroute Section */}
              {traceData.length > 0 && (
                <div className="space-y-6 print:break-inside-avoid pt-6 border-t border-gray-200 dark:border-gray-800">
                  <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                    <div>
                      <h2 className="text-2xl font-bold flex items-center gap-2">
                        <Activity className="w-6 h-6 text-indigo-500" />
                        วิเคราะห์เส้นทางเชื่อมต่อ (Route Analysis)
                      </h2>
                      <p className="text-gray-500 text-sm mt-1">การวิเคราะห์คุณภาพเครือข่ายแบบ Hop-by-hop</p>
                    </div>
                    <div className="flex items-center gap-2 bg-white dark:bg-gray-800 p-2 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm">
                      <span className="text-sm font-medium text-gray-600 dark:text-gray-300">เลือกจุดทดสอบ:</span>
                      <select
                        className="h-8 rounded-md border border-gray-200 bg-gray-50 dark:bg-gray-900 px-3 py-1 text-sm focus:ring-2 focus:ring-indigo-500 dark:border-gray-600 focus:outline-none"
                        value={selectedTraceRoom}
                        onChange={(e) => setSelectedTraceRoom(e.target.value)}
                      >
                        <option value="">-- เลือก --</option>
                        {entries.map(e => (
                          <option key={e.room} value={e.room}>{e.room}</option>
                        ))}
                      </select>
                    </div>
                  </div>

                  {currentTrace.length > 0 ? (
                    <>
                      <TraceRouteSummary currentTrace={currentTrace} />

                      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        <Card className="shadow-sm border-gray-200 dark:border-gray-800">
                          <CardHeader className="bg-gray-50/50 dark:bg-gray-900/50 border-b border-gray-100 dark:border-gray-800 pb-3">
                            <CardTitle className="text-base">สถานะการเชื่อมต่อ (Timeline)</CardTitle>
                          </CardHeader>
                          <CardContent className="pt-4 overflow-y-auto max-h-[700px]">
                            <TraceRouteTimeline data={currentTrace} />
                          </CardContent>
                        </Card>

                        <div className="space-y-6 flex flex-col">
                          <Card className="shadow-sm border-gray-200 dark:border-gray-800 flex-1">
                            <CardHeader className="bg-gray-50/50 dark:bg-gray-900/50 border-b border-gray-100 dark:border-gray-800 pb-3">
                              <CardTitle className="text-base">ช่วงความหน่วงเวลาแต่ละจุด (Latency Range)</CardTitle>
                            </CardHeader>
                            <CardContent className="pt-4 h-[300px]">
                              <TraceRouteLatencyChart data={currentTrace} />
                            </CardContent>
                          </Card>

                          <Card className="shadow-sm border-gray-200 dark:border-gray-800 flex-1">
                            <CardHeader className="bg-gray-50/50 dark:bg-gray-900/50 border-b border-gray-100 dark:border-gray-800 pb-3">
                              <CardTitle className="text-base">อัตราข้อมูลสูญหายแต่ละจุด (Packet Loss)</CardTitle>
                              <p className="text-xs text-gray-500 mt-1">(Loss ระหว่างทางอาจไม่ใช่ปัญหาของปลายทางเสมอไป)</p>
                            </CardHeader>
                            <CardContent className="pt-4 h-[250px]">
                              <TraceRouteLossChart data={currentTrace} />
                            </CardContent>
                          </Card>
                        </div>
                      </div>

                      <Card className="shadow-sm border-gray-200 dark:border-gray-800 overflow-hidden">
                        <CardHeader className="bg-gray-50/50 dark:bg-gray-900/50 border-b border-gray-100 dark:border-gray-800 pb-3">
                          <CardTitle className="text-base">ข้อมูลดิบ (Raw Data)</CardTitle>
                        </CardHeader>
                        <div className="overflow-x-auto">
                          <TraceRouteTable data={currentTrace} />
                        </div>
                      </Card>
                    </>
                  ) : (
                    <div className="p-8 text-center bg-white dark:bg-gray-900 rounded-xl border border-dashed border-gray-300 dark:border-gray-700">
                      <MapIcon className="w-10 h-10 mx-auto text-gray-300 dark:text-gray-600 mb-3" />
                      <p className="text-gray-500">ไม่มีข้อมูล Traceroute สำหรับจุดทดสอบ "{selectedTraceRoom}"</p>
                    </div>
                  )}
                </div>
              )}

              <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
                <div className="lg:col-span-1 space-y-6">
                  <Card className="print:break-inside-avoid">
                    <CardHeader>
                      <CardTitle className="text-base">สัดส่วนคุณภาพ (Rating)</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="h-[200px] w-full">
                        <ResponsiveContainer width="100%" height="100%">
                          <PieChart>
                            <Pie data={ratingData} cx="50%" cy="50%" innerRadius={40} outerRadius={60} paddingAngle={5} dataKey="value" label>
                              {ratingData.map((entry, index) => (
                                <Cell key={`cell-${index}`} fill={entry.color} />
                              ))}
                            </Pie>
                            <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px', color: '#f8fafc' }} />
                            <Legend />
                          </PieChart>
                        </ResponsiveContainer>
                      </div>
                    </CardContent>
                  </Card>

                  <Card className="print:break-inside-avoid">
                    <CardHeader>
                      <CardTitle className="text-base">สัดส่วนคลื่นความถี่ (Band)</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="h-[200px] w-full">
                        <ResponsiveContainer width="100%" height="100%">
                          <PieChart>
                            <Pie data={bandData} cx="50%" cy="50%" innerRadius={40} outerRadius={60} paddingAngle={5} dataKey="value" label>
                              {bandData.map((entry, index) => (
                                <Cell key={`cell-${index}`} fill={entry.color} />
                              ))}
                            </Pie>
                            <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px', color: '#f8fafc' }} />
                            <Legend />
                          </PieChart>
                        </ResponsiveContainer>
                      </div>
                    </CardContent>
                  </Card>
                </div>

                <Card className="lg:col-span-3 print:break-inside-avoid">
                  <CardHeader>
                    <CardTitle className="text-base">สัญญาณ (RSSI) แยกตามจุด (เรียงจากแย่ไปดี)</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="h-[400px] w-full">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={rssiData} margin={{ top: 30, right: 30, left: 0, bottom: 40 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                          <XAxis dataKey="name" stroke="#94a3b8" fontSize={12} angle={-45} textAnchor="end" height={60} interval={0} />
                          <YAxis stroke="#94a3b8" fontSize={12} domain={[-100, -30]} />
                          <Tooltip cursor={{ fill: 'rgba(255, 255, 255, 0.05)' }} contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px', color: '#f8fafc' }} />
                          <ReferenceLine y={-67} stroke="#10b981" strokeDasharray="4 4" label={{ position: 'insideTopLeft', value: 'Target (-67 dBm)', fill: '#10b981', fontSize: 12, fontWeight: 'bold' }} />
                          <ReferenceLine y={-75} stroke="#ef4444" strokeDasharray="4 4" label={{ position: 'insideBottomLeft', value: 'Poor (-75 dBm)', fill: '#ef4444', fontSize: 12, fontWeight: 'bold' }} />
                          <Bar dataKey="rssi" fill="#3b82f6" radius={[4, 4, 0, 0]} maxBarSize={50}>
                            {rssiData.map((entry, index) => (
                              <Cell key={`cell-${index}`} fill={entry.rssi < -75 ? '#ef4444' : entry.rssi < -67 ? '#f59e0b' : '#10b981'} />
                            ))}
                            <LabelList dataKey="rssi" position="top" fill="#94a3b8" fontSize={11} fontWeight="bold" />
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Throughput */}
              <Card className="print:break-inside-avoid">
                <CardHeader>
                  <CardTitle className="text-base">TCP Download vs Upload (Mbps)</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="h-[400px] w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={throughputData} margin={{ top: 30, right: 30, left: 0, bottom: 40 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                        <XAxis dataKey="name" stroke="#94a3b8" fontSize={12} angle={-45} textAnchor="end" height={60} interval={0} />
                        <YAxis stroke="#94a3b8" fontSize={12} />
                        <Tooltip cursor={{ fill: 'rgba(255, 255, 255, 0.05)' }} contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px', color: '#f8fafc' }} />
                        <Legend verticalAlign="top" height={36} />
                        <ReferenceLine y={50} stroke="#10b981" strokeDasharray="4 4" label={{ position: 'insideTopLeft', value: 'Good (50 Mbps)', fill: '#10b981', fontSize: 12 }} />
                        <Bar dataKey="Download" fill="#10b981" radius={[4, 4, 0, 0]} maxBarSize={40}>
                          <LabelList dataKey="Download" position="top" fill="#10b981" fontSize={10} fontWeight="bold" />
                        </Bar>
                        <Bar dataKey="Upload" fill="#3b82f6" radius={[4, 4, 0, 0]} maxBarSize={40}>
                          <LabelList dataKey="Upload" position="top" fill="#3b82f6" fontSize={10} fontWeight="bold" />
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>

              {/* Ping & Jitter */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <Card className="print:break-inside-avoid">
                  <CardHeader>
                    <CardTitle className="text-base">Server Ping (ms)</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="h-[350px] w-full">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={pingData} margin={{ top: 30, right: 10, left: 0, bottom: 40 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                          <XAxis dataKey="name" stroke="#94a3b8" fontSize={12} angle={-45} textAnchor="end" height={60} interval={0} />
                          <YAxis stroke="#94a3b8" fontSize={12} />
                          <Tooltip cursor={{ fill: 'rgba(255, 255, 255, 0.05)' }} contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px', color: '#f8fafc' }} />
                          <ReferenceLine y={20} stroke="#10b981" strokeDasharray="4 4" label={{ position: 'insideTopLeft', value: 'Good (< 20 ms)', fill: '#10b981', fontSize: 12 }} />
                          <Bar dataKey="ping" fill="#f59e0b" radius={[4, 4, 0, 0]} maxBarSize={40}>
                            <LabelList dataKey="ping" position="top" fill="#f59e0b" fontSize={11} fontWeight="bold" />
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </CardContent>
                </Card>

                <Card className="print:break-inside-avoid">
                  <CardHeader>
                    <CardTitle className="text-base">UDP Jitter (ms)</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="h-[350px] w-full">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={jitterData} margin={{ top: 30, right: 10, left: 0, bottom: 40 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                          <XAxis dataKey="name" stroke="#94a3b8" fontSize={12} angle={-45} textAnchor="end" height={60} interval={0} />
                          <YAxis stroke="#94a3b8" fontSize={12} />
                          <Tooltip cursor={{ fill: 'rgba(255, 255, 255, 0.05)' }} contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px', color: '#f8fafc' }} />
                          <ReferenceLine y={30} stroke="#f59e0b" strokeDasharray="4 4" label={{ position: 'insideTopLeft', value: 'Good (< 30 ms)', fill: '#f59e0b', fontSize: 12 }} />
                          <Bar dataKey="jitter" fill="#f97316" radius={[4, 4, 0, 0]} maxBarSize={40}>
                            <LabelList dataKey="jitter" position="top" fill="#f97316" fontSize={11} fontWeight="bold" />
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Packet Loss */}
              <Card className="print:break-inside-avoid">
                <CardHeader>
                  <CardTitle className="text-base">อัตราข้อมูลสูญหาย (Packet Loss %)</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="h-[350px] w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={lossData} margin={{ top: 30, right: 30, left: 0, bottom: 40 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                        <XAxis dataKey="name" stroke="#94a3b8" fontSize={12} angle={-45} textAnchor="end" height={60} interval={0} />
                        <YAxis stroke="#94a3b8" fontSize={12} />
                        <Tooltip cursor={{ fill: 'rgba(255, 255, 255, 0.05)' }} contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px', color: '#f8fafc' }} />
                        <Legend verticalAlign="top" height={36} />
                        <ReferenceLine y={1} stroke="#ef4444" strokeDasharray="4 4" label={{ position: 'insideTopLeft', value: 'Good (< 1%)', fill: '#ef4444', fontSize: 12 }} />
                        <Bar dataKey="udpLoss" name="UDP Loss (%)" fill="#ef4444" radius={[4, 4, 0, 0]} maxBarSize={40}>
                          <LabelList dataKey="udpLoss" position="top" fill="#ef4444" fontSize={11} fontWeight="bold" />
                        </Bar>
                        <Bar dataKey="pingLoss" name="Ping Loss (%)" fill="#ec4899" radius={[4, 4, 0, 0]} maxBarSize={40}>
                          <LabelList dataKey="pingLoss" position="top" fill="#ec4899" fontSize={11} fontWeight="bold" />
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>

            </>
          )}
        </main>
      </div>
    </div>
  );
}

// =====================================
// Helper Components
// =====================================
function KpiCard({ title, value, isWarning = false, highlight = false }: { title: string, value: string, isWarning?: boolean, highlight?: boolean }) {
  return (
    <Card className={`${highlight ? 'border-red-500 dark:border-red-500/50' : ''}`}>
      <CardContent className="p-4 flex flex-col justify-center items-center text-center h-full">
        <p className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-1">{title}</p>
        <p className={`text-xl font-bold ${isWarning || highlight ? 'text-red-500' : 'text-gray-900 dark:text-gray-100'}`}>
          {value}
        </p>
      </CardContent>
    </Card>
  );
}

function TraceRouteSummary({ currentTrace }: { currentTrace: any[] }) {
  const hops = [...currentTrace].sort((a, b) => Number(a.Hop) - Number(b.Hop));
  const hopCount = hops.length;
  const lastHop = hopCount > 0 ? hops[hopCount - 1] : null;
  const target = lastHop?.IP || "-";
  const destAvgRTT = lastHop?.Avg_ms || "-";
  const destLoss = lastHop?.["Loss_%"] ?? "-";

  const validHops = hops.filter(h => safeNum(h.Avg_ms) > 0);
  const worstHopAvg = validHops.length > 0 ? [...validHops].sort((a, b) => safeNum(b.Avg_ms) - safeNum(a.Avg_ms))[0] : null;

  const timeoutsCount = hops.filter(h => h.IP === "Timeout" || h.IP === "Unknown" || h.IP === "Unreachable" || safeNum(h["Loss_%"]) === 100).length;

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
      <KpiCard title="Target" value={target.toString().length > 15 ? "..." + target.toString().slice(-12) : target} />
      <KpiCard title="Hop Count" value={hopCount.toString()} />
      <KpiCard title="Dest. Avg RTT" value={destAvgRTT === "-" ? "-" : `${destAvgRTT} ms`} isWarning={safeNum(destAvgRTT) > 100} />
      <KpiCard title="Dest. Loss" value={destLoss === "-" ? "-" : `${destLoss}%`} isWarning={safeNum(destLoss) > 0} />
      <KpiCard title="Worst Hop RTT" value={worstHopAvg ? `Hop ${worstHopAvg.Hop} (${worstHopAvg.Avg_ms}ms)` : "-"} highlight={worstHopAvg !== null && safeNum(worstHopAvg.Avg_ms) > 100} />
      <KpiCard title="Timeouts" value={timeoutsCount.toString()} isWarning={timeoutsCount > 0} />
    </div>
  );
}

function getHopStatus(hop: any) {
  const isTimeout = hop.IP === "Timeout" || hop.IP === "Unknown" || hop.IP === "Unreachable";
  const loss = hop["Loss_%"] !== null && hop["Loss_%"] !== "" && hop["Loss_%"] !== undefined ? Number(hop["Loss_%"]) : null;
  const isICMPBlocked = !isTimeout && loss === 100;
  const avg = safeNum(hop.Avg_ms);

  if (isTimeout) return { label: "Timeout", color: "bg-red-500 border-red-100 dark:border-red-900", textColor: "text-red-500" };
  if (isICMPBlocked) return { label: "No ICMP Reply", color: "bg-gray-400 border-gray-200 dark:border-gray-700", textColor: "text-gray-500" };
  if (loss !== null && loss > 0) return { label: "Partial Loss", color: "bg-orange-500 border-orange-100 dark:border-orange-900", textColor: "text-orange-500" };
  if (avg > 100) return { label: "High Latency", color: "bg-yellow-500 border-yellow-100 dark:border-yellow-900", textColor: "text-yellow-600 dark:text-yellow-500" };
  return { label: "OK", color: "bg-emerald-500 border-emerald-100 dark:border-emerald-900", textColor: "text-emerald-500" };
}

function TraceRouteTimeline({ data }: { data: any[] }) {
  const hops = [...data].sort((a, b) => Number(a.Hop) - Number(b.Hop));

  return (
    <div className="flex flex-col space-y-0 py-2 pl-2 relative max-w-3xl mx-auto">
      <div className="absolute top-6 bottom-6 left-[27px] w-0.5 bg-gray-200 dark:bg-gray-700 z-0"></div>

      {hops.map((hop, i) => {
        const status = getHopStatus(hop);
        const avg = hop.Avg_ms || "-";
        const max = hop.Max_ms || "-";

        return (
          <div key={i} className="flex items-start z-10 relative group pb-4 last:pb-0">
            <div className="w-14 flex-shrink-0 text-right pr-4 pt-2.5">
              <span className="text-xs font-bold text-gray-400 dark:text-gray-500">Hop {hop.Hop}</span>
            </div>

            <div className="flex flex-col items-center mr-4 pt-2.5">
              <div className={`w-3.5 h-3.5 rounded-full ring-4 ${status.color} shadow-sm z-10`}></div>
            </div>

            <div className="flex-1 bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700 rounded-xl p-3 shadow-sm hover:shadow-md transition-all group-hover:border-indigo-200 dark:group-hover:border-indigo-800">
              <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-2">
                <div>
                  <h4 className={`font-mono text-sm font-semibold ${status.label === "Timeout" ? 'text-red-500' : 'text-gray-800 dark:text-gray-200'}`}>
                    {hop.IP}
                  </h4>
                  <div className={`text-xs font-semibold ${status.textColor}`}>{status.label}</div>
                  {hop.Hostname && <div className="text-[10px] text-gray-400 truncate max-w-[200px]" title={hop.Hostname}>{hop.Hostname}</div>}
                </div>

                {status.label !== "Timeout" && status.label !== "No ICMP Reply" && (
                  <div className="flex gap-4 text-xs">
                    <div className="flex flex-col sm:items-end">
                      <span className="text-gray-400 text-[10px] uppercase tracking-wider">Avg</span>
                      <span className="font-medium text-gray-700 dark:text-gray-300">{avg} ms</span>
                    </div>
                    <div className="flex flex-col sm:items-end hidden sm:flex">
                      <span className="text-gray-400 text-[10px] uppercase tracking-wider">Max</span>
                      <span className="font-medium text-gray-500 dark:text-gray-400">{max} ms</span>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function TraceRouteLatencyChart({ data }: { data: any[] }) {
  const chartData = data
    .filter(h => h.Avg_ms && h.IP !== "Timeout" && h.IP !== "Unknown")
    .map(h => ({
      hop: `Hop ${h.Hop}`,
      Avg: safeNum(h.Avg_ms),
      Min: safeNum(h.Min_ms),
      Max: safeNum(h.Max_ms)
    }));

  if (chartData.length === 0) return <div className="flex justify-center items-center h-full text-gray-400 text-sm">No valid latency data to display.</div>;

  return (
    <ResponsiveContainer width="100%" height="100%">
      <ComposedChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
        <XAxis dataKey="hop" stroke="#94a3b8" fontSize={11} />
        <YAxis stroke="#94a3b8" fontSize={11} />
        <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px', color: '#f8fafc' }} />
        <Legend />
        <Bar dataKey="Avg" fill="#6366f1" radius={[4, 4, 0, 0]} maxBarSize={40} />
        <Line type="monotone" dataKey="Max" stroke="#f43f5e" strokeWidth={2} dot={{ r: 3, fill: '#f43f5e' }} />
        <Line type="monotone" dataKey="Min" stroke="#10b981" strokeWidth={2} dot={{ r: 3, fill: '#10b981' }} />
      </ComposedChart>
    </ResponsiveContainer>
  );
}

function TraceRouteLossChart({ data }: { data: any[] }) {
  const chartData = data
    .filter(h => h.IP !== "Timeout" && h.IP !== "Unknown" && h.IP !== "Unreachable")
    .map(h => {
      const loss = h["Loss_%"] !== null && h["Loss_%"] !== "" ? Number(h["Loss_%"]) : 0;
      return {
        hop: `Hop ${h.Hop}`,
        loss: loss
      };
    });

  if (chartData.length === 0) return <div className="flex justify-center items-center h-full text-gray-400 text-sm">No packet loss data available.</div>;

  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
        <XAxis dataKey="hop" stroke="#94a3b8" fontSize={11} />
        <YAxis stroke="#94a3b8" fontSize={11} domain={[0, 100]} />
        <Tooltip cursor={{ fill: 'rgba(255, 255, 255, 0.05)' }} contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px', color: '#f8fafc' }} />
        <Bar dataKey="loss" name="Packet Loss (%)" fill="#f97316" radius={[4, 4, 0, 0]} maxBarSize={40}>
          <LabelList dataKey="loss" position="top" fill="#f97316" fontSize={10} formatter={(v: any) => Number(v) > 0 ? `${v}%` : ''} />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

function TraceRouteTable({ data }: { data: any[] }) {
  const hops = [...data].sort((a, b) => Number(a.Hop) - Number(b.Hop));

  return (
    <table className="w-full text-sm text-left whitespace-nowrap">
      <thead className="text-xs text-gray-500 bg-gray-50 dark:bg-gray-900/80 dark:text-gray-400 uppercase border-b dark:border-gray-800">
        <tr>
          <th className="px-4 py-3">Hop</th>
          <th className="px-4 py-3">IP Address</th>
          <th className="px-4 py-3">Hostname</th>
          <th className="px-4 py-3">Status</th>
          <th className="px-4 py-3">RTT1</th>
          <th className="px-4 py-3">RTT2</th>
          <th className="px-4 py-3">RTT3</th>
          <th className="px-4 py-3">Min</th>
          <th className="px-4 py-3">Max</th>
          <th className="px-4 py-3">Avg</th>
          <th className="px-4 py-3">Loss</th>
        </tr>
      </thead>
      <tbody>
        {hops.map((hop, i) => {
          const status = getHopStatus(hop);
          const loss = hop["Loss_%"] !== null && hop["Loss_%"] !== "" && hop["Loss_%"] !== undefined ? `${hop["Loss_%"]}%` : "-";

          return (
            <tr key={i} className="border-b dark:border-gray-800 hover:bg-gray-50/50 dark:hover:bg-gray-800/50">
              <td className="px-4 py-3 font-medium text-gray-900 dark:text-gray-100">{hop.Hop}</td>
              <td className="px-4 py-3 font-mono text-xs">{hop.IP}</td>
              <td className="px-4 py-3 text-xs text-gray-500 truncate max-w-[150px]" title={hop.Hostname}>{hop.Hostname || "-"}</td>
              <td className="px-4 py-3">
                <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-gray-100 dark:bg-gray-800 ${status.textColor}`}>
                  {status.label}
                </span>
              </td>
              <td className="px-4 py-3 text-gray-500 text-xs">{hop.RTT1 || "*"}</td>
              <td className="px-4 py-3 text-gray-500 text-xs">{hop.RTT2 || "*"}</td>
              <td className="px-4 py-3 text-gray-500 text-xs">{hop.RTT3 || "*"}</td>
              <td className="px-4 py-3">{hop.Min_ms || "-"}</td>
              <td className="px-4 py-3">{hop.Max_ms || "-"}</td>
              <td className="px-4 py-3 font-medium">{hop.Avg_ms || "-"}</td>
              <td className={`px-4 py-3 ${loss !== "-" && loss !== "0%" ? "text-red-500 font-medium" : ""}`}>{loss}</td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
