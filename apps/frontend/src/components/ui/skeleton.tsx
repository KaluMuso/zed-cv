import { cn } from "@/lib/utils";

function Skeleton({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="skeleton"
      className={cn(
        "rounded-md bg-gradient-to-r from-surface via-border to-surface bg-[length:200%_100%] animate-shimmer dark:from-surface-dark dark:via-border-dark dark:to-surface-dark",
        className
      )}
      {...props}
    />
  );
}

export { Skeleton };
