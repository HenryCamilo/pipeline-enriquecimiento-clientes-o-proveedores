import type { InputHTMLAttributes } from "react";

interface Props extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  hint?: string;
}

export function AppInput({ label, hint, className = "", id, ...rest }: Props) {
  return (
    <div className="flex flex-col gap-1">
      {label && (
        <label className="ap-label" htmlFor={id}>
          {label}
        </label>
      )}
      <input id={id} className={`ap-input ${className}`} {...rest} />
      {hint && <span className="ap-hint">{hint}</span>}
    </div>
  );
}
