import { env as privateEnv } from "$env/dynamic/private";
import { env as publicEnv } from "$env/dynamic/public";
import { createApiClient } from "./apiClient";

export function createApiClientForRequest() {
  return createApiClient({
    internalBaseUrl: privateEnv.API_ORIGIN ?? "DEFAULT_INTERNAL_BASE_URL",
    externalBaseUrl: publicEnv.PUBLIC_API_ORIGIN ?? "DEFAULT_EXTERNAL_BASE_URL",
  });
}

