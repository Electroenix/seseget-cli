import { useState, type FormEvent } from "react";
import { KeyRound, Library, LoaderCircle, ShieldCheck } from "lucide-react";
import { useAuth } from "../contexts/AuthContext";
import { verifyToken } from "../api/client";
import { Button } from "./ui";

interface LoginPageProps {
  version?: string;
}

export default function LoginPage({ version }: LoginPageProps) {
  const { login } = useAuth();
  const [value, setValue] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
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
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-canvas px-4">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_50%_18%,rgba(216,112,147,0.13),transparent_34rem)]" />
      <div className="relative w-full max-w-sm">
        <div className="mb-5 flex flex-col items-center text-center">
          <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-2xl border border-accent/25 bg-accent-soft text-accent">
            <Library className="h-6 w-6" />
          </div>
          <h1 className="text-lg font-semibold tracking-wide">seseGet</h1>
          <p className="mt-1 text-xs text-muted">Download Workbench</p>
        </div>

        <div className="panel p-5">
          <div className="mb-4 flex items-center gap-2 border-b border-edge pb-3">
            <ShieldCheck className="h-4 w-4 text-accent" />
            <div>
              <div className="text-sm font-medium">需要认证</div>
              <div className="text-[11px] text-faint">输入服务端生成的访问 Token</div>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="token" className="field-label">
                Auth Token
              </label>
              <div className="relative">
                <KeyRound className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-faint" />
                <input
                  id="token"
                  type="password"
                  className={`field pl-9 font-mono text-xs ${error ? "border-danger/60" : ""}`}
                  placeholder="输入 Token..."
                  value={value}
                  onChange={(event) => setValue(event.target.value)}
                  autoComplete="current-password"
                  autoFocus
                />
              </div>
              {error && <p className="mt-1.5 text-[11px] text-danger">{error}</p>}
            </div>

            <Button
              type="submit"
              variant="primary"
              className="w-full"
              disabled={loading}
            >
              {loading ? (
                <>
                  <LoaderCircle className="h-4 w-4 animate-spin" />
                  验证中...
                </>
              ) : (
                "进入工作台"
              )}
            </Button>
          </form>
        </div>

        {version && (
          <p className="mt-4 text-center font-mono text-[10px] text-faint">
            seseGet v{version}
          </p>
        )}
      </div>
    </div>
  );
}
