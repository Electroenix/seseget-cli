import type { ReactNode } from "react";
import { AlertTriangle } from "lucide-react";
import type {
  ConfigFieldSchema,
  ConfigObject,
  ConfigSectionSchema,
  FormatOptions,
} from "../types/api";
import ConfigFieldLabel from "./ConfigFieldLabel";
import SecretField from "./SecretField";
import Switch from "./Switch";
import { cx } from "../lib/cx";

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
          .filter(Boolean),
      ),
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
    <div className="divide-y divide-edge-soft">
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
            <section key={fieldId} className="py-4 first:pt-0 last:pb-0">
              <h3 className="mb-2 text-[10px] font-semibold uppercase tracking-[0.14em] text-faint">
                {label}
              </h3>
              <div className="rounded-lg border border-edge-soft bg-canvas/25 px-4 py-3">
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
              </div>
            </section>
          );
        }

        const formatChoices = formatOptions?.[fieldId];
        const fallbackKind = Array.isArray(value)
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
          const extraSelected = selected.filter((item) => !formatChoices.includes(item));
          const allChoices = [...formatChoices, ...extraSelected];

          control = (
            <div className="flex flex-wrap gap-2">
              {allChoices.map((option) => {
                const isExtra = !formatChoices.includes(option);
                return (
                  <label
                    key={option}
                    className={cx(
                      "flex cursor-pointer items-center gap-2 rounded-lg border px-2.5 py-1.5 text-xs transition",
                      selected.includes(option)
                        ? "border-accent/40 bg-accent-soft text-fg"
                        : "border-edge bg-raised text-muted hover:border-[#3a424c]",
                    )}
                    title={isExtra ? "该格式当前未注册" : undefined}
                  >
                    <input
                      className="h-3.5 w-3.5 accent-accent"
                      type="checkbox"
                      checked={selected.includes(option)}
                      onChange={(event) => {
                        const next = event.target.checked
                          ? [...selected, option]
                          : selected.filter((item) => item !== option);
                        onChange(fieldId, next);
                      }}
                    />
                    {option}
                    {isExtra && <AlertTriangle className="h-3 w-3 text-warning" />}
                  </label>
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
              className="field"
              value={arrayValue}
              placeholder="多个值用逗号分隔"
              onChange={(event) =>
                onChange(
                  fieldId,
                  event.target.value
                    .split(",")
                    .map((item) => item.trim())
                    .filter(Boolean),
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
                if (onSecretClear) onSecretClear(fieldId);
                else onChange(fieldId, "");
              }}
            />
          );
        } else if (fieldKind === "bool") {
          control = (
            <Switch
              id={fieldId}
              checked={Boolean(values[fieldId])}
              labelledBy={`${fieldId}-label`}
              onChange={(checked) => onChange(fieldId, checked)}
            />
          );
        } else if (fieldKind === "int") {
          control = (
            <input
              type="number"
              id={fieldId}
              className="field max-w-xs"
              value={Number(values[fieldId])}
              min={meta?.minimum ?? undefined}
              max={meta?.maximum ?? undefined}
              onChange={(event) => onChange(fieldId, Number(event.target.value))}
            />
          );
        } else {
          control = (
            <input
              type="text"
              id={fieldId}
              className="field"
              value={String(values[fieldId] ?? "")}
              onChange={(event) => onChange(fieldId, event.target.value)}
            />
          );
        }

        return (
          <div
            key={fieldId}
            className="grid gap-2 py-4 first:pt-0 last:pb-0 md:grid-cols-[minmax(160px,220px)_minmax(0,1fr)] md:items-center md:gap-6"
          >
            <div className="min-w-0">
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
            <div className="min-w-0">{control}</div>
          </div>
        );
      })}
    </div>
  );
}
