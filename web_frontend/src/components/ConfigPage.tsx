import { useState } from "react";
import type { ReactNode } from "react";
import { Check, LoaderCircle, Settings2 } from "lucide-react";
import type {
  ConfigChanges,
  ConfigObject,
  ConfigSchema,
  FormatOptions,
} from "../types/api";
import ConfigFieldBuilder from "./ConfigFieldBuilder";
import { Button } from "./ui";
import { cx } from "../lib/cx";

interface ConfigPageProps {
  config: ConfigObject | null;
  schema: ConfigSchema | null;
  formatOptions: FormatOptions | null;
  secretFields: string[];
  secretConfigured: string[];
  onSave: (changes: ConfigChanges) => Promise<{ ok: boolean; message?: string }>;
}

function deepClone<T>(obj: T): T {
  return JSON.parse(JSON.stringify(obj));
}

function flattenObject(obj: ConfigObject, prefix = ""): Record<string, unknown> {
  const result: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(obj)) {
    const path = prefix ? `${prefix}.${key}` : key;
    if (value !== null && typeof value === "object" && !Array.isArray(value)) {
      Object.assign(result, flattenObject(value as ConfigObject, path));
    } else {
      result[path] = value;
    }
  }
  return result;
}

function setNestedValue(obj: ConfigObject, path: string, value: unknown): ConfigObject {
  const keys = path.split(".");
  const result = deepClone(obj);
  let target: Record<string, unknown> = result;
  for (let i = 0; i < keys.length - 1; i += 1) {
    if (!target[keys[i]] || typeof target[keys[i]] !== "object") {
      target[keys[i]] = {};
    }
    target = target[keys[i]] as Record<string, unknown>;
  }
  target[keys[keys.length - 1]] = value;
  return result;
}

export default function ConfigPage({
  config,
  schema,
  formatOptions,
  secretFields,
  secretConfigured,
  onSave,
}: ConfigPageProps) {
  const initialConfig = config ? deepClone(config) : {};
  const [localConfig, setLocalConfig] = useState<ConfigObject>(initialConfig);
  const [localValues, setLocalValues] = useState<Record<string, unknown>>(
    flattenObject(initialConfig),
  );
  const [dirtyPaths, setDirtyPaths] = useState<Set<string>>(new Set());
  const [configuredSecrets, setConfiguredSecrets] = useState<Set<string>>(
    new Set(secretConfigured),
  );
  const [activeSection, setActiveSection] = useState(
    Object.keys(initialConfig)[0] ?? "",
  );
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState("");

  const sectionKeys = Object.keys(localConfig);
  const activeData = localConfig[activeSection];
  const activeSectionLabel = schema?.sections[activeSection]?.label ?? activeSection;
  const canSave = dirtyPaths.size > 0;

  const handleFieldChange = (path: string, value: unknown) => {
    setSaveError("");
    setDirtyPaths((prev) => new Set(prev).add(path));
    setLocalValues((prev) => ({ ...prev, [path]: value }));
    setLocalConfig((prev) => setNestedValue(prev, path, value));

    if (secretFields.includes(path)) {
      setConfiguredSecrets((prev) => {
        const next = new Set(prev);
        if (value === "") next.delete(path);
        else next.add(path);
        return next;
      });
    }
  };

  const handleSecretClear = (path: string) => {
    handleFieldChange(path, "");
  };

  const handleSave = async () => {
    if (!canSave || saving) return;

    const changes: ConfigChanges = {};
    for (const path of dirtyPaths) {
      changes[path] = localValues[path];
    }

    setSaving(true);
    setSaveError("");
    try {
      const result = await onSave(changes);
      if (result.ok) setDirtyPaths(new Set());
      else setSaveError(result.message || "保存配置失败");
    } finally {
      setSaving(false);
    }
  };

  let content: ReactNode;
  if (!activeData || typeof activeData !== "object") {
    content = <p className="py-8 text-center text-xs text-muted">暂无配置项</p>;
  } else {
    content = (
      <ConfigFieldBuilder
        config={activeData as ConfigObject}
        prefix={activeSection}
        values={localValues}
        onChange={handleFieldChange}
        formatOptions={formatOptions}
        fieldSchema={schema?.fields ?? null}
        sectionMeta={schema?.sections ?? null}
        secretFields={secretFields}
        secretConfigured={Array.from(configuredSecrets)}
        onSecretClear={handleSecretClear}
      />
    );
  }

  if (!config) {
    return (
      <div className="flex items-center justify-center gap-2 py-24 text-xs text-muted">
        <LoaderCircle className="h-4 w-4 animate-spin" />
        加载配置中...
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-xs text-muted">
          <Settings2 className="h-4 w-4 text-accent" />
          {canSave ? `${dirtyPaths.size} 项未保存` : "所有更改已保存"}
        </div>
        <Button
          variant="primary"
          onClick={handleSave}
          disabled={!canSave || saving}
          loading={saving}
        >
          {!saving && <Check className="h-4 w-4" />}
          {saving ? "保存中..." : "保存更改"}
        </Button>
      </div>

      {saveError && (
        <div className="rounded-lg border border-danger/30 bg-danger-soft px-3 py-2 text-xs text-danger">
          {saveError}
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-[190px_minmax(0,1fr)]">
        <nav className="panel h-fit p-2 lg:sticky lg:top-20">
          {sectionKeys.map((key) => (
            <button
              type="button"
              key={key}
              className={cx(
                "mb-0.5 flex w-full items-center rounded-md px-3 py-2 text-left text-xs transition last:mb-0",
                activeSection === key
                  ? "bg-accent-soft font-medium text-fg"
                  : "text-muted hover:bg-white/5 hover:text-fg",
              )}
              onClick={() => setActiveSection(key)}
            >
              {schema?.sections[key]?.label ?? key}
            </button>
          ))}
        </nav>

        <section className="panel overflow-hidden">
          <div className="border-b border-edge px-5 py-3">
            <h2 className="text-sm font-semibold text-fg">{activeSectionLabel}</h2>
          </div>
          <div className="px-5 py-4">{content}</div>
        </section>
      </div>
    </div>
  );
}
