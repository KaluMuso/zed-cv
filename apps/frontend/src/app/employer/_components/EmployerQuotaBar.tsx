export function EmployerQuotaBar({
  used,
  limit,
}: {
  used: number;
  limit: number;
}) {
  const unlimited = limit >= 99999;
  const pct = unlimited ? (used > 0 ? 8 : 0) : Math.min(100, Math.round((used / Math.max(limit, 1)) * 100));

  return (
    <div className="space-y-1.5">
      <div className="flex justify-between text-xs text-muted-foreground">
        <span>Contacts this period</span>
        <span>
          {used}/{unlimited ? "∞" : limit}
        </span>
      </div>
      <div
        className="h-2 w-full rounded-full bg-muted overflow-hidden"
        role="progressbar"
        aria-valuenow={used}
        aria-valuemin={0}
        aria-valuemax={unlimited ? used || 1 : limit}
        aria-label="Contact quota used"
      >
        <div
          className="h-full rounded-full bg-primary transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
