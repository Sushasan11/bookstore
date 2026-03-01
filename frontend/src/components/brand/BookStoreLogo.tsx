import { cn } from "@/lib/utils";

interface BookStoreLogoProps {
  /** Controls which parts render */
  variant?: "full" | "icon-only" | "text-only";
  /** Icon size in px (width = height) */
  iconSize?: number;
  /** Extra Tailwind classes for the wrapper */
  className?: string;
  /** Extra Tailwind classes for the text span */
  textClassName?: string;
}

export function BookStoreLogo({
  variant = "full",
  iconSize = 28,
  className,
  textClassName,
}: BookStoreLogoProps) {
  const showIcon = variant === "full" || variant === "icon-only";
  const showText = variant === "full" || variant === "text-only";

  return (
    <span className={cn("inline-flex items-center gap-2", className)}>
      {showIcon && (
        <svg
          width={iconSize}
          height={iconSize}
          viewBox="0 0 32 32"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          aria-hidden="true"
        >
          {/* Left page of open book */}
          <path
            d="M16 26 C16 26 7 22 4 8 L4 8 C4 7 5 6 6 6 L15 6 C15.6 6 16 6.4 16 7 L16 26Z"
            fill="currentColor"
            opacity="0.15"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinejoin="round"
          />
          {/* Right page of open book */}
          <path
            d="M16 26 C16 26 25 22 28 8 L28 8 C28 7 27 6 26 6 L17 6 C16.4 6 16 6.4 16 7 L16 26Z"
            fill="currentColor"
            opacity="0.15"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinejoin="round"
          />
          {/* Center spine */}
          <line
            x1="16"
            y1="7"
            x2="16"
            y2="26"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
          />
          {/* Left page lines (text suggestion) */}
          <line x1="8" y1="11" x2="14" y2="11" stroke="currentColor" strokeWidth="1" strokeLinecap="round" opacity="0.5" />
          <line x1="7" y1="14" x2="14" y2="14" stroke="currentColor" strokeWidth="1" strokeLinecap="round" opacity="0.5" />
          <line x1="7" y1="17" x2="14" y2="17" stroke="currentColor" strokeWidth="1" strokeLinecap="round" opacity="0.5" />
          {/* Right page lines */}
          <line x1="18" y1="11" x2="24" y2="11" stroke="currentColor" strokeWidth="1" strokeLinecap="round" opacity="0.5" />
          <line x1="18" y1="14" x2="25" y2="14" stroke="currentColor" strokeWidth="1" strokeLinecap="round" opacity="0.5" />
          <line x1="18" y1="17" x2="25" y2="17" stroke="currentColor" strokeWidth="1" strokeLinecap="round" opacity="0.5" />
        </svg>
      )}
      {showText && (
        <span
          className={cn(
            "font-semibold tracking-tight",
            textClassName
          )}
        >
          BookStore
        </span>
      )}
    </span>
  );
}
