import axiosClient from "@/lib/axios";
import type {
  IntelligenceStats,
  Job,
  OperationsStats,
  ProfileData,
  Resume,
  TokenResponse,
  TelemetryEvent,
  UserAccount,
  WorkflowDetails,
  WorkflowTrace,
} from "@/lib/types";

type Credentials = {
  email: string;
  password: string;
};

type ProfilePayload = {
  full_name: string;
  title: string;
  experience_years: number;
  remote_preference: string;
  salary_expectation: number;
  preferred_currency: string;
  bio: string;
  skills: string[];
  tech_stack: Record<string, string[]>;
  preferred_roles: string[];
  preferred_locations: string[];
  work_authorization: string | null;
};

const dataOf = <T>(request: Promise<{ data: T }>) => request.then((response) => response.data);

export const backendApi = {
  auth: {
    register: (credentials: Credentials) =>
      dataOf(axiosClient.post<UserAccount>("/auth/register", credentials)),
    login: (credentials: Credentials) =>
      dataOf(axiosClient.post<TokenResponse>("/auth/login", credentials)),
    logout: () => dataOf(axiosClient.post<{ message: string }>("/auth/logout")),
    exportData: () => dataOf(axiosClient.get<Record<string, unknown>>("/auth/export")),
    purgeAccount: () => dataOf(axiosClient.delete<{ status: string }>("/auth/purge")),
  },

  profiles: {
    me: () => dataOf(axiosClient.get<ProfileData | null>("/profiles/me")),
    create: (payload: ProfilePayload) => dataOf(axiosClient.post<ProfileData>("/profiles/", payload)),
    update: (payload: ProfilePayload) => dataOf(axiosClient.patch<ProfileData>("/profiles/", payload)),
  },

  resumes: {
    get: (resumeId: string | number) =>
      dataOf(axiosClient.get<Resume>(`/profiles/resumes/${resumeId}`)),
    upload: (file: File) => {
      const formData = new FormData();
      formData.append("file", file);

      return dataOf(
        axiosClient.post<{ status: string; resume_id: number }>("/profiles/resumes/upload", formData, {
          headers: { "Content-Type": "multipart/form-data" },
        })
      );
    },
    delete: (resumeId: number) => dataOf(axiosClient.delete<void>(`/profiles/resumes/${resumeId}`)),
    retry: (resumeId: number) =>
      dataOf(axiosClient.post<{ status: string; resume_id: number }>(`/profiles/resumes/${resumeId}/retry`)),
    approve: (resumeId: string | number, approvedFields: string[]) =>
      dataOf(
        axiosClient.post<{ status: string; synced_fields: string[] }>(
          `/profiles/resumes/${resumeId}/approve`,
          { approved_fields: approvedFields }
        )
      ),
  },

  jobs: {
    list: () => dataOf(axiosClient.get<Job[]>("/jobs/")),
    get: (jobId: number) => dataOf(axiosClient.get<Job>(`/jobs/${jobId}`)),
    scrape: () => dataOf(axiosClient.post<{ task_id: string; status: string }>("/jobs/scrape")),
    analyze: (jobId: number) =>
      dataOf(axiosClient.post<{ task_id: string; status: string }>(`/jobs/${jobId}/analyze`)),
    analyzeScraped: () =>
      dataOf(axiosClient.post<{ triggered_count: number; task_ids: string[] }>("/jobs/analyze-scraped")),
    apply: (jobId: number) =>
      dataOf(axiosClient.post<{ task_id?: string | null; status: string; workflow_id?: number | null }>(`/jobs/${jobId}/apply`)),
    finalize: (jobId: number) =>
      dataOf(axiosClient.post<{ status: string; job_id: number; workflow_id?: number; task_id?: string; new_status: string }>(`/jobs/${jobId}/finalize`)),
  },

  intelligence: {
    stats: () => dataOf(axiosClient.get<IntelligenceStats>("/intelligence/stats")),
    recordOutcome: (jobId: number, payload: { status: string; note?: string }) =>
      dataOf(axiosClient.post<{ status: string }>(`/intelligence/applications/${jobId}/outcome`, payload)),
  },

  operations: {
    stats: () => dataOf(axiosClient.get<OperationsStats>("/operations/stats")),
  },

  workflows: {
    get: (workflowId: number) => dataOf(axiosClient.get<WorkflowDetails>(`/workflows/${workflowId}`)),
    getByJob: (jobId: number) => dataOf(axiosClient.get<WorkflowDetails>(`/workflows/by-job/${jobId}`)),
    retryStep: (workflowId: number, stepId: number) =>
      dataOf(axiosClient.post<{ status: string }>(`/workflows/${workflowId}/steps/${stepId}/retry`)),
    replayLastCheckpoint: (workflowId: number) =>
      dataOf(axiosClient.post<{ status: string; step_id: number }>(`/workflows/${workflowId}/replay-last-checkpoint`)),
    resolveStep: (workflowId: number, stepId: number, payload: Record<string, unknown>) =>
      dataOf(axiosClient.post<{ status: string }>(`/workflows/${workflowId}/steps/${stepId}/resolve`, payload)),
    reportStep: (workflowId: number, stepId: number, note?: string) =>
      dataOf(axiosClient.post<{ status: string }>(`/workflows/${workflowId}/steps/${stepId}/report`, { note })),
    terminate: (workflowId: number, reason?: string) =>
      dataOf(axiosClient.post<{ status: string }>(`/workflows/${workflowId}/terminate`, { reason })),
  },

  transparency: {
    trace: (workflowId: number) => dataOf(axiosClient.get<WorkflowTrace>(`/transparency/trace/${workflowId}`)),
    productEvent: (eventType: string, payload: Record<string, unknown> = {}, resourceId?: string) =>
      dataOf(axiosClient.post<{ status: string }>("/transparency/product-events", {
        event_type: eventType,
        payload,
        resource_id: resourceId,
      })),
  },

  telemetry: {
    history: () => dataOf(axiosClient.get<TelemetryEvent[]>("/ws/history")),
  },
};
