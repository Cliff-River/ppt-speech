export type ApiErrorBody = {
  code?: string;
  detail?: string;
};

export class ApiError extends Error {
  status: number;
  body?: ApiErrorBody;

  constructor(message: string, status: number, body?: ApiErrorBody) {
    super(message);
    this.status = status;
    this.body = body;
  }
}

export async function apiFetch<T>(
  input: RequestInfo | URL,
  init?: RequestInit,
): Promise<T> {
  const res = await fetch(input, init);
  if (res.ok) {
    return (await res.json()) as T;
  }

  let body: ApiErrorBody | undefined;
  try {
    body = (await res.json()) as ApiErrorBody;
  } catch {
    body = undefined;
  }

  const message = body?.detail ?? `Request failed (${res.status})`;
  throw new ApiError(message, res.status, body);
}

