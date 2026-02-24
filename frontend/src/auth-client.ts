export type AuthRole = "provider" | "admin";

export type TokenPair = {
  access_token: string;
  refresh_token: string | null;
};

export type AuthVersion = {
  api_version: string;
  refresh_rotation_enabled: boolean;
  rate_limit_policy: string;
  supported_roles: AuthRole[];
};

export type MeResponse = {
  provider_id: string;
  role: AuthRole;
};

export type AuthErrorBody = {
  msg?: string;
  error?: {
    code?: string;
    message?: string;
    request_id?: string;
  };
};

export interface TokenStore {
  getAccessToken(): string | null;
  getRefreshToken(): string | null;
  setTokens(tokens: TokenPair): void;
  clearTokens(): void;
}

export class MemoryTokenStore implements TokenStore {
  private accessToken: string | null = null;
  private refreshToken: string | null = null;

  getAccessToken(): string | null {
    return this.accessToken;
  }

  getRefreshToken(): string | null {
    return this.refreshToken;
  }

  setTokens(tokens: TokenPair): void {
    this.accessToken = tokens.access_token;
    this.refreshToken = tokens.refresh_token;
  }

  clearTokens(): void {
    this.accessToken = null;
    this.refreshToken = null;
  }
}

type RequestOptions = {
  method?: "GET" | "POST";
  body?: unknown;
  auth?: boolean;
};

export class AuthClient {
  private readonly baseUrl: string;
  private readonly tokenStore: TokenStore;
  private authVersion: AuthVersion | null = null;

  constructor(baseUrl: string, tokenStore: TokenStore = new MemoryTokenStore()) {
    this.baseUrl = baseUrl.replace(/\/+$/, "");
    this.tokenStore = tokenStore;
  }

  async getVersion(): Promise<AuthVersion> {
    const response = await this.request<AuthVersion>("/api/auth/version");
    this.authVersion = response;
    return response;
  }

  async register(email: string, password: string): Promise<{ msg: string }> {
    return this.request("/api/auth/register", {
      method: "POST",
      body: { email, password },
    });
  }

  async loginProvider(email: string, password: string): Promise<TokenPair> {
    const tokens = await this.request<TokenPair>("/api/auth/login", {
      method: "POST",
      body: { email, password },
    });
    this.tokenStore.setTokens(tokens);
    return tokens;
  }

  async loginAdmin(email: string, password: string): Promise<TokenPair> {
    const tokens = await this.request<TokenPair>("/api/auth/admin/login", {
      method: "POST",
      body: { email, password },
    });
    this.tokenStore.setTokens(tokens);
    return tokens;
  }

  async me(): Promise<MeResponse> {
    return this.requestWithRefresh<MeResponse>("/api/auth/me", { auth: true });
  }

  async refresh(): Promise<TokenPair> {
    const refreshToken = this.tokenStore.getRefreshToken();
    if (!refreshToken) {
      throw new Error("Missing refresh token.");
    }
    const tokens = await this.request<TokenPair>("/api/auth/refresh", {
      method: "POST",
      auth: false,
    }, refreshToken);
    this.tokenStore.setTokens(tokens);
    return tokens;
  }

  async logout(): Promise<void> {
    const accessToken = this.tokenStore.getAccessToken();
    if (accessToken) {
      try {
        await this.request("/api/auth/logout", {
          method: "POST",
          auth: true,
        });
      } catch {
        // Always clear local state, even when server-side logout call fails.
      }
    }
    this.tokenStore.clearTokens();
  }

  // Generic protected request that retries once after refresh on 401.
  async requestWithRefresh<T>(path: string, options: RequestOptions = {}): Promise<T> {
    try {
      return await this.request<T>(path, { ...options, auth: true });
    } catch (error) {
      if (!(error instanceof AuthHttpError) || error.status !== 401) {
        throw error;
      }
      await this.refresh();
      return this.request<T>(path, { ...options, auth: true });
    }
  }

  private async request<T>(
    path: string,
    options: RequestOptions = {},
    explicitToken?: string
  ): Promise<T> {
    const method = options.method ?? "GET";
    const url = `${this.baseUrl}${path}`;
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };

    const token = explicitToken ?? (options.auth ? this.tokenStore.getAccessToken() : null);
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }

    const response = await fetch(url, {
      method,
      headers,
      body: options.body ? JSON.stringify(options.body) : undefined,
    });

    const text = await response.text();
    const data = text ? (JSON.parse(text) as T | AuthErrorBody) : ({} as T);

    if (!response.ok) {
      const errorBody = data as AuthErrorBody;
      throw new AuthHttpError(
        response.status,
        errorBody.msg || errorBody.error?.message || "Request failed",
        errorBody.error?.request_id
      );
    }

    return data as T;
  }
}

export class AuthHttpError extends Error {
  readonly status: number;
  readonly requestId?: string;

  constructor(status: number, message: string, requestId?: string) {
    super(message);
    this.name = "AuthHttpError";
    this.status = status;
    this.requestId = requestId;
  }
}
