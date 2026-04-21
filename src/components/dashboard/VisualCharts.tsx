"use client";

import React from "react";
import { SurveyEntry } from "@/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  LabelList
} from "recharts";

interface VisualChartsProps {
  entry: SurveyEntry;
}

export function VisualCharts({ entry }: VisualChartsProps) {
  // Parse numbers securely
  const getNum = (val: any) => (val === "" || val === null || val === undefined ? 0 : Number(val));

  const throughputData = [
    { name: "TCP Up", value: getNum(entry.tcpUpload), color: "#3b82f6" }, // blue-500
    { name: "TCP Down", value: getNum(entry.tcpDownload), color: "#10b981" }, // emerald-500
    { name: "UDP Act.", value: getNum(entry.udpActual), color: "#8b5cf6" }, // violet-500
  ];

  const latencyData = [
    { name: "Ping GW", value: getNum(entry.pingGatewayMs), color: "#f59e0b" }, // amber-500
    { name: "Ping Srv", value: getNum(entry.pingServerMs), color: "#ef4444" }, // red-500
    { name: "Jitter", value: getNum(entry.udpJitter), color: "#f97316" }, // orange-500
  ];

  // Only show charts if there's at least some data
  const hasThroughputData = throughputData.some(d => d.value > 0);
  const hasLatencyData = latencyData.some(d => d.value > 0);

  if (!hasThroughputData && !hasLatencyData) return null;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {hasThroughputData && (
        <Card className="print:break-inside-avoid">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold text-gray-500 dark:text-gray-400">
              Throughput (Mbps)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[250px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={throughputData} margin={{ top: 20, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                  <XAxis dataKey="name" stroke="#94a3b8" fontSize={12} tickLine={false} axisLine={false} interval={0} />
                  <YAxis stroke="#94a3b8" fontSize={12} tickLine={false} axisLine={false} />
                  <Tooltip 
                    cursor={{ fill: 'rgba(255, 255, 255, 0.05)' }}
                    contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px', color: '#f8fafc' }}
                  />
                  <Bar dataKey="value" radius={[4, 4, 0, 0]} maxBarSize={50}>
                    {throughputData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                    <LabelList dataKey="value" position="top" fill="#94a3b8" fontSize={11} fontWeight="bold" />
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      )}

      {hasLatencyData && (
        <Card className="print:break-inside-avoid">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold text-gray-500 dark:text-gray-400">
              Latency & Jitter (ms)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[250px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={latencyData} margin={{ top: 20, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                  <XAxis dataKey="name" stroke="#94a3b8" fontSize={12} tickLine={false} axisLine={false} interval={0} />
                  <YAxis stroke="#94a3b8" fontSize={12} tickLine={false} axisLine={false} />
                  <Tooltip 
                    cursor={{ fill: 'rgba(255, 255, 255, 0.05)' }}
                    contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px', color: '#f8fafc' }}
                  />
                  <Bar dataKey="value" radius={[4, 4, 0, 0]} maxBarSize={50}>
                    {latencyData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                    <LabelList dataKey="value" position="top" fill="#94a3b8" fontSize={11} fontWeight="bold" />
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
