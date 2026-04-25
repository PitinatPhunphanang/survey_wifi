export interface SurveyEntry {
  id: string;
  createdAt: number;

  // A) Location Information
  timestamp: string;
  building: string;
  floor: string;
  room: string;
  note: string;

  // B) Wi-Fi Information
  ssid: string;
  bssid: string;
  band: string | null; // Support various formats: "2.4 GHz", "2.4", "5 GHz", "5", "2G", "5G", etc.
  radioType: string;
  channel: number | "";
  signalPercent: number | "";
  rssi: number | "";
  rxRate: number | "";
  txRate: number | "";

  // C) Gateway / Server Connectivity
  gatewayIp: string;
  pingGatewayMs: number | "";
  pingGatewayLoss: number | "";
  pingServerMs: number | "";
  pingLoss: number | "";

  // D) Throughput / Quality
  tcpUpload: number | "";
  tcpDownload: number | "";
  udpTarget: number | "";
  udpActual: number | "";
  udpJitter: number | "";
  udpLoss: number | "";
}

export interface MetricEvaluation {
  status: "Excellent" | "Good" | "Fair" | "Poor" | "Informational" | "Warning" | "Not provided";
  text: string;
}

export interface HealthReport {
  overallRating: "GOOD" | "FAIR" | "POOR";
  healthScore: number;
  topIssues: string[];
  recommendations: string[];
  narrative: string;
  summary: string;
  evaluations: Record<string, MetricEvaluation>;
}

export interface Thresholds {
  rssi: { excellent: number; good: number; fair: number; poor: number };
  signalPercent: { good: number; fair: number; poor: number };
  pingGatewayMs: { excellent: number; good: number; fair: number; poor: number };
  pingServerMs: { good: number; fair: number; poor: number };
  pingLoss: { good: number; fair: number; poor: number }; // poor is > 2, fair > 0
  udpJitter: { good: number; fair: number; poor: number };
  udpLoss: { good: number; fair: number; poor: number };
  tcpUpload: { good: number; fair: number; poor: number };
  tcpDownload: { good: number; fair: number; poor: number };
}

export const DEFAULT_THRESHOLDS: Thresholds = {
  rssi: { excellent: -65, good: -67, fair: -75, poor: -76 }, // using bounds
  signalPercent: { good: 80, fair: 60, poor: 59 },
  pingGatewayMs: { excellent: 5, good: 10, fair: 20, poor: 21 },
  pingServerMs: { good: 20, fair: 50, poor: 51 },
  pingLoss: { good: 0, fair: 2, poor: 2.1 },
  udpJitter: { good: 29.99, fair: 50, poor: 50.01 },
  udpLoss: { good: 0.99, fair: 4.99, poor: 5 },
  tcpUpload: { good: 50, fair: 20, poor: 19.99 },
  tcpDownload: { good: 50, fair: 20, poor: 19.99 },
};
