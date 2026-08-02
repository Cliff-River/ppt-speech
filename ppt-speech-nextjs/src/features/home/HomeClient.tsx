"use client";

import { Button, Card, Chip, Input, Label, ProgressBar, Spinner, TextField } from "@heroui/react";
import { useMemo, useRef, useState, useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";

import type { Locale } from "@/i18n/config";
import { locales } from "@/i18n/config";
import { useI18n } from "@/i18n/I18nProvider";
import type { ProgressEvent, Voice } from "@/lib/pptSpeech";
import { createTask, fetchTasks, fetchVoices } from "@/lib/pptSpeech";
import {
  applyVoiceFilters,
  collectLanguages,
  collectRegionsForLanguage,
  collectStyles,
  sortVoices,
  type VoiceFilters,
} from "@/lib/voiceFilter";
import { loadRecentVoices, pushRecentVoice, type RecentVoice } from "@/lib/recentVoices";
import {
  applyProgress,
  fromCreateResponse,
  loadTasks,
  saveTasks,
  type LocalTask,
  upsertTask,
} from "@/lib/taskStore";

function isTerminal(status: LocalTask["status"]) {
  return status === "COMPLETED" || status === "FAILED";
}

function parseFileNameFromContentDisposition(header: string | null) {
  if (!header) return null;
  const match = /filename="?([^"]+)"?/i.exec(header);
  return match?.[1] ?? null;
}

export function HomeClient({ locale }: { locale: Locale }) {
  const { t } = useI18n();
  const router = useRouter();
  const pathname = usePathname();

  const [voices, setVoices] = useState<Voice[] | null>(null);
  const [voicesLoading, setVoicesLoading] = useState(true);
  const [voicesError, setVoicesError] = useState<string | null>(null);

  const [selectedVoice, setSelectedVoice] = useState<Voice | null>(null);
  const [recentVoices, setRecentVoices] = useState<RecentVoice[]>([]);

  const [filters, setFilters] = useState<VoiceFilters>({
    query: "",
    gender: null,
    language: null,
    region: null,
    multilingualOnly: false,
    style: null,
  });

  const [file, setFile] = useState<File | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const [hydrated, setHydrated] = useState(false);
  const [tasks, setTasks] = useState<LocalTask[]>(() => []);
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null);
  const [downloadBusyId, setDownloadBusyId] = useState<string | null>(null);

  const esMapRef = useRef<Map<string, EventSource>>(new Map());

  const sortedVoices = useMemo(() => {
    return voices ? sortVoices(voices) : [];
  }, [voices]);

  const styleOptions = useMemo(() => collectStyles(sortedVoices), [sortedVoices]);
  const languageOptions = useMemo(() => collectLanguages(sortedVoices), [sortedVoices]);
  const regionOptions = useMemo(
    () => collectRegionsForLanguage(sortedVoices, filters.language),
    [sortedVoices, filters.language],
  );

  const filteredVoices = useMemo(() => {
    return applyVoiceFilters(sortedVoices, filters);
  }, [sortedVoices, filters]);

  const activeTask = useMemo(() => {
    if (!activeTaskId) return null;
    return tasks.find((t) => t.taskId === activeTaskId) ?? null;
  }, [tasks, activeTaskId]);

  useEffect(() => {
    setRecentVoices(loadRecentVoices());
    setTasks(loadTasks());
    setHydrated(true);
  }, []);

  useEffect(() => {
    const controller = new AbortController();

    fetchVoices(controller.signal)
      .then((r) => {
        setVoices(r.voices ?? []);
        setVoicesError(null);
      })
      .catch((e: unknown) => {
        const msg = e instanceof Error ? e.message : t("error.generic");
        setVoicesError(msg);
      })
      .finally(() => setVoicesLoading(false));

    return () => controller.abort();
  }, [t]);

  useEffect(() => {
    if (!hydrated) return;
    saveTasks(tasks);
  }, [hydrated, tasks]);

  useEffect(() => {
    if (!hydrated) return;
    const controller = new AbortController();
    fetchTasks(controller.signal)
      .then((r) => {
        const server = new Map<string, string>();
        for (const snapshot of r.tasks ?? []) {
          const taskId = snapshot["task_id"];
          const status = snapshot["status"];
          if (taskId && status) server.set(taskId, status);
        }

        setTasks((prev) => {
          const next = [...prev];
          for (const task of next) {
            const serverStatus = server.get(task.taskId);
            if (!serverStatus) continue;
            if ((serverStatus === "PENDING" || serverStatus === "PROCESSING") && isTerminal(task.status)) {
              task.status = serverStatus as LocalTask["status"];
            }
          }
          return next;
        });
      })
      .catch(() => undefined);

    return () => controller.abort();
  }, [hydrated]);

  useEffect(() => {
    const current = esMapRef.current;
    return () => {
      for (const es of current.values()) {
        es.close();
      }
      current.clear();
    };
  }, []);

  useEffect(() => {
    const current = esMapRef.current;
    for (const task of tasks) {
      if (isTerminal(task.status)) {
        const es = current.get(task.taskId);
        if (es) {
          es.close();
          current.delete(task.taskId);
        }
        continue;
      }

      if (current.has(task.taskId)) continue;

      const url = task.progressUrl.startsWith("http") ? task.progressUrl : task.progressUrl;
      const es = new EventSource(url);
      current.set(task.taskId, es);

      es.onmessage = (evt) => {
        try {
          const data = JSON.parse(evt.data) as ProgressEvent;
          if (!data || typeof data !== "object") return;
          setTasks((prev) => {
            const found = prev.find((t) => t.taskId === task.taskId);
            if (!found) return prev;
            const nextTask = applyProgress(found, data);
            return upsertTask(prev, nextTask);
          });
        } catch {
          return;
        }
      };

      es.onerror = () => undefined;
    }
  }, [tasks]);

  function onSwitchLocale(nextLocale: Locale) {
    const rest = pathname.replace(new RegExp(`^/${locale}`), "");
    router.push(`/${nextLocale}${rest}`);
  }

  async function onSubmit() {
    setSubmitError(null);
    if (!selectedVoice) {
      setSubmitError(t("voice.section"));
      return;
    }
    if (!file) {
      setSubmitError(t("upload.file.hint"));
      return;
    }
    if (!file.name.toLowerCase().endsWith(".pptx")) {
      setSubmitError(t("upload.file.hint"));
      return;
    }

    setSubmitting(true);
    try {
      const resp = await createTask({
        file,
        voiceName: selectedVoice.ShortName,
        autoAdvance: true,
        autoAdvanceDelaySeconds: 2,
      });

      const newTask = fromCreateResponse({
        resp,
        voiceName: selectedVoice.ShortName,
        fileName: file.name,
      });

      pushRecentVoice(selectedVoice);
      setRecentVoices(loadRecentVoices());
      setTasks((prev) => upsertTask(prev, newTask));
      setActiveTaskId(newTask.taskId);
      setFile(null);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : t("error.generic");
      setSubmitError(msg);
    } finally {
      setSubmitting(false);
    }
  }

  async function downloadResult(task: LocalTask) {
    setDownloadBusyId(task.taskId);
    try {
      const res = await fetch(task.resultUrl);
      if (res.status === 409) {
        throw new Error(t("task.notReady"));
      }
      if (res.status === 410) {
        throw new Error(t("task.expired"));
      }
      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || t("error.generic"));
      }

      const blob = await res.blob();
      const filename =
        parseFileNameFromContentDisposition(res.headers.get("content-disposition")) ??
        `output_${task.taskId.slice(0, 8)}.pptx`;

      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } finally {
      setDownloadBusyId(null);
    }
  }

  const genderOptions = useMemo(() => {
    const set = new Set<string>();
    for (const v of sortedVoices) {
      const g = v.Gender;
      if (g) set.add(g);
    }
    return Array.from(set).sort((a, b) => a.localeCompare(b));
  }, [sortedVoices]);

  return (
    <div className="flex flex-1 justify-center px-4 py-8">
      <div className="flex w-full max-w-5xl flex-col gap-6">
        <header className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div className="flex flex-col gap-1">
            <h1 className="text-2xl font-semibold">{t("app.title")}</h1>
            <p className="text-sm text-zinc-600 dark:text-zinc-300">{t("app.subtitle")}</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <div className="text-sm text-zinc-600 dark:text-zinc-300">{t("nav.language")}</div>
            {locales.map((l) => (
              <Button
                key={l}
                size="sm"
                variant={l === locale ? "secondary" : "outline"}
                onPress={() => onSwitchLocale(l)}
              >
                {l.toUpperCase()}
              </Button>
            ))}
          </div>
        </header>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <Card className="p-4">
            <div className="flex flex-col gap-4">
              <div className="text-lg font-semibold">{t("voice.section")}</div>

              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <TextField name="voiceSearch">
                  <Label>{t("voice.search.label")}</Label>
                  <Input
                    placeholder={t("voice.search.placeholder")}
                    value={filters.query}
                    onChange={(e) =>
                      setFilters((p) => ({ ...p, query: e.target.value }))
                    }
                  />
                </TextField>

                <div className="flex flex-col gap-1">
                  <div className="text-sm text-zinc-600 dark:text-zinc-300">
                    {t("voice.gender.label")}
                  </div>
                  <select
                    className="h-10 rounded-md border border-zinc-200 bg-white px-3 text-sm dark:border-zinc-800 dark:bg-zinc-950"
                    value={filters.gender ?? ""}
                    onChange={(e) =>
                      setFilters((p) => ({ ...p, gender: e.target.value || null }))
                    }
                  >
                    <option value="">{t("voice.gender.any")}</option>
                    {genderOptions.map((g) => (
                      <option key={g} value={g}>
                        {g}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="flex flex-col gap-1">
                  <div className="text-sm text-zinc-600 dark:text-zinc-300">
                    {t("voice.language.label")}
                  </div>
                  <select
                    className="h-10 rounded-md border border-zinc-200 bg-white px-3 text-sm dark:border-zinc-800 dark:bg-zinc-950"
                    value={filters.language ?? ""}
                    onChange={(e) =>
                      setFilters((p) => ({
                        ...p,
                        language: e.target.value || null,
                        region: null,
                      }))
                    }
                  >
                    <option value="">{t("voice.gender.any")}</option>
                    {languageOptions.map((l) => (
                      <option key={l} value={l}>
                        {l}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="flex flex-col gap-1">
                  <div className="text-sm text-zinc-600 dark:text-zinc-300">
                    {t("voice.region.label")}
                  </div>
                  <select
                    className="h-10 rounded-md border border-zinc-200 bg-white px-3 text-sm disabled:cursor-not-allowed disabled:opacity-60 dark:border-zinc-800 dark:bg-zinc-950"
                    value={filters.region ?? ""}
                    disabled={!filters.language}
                    onChange={(e) =>
                      setFilters((p) => ({ ...p, region: e.target.value || null }))
                    }
                  >
                    <option value="">{t("voice.gender.any")}</option>
                    {regionOptions.map((r) => (
                      <option key={r} value={r}>
                        {r}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="flex items-center gap-2">
                  <input
                    id="multilingual"
                    type="checkbox"
                    checked={filters.multilingualOnly}
                    onChange={(e) =>
                      setFilters((p) => ({ ...p, multilingualOnly: e.target.checked }))
                    }
                  />
                  <label htmlFor="multilingual" className="text-sm">
                    {t("voice.multilingual")}
                  </label>
                </div>

                <div className="flex flex-col gap-1">
                  <div className="text-sm text-zinc-600 dark:text-zinc-300">
                    {t("voice.style.label")}
                  </div>
                  <select
                    className="h-10 rounded-md border border-zinc-200 bg-white px-3 text-sm dark:border-zinc-800 dark:bg-zinc-950"
                    value={filters.style ?? ""}
                    onChange={(e) =>
                      setFilters((p) => ({ ...p, style: e.target.value || null }))
                    }
                  >
                    <option value="">{t("voice.style.any")}</option>
                    {styleOptions.map((s) => (
                      <option key={s} value={s}>
                        {s}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="flex flex-col gap-2">
                <div className="text-sm text-zinc-600 dark:text-zinc-300">
                  {t("voice.quick.title")}
                </div>
                <div className="flex flex-wrap gap-2">
                  {recentVoices.length === 0 ? (
                    <div className="text-sm text-zinc-500">-</div>
                  ) : (
                    recentVoices.map((v) => (
                      <Button
                        key={v.shortName}
                        size="sm"
                        variant="outline"
                        onPress={() => {
                          const found = sortedVoices.find((x) => x.ShortName === v.shortName);
                          if (found) setSelectedVoice(found);
                        }}
                      >
                        {v.friendlyName}
                      </Button>
                    ))
                  )}
                </div>
              </div>

              <div className="rounded-lg border border-zinc-200 dark:border-zinc-800">
                <div className="flex items-center justify-between border-b border-zinc-200 px-3 py-2 text-sm dark:border-zinc-800">
                  <div className="text-zinc-600 dark:text-zinc-300">
                    {voicesLoading ? (
                      <div className="flex items-center gap-2">
                        <Spinner size="sm" />
                        <span>{t("progress.connecting")}</span>
                      </div>
                    ) : voicesError ? (
                      voicesError
                    ) : (
                      `${filteredVoices.length}`
                    )}
                  </div>
                  {selectedVoice ? (
                    <div className="flex items-center gap-2">
                      <Chip size="sm" color="accent">
                        {t("voice.selected")}
                      </Chip>
                      <div className="text-sm">{selectedVoice.FriendlyName ?? selectedVoice.ShortName}</div>
                    </div>
                  ) : null}
                </div>

                <div className="max-h-[420px] overflow-auto">
                  {filteredVoices.map((v) => {
                    const active = v.ShortName === selectedVoice?.ShortName;
                    return (
                      <button
                        key={v.ShortName}
                        type="button"
                        className={`flex w-full flex-col gap-1 px-3 py-2 text-left text-sm transition-colors ${
                          active
                            ? "bg-zinc-100 dark:bg-zinc-900"
                            : "hover:bg-zinc-50 dark:hover:bg-zinc-950"
                        }`}
                        onClick={() => setSelectedVoice(v)}
                      >
                        <div className="flex items-center justify-between gap-3">
                          <div className="font-medium">
                            {v.FriendlyName ?? v.ShortName}
                          </div>
                          <div className="text-xs text-zinc-500">{v.Locale}</div>
                        </div>
                        <div className="flex flex-wrap items-center gap-2 text-xs text-zinc-500">
                          {v.Gender ? <span>{v.Gender}</span> : null}
                          <span>{v.ShortName}</span>
                          {(v.StyleList?.length ?? 0) > 0 ? (
                            <span>{`${v.StyleList?.length} styles`}</span>
                          ) : null}
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>

              <div className="flex items-center justify-end gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  onPress={() => {
                    setFilters({
                      query: "",
                      gender: null,
                      language: null,
                      region: null,
                      multilingualOnly: false,
                      style: null,
                    });
                  }}
                >
                  {t("common.clear")}
                </Button>
              </div>
            </div>
          </Card>

          <div className="flex flex-col gap-6">
            <Card className="p-4">
              <div className="flex flex-col gap-4">
                <div className="text-lg font-semibold">{t("upload.section")}</div>

                <div className="flex flex-col gap-2">
                  <div className="text-sm text-zinc-600 dark:text-zinc-300">
                    {t("upload.file.label")}
                  </div>
                  <input
                    type="file"
                    accept=".pptx"
                    onChange={(e) => {
                      const f = e.target.files?.[0] ?? null;
                      setFile(f);
                      setSubmitError(null);
                    }}
                  />
                  <div className="text-xs text-zinc-500">{t("upload.file.hint")}</div>
                </div>

                {submitError ? (
                  <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950/30 dark:text-red-200">
                    {submitError}
                  </div>
                ) : null}

                <div className="flex items-center justify-end">
                  <Button
                    onPress={onSubmit}
                    isDisabled={!selectedVoice || !file || submitting}
                  >
                    {submitting ? (
                      <>
                        <Spinner size="sm" />
                        <span>{t("upload.submitting")}</span>
                      </>
                    ) : (
                      t("upload.submit")
                    )}
                  </Button>
                </div>
              </div>
            </Card>

            <Card className="p-4">
              <div className="flex flex-col gap-4">
                <div className="text-lg font-semibold">{t("task.section")}</div>

                {tasks.length === 0 ? (
                  <div className="text-sm text-zinc-500">{t("task.empty")}</div>
                ) : (
                  <div className="flex flex-col gap-2">
                    {tasks.map((task) => {
                      const active = task.taskId === activeTaskId;
                      const canDownload =
                        task.status === "COMPLETED" || task.resultReady === true;
                      return (
                        <div
                          key={task.taskId}
                          role="button"
                          tabIndex={0}
                          className={`flex w-full flex-col gap-1 rounded-md border px-3 py-2 text-left text-sm transition-colors ${
                            active
                              ? "border-zinc-400 bg-zinc-50 dark:border-zinc-700 dark:bg-zinc-950"
                              : "border-zinc-200 hover:bg-zinc-50 dark:border-zinc-800 dark:hover:bg-zinc-950"
                          }`}
                          onClick={() => setActiveTaskId(task.taskId)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter" || e.key === " ") {
                              e.preventDefault();
                              setActiveTaskId(task.taskId);
                            }
                          }}
                        >
                          <div className="flex items-center justify-between gap-3">
                            <div className="font-medium">
                              {task.fileName}
                            </div>
                            <Chip
                              size="sm"
                              color={
                                task.status === "FAILED"
                                  ? "danger"
                                  : task.status === "COMPLETED"
                                    ? "success"
                                    : "default"
                              }
                            >
                              {task.status}
                            </Chip>
                          </div>
                          <div className="flex flex-wrap items-center gap-2 text-xs text-zinc-500">
                            <span>{task.voiceName}</span>
                            {task.stage ? <span>{task.stage}</span> : null}
                            {task.percent !== undefined ? <span>{`${Math.round(task.percent)}%`}</span> : null}
                          </div>
                          <div className="flex items-center justify-end gap-2 pt-1">
                            <div onClick={(e) => e.stopPropagation()}>
                              <Button
                                size="sm"
                                variant="outline"
                                isDisabled={!canDownload || downloadBusyId === task.taskId}
                                onPress={() => downloadResult(task)}
                              >
                                {downloadBusyId === task.taskId ? (
                                  <>
                                    <Spinner size="sm" />
                                    <span>{t("task.downloading")}</span>
                                  </>
                                ) : (
                                  t("task.download")
                                )}
                              </Button>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </Card>

            {activeTask ? (
              <Card className="p-4">
                <div className="flex flex-col gap-4">
                  <div className="text-lg font-semibold">{t("progress.section")}</div>
                  <div className="flex flex-col gap-2 text-sm">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="text-zinc-600 dark:text-zinc-300">
                        {t("progress.stage")}: {activeTask.stage ?? "-"}
                      </div>
                      <div className="text-zinc-600 dark:text-zinc-300">
                        {t("progress.slide")}:{" "}
                        {activeTask.slideIdx
                          ? `${activeTask.slideIdx}/${activeTask.totalSlides ?? "-"}`
                          : "-"}
                      </div>
                    </div>

                    <ProgressBar
                      aria-label={t("progress.percent")}
                      className="w-full"
                      value={activeTask.percent ?? 0}
                    >
                      <Label>{t("progress.percent")}</Label>
                      <ProgressBar.Output />
                      <ProgressBar.Track>
                        <ProgressBar.Fill />
                      </ProgressBar.Track>
                    </ProgressBar>

                    {activeTask.error ? (
                      <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950/30 dark:text-red-200">
                        {t("task.failed")}: {activeTask.error}
                      </div>
                    ) : null}
                  </div>
                </div>
              </Card>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  );
}
