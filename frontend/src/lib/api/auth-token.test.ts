import { afterEach, describe, expect, it, vi } from "vitest";

import {
  authHeaders,
  refreshAccessToken,
  resetRefreshAccessTokenStateForTests,
  setAuthTokens,
} from "./auth-token";

describe("auth-token refresh", () => {
  afterEach(() => {
    resetRefreshAccessTokenStateForTests();
    localStorage.clear();
    vi.unstubAllGlobals();
  });

  it("refreshes access token from the stored refresh token", async () => {
    localStorage.setItem("atm:refreshToken", "refresh-old");
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        access_token: "access-new",
        refresh_token: "refresh-new",
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(refreshAccessToken()).resolves.toBe(true);
    expect(localStorage.getItem("atm:token")).toBe("access-new");
    expect(localStorage.getItem("atm:refreshToken")).toBe("refresh-new");
    expect(authHeaders()).toEqual({ Authorization: "Bearer access-new" });
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/auth/refresh",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ refresh_token: "refresh-old" }),
      }),
    );
  });

  it("shares one in-flight refresh across concurrent callers", async () => {
    localStorage.setItem("atm:refreshToken", "refresh-old");
    let resolveFetch: ((value: unknown) => void) | null = null;
    const fetchMock = vi.fn().mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveFetch = resolve;
        }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const first = refreshAccessToken();
    const second = refreshAccessToken();
    expect(fetchMock).toHaveBeenCalledTimes(1);

    resolveFetch?.({
      ok: true,
      json: async () => ({ access_token: "access-shared", refresh_token: "refresh-shared" }),
    });

    await expect(Promise.all([first, second])).resolves.toEqual([true, true]);
    expect(localStorage.getItem("atm:token")).toBe("access-shared");
  });

  it("returns false when no refresh token is stored", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    await expect(refreshAccessToken()).resolves.toBe(false);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("setAuthTokens stores both tokens for subsequent requests", () => {
    setAuthTokens("access-a", "refresh-a");
    expect(localStorage.getItem("atm:token")).toBe("access-a");
    expect(localStorage.getItem("atm:refreshToken")).toBe("refresh-a");
  });
});
