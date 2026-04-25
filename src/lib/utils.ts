import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Normalize Wi-Fi band to standard format
 * Supports: "2.4 GHz", "2.4", "2.4GHz", "2G", "2", "5 GHz", "5", "5GHz", "5G", "6 GHz", etc.
 */
export function normalizeBand(band: string | null | undefined): "2.4GHz" | "5GHz" | "6GHz" | "Unknown" {
  if (!band || typeof band !== "string") return "Unknown";
  
  const normalized = band.trim().toUpperCase();
  
  // 2.4 GHz patterns
  if (normalized.includes("2.4") || normalized === "2G" || normalized === "2") {
    return "2.4GHz";
  }
  
  // 5 GHz patterns
  if (normalized.includes("5") && !normalized.includes("2")) {
    if (normalized.includes("6")) return "6GHz"; // Avoid matching 5 in 6GHz
    return "5GHz";
  }
  
  // 6 GHz patterns
  if (normalized.includes("6")) {
    return "6GHz";
  }
  
  return "Unknown";
}

/**
 * Get badge color for band display
 */
export function getBandColor(band: string | null | undefined): { bg: string; text: string } {
  const normalized = normalizeBand(band);
  
  switch (normalized) {
    case "2.4GHz":
      return { bg: "bg-blue-100 dark:bg-blue-900/30", text: "text-blue-700 dark:text-blue-300" };
    case "5GHz":
      return { bg: "bg-purple-100 dark:bg-purple-900/30", text: "text-purple-700 dark:text-purple-300" };
    case "6GHz":
      return { bg: "bg-emerald-100 dark:bg-emerald-900/30", text: "text-emerald-700 dark:text-emerald-300" };
    default:
      return { bg: "bg-gray-100 dark:bg-gray-800", text: "text-gray-700 dark:text-gray-300" };
  }
}
