import type { ReactNode } from "react";
import type {
  ConfigFieldSchema,
  ConfigObject,
  ConfigSectionSchema,
  FormatOptions,
} from "../types/api";
import ConfigFieldLabel from "./ConfigFieldLabel";
import SecretField from "./SecretField";

interface ConfigFieldBuilderProps {
  config: ConfigObject;
  prefix?: string;
  values: Record<string, unknown>;
  onChange: (path: string, value: unknown) => void;
  formatOptions?: FormatOptions | null;
  fieldSchema?: Record<string, ConfigFieldSchema> | null;
  sectionMeta?: Record<string, ConfigSectionSchema> | null;
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
  fieldSchema,
  sectionMeta,
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
        const meta = fieldSchema?.[fieldId];
        const label = meta?.label ?? sectionMeta?.[fieldId]?.label ?? key;
        const description = meta?.description;

        if (isNested) {
          const nestedObj = value as ConfigObject;
          if (Object.keys(nestedObj).length === 0) return null;

          return (
            <section className="config-group" key={fieldId}>
              <h3 className="config-group-title">{label}</h3>
              <ConfigFieldBuilder
                config={nestedObj}
                prefix={fieldId}
                values={values}
                onChange={onChange}
                formatOptions={formatOptions}
                fieldSchema={fieldSchema}
                sectionMeta={sectionMeta}
                secretFields={secretFields}
                secretConfigured={secretConfigured}
                onSecretClear={onSecretClear}
              />
            </section>
          );
        }

        const formatChoices = formatOptions?.[fieldId];
        const fallbackKind =
          Array.isArray(value)
            ? "str_list"
            : typeof value === "number"
              ? "int"
              : typeof value === "boolean"
                ? "bool"
                : "str";
        const fieldKind = meta?.kind ?? fallbackKind;

        let control: ReactNode;

        if (formatChoices) {
          const selected = normalizeStringArray(values[fieldId]);
          const extraSelected = selected.filter(
            (item) => !formatChoices.includes(item)
          );
          const allChoices = [...formatChoices, ...extraSelected];

          control = (
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
          );
        } else if (fieldKind === "str_list" || Array.isArray(value)) {
          const arrayValue = normalizeStringArray(values[fieldId]).join(", ");
          control = (
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
            />
          );
        } else if (meta?.secret ?? secretFields.includes(fieldId)) {
          control = (
            <SecretField
              id={fieldId}
              label={label}
              value={String(values[fieldId] ?? "")}
              configured={secretConfigured.includes(fieldId)}
              showLabel={false}
              onChange={(nextValue) => onChange(fieldId, nextValue)}
              onClear={() => {
                if (onSecretClear) {
                  onSecretClear(fieldId);
                } else {
                  onChange(fieldId, "");
                }
              }}
            />
          );
        } else if (fieldKind === "bool") {
          control = (
            <label className="toggle-switch">
              <input
                type="checkbox"
                id={fieldId}
                checked={Boolean(values[fieldId])}
                aria-labelledby={`${fieldId}-label`}
                onChange={(e) => onChange(fieldId, e.target.checked)}
              />
              <span className="toggle-slider" />
            </label>
          );
        } else if (fieldKind === "int") {
          control = (
            <input
              type="number"
              id={fieldId}
              className="form-control form-control-sm"
              value={Number(values[fieldId])}
              onChange={(e) => onChange(fieldId, Number(e.target.value))}
            />
          );
        } else {
          control = (
            <input
              type="text"
              id={fieldId}
              className="form-control form-control-sm"
              value={String(values[fieldId] ?? "")}
              onChange={(e) => onChange(fieldId, e.target.value)}
            />
          );
        }

        return (
          <div className="settings-row" key={fieldId}>
            <div className="settings-label">
              {fieldKind === "bool" ? (
                <ConfigFieldLabel
                  titleId={`${fieldId}-label`}
                  asTitle
                  label={label}
                  description={description}
                />
              ) : (
                <ConfigFieldLabel
                  htmlFor={fieldId}
                  label={label}
                  description={description}
                />
              )}
            </div>
            <div className="settings-control">{control}</div>
          </div>
        );
      })}
    </>
  );
}
