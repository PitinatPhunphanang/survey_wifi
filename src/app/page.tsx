"use client";

import React, { useState, useEffect, useMemo } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { SurveyEntry, DEFAULT_THRESHOLDS, Thresholds } from "@/types";
import { evaluateEntry } from "@/lib/evaluation";
import { saveEntry, getHistory, deleteEntry, generateId } from "@/lib/storage";
import { exportToJson, exportHistoryToCsv, printReport } from "@/lib/export";
import { MetricCard } from "@/components/dashboard/MetricCard";
import { ReportSummary } from "@/components/dashboard/ReportSummary";
import { VisualCharts } from "@/components/dashboard/VisualCharts";
import { Save, Plus, Download, Printer, History, FileJson, Beaker, BookOpen, FileUp, LayoutDashboard } from "lucide-react";
import Link from "next/link";
import * as XLSX from "xlsx";

export default function Dashboard() {
  const [entry, setEntry] = useState<SurveyEntry>(getEmptyEntry());
  const [thresholds, setThresholds] = useState<Thresholds>(DEFAULT_THRESHOLDS);
  const [history, setHistory] = useState<SurveyEntry[]>([]);
  const [isClient, setIsClient] = useState(false);
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  useEffect(() => {
    setIsClient(true);
    setHistory(getHistory());
  }, []);

  const report = useMemo(() => {
    return evaluateEntry(entry, thresholds);
  }, [entry, thresholds]);

  const handleInputChange = (field: keyof SurveyEntry, value: any) => {
    setEntry((prev) => ({ ...prev, [field]: value }));
  };

  const handleSave = () => {
    const entryToSave = { ...entry, id: entry.id || generateId(), createdAt: Date.now() };
    saveEntry(entryToSave);
    setEntry(entryToSave); // Update current ID
    setHistory(getHistory());
  };

  const handleNew = () => {
    setEntry(getEmptyEntry());
  };

  const handleImportExcel = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (evt) => {
      try {
        const bstr = evt.target?.result;
        const wb = XLSX.read(bstr, { type: "array" });
        const wsname = wb.SheetNames[0];
        const ws = wb.Sheets[wsname];
        const data = XLSX.utils.sheet_to_json(ws);
        
        if (data.length > 0) {
          // Get the very last row which is the latest test
          const row: any = data[data.length - 1];
          
          setEntry({
            id: generateId(),
            createdAt: Date.now(),
            timestamp: row["Timestamp"] || new Date().toISOString(),
            building: row["Building"] || "",
            floor: row["Floor"]?.toString() || "",
            room: row["Room_Point"]?.toString() || "",
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
        }
      } catch (err) {
        console.error("Error reading Excel", err);
        alert("ไม่สามารถอ่านไฟล์ Excel ได้");
      }
      if (fileInputRef.current) fileInputRef.current.value = "";
    };
    reader.readAsArrayBuffer(file);
  };

  const loadSampleData = () => {
    setEntry({
      id: generateId(),
      createdAt: Date.now(),
      timestamp: new Date().toISOString(),
      building: "Headquarters",
      floor: "3",
      room: "Conference Room A",
      note: "Sample survey data",
      ssid: "Corp-WiFi",
      bssid: "00:11:22:33:44:55",
      band: "5 GHz",
      radioType: "802.11ax",
      channel: 36,
      signalPercent: 85,
      rssi: -62,
      rxRate: 866,
      txRate: 866,
      gatewayIp: "10.0.0.1",
      pingGatewayMs: 4,
      pingGatewayLoss: 0,
      pingServerMs: 15,
      pingLoss: 0,
      tcpUpload: 85,
      tcpDownload: 120,
      udpTarget: 10,
      udpActual: 10,
      udpJitter: 12,
      udpLoss: 0,
    });
  };

  if (!isClient) return null; // Avoid hydration mismatch

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
              <Link href="/" className="px-3 py-1.5 text-sm font-medium bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm rounded-md transition-all">Dashboard</Link>
              <Link href="/report" className="px-3 py-1.5 text-sm font-medium text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 transition-all">Floor Report</Link>
              <Link href="/reference" className="px-3 py-1.5 text-sm font-medium text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 transition-all">Guide</Link>
            </nav>
          </div>

          {/* Action Buttons */}
          <div className="flex flex-wrap items-center gap-2">
            <Button onClick={handleNew} variant="outline" size="sm"><Plus className="w-4 h-4 mr-2"/> New</Button>
            <Button onClick={() => fileInputRef.current?.click()} variant="outline" size="sm"><FileUp className="w-4 h-4 mr-2"/> Import</Button>
            <input type="file" ref={fileInputRef} onChange={handleImportExcel} accept=".xlsx,.xls,.csv" className="hidden" />
            <Button onClick={handleSave} size="sm"><Save className="w-4 h-4 mr-2"/> Save</Button>
            <Button onClick={() => exportHistoryToCsv(history)} variant="secondary" size="sm"><Download className="w-4 h-4 mr-2"/> CSV</Button>
            <Button onClick={printReport} variant="outline" size="sm"><Printer className="w-4 h-4 mr-2"/> Print</Button>
            <Button onClick={loadSampleData} variant="outline" size="sm" className="hidden sm:flex"><Beaker className="w-4 h-4 mr-2"/> Sample</Button>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 md:px-8 mt-8 space-y-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          
          {/* Left Column: Form */}
          <div className="lg:col-span-5 space-y-6">
            <Card>
              <CardHeader className="bg-gray-50/50 dark:bg-gray-900/50 border-b">
                <CardTitle className="text-lg">Survey Input</CardTitle>
              </CardHeader>
              <CardContent className="p-6 space-y-8">
                
                {/* A) Location */}
                <section className="space-y-4">
                  <h3 className="font-semibold text-sm text-blue-600 dark:text-blue-400 uppercase tracking-wider">A) Location Info</h3>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-1"><Label>Building</Label><Input value={entry.building} onChange={(e) => handleInputChange("building", e.target.value)} /></div>
                    <div className="space-y-1"><Label>Floor</Label><Input value={entry.floor} onChange={(e) => handleInputChange("floor", e.target.value)} /></div>
                    <div className="space-y-1"><Label>Room/Point</Label><Input value={entry.room} onChange={(e) => handleInputChange("room", e.target.value)} /></div>
                    <div className="space-y-1"><Label>Note</Label><Input value={entry.note} onChange={(e) => handleInputChange("note", e.target.value)} /></div>
                  </div>
                </section>

                {/* B) Wi-Fi */}
                <section className="space-y-4">
                  <h3 className="font-semibold text-sm text-blue-600 dark:text-blue-400 uppercase tracking-wider">B) Wi-Fi Info</h3>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-1"><Label>SSID</Label><Input value={entry.ssid} onChange={(e) => handleInputChange("ssid", e.target.value)} /></div>
                    <div className="space-y-1"><Label>BSSID</Label><Input value={entry.bssid} onChange={(e) => handleInputChange("bssid", e.target.value)} /></div>
                    <div className="space-y-1">
                      <Label>Band</Label>
                      <select className="flex h-9 w-full rounded-md border border-gray-200 bg-transparent px-3 py-1 text-sm shadow-sm dark:border-gray-600 dark:bg-gray-900" value={entry.band} onChange={(e) => handleInputChange("band", e.target.value as any)}>
                        <option value="">Select...</option>
                        <option value="2.4 GHz">2.4 GHz</option>
                        <option value="5 GHz">5 GHz</option>
                        <option value="6 GHz">6 GHz</option>
                      </select>
                    </div>
                    <div className="space-y-1"><Label>Channel</Label><Input type="number" value={entry.channel} onChange={(e) => handleInputChange("channel", e.target.value)} /></div>
                    <div className="space-y-1"><Label>Signal %</Label><Input type="number" value={entry.signalPercent} onChange={(e) => handleInputChange("signalPercent", e.target.value)} /></div>
                    <div className="space-y-1"><Label>RSSI (dBm)</Label><Input type="number" value={entry.rssi} onChange={(e) => handleInputChange("rssi", e.target.value)} /></div>
                    <div className="space-y-1"><Label>Rx Rate (Mbps)</Label><Input type="number" value={entry.rxRate} onChange={(e) => handleInputChange("rxRate", e.target.value)} /></div>
                    <div className="space-y-1"><Label>Tx Rate (Mbps)</Label><Input type="number" value={entry.txRate} onChange={(e) => handleInputChange("txRate", e.target.value)} /></div>
                  </div>
                </section>

                {/* C) Gateway / Server */}
                <section className="space-y-4">
                  <h3 className="font-semibold text-sm text-blue-600 dark:text-blue-400 uppercase tracking-wider">C) Gateway / Server</h3>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-1 col-span-2"><Label>Gateway IP</Label><Input value={entry.gatewayIp} onChange={(e) => handleInputChange("gatewayIp", e.target.value)} /></div>
                    <div className="space-y-1"><Label>Ping GW (ms)</Label><Input type="number" value={entry.pingGatewayMs} onChange={(e) => handleInputChange("pingGatewayMs", e.target.value)} /></div>
                    <div className="space-y-1"><Label>Ping GW Loss (%)</Label><Input type="number" step="0.1" value={entry.pingGatewayLoss} onChange={(e) => handleInputChange("pingGatewayLoss", e.target.value)} /></div>
                    <div className="space-y-1"><Label>Ping Server (ms)</Label><Input type="number" value={entry.pingServerMs} onChange={(e) => handleInputChange("pingServerMs", e.target.value)} /></div>
                    <div className="space-y-1"><Label>Ping Srv Loss (%)</Label><Input type="number" step="0.1" value={entry.pingLoss} onChange={(e) => handleInputChange("pingLoss", e.target.value)} /></div>
                  </div>
                </section>

                {/* D) Throughput */}
                <section className="space-y-4">
                  <h3 className="font-semibold text-sm text-blue-600 dark:text-blue-400 uppercase tracking-wider">D) Throughput / Quality</h3>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-1"><Label>TCP Up (Mbps)</Label><Input type="number" value={entry.tcpUpload} onChange={(e) => handleInputChange("tcpUpload", e.target.value)} /></div>
                    <div className="space-y-1"><Label>TCP Down (Mbps)</Label><Input type="number" value={entry.tcpDownload} onChange={(e) => handleInputChange("tcpDownload", e.target.value)} /></div>
                    <div className="space-y-1"><Label>UDP Target (Mbps)</Label><Input type="number" value={entry.udpTarget} onChange={(e) => handleInputChange("udpTarget", e.target.value)} /></div>
                    <div className="space-y-1"><Label>UDP Actual (Mbps)</Label><Input type="number" value={entry.udpActual} onChange={(e) => handleInputChange("udpActual", e.target.value)} /></div>
                    <div className="space-y-1"><Label>UDP Jitter (ms)</Label><Input type="number" step="0.1" value={entry.udpJitter} onChange={(e) => handleInputChange("udpJitter", e.target.value)} /></div>
                    <div className="space-y-1"><Label>UDP Loss (%)</Label><Input type="number" step="0.1" value={entry.udpLoss} onChange={(e) => handleInputChange("udpLoss", e.target.value)} /></div>
                  </div>
                </section>

              </CardContent>
            </Card>
          </div>

          {/* Right Column: Dashboard & Evaluation */}
          <div className="lg:col-span-7 space-y-6 print:block">
            <ReportSummary report={report} />
            
            <VisualCharts entry={entry} />

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <MetricCard title="RSSI" value={entry.rssi} unit="dBm" evaluation={report.evaluations.rssi} />
              <MetricCard title="TCP Upload" value={entry.tcpUpload} unit="Mbps" evaluation={report.evaluations.tcpUpload} />
              <MetricCard title="TCP Download" value={entry.tcpDownload} unit="Mbps" evaluation={report.evaluations.tcpDownload} />
              <MetricCard title="Ping Server" value={entry.pingServerMs} unit="ms" evaluation={report.evaluations.pingServer} />
              <MetricCard title="UDP Jitter" value={entry.udpJitter} unit="ms" evaluation={report.evaluations.udpJitter} />
              <MetricCard title="UDP Packet Loss" value={entry.udpLoss} unit="%" evaluation={report.evaluations.udpLoss} />
              <MetricCard title="Signal" value={entry.signalPercent} unit="%" evaluation={report.evaluations.signalPercent} />
              <MetricCard title="Ping Gateway" value={entry.pingGatewayMs} unit="ms" evaluation={report.evaluations.pingGateway} />
              <MetricCard title="Band" value={entry.band || null} evaluation={report.evaluations.band} />
            </div>

            {/* History Table */}
            {history.length > 0 && (
              <Card className="print:hidden">
                <CardHeader>
                  <CardTitle className="flex items-center text-base"><History className="w-4 h-4 mr-2"/> Recent Entries</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm text-left">
                      <thead className="text-xs text-gray-500 bg-gray-50 dark:bg-gray-800 dark:text-gray-400">
                        <tr>
                          <th className="px-4 py-2">Location</th>
                          <th className="px-4 py-2">Score</th>
                          <th className="px-4 py-2">Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {history.slice(0, 5).map(h => {
                          const hReport = evaluateEntry(h, thresholds);
                          return (
                            <tr key={h.id} className="border-b dark:border-gray-800">
                              <td className="px-4 py-2">{h.building} {h.room}</td>
                              <td className="px-4 py-2"><Badge variant={hReport.overallRating === "GOOD" ? "success" : hReport.overallRating === "FAIR" ? "warning" : "destructive"}>{hReport.overallRating}</Badge></td>
                              <td className="px-4 py-2">
                                <Button variant="link" size="sm" onClick={() => setEntry(h)}>Load</Button>
                                <Button variant="link" size="sm" className="text-red-500" onClick={() => {
                                  deleteEntry(h.id);
                                  setHistory(getHistory());
                                }}>Del</Button>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>

        </div>
      </div>
    </div>
  );
}

function getEmptyEntry(): SurveyEntry {
  return {
    id: "",
    createdAt: Date.now(),
    timestamp: new Date().toISOString(),
    building: "", floor: "", room: "", note: "",
    ssid: "", bssid: "", band: "", radioType: "", channel: "", signalPercent: "", rssi: "", rxRate: "", txRate: "",
    gatewayIp: "", pingGatewayMs: "", pingGatewayLoss: "", pingServerMs: "", pingLoss: "",
    tcpUpload: "", tcpDownload: "", udpTarget: "", udpActual: "", udpJitter: "", udpLoss: "",
  };
}
