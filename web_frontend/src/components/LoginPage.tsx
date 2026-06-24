import { useState, type FormEvent } from "react";
import { useAuth } from "../contexts/AuthContext";

async function verifyToken(token: string): Promise<boolean> {
  try {
    const response = await fetch("/api/auth/verify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token }),
    });
    return response.ok;
  } catch {
    return false;
  }
}

export default function LoginPage() {
  const { login } = useAuth();
  const [value, setValue] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const trimmed = value.trim();
    if (!trimmed) {
      setError("请输入认证 Token");
      return;
    }

    setLoading(true);
    setError("");

    const ok = await verifyToken(trimmed);
    if (ok) {
      login(trimmed);
    } else {
      setError("Token 无效，请重试");
    }

    setLoading(false);
  };

  return (
    <div
      className="d-flex align-items-center justify-content-center"
      style={{ minHeight: "100vh" }}
    >
      <div className="card bg-dark border-secondary" style={{ width: 400 }}>
        <div className="card-body p-4">
          <div className="text-center mb-4">
            <div
              style={{
                fontSize: "2.5rem",
                color: "var(--bs-primary)",
                marginBottom: "0.5rem",
              }}
            >
              <i className="bi bi-shield-lock" />
            </div>
            <h4 className="text-light mb-1">seseGet</h4>
          </div>

          <form onSubmit={handleSubmit}>
            <div className="mb-3">
              <label htmlFor="token" className="form-label text-light small">
                Auth Token
              </label>
              <input
                id="token"
                type="password"
                className={`form-control bg-dark text-light border-secondary ${error ? "is-invalid" : ""}`}
                placeholder="输入 Token..."
                value={value}
                onChange={(e) => setValue(e.target.value)}
                autoFocus
              />
              {error && (
                <div className="invalid-feedback">{error}</div>
              )}
            </div>

            <button
              type="submit"
              className="btn btn-primary w-100"
              disabled={loading}
            >
              {loading ? (
                <>
                  <span
                    className="spinner-border spinner-border-sm me-2"
                    role="status"
                  />
                  验证中...
                </>
              ) : (
                "确认"
              )}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
