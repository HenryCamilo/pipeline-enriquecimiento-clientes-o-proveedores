import type { HTMLAttributes } from "react";

interface Props extends HTMLAttributes<HTMLDivElement> {
  raised?: boolean;
}

export function AppCard({ raised = false, className = "", children, ...rest }: Props) {
  return (
    <div
      className={`${raised ? "ap-surface-2" : "ap-surface"} ${className}`}
      {...rest}
    >
      {children}
    </div>
  );
}
