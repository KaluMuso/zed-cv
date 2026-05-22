/** e.g. "FRIDAY, 22 MAY 2026" */
export function formatDashboardHeaderDate(date: Date): string {
  const weekday = date.toLocaleDateString("en-GB", { weekday: "long" });
  const day = date.getDate();
  const month = date.toLocaleDateString("en-GB", { month: "long" });
  const year = date.getFullYear();
  return `${weekday.toUpperCase()}, ${day} ${month.toUpperCase()} ${year}`;
}
