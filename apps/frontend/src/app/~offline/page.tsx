import Link from "next/link";

export const metadata = {
  title: "Offline",
  description: "You are offline. Reconnect to refresh ZedApply.",
};

export default function OfflinePage() {
  return (
    <div className="mx-auto flex min-h-[50vh] max-w-lg flex-col items-center justify-center px-6 py-16 text-center">
      <h1 className="font-display text-2xl font-semibold text-foreground">
        You&apos;re offline
      </h1>
      <p className="mt-3 text-sm text-muted-foreground">
        Cached pages may still work. Reconnect to see fresh job matches and pay
        for upgrades.
      </p>
      <Link
        href="/matches"
        className="mt-6 inline-flex min-h-11 items-center justify-center rounded-md bg-primary-500 px-4 text-sm font-medium text-primary-foreground shadow-soft hover:bg-primary-600"
      >
        Back to matches
      </Link>
    </div>
  );
}
