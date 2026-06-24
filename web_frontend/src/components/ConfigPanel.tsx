import { useState } from "react";
import Modal from "react-bootstrap/Modal";
import type { ConfigObject } from "../types/api";
import ConfigFieldBuilder from "./ConfigFieldBuilder";

/** 侧边栏中 Web 标签页的标识键 */
const WEB_TAB_KEY = "__web__";

interface ConfigPanelProps {
  open: boolean;
  config: ConfigObject | null;
  webConfig: ConfigObject | null;
  onSave: (config: ConfigObject) => void;
  onSaveWeb: (config: ConfigObject) => void;
  onClose: () => void;
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

export default function ConfigPanel({
  open,
  config,
  webConfig,
  onSave,
  onSaveWeb,
  onClose,
}: ConfigPanelProps) {
  // 主配置本地状态
  const initConfig = config ? deepClone(config) : {};
  const initValues = config ? flattenObject(initConfig) : {};
  const initKeys = Object.keys(initConfig);
  const [localConfig, setLocalConfig] = useState<ConfigObject>(initConfig);
  const [localValues, setLocalValues] = useState<Record<string, unknown>>(initValues);

  // Web 配置本地状态
  const initWebConfig = webConfig ? deepClone(webConfig) : {};
  const initWebValues = webConfig ? flattenObject(initWebConfig) : {};
  const [localWebConfig, setLocalWebConfig] = useState<ConfigObject>(initWebConfig);
  const [localWebValues, setLocalWebValues] = useState<Record<string, unknown>>(initWebValues);

  const [activeSection, setActiveSection] = useState<string>(
    initKeys.length > 0 ? initKeys[0] : (webConfig && Object.keys(webConfig).length > 0 ? WEB_TAB_KEY : "")
  );

  // 主配置字段变更
  const handleFieldChange = (path: string, value: unknown) => {
    setLocalValues((prev) => ({ ...prev, [path]: value }));
    setLocalConfig((prev) => setNestedValue(prev, path, value));
  };

  // Web 配置字段变更
  const handleWebFieldChange = (path: string, value: unknown) => {
    setLocalWebValues((prev) => ({ ...prev, [path]: value }));
    setLocalWebConfig((prev) => setNestedValue(prev, path, value));
  };

  const handleSave = () => {
    if (activeSection === WEB_TAB_KEY) {
      onSaveWeb(localWebConfig);
    } else {
      onSave(localConfig);
    }
  };

  const sectionKeys = Object.keys(localConfig);
  const showWebTab = localWebConfig && Object.keys(localWebConfig).length > 0;

  // 当前渲染的数据
  const isWebTab = activeSection === WEB_TAB_KEY;
  const activeData = isWebTab ? localWebConfig : localConfig[activeSection];

  return (
    <Modal show={open} onHide={onClose} size="xl" centered>
      <Modal.Header closeButton className="py-2">
        <Modal.Title className="fs-5">配置中心</Modal.Title>
      </Modal.Header>
      <Modal.Body className="p-0">
        {sectionKeys.length === 0 && !showWebTab ? (
          <p className="text-muted text-center py-5">暂无配置项</p>
        ) : (
          <div className="d-flex" style={{ height: "60vh" }}>
            <div
              className="config-sidebar border-end"
              style={{
                width: "180px",
                minWidth: "180px",
              }}
            >
              <div className="list-group list-group-flush h-100" style={{overflow: "auto"}}>
                {sectionKeys.map((key) => (
                  <button
                    key={key}
                    className={`list-group-item list-group-item-action py-3 px-3 border-0 ${
                      activeSection === key ? "active" : ""
                    }`}
                    onClick={() => setActiveSection(key)}
                  >
                    <span className="small fw-medium">{key}</span>
                  </button>
                ))}
                {showWebTab && (
                  <button
                    className={`list-group-item list-group-item-action py-3 px-3 border-0 ${
                      isWebTab ? "active" : ""
                    }`}
                    onClick={() => setActiveSection(WEB_TAB_KEY)}
                  >
                    <span className="small fw-medium">web</span>
                  </button>
                )}
              </div>
            </div>

            <div
              className="flex-grow-1 p-4"
              style={{ overflowY: "auto" }}
            >
              {activeData !== undefined && (
                <>
                  <h6 className="text-muted text-uppercase small mb-3">
                    {isWebTab ? "WEB" : activeSection}
                  </h6>
                  {typeof activeData === "object" &&
                  activeData !== null &&
                  !Array.isArray(activeData) ? (
                    <ConfigFieldBuilder
                      config={activeData as ConfigObject}
                      prefix={isWebTab ? "" : activeSection}
                      values={isWebTab ? localWebValues : localValues}
                      onChange={isWebTab ? handleWebFieldChange : handleFieldChange}
                    />
                  ) : (
                    <ConfigFieldBuilder
                      config={
                        isWebTab
                          ? localWebConfig
                          : { [activeSection]: activeData as never }
                      }
                      values={isWebTab ? localWebValues : localValues}
                      onChange={isWebTab ? handleWebFieldChange : handleFieldChange}
                    />
                  )}
                </>
              )}
            </div>
          </div>
        )}
      </Modal.Body>
      <Modal.Footer className="py-2">
        <button className="btn btn-outline-secondary btn-sm" onClick={onClose}>
          取消
        </button>
        <button
          className="btn btn-primary btn-sm"
          onClick={handleSave}
        >
          <i className="bi bi-check-lg me-1" />
          保存
        </button>
      </Modal.Footer>
    </Modal>
  );
}
