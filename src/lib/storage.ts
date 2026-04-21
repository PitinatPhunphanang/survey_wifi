import { SurveyEntry } from "@/types";

const STORAGE_KEY = "wifi_survey_history";

export function saveEntry(entry: SurveyEntry): void {
  try {
    const history = getHistory();
    const existingIndex = history.findIndex((e) => e.id === entry.id);
    if (existingIndex >= 0) {
      history[existingIndex] = entry;
    } else {
      history.unshift(entry);
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(history));
  } catch (error) {
    console.error("Failed to save entry to localStorage", error);
  }
}

export function getHistory(): SurveyEntry[] {
  try {
    const data = localStorage.getItem(STORAGE_KEY);
    return data ? JSON.parse(data) : [];
  } catch (error) {
    console.error("Failed to parse history from localStorage", error);
    return [];
  }
}

export function deleteEntry(id: string): void {
  try {
    const history = getHistory();
    const newHistory = history.filter((e) => e.id !== id);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(newHistory));
  } catch (error) {
    console.error("Failed to delete entry from localStorage", error);
  }
}

export function generateId(): string {
  return Math.random().toString(36).substring(2, 9);
}
