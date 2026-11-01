import { useCallback, useState } from "react";
import type {
  ConfigChanges,
  ConfigObject,
  ConfigSchema,
  FormatOptions,
} from "../types/api";
import {
  fetchConfigSchema,
  fetchFormatOptions,
  fetchSettings,
  saveSettings,
} from "../api/client";

export function useConfigSettings() {
  const [data, setData] = useState<ConfigObject | null>(null);
  const [secretFields, setSecretFields] = useState<string[]>([]);
  const [secretConfigured, setSecretConfigured] = useState<string[]>([]);
  const [schema, setSchema] = useState<ConfigSchema | null>(null);
  const [formatOptions, setFormatOptions] = useState<FormatOptions | null>(null);

  const load = useCallback(async () => {
    try {
      const formatsPromise = fetchFormatOptions().catch((err) => {
        console.error("Failed to load format options:", err);
        return null;
      });
      const schemaPromise = fetchConfigSchema().catch((err) => {
        console.error("Failed to load config schema:", err);
        return null;
      });
      const [mainResponse, formatsResponse, schemaResponse] = await Promise.all([
        fetchSettings(),
        formatsPromise,
        schemaPromise,
      ]);
      setData(mainResponse.data.config);
      setSecretFields(mainResponse.data.secret_fields);
      setSecretConfigured(mainResponse.data.secret_configured);
      setSchema(schemaResponse?.data ?? null);
      setFormatOptions(formatsResponse?.data ?? null);
    } catch (err) {
      console.error("Failed to load config:", err);
    }
  }, []);

  const save = useCallback(async (changes: ConfigChanges) => {
    try {
      const response = await saveSettings(changes);
      if (response.code !== 200) {
        return { ok: false, message: response.message || "保存配置失败" };
      }
      return { ok: true };
    } catch (err) {
      console.error("Failed to save config:", err);
      return { ok: false, message: "保存配置失败" };
    }
  }, []);

  return {
    data,
    secretFields,
    secretConfigured,
    schema,
    formatOptions,
    load,
    save,
  };
}
