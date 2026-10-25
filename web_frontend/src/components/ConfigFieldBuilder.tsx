import type { ConfigObject, FormatOptions } from "../types/api";

interface ConfigFieldBuilderProps {
  config: ConfigObject;
  prefix?: string;
  values: Record<string, unknown>;
  onChange: (path: string, value: unknown) => void;
  formatOptions?: FormatOptions | null;
  secretFields?: string[];
  secretConfigured?: string[];
  onSecretClear?: (path: string) => void;
}

function normalizeStringArray(value: unknown): string[] {
  if (Array.isArray(value)) {
    return Array.from(new Set(value.map(String)));
  }
  if (typeof value === "string" && value.trim()) {
    return Array.from(
      new Set(
        value
          .split(",")
          .map((item) => item.trim())
          .filter(Boolean)
      )
    );
  }
  return [];
}

export default function ConfigFieldBuilder({
  config,
  prefix = "",
  values,
  onChange,
  formatOptions,
  secretFields = [],
  secretConfigured = [],
  onSecretClear,
}: ConfigFieldBuilderProps) {
  return (
    <>
      {Object.entries(config).map(([key, value]) => {
        const fieldId = prefix ? `${prefix}.${key}` : key;
        const isNested =
          value !== null && typeof value === "object" && !Array.isArray(value);

        if (isNested) {
          const nestedObj = value as ConfigObject;
          if (Object.keys(nestedObj).length === 0) return null;

          return (
            <div className="config-sub-section" key={fieldId}>
              <div className="config-sub-title" id={`list-item-${key}`}>
                {key}
              </div>
              <ConfigFieldBuilder
                config={nestedObj}
                prefix={fieldId}
                values={values}
                onChange={onChange}
                formatOptions={formatOptions}
                secretFields={secretFields}
                secretConfigured={secretConfigured}
                onSecretClear={onSecretClear}
              />
            </div>
          );
        }

        const formatChoices = formatOptions?.[fieldId];

        if (formatChoices) {
          const selected = normalizeStringArray(values[fieldId]);
          const extraSelected = selected.filter(
            (item) => !formatChoices.includes(item)
          );
          const allChoices = [...formatChoices, ...extraSelected];

          return (
            <div className="config-field" key={fieldId}>
              <label className="d-block">{key}</label>
              <div className="d-flex flex-wrap gap-3">
                {allChoices.map((option) => {
                  const isExtra = !formatChoices.includes(option);
                  return (
                    <div className="form-check" key={option}>
                      <input
                        className="form-check-input"
                        type="checkbox"
                        id={`${fieldId}-${option}`}
                        checked={selected.includes(option)}
                        onChange={(e) => {
                          const next = e.target.checked
                            ? [...selected, option]
                            : selected.filter((item) => item !== option);
                          onChange(fieldId, next);
                        }}
                      />
                      <label
                        className={`form-check-label small ${
                          isExtra ? "text-warning" : ""
                        }`}
                        htmlFor={`${fieldId}-${option}`}
                        title={isExtra ? "该格式当前未注册" : undefined}
                      >
                        {option}
                        {isExtra ? "（未注册）" : ""}
                      </label>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        }

        if (Array.isArray(value)) {
          const arrayValue = normalizeStringArray(values[fieldId]).join(", ");

          return (
            <div className="config-field" key={fieldId}>
              <label htmlFor={fieldId} className="d-block">
                {key}
              </label>
              <input
                type="text"
                id={fieldId}
                className="form-control form-control-sm"
                value={arrayValue}
                placeholder="多个值用逗号分隔"
                onChange={(e) =>
                  onChange(
                    fieldId,
                    e.target.value
                      .split(",")
                      .map((item) => item.trim())
                      .filter(Boolean)
                  )
                }
                style={{ maxWidth: "100%" }}
              />
            </div>
          );
        }

        const fieldType = typeof value;
        const isSecret = secretFields.includes(fieldId);
        const isConfigured = secretConfigured.includes(fieldId);

        if (isSecret) {
          return (
            <div className="config-field" key={fieldId}>
              <label htmlFor={fieldId} className="d-block">
                {key}
              </label>
              <div className="d-flex align-items-center gap-2">
                <input
                  type="password"
                  id={fieldId}
                  className="form-control form-control-sm"
                  value={String(values[fieldId] ?? "")}
                  placeholder={isConfigured ? "***" : "未设置"}
                  autoComplete="new-password"
                  onChange={(e) => onChange(fieldId, e.target.value)}
                  style={{ maxWidth: "100%" }}
                />
                {isConfigured && (
                  <button
                    type="button"
                    className="btn btn-outline-secondary btn-sm text-nowrap"
                    onClick={() => {
                      if (onSecretClear) {
                        onSecretClear(fieldId);
                      } else {
                        onChange(fieldId, "");
                      }
                    }}
                  >
                    清空
                  </button>
                )}
              </div>
            </div>
          );
        }

        return (
          <div className="config-field" key={fieldId}>
            <label htmlFor={fieldId} className="d-block">
              {key}
            </label>

            {fieldType === "boolean" ? (
              <div className="d-flex align-items-center gap-2">
                <label className="toggle-switch">
                  <input
                    type="checkbox"
                    id={fieldId}
                    checked={Boolean(values[fieldId])}
                    onChange={(e) => onChange(fieldId, e.target.checked)}
                  />
                  <span className="toggle-slider" />
                </label>
                <span className="toggle-label">
                  {values[fieldId] ? "ON" : "OFF"}
                </span>
              </div>
            ) : fieldType === "number" ? (
              <input
                type="number"
                id={fieldId}
                className="form-control form-control-sm"
                value={Number(values[fieldId])}
                onChange={(e) => onChange(fieldId, Number(e.target.value))}
                style={{ maxWidth: "240px" }}
              />
            ) : (
              <input
                type={
                  key.toLowerCase().includes("password") ? "password" : "text"
                }
                id={fieldId}
                className="form-control form-control-sm"
                value={String(values[fieldId] ?? "")}
                onChange={(e) => onChange(fieldId, e.target.value)}
                style={{ maxWidth: "100%" }}
              />
            )}
          </div>
        );
      })}
    </>
  );
}
