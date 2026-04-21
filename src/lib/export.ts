import { SurveyEntry } from "@/types";

export function exportToJson(entry: SurveyEntry) {
  const dataStr = JSON.stringify(entry, null, 2);
  const blob = new Blob([dataStr], { type: "application/json" });
  downloadBlob(blob, `wifi-survey-${entry.building || "entry"}-${entry.id}.json`);
}

export function exportHistoryToCsv(history: SurveyEntry[]) {
  if (history.length === 0) return;

  const headers = Object.keys(history[0]).join(",");
  const rows = history.map((entry) => {
    return Object.values(entry)
      .map((val) => `"${String(val).replace(/"/g, '""')}"`)
      .join(",");
  });

  const csvContent = [headers, ...rows].join("\n");
  const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
  downloadBlob(blob, "wifi-survey-history.csv");
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export function printReport() {
  window.print();
}
