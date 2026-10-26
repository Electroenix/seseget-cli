import { OverlayTrigger, Tooltip } from "react-bootstrap";

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
  const tooltipId = `config-help-${htmlFor ?? titleId ?? label}`;

  return (
    <div className="config-field-label-row">
      {asTitle ? (
        <span id={titleId} className="config-field-title">
          {label}
        </span>
      ) : (
        <label htmlFor={htmlFor} className="config-field-label">
          {label}
        </label>
      )}
      {description && (
        <OverlayTrigger
          placement="top"
          trigger={["hover", "focus"]}
          overlay={<Tooltip id={tooltipId}>{description}</Tooltip>}
        >
          <button
            type="button"
            className="config-help-button"
            aria-label={`${label} 说明`}
          >
            <i className="bi bi-question-circle" />
          </button>
        </OverlayTrigger>
      )}
    </div>
  );
}
