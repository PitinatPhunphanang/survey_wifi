"use client";

import React, { useState } from "react";
import Link from "next/link";
import * as XLSX from "xlsx";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ArrowLeft, FileUp, Printer, LayoutDashboard, Activity, Map } from "lucide-react";
import { SurveyEntry, DEFAULT_THRESHOLDS } from "@/types";
import { evaluateEntry } from "@/lib/evaluation";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
  LabelList,
  ReferenceLine,
  ComposedChart,
  Line
} from "recharts";

// Helper
const safeNum = (val: any) => (isNaN(Number(val)) || val === "" || val === null ? 0 : Number(val));

export default function FloorReport() {
  const [floorData, setFloorData] = useState<Record<string, SurveyEntry[]>>({});
  const [traceData, setTraceData] = useState<any[]>([]);
  const [sheetNames, setSheetNames] = useState<string[]>([]);
  const [selectedSheet, setSelectedSheet] = useState<string>("");
  const [selectedTraceRoom, setSelectedTraceRoom] = useState<string>("");
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  const entries = floorData[selectedSheet] || [];
  const floorName = entries.length > 0 ? `${entries[0].building} - Floor ${selectedSheet}` : "";

  const handleImportExcel = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (evt) => {
      try {
        const bstr = evt.target?.result;
        const wb = XLSX.read(bstr, { type: "array" });
        const groupedByFloor: Record<string, SurveyEntry[]> = {};
        let rawTraces: any[] = [];

        wb.SheetNames.forEach(wsname => {
          const ws = wb.Sheets[wsname];
          const data = XLSX.utils.sheet_to_json(ws);
          
          if (wsname === "TraceRoute") {
            rawTraces = data;
            return;
          }
          
          if (data.length > 0) {
            data.forEach((row: any, idx) => {
              const floorVal = row["Floor"]?.toString() || wsname;
              if (!groupedByFloor[floorVal]) {
                groupedByFloor[floorVal] = [];
              }
              
              groupedByFloor[floorVal].push({
                id: `row-${wsname}-${idx}`,
                createdAt: Date.now(),
                timestamp: row["Timestamp"] || "",
                building: row["Building"] || "",
                floor: floorVal,
                room: row["Room_Point"]?.toString() || `Point ${idx+1}`,
                note: row["Note"] || "",
                ssid: row["SSID"] || "",
                bssid: row["BSSID"] || "",
                band: row["Band"] || "",
                radioType: row["Radio_Type"] || "",
                channel: row["Channel"] || "",
                signalPercent: row["Signal_%"] !== undefined ? row["Signal_%"] : "",
                rssi: row["RSSI_dBm"] !== undefined ? row["RSSI_dBm"] : "",
                rxRate: row["Receive_Rate_Mbps"] || "",
                txRate: row["Transmit_Rate_Mbps"] || "",
                gatewayIp: row["Gateway_IP"] || "",
                pingGatewayMs: row["Ping_Gateway_ms"] !== undefined ? row["Ping_Gateway_ms"] : "",
                pingGatewayLoss: row["Ping_Gateway_Loss_%"] !== undefined ? row["Ping_Gateway_Loss_%"] : "",
                pingServerMs: row["Ping_Server_ms"] !== undefined ? row["Ping_Server_ms"] : "",
                pingLoss: row["Ping_Server_Loss_%"] !== undefined ? row["Ping_Server_Loss_%"] : "",
                tcpUpload: row["TCP_Upload_Mbps"] !== undefined ? row["TCP_Upload_Mbps"] : "",
                tcpDownload: row["TCP_Download_Mbps"] !== undefined ? row["TCP_Download_Mbps"] : "",
                udpTarget: row["UDP_Target_Bandwidth"] || "",
                udpActual: row["UDP_Actual_Mbps"] !== undefined ? row["UDP_Actual_Mbps"] : "",
                udpJitter: row["UDP_Jitter_ms"] !== undefined ? row["UDP_Jitter_ms"] : "",
                udpLoss: row["UDP_PacketLoss_%"] !== undefined ? row["UDP_PacketLoss_%"] : "",
              });
            });
          }
        });

        setFloorData(groupedByFloor);
        setTraceData(rawTraces);
        const validFloors = Object.keys(groupedByFloor).sort((a, b) => a.localeCompare(b, undefined, { numeric: true }));
        setSheetNames(validFloors);
        
        if (validFloors.length > 0) {
          setSelectedSheet(validFloors[0]);
          if (groupedByFloor[validFloors[0]]?.length > 0) {
            setSelectedTraceRoom(groupedByFloor[validFloors[0]][0].room);
          }
        } else {
          alert("No valid data found in Excel sheets.");
        }
      } catch (err) {
        console.error("Error reading Excel", err);
        alert("ไม่สามารถอ่านไฟล์ Excel ได้");
      }
      if (fileInputRef.current) fileInputRef.current.value = "";
    };
    reader.readAsArrayBuffer(file);
  };

  // KPI Calculations
  const count = entries.length;
  const avgRssi = count > 0 ? entries.reduce((acc, curr) => acc + safeNum(curr.rssi), 0) / count : 0;
  const avgTcpDown = count > 0 ? entries.reduce((acc, curr) => acc + safeNum(curr.tcpDownload), 0) / count : 0;
  const avgTcpUp = count > 0 ? entries.reduce((acc, curr) => acc + safeNum(curr.tcpUpload), 0) / count : 0;
  const avgPing = count > 0 ? entries.reduce((acc, curr) => acc + safeNum(curr.pingServerMs), 0) / count : 0;
  const avgJitter = count > 0 ? entries.reduce((acc, curr) => acc + safeNum(curr.udpJitter), 0) / count : 0;
  const avgLoss = count > 0 ? entries.reduce((acc, curr) => acc + safeNum(curr.udpLoss), 0) / count : 0;

  const evaluated = entries.map(e => ({ ...e, report: evaluateEntry(e, DEFAULT_THRESHOLDS) }));
  const poorCount = evaluated.filter(e => e.report.overallRating === "POOR").length;

  // Rating Chart Data
  const ratingData = [
    { name: "GOOD", value: evaluated.filter(e => e.report.overallRating === "GOOD").length, color: "#10b981" },
    { name: "FAIR", value: evaluated.filter(e => e.report.overallRating === "FAIR").length, color: "#f59e0b" },
    { name: "POOR", value: poorCount, color: "#ef4444" }
  ].filter(d => d.value > 0);

  // RSSI Sorted
  const rssiData = [...entries]
    .map(e => ({ name: e.room, rssi: safeNum(e.rssi) }))
    .sort((a, b) => a.rssi - b.rssi); // Worst (lowest) to best (highest) - note: -80 is less than -50

  const throughputData = entries.map(e => ({
    name: e.room,
    Download: safeNum(e.tcpDownload),
    Upload: safeNum(e.tcpUpload)
  }));

  const pingData = entries.map(e => ({ name: e.room, ping: safeNum(e.pingServerMs) }));
  const jitterData = entries.map(e => ({ name: e.room, jitter: safeNum(e.udpJitter) }));
  const lossData = entries.map(e => ({ 
    name: e.room, 
    udpLoss: safeNum(e.udpLoss), 
    pingLoss: safeNum(e.pingLoss) 
  }));

  // Band Data
  const bandCounts = entries.reduce((acc, curr) => {
    const band = curr.band ? curr.band.toUpperCase() : "UNKNOWN";
    if (!acc[band]) acc[band] = 0;
    acc[band]++;
    return acc;
  }, {} as Record<string, number>);
  
  const bandData = Object.keys(bandCounts).map((key, i) => ({
    name: key,
    value: bandCounts[key],
    color: ['#8b5cf6', '#ec4899', '#06b6d4', '#f59e0b'][i % 4]
  }));

  // Worst Points Analysis
  const sortedRssi = [...entries].sort((a, b) => safeNum(a.rssi) - safeNum(b.rssi));
  const worstRssi = sortedRssi.slice(0, 3).map(e => ({ room: e.room, val: e.rssi }));
  const worstPing = [...entries].sort((a, b) => safeNum(b.pingServerMs) - safeNum(a.pingServerMs))[0];
  const worstJitter = [...entries].sort((a, b) => safeNum(b.udpJitter) - safeNum(a.udpJitter))[0];
  const worstLoss = [...entries].sort((a, b) => Math.max(safeNum(b.udpLoss), safeNum(b.pingLoss)) - Math.max(safeNum(a.udpLoss), safeNum(a.pingLoss)))[0];

  // Auto Summary Generation
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

  // Filter traceroute data for selected room
  const currentTrace = traceData.filter(
    t => t.Floor?.toString() === selectedSheet && t.Room_Point?.toString() === selectedTraceRoom
  );

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 text-gray-900 dark:text-gray-100 font-sans pb-8">
      
      {/* Top Navbar / Tabbar */}
      <header className="sticky top-0 z-50 w-full bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 shadow-sm px-4 md:px-8 py-3 print:hidden">
        <div className="max-w-7xl mx-auto flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-sm">W</span>
              </div>
              <h1 className="text-lg font-bold tracking-tight hidden sm:block">Wi-Fi Survey Pro</h1>
            </div>
            
            {/* Tab Navigation */}
            <nav className="flex items-center gap-1 bg-gray-100 dark:bg-gray-800 p-1 rounded-lg">
              <Link href="/" className="px-3 py-1.5 text-sm font-medium text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 transition-all">Dashboard</Link>
              <Link href="/report" className="px-3 py-1.5 text-sm font-medium bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm rounded-md transition-all">Floor Report</Link>
              <Link href="/reference" className="px-3 py-1.5 text-sm font-medium text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 transition-all">Guide</Link>
            </nav>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {sheetNames.length > 1 && (
              <select 
                className="h-9 rounded-md border border-gray-200 bg-transparent px-3 py-1 text-sm dark:border-gray-600 dark:bg-gray-900 focus:outline-none"
                value={selectedSheet}
                onChange={(e) => {
                  setSelectedSheet(e.target.value);
                  const newFloorEntries = floorData[e.target.value] || [];
                  if (newFloorEntries.length > 0) {
                    setSelectedTraceRoom(newFloorEntries[0].room);
                  } else {
                    setSelectedTraceRoom("");
                  }
                }}
              >
                {sheetNames.map(name => (
                  <option key={name} value={name}>Floor: {name}</option>
                ))}
              </select>
            )}
            <Button onClick={() => fileInputRef.current?.click()} variant="outline" size="sm">
              <FileUp className="w-4 h-4 mr-2"/> Import Floor Excel
            </Button>
            <input type="file" ref={fileInputRef} onChange={handleImportExcel} accept=".xlsx,.xls,.csv" className="hidden" />
            <Button onClick={() => window.print()} variant="outline" size="sm">
              <Printer className="w-4 h-4 mr-2"/> Print
            </Button>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 md:px-8 mt-8 space-y-8">
        {entries.length === 0 ? (
          <div className="flex flex-col items-center justify-center p-20 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl border-dashed">
            <LayoutDashboard className="w-16 h-16 text-gray-300 dark:text-gray-600 mb-4" />
            <h2 className="text-xl font-semibold text-gray-500 dark:text-gray-400">No Data Loaded</h2>
            <p className="text-sm text-gray-400 dark:text-gray-500 mt-2">Click "Import Floor Excel" to generate the report.</p>
          </div>
        ) : (
          <div className="space-y-8">
            <div className="text-center print:block hidden mb-8">
              <h1 className="text-3xl font-bold">Wi-Fi Survey Floor Report</h1>
              <h2 className="text-xl text-gray-500 mt-2">{floorName}</h2>
            </div>

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
                  <CardTitle className="text-base text-blue-800 dark:text-blue-300">Auto Summary / Remarks</CardTitle>
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
                  <CardTitle className="text-base text-red-600 dark:text-red-400">Critical Points Action List</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3 text-sm">
                    <div className="flex justify-between items-center border-b border-gray-100 dark:border-gray-800 pb-1">
                      <span className="text-gray-500">Worst RSSI:</span>
                      <span className="font-semibold text-red-500">{worstRssi.map(r => r.room).join(', ')}</span>
                    </div>
                    <div className="flex justify-between items-center border-b border-gray-100 dark:border-gray-800 pb-1">
                      <span className="text-gray-500">Max Ping:</span>
                      <span className="font-medium">{worstPing?.room} ({safeNum(worstPing?.pingServerMs)}ms)</span>
                    </div>
                    <div className="flex justify-between items-center border-b border-gray-100 dark:border-gray-800 pb-1">
                      <span className="text-gray-500">Max Jitter:</span>
                      <span className="font-medium">{worstJitter?.room} ({safeNum(worstJitter?.udpJitter)}ms)</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-gray-500">Max Loss:</span>
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
                      Route Analysis
                    </h2>
                    <p className="text-gray-500 text-sm mt-1">Detailed hop-by-hop path diagnostics.</p>
                  </div>
                  <div className="flex items-center gap-2 bg-white dark:bg-gray-800 p-2 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm">
                    <span className="text-sm font-medium text-gray-600 dark:text-gray-300">Select Point:</span>
                    <select 
                      className="h-8 rounded-md border border-gray-200 bg-gray-50 dark:bg-gray-900 px-3 py-1 text-sm focus:ring-2 focus:ring-indigo-500 dark:border-gray-600 focus:outline-none"
                      value={selectedTraceRoom}
                      onChange={(e) => setSelectedTraceRoom(e.target.value)}
                    >
                      <option value="">-- Select --</option>
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
                            <CardTitle className="text-base">Hop Status Timeline</CardTitle>
                          </CardHeader>
                          <CardContent className="pt-4 overflow-y-auto max-h-[700px]">
                            <TraceRouteTimeline data={currentTrace} />
                          </CardContent>
                      </Card>

                      <div className="space-y-6 flex flex-col">
                          <Card className="shadow-sm border-gray-200 dark:border-gray-800 flex-1">
                            <CardHeader className="bg-gray-50/50 dark:bg-gray-900/50 border-b border-gray-100 dark:border-gray-800 pb-3">
                              <CardTitle className="text-base">Per-Hop Latency Range (ms)</CardTitle>
                            </CardHeader>
                            <CardContent className="pt-4 h-[300px]">
                              <TraceRouteLatencyChart data={currentTrace} />
                            </CardContent>
                          </Card>

                          <Card className="shadow-sm border-gray-200 dark:border-gray-800 flex-1">
                            <CardHeader className="bg-gray-50/50 dark:bg-gray-900/50 border-b border-gray-100 dark:border-gray-800 pb-3">
                              <CardTitle className="text-base">Packet Loss by Hop (%)</CardTitle>
                              <p className="text-xs text-gray-500 mt-1">Intermediate hop loss does not always indicate end-to-end loss.</p>
                            </CardHeader>
                            <CardContent className="pt-4 h-[250px]">
                              <TraceRouteLossChart data={currentTrace} />
                            </CardContent>
                          </Card>
                      </div>
                    </div>

                    <Card className="shadow-sm border-gray-200 dark:border-gray-800 overflow-hidden">
                      <CardHeader className="bg-gray-50/50 dark:bg-gray-900/50 border-b border-gray-100 dark:border-gray-800 pb-3">
                        <CardTitle className="text-base">Raw Hop Data</CardTitle>
                      </CardHeader>
                      <div className="overflow-x-auto">
                        <TraceRouteTable data={currentTrace} />
                      </div>
                    </Card>
                  </>
                ) : (
                  <div className="p-8 text-center bg-white dark:bg-gray-900 rounded-xl border border-dashed border-gray-300 dark:border-gray-700">
                    <Map className="w-10 h-10 mx-auto text-gray-300 dark:text-gray-600 mb-3" />
                    <p className="text-gray-500">No traceroute data available for point "{selectedTraceRoom}".</p>
                  </div>
                )}
              </div>
            )}

            <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
              {/* Left Column: Rating & Band */}
              <div className="lg:col-span-1 space-y-6">
                <Card className="print:break-inside-avoid">
                  <CardHeader>
                    <CardTitle className="text-base">Rating Distribution</CardTitle>
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
                    <CardTitle className="text-base">Band Distribution</CardTitle>
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

              {/* Right Column: RSSI */}
              <Card className="lg:col-span-3 print:break-inside-avoid">
                <CardHeader>
                  <CardTitle className="text-base">RSSI by Room (Sorted Worst to Best)</CardTitle>
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
                      <Legend verticalAlign="top" height={36}/>
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
                <CardTitle className="text-base">Packet Loss (%)</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-[350px] w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={lossData} margin={{ top: 30, right: 30, left: 0, bottom: 40 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                      <XAxis dataKey="name" stroke="#94a3b8" fontSize={12} angle={-45} textAnchor="end" height={60} interval={0} />
                      <YAxis stroke="#94a3b8" fontSize={12} />
                      <Tooltip cursor={{ fill: 'rgba(255, 255, 255, 0.05)' }} contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px', color: '#f8fafc' }} />
                      <Legend verticalAlign="top" height={36}/>
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

          </div>
        )}
      </div>
    </div>
  );
}

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
  
  // Timeout/Unreachable
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
