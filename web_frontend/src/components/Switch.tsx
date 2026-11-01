import { cx } from "../lib/cx";

interface SwitchProps {
  id?: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
  labelledBy?: string;
  ariaLabel?: string;
}

export default function Switch({
  id,
  checked,
  onChange,
  disabled = false,
  labelledBy,
  ariaLabel,
}: SwitchProps) {
  return (
    <button
      id={id}
      type="button"
      role="switch"
      aria-checked={checked}
      aria-labelledby={labelledBy}
      aria-label={ariaLabel}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={cx(
        "relative inline-flex h-5 w-9 shrink-0 items-center overflow-hidden rounded-full align-middle transition-colors",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/30 focus-visible:ring-offset-2 focus-visible:ring-offset-panel",
        checked ? "bg-accent" : "bg-edge",
        disabled && "cursor-not-allowed opacity-45",
      )}
    >
      <span
        className={cx(
          "pointer-events-none absolute left-[3px] top-[3px] h-3.5 w-3.5 rounded-full bg-white shadow-sm transition-transform",
          checked && "translate-x-4",
        )}
      />
    </button>
  );
}
