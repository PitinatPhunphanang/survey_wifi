import React from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ArrowLeft } from "lucide-react";
import { DEFAULT_THRESHOLDS } from "@/types";

export default function ReferenceGuide() {
  const t = DEFAULT_THRESHOLDS;

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
              <Link href="/report" className="px-3 py-1.5 text-sm font-medium text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 transition-all">Floor Report</Link>
              <Link href="/reference" className="px-3 py-1.5 text-sm font-medium bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm rounded-md transition-all">Guide</Link>
            </nav>
          </div>
        </div>
      </header>

      <div className="max-w-4xl mx-auto px-4 md:px-8 mt-8 space-y-8">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <GuideCard title="Overall Rating (Health)">
            <p className="text-sm mb-2"><strong>GOOD</strong> when ALL of the following are met:</p>
            <ul className="text-sm list-disc pl-5 space-y-1 mb-4 text-gray-600 dark:text-gray-300">
              <li>RSSI &ge; -67 dBm</li>
              <li>TCP Upload &ge; 50 Mbps</li>
              <li>TCP Download &ge; 50 Mbps</li>
              <li>UDP Packet Loss &lt; 1%</li>
              <li>Ping Server &le; 20 ms</li>
            </ul>
            <p className="text-sm mb-2"><strong>FAIR</strong> when ALL of the following are met (but didn't reach GOOD):</p>
            <ul className="text-sm list-disc pl-5 space-y-1 text-gray-600 dark:text-gray-300">
              <li>RSSI &ge; -75 dBm</li>
              <li>TCP Upload &ge; 20 Mbps</li>
              <li>TCP Download &ge; 20 Mbps</li>
              <li>UDP Packet Loss &lt; 5%</li>
            </ul>
            <p className="text-sm mt-4"><strong>POOR</strong> if the above conditions are not met.</p>
          </GuideCard>

          <GuideCard title="RSSI (Signal Strength)">
            <MetricRow label="Excellent" condition={`≥ ${t.rssi.excellent} dBm`} variant="success" />
            <MetricRow label="Good" condition={`${t.rssi.good} to ${t.rssi.excellent - 1} dBm`} variant="success" />
            <MetricRow label="Fair" condition={`${t.rssi.fair} to ${t.rssi.good - 1} dBm`} variant="warning" />
            <MetricRow label="Poor" condition={`< ${t.rssi.fair} dBm`} variant="destructive" />
          </GuideCard>

          <GuideCard title="TCP Throughput (Up / Down)">
            <MetricRow label="Good" condition={`≥ ${t.tcpUpload.good} Mbps`} variant="success" />
            <MetricRow label="Fair" condition={`${t.tcpUpload.fair} to ${t.tcpUpload.good - 0.01} Mbps`} variant="warning" />
            <MetricRow label="Poor" condition={`< ${t.tcpUpload.fair} Mbps`} variant="destructive" />
          </GuideCard>

          <GuideCard title="Ping Server Latency">
            <MetricRow label="Good" condition={`≤ ${t.pingServerMs.good} ms`} variant="success" />
            <MetricRow label="Fair" condition={`${t.pingServerMs.good + 1} to ${t.pingServerMs.fair} ms`} variant="warning" />
            <MetricRow label="Poor" condition={`> ${t.pingServerMs.fair} ms`} variant="destructive" />
          </GuideCard>

          <GuideCard title="UDP Jitter">
            <MetricRow label="Good" condition={`< 30 ms`} variant="success" />
            <MetricRow label="Fair" condition={`30 to 50 ms`} variant="warning" />
            <MetricRow label="Poor" condition={`> 50 ms`} variant="destructive" />
          </GuideCard>

          <GuideCard title="UDP Packet Loss">
            <MetricRow label="Good" condition={`< 1%`} variant="success" />
            <MetricRow label="Fair" condition={`1% to 4.99%`} variant="warning" />
            <MetricRow label="Poor" condition={`≥ 5%`} variant="destructive" />
          </GuideCard>

          <GuideCard title="Ping Gateway Latency">
            <MetricRow label="Excellent" condition={`≤ ${t.pingGatewayMs.excellent} ms`} variant="success" />
            <MetricRow label="Good" condition={`${t.pingGatewayMs.excellent + 1} to ${t.pingGatewayMs.good} ms`} variant="success" />
            <MetricRow label="Fair" condition={`${t.pingGatewayMs.good + 1} to ${t.pingGatewayMs.fair} ms`} variant="warning" />
            <MetricRow label="Poor" condition={`> ${t.pingGatewayMs.fair} ms`} variant="destructive" />
          </GuideCard>
          
          <GuideCard title="Wi-Fi Bands & Channels">
            <div className="space-y-4">
              <div>
                <strong className="text-sm">6 GHz & 5 GHz:</strong>
                <p className="text-sm text-gray-600 dark:text-gray-300">Best / Preferred performance. All channels are acceptable.</p>
              </div>
              <div>
                <strong className="text-sm">2.4 GHz:</strong>
                <p className="text-sm text-gray-600 dark:text-gray-300 mb-2">Caution for high performance usage.</p>
                <MetricRow label="Preferred" condition={`Channels 1, 6, 11`} variant="informational" />
                <MetricRow label="Caution" condition={`Any other channel`} variant="warning" />
              </div>
            </div>
          </GuideCard>
        </div>
      </div>
    </div>
  );
}

function GuideCard({ title, children }: { title: string, children: React.ReactNode }) {
  return (
    <Card>
      <CardHeader className="bg-gray-50/50 dark:bg-gray-900/50 border-b">
        <CardTitle className="text-base">{title}</CardTitle>
      </CardHeader>
      <CardContent className="p-4 space-y-2">
        {children}
      </CardContent>
    </Card>
  );
}

function MetricRow({ label, condition, variant }: { label: string, condition: string, variant: string }) {
  return (
    <div className="flex items-center justify-between border-b dark:border-gray-800 last:border-0 pb-2 last:pb-0">
      <Badge variant={variant as any}>{label}</Badge>
      <span className="text-sm font-medium">{condition}</span>
    </div>
  );
}
