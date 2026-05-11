import type { HTMLAttributes, TableHTMLAttributes, ThHTMLAttributes, TdHTMLAttributes } from "react";

export function AppTable({ className = "", children, ...rest }: TableHTMLAttributes<HTMLTableElement>) {
  return (
    <div className="ap-surface overflow-hidden p-0">
      <div className="ap-scrollbar overflow-x-auto">
        <table className={`w-full text-sm ${className}`} {...rest}>
          {children}
        </table>
      </div>
    </div>
  );
}

export function AppThead({ className = "", children, ...rest }: HTMLAttributes<HTMLTableSectionElement>) {
  return (
    <thead
      className={`border-b border-[var(--app-border)] bg-[var(--app-surface-2)] ${className}`}
      {...rest}
    >
      {children}
    </thead>
  );
}

export function AppTh({ className = "", children, ...rest }: ThHTMLAttributes<HTMLTableCellElement>) {
  return (
    <th
      className={`px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-[var(--app-text-muted)] ${className}`}
      {...rest}
    >
      {children}
    </th>
  );
}

export function AppTd({ className = "", children, ...rest }: TdHTMLAttributes<HTMLTableCellElement>) {
  return (
    <td
      className={`px-4 py-3 text-[var(--app-text)] ${className}`}
      {...rest}
    >
      {children}
    </td>
  );
}
