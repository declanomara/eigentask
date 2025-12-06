export type ApiClientConfig = {
  internalBaseUrl: string;
  externalBaseUrl: string;
};

// tasks

export type TaskStatus = "BACKLOG" | "PLANNED" | "COMPLETED" | "REMOVED";

export type Task = {
  id: number;
  title: string;
  description: string | null;
  status: TaskStatus;
  due_at: string | null;
  planned_start_at: string | null;
  planned_end_at: string | null;
  planned_duration: number | null;
  created_at: string;
  updated_at: string;
};

export type CreateTaskRequest = {
  title: string;
  description?: string | null;
  status?: TaskStatus;
  due_at?: string | null;
  planned_start_at?: string | null;
  planned_end_at?: string | null;
  planned_duration?: number | null;
};

export type UpdateTaskRequest = {
  title?: string;
  description?: string | null;
  status?: TaskStatus;
  due_at?: string | null;
  planned_start_at?: string | null;
  planned_end_at?: string | null;
  planned_duration?: number | null;
};

export type DeleteTaskRequest = {
  id: number;
};

export type CreateTaskResult = {
  ok: boolean;
  task?: Task;
  status?: number;
  error?: string;
};

export type UpdateTaskResult = {
  ok: boolean;
  task?: Task;
  status?: number;
  error?: string;
};

export type DeleteTaskResult = {
  ok: boolean;
  status?: number;
  error?: string;
};

export type GetTasksResult = {
  ok: boolean;
  tasks: Task[];
  status?: number;
  error?: string;
};

// auth

export type User = {
  sub: string;
  preferred_username: string;
  email: string;
  name: string;
  roles: string[];
};

export type AuthStatus = {
  authenticated: boolean;
  user?: User;
};

export type AuthStatusResult = {
  ok: boolean;
  auth?: AuthStatus;
  status?: number;
  error?: string;
};

export function createApiClient(config: ApiClientConfig) {
  const internalBaseUrl = config.internalBaseUrl.replace(/\/$/, "");
  const externalBaseUrl = config.externalBaseUrl.replace(/\/$/, "");

  const tasksEndpoint = "/tasks/";
  const authEndpoint = "/auth/";

  function buildUrl(path: string) {
    if (path.startsWith("http")) return path;
    const p = path.startsWith("/") ? path : `/${path}`;
    return `${internalBaseUrl}${p}`;
  }

  async function request(
    path: string,
    init: RequestInit,
    cookie?: string,
  ): Promise<Response> {
    const url = buildUrl(path);
    const headers = new Headers(init.headers ?? {});
    if (cookie) headers.set("Cookie", cookie);
    headers.set("Accept", "application/json");
    headers.set("Connection", "close");
    const reqInit: RequestInit = {
      ...init,
      headers,
      redirect: "manual", // don't auto-follow
      credentials: "include",
    };
    return await fetch(url, reqInit);
  }

  return {
    getTasks: async (cookie?: string): Promise<GetTasksResult> => {
      const res = await request(tasksEndpoint, { method: "GET" }, cookie);
      const status = res.status;
      if (res.ok) {
        const tasks = (await res.json()) as Task[];
        return { ok: true, tasks, status };
      }
      const text = await res.text().catch(() => "");
      return {
        ok: false,
        tasks: [],
        status,
        error: `API error: ${status} ${text}`,
      };
    },

    createTask: async (
      input: CreateTaskRequest,
      cookie?: string,
    ): Promise<CreateTaskResult> => {
      const res = await request(
        tasksEndpoint,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
            Connection: "close",
          },
          body: JSON.stringify(input),
        },
        cookie,
      );
      const status = res.status;
      if (res.ok) {
        const task = (await res.json()) as Task;
        return { ok: true, task, status };
      }
      const text = await res.text().catch(() => "");
      return { ok: false, status, error: `Create failed: ${status} ${text}` };
    },
    updateTask: async (
      id: number,
      input: UpdateTaskRequest,
      cookie?: string,
    ): Promise<UpdateTaskResult> => {
      const res = await request(
        `${tasksEndpoint}${id}`,
        {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
            Connection: "close",
          },
          body: JSON.stringify(input),
        },
        cookie,
      );
      const status = res.status;
      if (res.ok) {
        const task = (await res.json()) as Task;
        return { ok: true, task, status };
      }
      const text = await res.text().catch(() => "");
      return { ok: false, status, error: `Update failed: ${status} ${text}` };
    },

    deleteTask: async (
      id: number,
      cookie?: string,
    ): Promise<DeleteTaskResult> => {
      const res = await request(
        `${tasksEndpoint}${id}`,
        {
          method: "DELETE",
          headers: {
            Accept: "application/json",
            Connection: "close",
          },
        },
        cookie,
      );
      const status = res.status;
      if (res.ok || status === 204) {
        return { ok: true, status };
      }
      const text = await res.text().catch(() => "");
      return { ok: false, status, error: `Delete failed: ${status} ${text}` };
    },
    authStatus: async (cookie?: string): Promise<AuthStatusResult> => {
      const res = await request(
        `${authEndpoint}status`,
        {
          method: "GET",
          headers: {
            Accept: "application/json",
            Connection: "close",
          },
        },
        cookie,
      );
      const status = res.status;
      if (res.ok) {
        const auth = (await res.json()) as AuthStatus;
        return { ok: true, auth, status };
      }
      const text = await res.text().catch(() => "");
      return {
        ok: false,
        status,
        error: `Auth status failed: ${status} ${text}`,
      };
    },

    internalBaseUrl,
    externalBaseUrl,
  };
}
