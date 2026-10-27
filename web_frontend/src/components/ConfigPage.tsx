import { useState } from "react";
import type { ReactNode } from "react";
import type {
  ConfigChanges,
  ConfigObject,
  ConfigSchema,
  FormatOptions,
} from "../types/api";
import ConfigFieldBuilder from "./ConfigFieldBuilder";

interface ConfigPageProps {
  config: ConfigObject | null;
  schema: ConfigSchema | null;
  formatOptions: FormatOptions | null;
  secretFields: string[];
  secretConfigured: string[];
  onSave: (changes: ConfigChanges) => Promise<boolean>;
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

function setNestedValue(
  obj: ConfigObject,
  path: string,
  value: unknown
): ConfigObject {
  const keys = path.split(".");
  const result = deepClone(obj);
  let target: Record<string, unknown> = result;
  for (let i = 0; i < keys.length - 1; i++) {
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
    flattenObject(initialConfig)
  );
  const [dirtyPaths, setDirtyPaths] = useState<Set<string>>(new Set());
  const [configuredSecrets, setConfiguredSecrets] = useState<Set<string>>(
    new Set(secretConfigured)
  );
  const [activeSection, setActiveSection] = useState(
    Object.keys(initialConfig)[0] ?? ""
  );
  const [saving, setSaving] = useState(false);

  const sectionKeys = Object.keys(localConfig);
  const activeData = localConfig[activeSection];
  const activeSectionLabel =
    schema?.sections[activeSection]?.label ?? activeSection;
  const canSave = dirtyPaths.size > 0;

  const handleFieldChange = (path: string, value: unknown) => {
    setDirtyPaths((prev) => new Set(prev).add(path));
    setLocalValues((prev) => ({ ...prev, [path]: value }));
    setLocalConfig((prev) => setNestedValue(prev, path, value));

    if (secretFields.includes(path)) {
      setConfiguredSecrets((prev) => {
        const next = new Set(prev);
        if (value === "") {
          next.delete(path);
        } else {
          next.add(path);
        }
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
    try {
      if (dirtyPaths.size > 0) {
        const ok = await onSave(changes);
        if (!ok) return;
        setDirtyPaths(new Set());
      }
    } finally {
      setSaving(false);
    }
  };


  let content: ReactNode;
  if (!activeData || typeof activeData !== "object") {
    content = <p className="text-muted">暂无配置项</p>;
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
      <div className="config-page">
        <div className="config-loading text-muted">加载配置中...</div>
      </div>
    );
  }

  return (
    <div className="config-page">
      <div className="config-page-header">
        <h1 className="config-page-title">配置</h1>
        <button
          type="button"
          className="btn btn-primary btn-sm config-save-button"
          onClick={handleSave}
          disabled={!canSave || saving}
          aria-busy={saving}
        >
          {saving ? "保存中..." : "保存"}
        </button>
      </div>

      <div className="config-layout">
        <aside className="config-nav">
          {sectionKeys.map((key) => (
            <button
              type="button"
              key={key}
              className={`config-nav-item ${
                activeSection === key ? "active" : ""
              }`}
              onClick={() => setActiveSection(key)}
            >
              {schema?.sections[key]?.label ?? key}
            </button>
          ))}
        </aside>

        <main className="config-content">
          <section className="config-card">
            <h2 className="config-section-title">{activeSectionLabel}</h2>
            {content}
          </section>
        </main>
      </div>
    </div>
  );
}
