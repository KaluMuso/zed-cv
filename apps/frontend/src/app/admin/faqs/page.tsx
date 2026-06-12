"use client";

import dynamic from "next/dynamic";
import { useAuth } from "@/lib/auth";
import { AdminTabLoader } from "../_components/AdminTabLoader";

const FaqsTab = dynamic(
  () => import("../_tabs/FaqsTab").then((m) => ({ default: m.FaqsTab })),
  { loading: () => <AdminTabLoader /> }
);

export default function AdminFaqsPage() {
  const { token } = useAuth();
  if (!token) return null;
  return <FaqsTab token={token} />;
}
