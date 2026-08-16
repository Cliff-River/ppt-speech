import { apiFetch } from "@/lib/api";

export type Voice = {
  Name?: string;
  ShortName: string;
  Gender?: string;
  Locale?: string;
  FriendlyName?: string;
  Status?: string;
  StyleList?: string[];
  SecondaryLocaleList?: string[];
  VoiceTag?: {
    ContentCategories?: string[];
    VoicePersonalities?: string[];
  };
};

export type VoicesResponse = {
  voices: Voice[];
};

export type TaskCreateResponse = {
  task_id: string;
  status: string;
  progress_url: string;
  result_url: string;
};

export type TaskSnapshot = Record<string, string>;

export type TasksListResponse = {
  tasks: TaskSnapshot[];
};

export type ProgressStatus = "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED";

export type ProgressEvent = {
  task_id: string;
  status: ProgressStatus;
  stage?: string;
  slide_idx?: number;
  total_slides?: number;
  percent?: number;
  eta_seconds?: number;
  message?: string;
  error?: string;
  result_ready?: boolean;
  updated_at?: number;
};

export async function fetchVoices(signal?: AbortSignal) {
  return apiFetch<VoicesResponse>("/api/v1/voices", { signal });
}

export async function createTask(params: {
  file: File;
  voiceName: string;
  speechRate?: string;
  autoAdvance?: boolean;
  autoAdvanceDelaySeconds?: number;
}) {
  const body = new FormData();
  body.set("file", params.file);
  body.set("voice_name", params.voiceName);
  if (params.speechRate) {
    body.set("speech_rate", params.speechRate);
  }
  if (params.autoAdvance !== undefined) {
    body.set("auto_advance", params.autoAdvance ? "true" : "false");
  }
  if (params.autoAdvanceDelaySeconds !== undefined) {
    body.set("auto_advance_delay", String(params.autoAdvanceDelaySeconds));
  }

  return apiFetch<TaskCreateResponse>("/api/v1/tasks", {
    method: "POST",
    body,
  });
}

export async function fetchTasks(signal?: AbortSignal) {
  return apiFetch<TasksListResponse>("/api/v1/tasks", { signal });
}

export async function fetchTask(taskId: string, signal?: AbortSignal) {
  return apiFetch<TaskSnapshot>(`/api/v1/tasks/${encodeURIComponent(taskId)}`, {
    signal,
  });
}

