import { useId, type InputHTMLAttributes } from "react";

interface Props extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  hint?: string;
}

export function Field({ label, hint, className = "", ...rest }: Props) {
  const id = useId();
  return (
    <div className={className}>
      <label htmlFor={id} className="mb-1.5 block text-sm font-medium">{label}</label>
      <input id={id} className="field" {...rest} />
      {hint && <p className="mt-1.5 text-xs text-dim">{hint}</p>}
    </div>
  );
}
