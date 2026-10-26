import { useState } from "react";
import ConfigFieldLabel from "./ConfigFieldLabel";

interface SecretFieldProps {
  id: string;
  label: string;
  description?: string;
  showLabel?: boolean;
  value: string;
  configured: boolean;
  onChange: (value: string) => void;
  onClear: () => void;
}

export default function SecretField({
  id,
  label,
  description,
  showLabel = true,
  value,
  configured,
  onChange,
  onClear,
}: SecretFieldProps) {
  const [visible, setVisible] = useState(false);
  const hasInput = value.length > 0;
  const canClear = configured || hasInput;

  return (
    <div className="config-field secret-field">
      {showLabel && (
        <ConfigFieldLabel
          htmlFor={id}
          label={label}
          description={description}
        />
      )}
      <div className="d-flex align-items-center gap-2">
        <input
          type={visible ? "text" : "password"}
          id={id}
          className="form-control form-control-sm"
          value={value}
          placeholder={configured ? "********" : "未设置"}
          autoComplete="new-password"
          onChange={(e) => onChange(e.target.value)}
          style={{ maxWidth: "100%" }}
        />
        <button
          type="button"
          className="btn btn-link btn-sm px-1 text-decoration-none"
          onClick={() => setVisible((prev) => !prev)}
          disabled={!hasInput}
          aria-label={`${visible ? "隐藏" : "查看"}${label}`}
          aria-pressed={visible}
          title={visible ? "隐藏内容" : "查看内容"}
        >
          <i className={`bi ${visible ? "bi-eye-slash" : "bi-eye"}`} />
        </button>
        <button
          type="button"
          className="btn btn-outline-danger btn-sm text-nowrap"
          onClick={() => {
            setVisible(false);
            onClear();
          }}
          disabled={!canClear}
          aria-label={`删除${label}`}
          title="删除该字段的值"
        >
          <i className="bi bi-trash me-1" />
          删除
        </button>
      </div>
    </div>
  );
}
