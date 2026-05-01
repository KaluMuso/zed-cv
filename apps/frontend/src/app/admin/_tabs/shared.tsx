import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export function formatNgwee(n: number): string {
  return `K${(n / 100).toLocaleString("en-ZM", { maximumFractionDigits: 2 })}`;
}

export function formatDate(s: string | null | undefined): string {
  if (!s) return "—";
  return new Date(s).toLocaleDateString("en-ZM");
}

export function StatCard({
  label,
  value,
  hint,
}: {
  label: string;
  value: string;
  hint?: string;
}) {
  return (
    <Card>
      <CardHeader>
        <CardDescription>{label}</CardDescription>
        <CardTitle className="text-2xl tabular-nums">{value}</CardTitle>
        {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
      </CardHeader>
    </Card>
  );
}
