import { SurveyEntry, HealthReport, Thresholds, MetricEvaluation, DEFAULT_THRESHOLDS } from "@/types";

export function evaluateEntry(entry: SurveyEntry, thresholds: Thresholds = DEFAULT_THRESHOLDS): HealthReport {
  const evals: Record<string, MetricEvaluation> = {};
  const issues: string[] = [];
  const recs: Set<string> = new Set();

  // Helper to parse numbers
  const num = (val: number | "") => (val === "" ? null : Number(val));

  const rssi = num(entry.rssi);
  const tcpUp = num(entry.tcpUpload);
  const tcpDown = num(entry.tcpDownload);
  const udpLoss = num(entry.udpLoss);
  const pingServer = num(entry.pingServerMs);
  const pingGateway = num(entry.pingGatewayMs);
  const pingLoss = num(entry.pingLoss);
  const jitter = num(entry.udpJitter);
  const signal = num(entry.signalPercent);
  const rx = num(entry.rxRate);
  const tx = num(entry.txRate);

  // --- RSSI ---
  if (rssi === null) {
    evals.rssi = { status: "Not provided", text: "Missing RSSI data." };
  } else if (rssi >= thresholds.rssi.excellent) {
    evals.rssi = { status: "Excellent", text: "Exceptional signal strength." };
  } else if (rssi >= thresholds.rssi.good) {
    evals.rssi = { status: "Good", text: "RSSI is strong enough for stable roaming and typical office usage." };
  } else if (rssi >= thresholds.rssi.fair) {
    evals.rssi = { status: "Fair", text: "Signal is acceptable, but may degrade with obstacles or movement." };
    issues.push("Fair signal strength");
  } else {
    evals.rssi = { status: "Poor", text: "Signal is too weak for reliable connectivity." };
    issues.push("Poor signal strength");
    recs.add("Check AP placement, obstructions, or distance from AP.");
  }

  // --- Signal % ---
  if (signal === null) {
    evals.signalPercent = { status: "Not provided", text: "" };
  } else if (signal >= thresholds.signalPercent.good) {
    evals.signalPercent = { status: "Good", text: "Good signal quality." };
  } else if (signal >= thresholds.signalPercent.fair) {
    evals.signalPercent = { status: "Fair", text: "Fair signal quality." };
  } else {
    evals.signalPercent = { status: "Poor", text: "Poor signal quality." };
  }

  // --- Ping Gateway ---
  if (pingGateway === null) {
    evals.pingGateway = { status: "Not provided", text: "" };
  } else if (pingGateway <= thresholds.pingGatewayMs.excellent) {
    evals.pingGateway = { status: "Excellent", text: "Excellent local gateway latency." };
  } else if (pingGateway <= thresholds.pingGatewayMs.good) {
    evals.pingGateway = { status: "Good", text: "Good local gateway latency." };
  } else if (pingGateway <= thresholds.pingGatewayMs.fair) {
    evals.pingGateway = { status: "Fair", text: "Fair gateway latency, might indicate local contention." };
  } else {
    evals.pingGateway = { status: "Poor", text: "High gateway latency, local network issue likely." };
    issues.push("High Gateway Latency");
    recs.add("Check local AP load and wired uplink performance.");
  }

  // --- Ping Server ---
  if (pingServer === null) {
    evals.pingServer = { status: "Not provided", text: "" };
  } else if (pingServer <= thresholds.pingServerMs.good) {
    evals.pingServer = { status: "Good", text: "Good server latency." };
  } else if (pingServer <= thresholds.pingServerMs.fair) {
    evals.pingServer = { status: "Fair", text: "Fair server latency." };
  } else {
    evals.pingServer = { status: "Poor", text: "High server latency." };
    issues.push("High Server Latency");
  }

  // --- Ping Loss ---
  if (pingLoss === null) {
    evals.pingLoss = { status: "Not provided", text: "" };
  } else if (pingLoss <= thresholds.pingLoss.good) {
    evals.pingLoss = { status: "Good", text: "No ping packet loss." };
  } else if (pingLoss <= thresholds.pingLoss.fair) {
    evals.pingLoss = { status: "Fair", text: "Minor ping packet loss." };
  } else {
    evals.pingLoss = { status: "Poor", text: "High ping packet loss." };
    issues.push("ICMP Packet Loss");
  }

  // --- UDP Jitter ---
  if (jitter === null) {
    evals.udpJitter = { status: "Not provided", text: "" };
  } else if (jitter <= thresholds.udpJitter.good) {
    evals.udpJitter = { status: "Good", text: "Low jitter, great for real-time traffic." };
  } else if (jitter <= thresholds.udpJitter.fair) {
    evals.udpJitter = { status: "Fair", text: "Moderate jitter." };
  } else {
    evals.udpJitter = { status: "Poor", text: "UDP jitter is higher than ideal for real-time voice/video." };
    issues.push("High UDP Jitter");
    recs.add("Check congestion, interference, or upstream path quality.");
  }

  // --- UDP Loss ---
  if (udpLoss === null) {
    evals.udpLoss = { status: "Not provided", text: "" };
  } else if (udpLoss <= thresholds.udpLoss.good) {
    evals.udpLoss = { status: "Good", text: "Minimal UDP loss." };
  } else if (udpLoss <= thresholds.udpLoss.fair) {
    evals.udpLoss = { status: "Fair", text: "Moderate UDP loss." };
  } else {
    evals.udpLoss = { status: "Poor", text: "High UDP loss." };
    issues.push("High UDP Packet Loss");
    recs.add("Check interference, retries, saturation, and AP/client quality.");
  }

  // --- TCP Upload ---
  if (tcpUp === null) {
    evals.tcpUpload = { status: "Not provided", text: "" };
  } else if (tcpUp >= thresholds.tcpUpload.good) {
    evals.tcpUpload = { status: "Good", text: "Excellent upload throughput." };
  } else if (tcpUp >= thresholds.tcpUpload.fair) {
    evals.tcpUpload = { status: "Fair", text: "Acceptable upload throughput." };
  } else {
    evals.tcpUpload = { status: "Poor", text: "Poor upload throughput." };
    issues.push("Low TCP Upload");
    if (rssi !== null && rssi >= thresholds.rssi.good) {
      recs.add("Check contention, server path, channel width, client capability, or uplink bottleneck.");
    }
  }

  // --- TCP Download ---
  if (tcpDown === null) {
    evals.tcpDownload = { status: "Not provided", text: "" };
  } else if (tcpDown >= thresholds.tcpDownload.good) {
    evals.tcpDownload = { status: "Good", text: "Excellent download throughput." };
  } else if (tcpDown >= thresholds.tcpDownload.fair) {
    evals.tcpDownload = { status: "Fair", text: "Acceptable download throughput." };
  } else {
    evals.tcpDownload = { status: "Poor", text: "Poor download throughput." };
    issues.push("Low TCP Download");
    if (rssi !== null && rssi >= thresholds.rssi.good) {
      recs.add("Check contention, server path, channel width, client capability, or uplink bottleneck.");
    }
  }

  // --- Rates ---
  evals.rxRate = { status: rx !== null && rx < 100 ? "Warning" : "Informational", text: "Receive Rate" } as any;
  evals.txRate = { status: tx !== null && tx < 100 ? "Warning" : "Informational", text: "Transmit Rate" } as any;

  // --- Band & Channel ---
  if (entry.band === "6 GHz") {
    evals.band = { status: "Excellent", text: "Best performance band." };
    evals.channel = { status: "Informational", text: "Operating on 6GHz channel." };
  } else if (entry.band === "5 GHz") {
    evals.band = { status: "Good", text: "Preferred performance band." };
    evals.channel = { status: "Informational", text: "Operating on 5GHz channel." };
  } else if (entry.band === "2.4 GHz") {
    evals.band = { status: "Warning", text: "Caution for high-performance usage." } as any;
    if (entry.channel !== "" && ![1, 6, 11].includes(Number(entry.channel))) {
      evals.channel = { status: "Warning", text: "2.4 GHz channel is not one of the preferred non-overlapping channels." } as any;
      issues.push("Non-standard 2.4GHz channel");
      recs.add("Review channel planning (use 1, 6, or 11).");
    } else {
      evals.channel = { status: "Informational", text: "Standard 2.4GHz channel." };
    }
  } else {
    evals.band = { status: "Not provided", text: "" };
    evals.channel = { status: "Not provided", text: "" };
  }

  // --- Health Score Calculation ---
  let score = 0;
  let maxScore = 0;
  
  const addScore = (val: number | null, weight: number, thresholdKey: "rssi"|"tcpUpload"|"tcpDownload"|"pingServerMs"|"udpJitter"|"udpLoss"|"pingGatewayMs", isLowerBetter: boolean) => {
    if (val === null) return;
    maxScore += weight;
    const t = thresholds[thresholdKey];
    if (isLowerBetter) {
      if (val <= (t as any).good) score += weight;
      else if (val <= (t as any).fair) score += weight * 0.5;
    } else {
      if (val >= (t as any).good) score += weight;
      else if (val >= (t as any).fair) score += weight * 0.5;
    }
  };

  addScore(rssi, 25, "rssi", false);
  addScore(tcpUp, 15, "tcpUpload", false);
  addScore(tcpDown, 15, "tcpDownload", false);
  addScore(pingServer, 15, "pingServerMs", true);
  addScore(jitter, 10, "udpJitter", true);
  addScore(udpLoss, 15, "udpLoss", true);
  addScore(pingGateway, 5, "pingGatewayMs", true);

  const healthScore = maxScore > 0 ? Math.round((score / maxScore) * 100) : 0;

  // --- Overall Rating (Strict Logic) ---
  let overallRating: "GOOD" | "FAIR" | "POOR" = "POOR";
  
  // To evaluate GOOD/FAIR, we need these values. If null, we fail the condition.
  const cRssi = rssi !== null ? rssi : -999;
  const cUp = tcpUp !== null ? tcpUp : 0;
  const cDown = tcpDown !== null ? tcpDown : 0;
  const cLoss = udpLoss !== null ? udpLoss : 999;
  const cPing = pingServer !== null ? pingServer : 999;

  if (cRssi >= -67 && cUp >= 50 && cDown >= 50 && cLoss < 1 && cPing <= 20) {
    overallRating = "GOOD";
  } else if (cRssi >= -75 && cUp >= 20 && cDown >= 20 && cLoss < 5) {
    overallRating = "FAIR";
  } else {
    overallRating = "POOR";
  }

  // --- Summary & Narrative ---
  const narrative = `This survey point at ${entry.building || 'unknown building'} ${entry.floor ? 'Floor ' + entry.floor : ''} ${entry.room || ''} is rated ${overallRating}. ` +
    `Signal strength is ${rssi ? rssi + ' dBm' : 'not recorded'} and packet loss is ${udpLoss !== null ? udpLoss + '%' : 'unknown'}. ` +
    (overallRating !== "GOOD" ? `Performance is constrained due to ${issues.length > 0 ? issues[0].toLowerCase() : 'various factors'}. ` : 'Overall performance meets preferred targets. ') +
    (entry.band === "2.4 GHz" ? `Device is operating on 2.4 GHz, which may affect performance in busy environments.` : '');

  const summary = `Location: ${entry.building || '-'} / ${entry.floor || '-'} / ${entry.room || '-'}
Observed Condition: ${overallRating} (Health Score: ${maxScore > 0 ? healthScore : 'N/A'})
Risk Level: ${overallRating === "GOOD" ? "Low" : overallRating === "FAIR" ? "Medium" : "High"}
Key Issues: ${issues.length > 0 ? issues.slice(0, 3).join(", ") : "None detected"}
Recommendations: ${Array.from(recs).length > 0 ? Array.from(recs).join(" ") : "Continue standard monitoring."}`;

  return {
    overallRating,
    healthScore: maxScore > 0 ? healthScore : 0,
    topIssues: issues.slice(0, 3),
    recommendations: Array.from(recs),
    narrative,
    summary,
    evaluations: evals
  };
}
