import { cn } from "@/lib/utils";

/** Uppercase section label used on job detail, profile cards, etc. */
export function SectionEyebrow({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <h3
      className={cn(
        "text-xs font-bold tracking-widest uppercase text-muted-foreground mb-3",
        className,
      )}
    >
      {children}
    </h3>
  );
}
