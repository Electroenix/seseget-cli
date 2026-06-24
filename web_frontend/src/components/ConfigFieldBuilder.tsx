import type { ConfigObject } from "../types/api";

interface ConfigFieldBuilderProps {
  config: ConfigObject;
  prefix?: string;
  values: Record<string, unknown>;
  onChange: (path: string, value: unknown) => void;
}

export default function ConfigFieldBuilder({
  config,
  prefix = "",
  values,
  onChange,
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
              />
            </div>
          );
        }

        const fieldType = typeof value;

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
