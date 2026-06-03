"use client";

import { useAuth } from "@/lib/auth";
import { ReviewJobsTab } from "../../_tabs/ReviewJobsTab";

export default function AdminJobReviewPage() {
  const { token } = useAuth();
  if (!token) return null;
  return <ReviewJobsTab token={token} />;
}
