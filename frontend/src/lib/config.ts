const trimTrailingSlash = (value: string) => value.trim().replace(/\/+$/, "");

const numberFromEnv = (value: string | undefined, fallback: number) => {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
};

const listFromEnv = (value: string | undefined, fallback: string[]) => {
  const items = value
    ?.split(",")
    .map((item) => item.trim())
    .filter(Boolean);

  return items && items.length > 0 ? items : fallback;
};

const apiBaseUrl = trimTrailingSlash(
  process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api/v1"
);

const wsBaseUrl = trimTrailingSlash(process.env.NEXT_PUBLIC_WS_URL || "");

export const appConfig = {
  appName: process.env.NEXT_PUBLIC_APP_NAME || "AutoApplyAI",
  appTagline:
    process.env.NEXT_PUBLIC_APP_TAGLINE ||
    "AI-powered matching, resume optimization, and automated form filling.",
  appPhase: process.env.NEXT_PUBLIC_APP_PHASE || "Realtime Telemetry",
  apiBaseUrl,
  wsBaseUrl,
  telemetryReconnectMs: numberFromEnv(process.env.NEXT_PUBLIC_TELEMETRY_RECONNECT_MS, 5000),
  telemetryEventLimit: numberFromEnv(process.env.NEXT_PUBLIC_TELEMETRY_EVENT_LIMIT, 50),
  workflowRefreshMs: numberFromEnv(process.env.NEXT_PUBLIC_WORKFLOW_REFRESH_MS, 2000),
  operationsRefreshMs: numberFromEnv(process.env.NEXT_PUBLIC_OPERATIONS_REFRESH_MS, 5000),
  dailyApplicationLimit: numberFromEnv(process.env.NEXT_PUBLIC_DAILY_APPLICATION_LIMIT, 5),
  workflowConcurrencyLimit: numberFromEnv(process.env.NEXT_PUBLIC_WORKFLOW_CONCURRENCY_LIMIT, 5),
  landingTargetJobs: numberFromEnv(process.env.NEXT_PUBLIC_LANDING_TARGET_JOBS, 100),
  matchAccuracyPercent: numberFromEnv(process.env.NEXT_PUBLIC_MATCH_ACCURACY_PERCENT, 99),
  aiModelLabel: process.env.NEXT_PUBLIC_AI_MODEL_LABEL || "AI",
  allowedResumeExtensions: listFromEnv(process.env.NEXT_PUBLIC_ALLOWED_RESUME_EXTENSIONS, [
    ".pdf",
    ".doc",
    ".docx",
  ]),
  maxResumeSizeMb: numberFromEnv(process.env.NEXT_PUBLIC_MAX_RESUME_MB, 10),
  defaultCurrency: process.env.NEXT_PUBLIC_DEFAULT_CURRENCY || "USD",
  currencyOptions: listFromEnv(process.env.NEXT_PUBLIC_CURRENCY_OPTIONS, ["USD", "INR"]),
  remoteOptions: listFromEnv(process.env.NEXT_PUBLIC_REMOTE_OPTIONS, [
    "Remote",
    "Hybrid",
    "On-site",
  ]),
};

export const getTelemetryWebSocketUrl = (token: string) => {
  const baseUrl =
    appConfig.wsBaseUrl ||
    appConfig.apiBaseUrl.replace(/^http/i, (protocol) =>
      protocol.toLowerCase() === "https" ? "wss" : "ws"
    );

  return `${baseUrl}/ws/telemetry?token=${encodeURIComponent(token)}`;
};
