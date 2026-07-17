const ACCESS_TOKEN_KEY = "atm:token";
const REFRESH_TOKEN_KEY = "atm:refreshToken";

let refreshInFlight: Promise<boolean> | null = null;

export function getAccessToken(): string | null {
  try {
    return localStorage.getItem(ACCESS_TOKEN_KEY);
  } catch {
    return null;
  }
}

export function getRefreshToken(): string | null {
  try {
    return localStorage.getItem(REFRESH_TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setAuthTokens(accessToken: string, refreshToken?: string | null): void {
  try {
    localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
    if (refreshToken) {
      localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
    }
  } catch {
    // ignore storage errors
  }
}

export function authHeaders(): Record<string, string> {
  const token = getAccessToken();
  if (token) {
    return { Authorization: `Bearer ${token}` };
  }
  return {};
}

/**
 * Exchange the stored refresh token for a new access token.
 * Concurrent callers share one in-flight request (single-flight).
 */
export async function refreshAccessToken(): Promise<boolean> {
  if (refreshInFlight) {
    return refreshInFlight;
  }

  refreshInFlight = (async () => {
    const refreshToken = getRefreshToken();
    if (!refreshToken) {
      return false;
    }

    try {
      const response = await fetch("/api/v1/auth/refresh", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      if (!response.ok) {
        return false;
      }

      const data = (await response.json()) as {
        access_token?: string;
        refresh_token?: string | null;
      };
      if (!data.access_token) {
        return false;
      }

      setAuthTokens(data.access_token, data.refresh_token);
      return true;
    } catch {
      return false;
    } finally {
      refreshInFlight = null;
    }
  })();

  return refreshInFlight;
}

/** Test helper — clears the in-flight refresh latch. */
export function resetRefreshAccessTokenStateForTests(): void {
  refreshInFlight = null;
}
