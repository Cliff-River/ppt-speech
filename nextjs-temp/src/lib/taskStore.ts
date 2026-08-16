import type { ProgressEvent, ProgressStatus, TaskCreateResponse } from "@/lib/pptSpeech";
import { readJson, writeJson } from "@/lib/storage";

export type LocalTask = {
  taskId: string;
  createdAt: number;
  voiceName: string;
  fileName: string;
  status: ProgressStatus;
  stage?: string;
  percent?: number;
  slideIdx?: number;
  totalSlides?: number;
  message?: string;
  error?: string;
  resultReady?: boolean;
  progressUrl: string;
  resultUrl: string;
};

const STORAGE_KEY = "ppt-speech.tasks.v1";

export function loadTasks(): LocalTask[] {
  return readJson<LocalTask[]>(STORAGE_KEY, []);
}

export function saveTasks(tasks: LocalTask[]) {
  writeJson(STORAGE_KEY, tasks);
}

export function upsertTask(tasks: LocalTask[], task: LocalTask) {
  const idx = tasks.findIndex((t) => t.taskId === task.taskId);
  if (idx === -1) {
    return [task, ...tasks];
  }
  const next = [...tasks];
  next[idx] = task;
  return next;
}

export function fromCreateResponse(args: {
  resp: TaskCreateResponse;
  voiceName: string;
  fileName: string;
}): LocalTask {
  return {
    taskId: args.resp.task_id,
    createdAt: Date.now(),
    voiceName: args.voiceName,
    fileName: args.fileName,
    status: (args.resp.status as ProgressStatus) ?? "PENDING",
    progressUrl: args.resp.progress_url,
    resultUrl: args.resp.result_url,
  };
}

export function applyProgress(task: LocalTask, evt: ProgressEvent): LocalTask {
  return {
    ...task,
    status: evt.status,
    stage: evt.stage ?? task.stage,
    percent: evt.percent ?? task.percent,
    slideIdx: evt.slide_idx ?? task.slideIdx,
    totalSlides: evt.total_slides ?? task.totalSlides,
    message: evt.message ?? task.message,
    error: evt.error ?? task.error,
    resultReady: evt.result_ready ?? task.resultReady,
  };
}

