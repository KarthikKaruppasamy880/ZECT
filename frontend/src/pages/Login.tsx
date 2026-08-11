import { useEffect, useState } from "react";
import { getAuthConfig, login } from "@/lib/api";
import { buildAuthorizeUrl, exchangeOidcToken, isMsalConfigured } from "@/lib/auth/msal";

interface LoginProps {
  onLogin: (token: string) => void;
}

export default function Login({ onLogin }: LoginProps) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [authMode, setAuthMode] = useState("local");
  const [oidcEnabled, setOidcEnabled] = useState(false);

  useEffect(() => {
    getAuthConfig()
      .then((c) => {
        setAuthMode(c.auth_mode);
        setOidcEnabled(c.oidc_enabled && (c.oidc_configured || isMsalConfigured()));
      })
      .catch(() => {});

    // Handle implicit fragment from Azure redirect
    const hash = window.location.hash.replace(/^#/, "");
    if (hash.includes("access_token=")) {
      const params = new URLSearchParams(hash);
      const access = params.get("access_token");
      if (access) {
        setLoading(true);
        exchangeOidcToken(access)
          .then((r) => {
            window.history.replaceState({}, "", window.location.pathname);
            onLogin(r.token);
          })
          .catch((e) => setError(e instanceof Error ? e.message : "SSO failed"))
          .finally(() => setLoading(false));
      }
    }
  }, [onLogin]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await login(username, password);
      try {
        localStorage.setItem("zect_username", res.username || username);
      } catch {
        /* ignore */
      }
      onLogin(res.token);
    } catch (e) {
      const msg =
        e instanceof Error ? e.message : "Invalid credentials. Please try again.";
      setError(msg || "Invalid credentials. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleOidc = () => {
    const url = buildAuthorizeUrl(username || undefined);
    if (!url) {
      setError("Azure SSO is not configured (set VITE_AZURE_CLIENT_ID / TENANT_ID).");
      return;
    }
    window.location.href = url;
  };

  const showLocal = authMode === "local" || authMode === "hybrid";

  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center">
      <div className="bg-slate-800 rounded-xl shadow-2xl p-8 w-full max-w-md border border-slate-700">
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 mb-4">
            <div className="w-10 h-10 rounded-lg bg-teal-600 flex items-center justify-center text-white font-bold text-xl">
              Z
            </div>
            <span className="text-xl font-bold text-white tracking-tight">ZECT</span>
          </div>
          <h1 className="text-2xl font-bold text-white">Welcome Back</h1>
          <p className="text-slate-400 mt-1 text-sm">
            Sign in to Mentrix Control Tower
          </p>
        </div>

        {showLocal && (
          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1.5">
                Email
              </label>
            <input
              data-testid="login-username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="you@company.com"
              className="w-full px-4 py-2.5 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent"
              required
            />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1.5">
                Password
              </label>
            <input
              data-testid="login-password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Local password"
              className="w-full px-4 py-2.5 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent"
              required
            />
            <p className="mt-1.5 text-xs text-slate-500" data-testid="login-local-hint">
              Local auth uses the account configured in backend/.env (ZECT_USERNAME /
              ZECT_PASSWORD). SSO / Azure AD can be enabled later — not required for
              Companion.
            </p>
            </div>

            {error && (
              <div className="bg-red-900/50 border border-red-700 text-red-300 px-4 py-2.5 rounded-lg text-sm">
                {error}
              </div>
            )}

            <button
              data-testid="login-submit"
              type="submit"
              disabled={loading}
              className="w-full py-2.5 bg-teal-600 hover:bg-teal-700 disabled:bg-teal-800 disabled:cursor-not-allowed text-white rounded-lg font-medium transition-colors"
            >
              {loading ? "Signing in..." : "Sign In"}
            </button>
          </form>
        )}

        {oidcEnabled && (
          <div className={showLocal ? "mt-4" : ""}>
            {showLocal && (
              <div className="relative my-4">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-slate-600" />
                </div>
                <div className="relative flex justify-center text-xs">
                  <span className="bg-slate-800 px-2 text-slate-500">or</span>
                </div>
              </div>
            )}
            {!showLocal && error && (
              <div className="bg-red-900/50 border border-red-700 text-red-300 px-4 py-2.5 rounded-lg text-sm mb-4">
                {error}
              </div>
            )}
            <button
              type="button"
              onClick={handleOidc}
              disabled={loading}
              className="w-full py-2.5 bg-slate-700 hover:bg-slate-600 text-white rounded-lg font-medium border border-slate-600"
            >
              Sign in with Microsoft
            </button>
          </div>
        )}

        <p className="mt-6 text-center text-xs text-slate-500">
          Mentrix · Engineering Delivery Platform
        </p>
      </div>
    </div>
  );
}
