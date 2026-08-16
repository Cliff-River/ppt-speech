import { describe, expect, it } from "vitest";

import type { ProgressEvent, TaskCreateResponse } from "@/lib/pptSpeech";
import { applyProgress, fromCreateResponse } from "@/lib/taskStore";

describe("taskStore", () => {
  it("fromCreateResponse maps fields", () => {
    const resp: TaskCreateResponse = {
      task_id: "t1",
      status: "PENDING",
      progress_url: "/api/v1/tasks/t1/progress",
      result_url: "/api/v1/tasks/t1/result",
    };

    const task = fromCreateResponse({ resp, voiceName: "en-US-AriaNeural", fileName: "a.pptx" });
    expect(task.taskId).toBe("t1");
    expect(task.voiceName).toBe("en-US-AriaNeural");
    expect(task.fileName).toBe("a.pptx");
    expect(task.progressUrl).toBe(resp.progress_url);
  });

  it("applyProgress updates latest fields", () => {
    const base = fromCreateResponse({
      resp: {
        task_id: "t1",
        status: "PENDING",
        progress_url: "/api/v1/tasks/t1/progress",
        result_url: "/api/v1/tasks/t1/result",
      },
      voiceName: "v",
      fileName: "a.pptx",
    });

    const evt: ProgressEvent = {
      task_id: "t1",
      status: "PROCESSING",
      stage: "SYNTHESIZING",
      percent: 12.3,
      slide_idx: 2,
      total_slides: 10,
      result_ready: false,
    };

    const next = applyProgress(base, evt);
    expect(next.status).toBe("PROCESSING");
    expect(next.stage).toBe("SYNTHESIZING");
    expect(next.slideIdx).toBe(2);
    expect(next.totalSlides).toBe(10);
    expect(next.percent).toBe(12.3);
  });
});

