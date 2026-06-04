import type { JobsListPreset } from "@/components/jobs/JobsSidebar";

export type JobFilterCountInput = {
  searchQuery: string;
  searchInput: string;
  location: string;
  sort: "relevance" | "recent" | "closing";
  selectedSkills: string[];
  employmentType: string;
  workArrangement: string;
  showClosed: boolean;
  listPreset: JobsListPreset;
};

/** Non-default filter dimensions for the mobile filters bar label. */
export function countActiveJobFilters(input: JobFilterCountInput): number {
  let count = 0;
  if (input.searchQuery.trim() || input.searchInput.trim()) count += 1;
  if (input.location) count += 1;
  if (input.selectedSkills.length > 0) count += 1;
  if (input.showClosed) count += 1;
  if (input.listPreset !== "all") {
    count += 1;
  } else {
    if (input.sort !== "recent") count += 1;
    if (input.employmentType) count += 1;
    if (input.workArrangement) count += 1;
  }
  return count;
}
