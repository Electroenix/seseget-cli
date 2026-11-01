import { useState } from "react";
import { Eye, EyeOff, Trash2 } from "lucide-react";
import ConfigFieldLabel from "./ConfigFieldLabel";
import { Button } from "./ui";

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
    <div>
      {showLabel && (
        <ConfigFieldLabel htmlFor={id} label={label} description={description} />
      )}
      <div className="flex items-center gap-2">
        <input
          type={visible ? "text" : "password"}
          id={id}
          className="field font-mono text-xs"
          value={value}
          placeholder={configured ? "********" : "未设置"}
          autoComplete="new-password"
          onChange={(event) => onChange(event.target.value)}
        />
        <Button
          variant="ghost"
          size="sm"
          className="h-8 w-8 px-0"
          onClick={() => setVisible((prev) => !prev)}
          disabled={!hasInput}
          aria-label={`${visible ? "隐藏" : "查看"}${label}`}
          title={visible ? "隐藏内容" : "查看内容"}
        >
          {visible ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
        </Button>
        <Button
          variant="danger"
          size="sm"
          className="h-8 w-8 px-0"
          onClick={() => {
            setVisible(false);
            onClear();
          }}
          disabled={!canClear}
          aria-label={`删除${label}`}
          title="删除该字段的值"
        >
          <Trash2 className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
