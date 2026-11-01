import { HelpCircle } from "lucide-react";

interface ConfigFieldLabelProps {
  label: string;
  description?: string;
  htmlFor?: string;
  titleId?: string;
  asTitle?: boolean;
}

export default function ConfigFieldLabel({
  label,
  description,
  htmlFor,
  titleId,
  asTitle = false,
}: ConfigFieldLabelProps) {
  return (
    <div className="flex items-center gap-1.5">
      {asTitle ? (
        <span id={titleId} className="text-xs font-medium text-fg">
          {label}
        </span>
      ) : (
        <label htmlFor={htmlFor} className="text-xs font-medium text-fg">
          {label}
        </label>
      )}
      {description && (
        <button
          type="button"
          className="text-faint transition hover:text-accent"
          title={description}
          aria-label={`${label} 说明`}
        >
          <HelpCircle className="h-3.5 w-3.5" />
        </button>
      )}
    </div>
  );
}
