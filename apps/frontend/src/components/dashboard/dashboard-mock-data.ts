export type DashboardStat = {
  label: string;
  value: string;
  detail?: string;
};

export type CondensedMatchJob = {
  id: string;
  title: string;
  company: string;
  location: string;
  matchScore: number;
  matchedSkills: string[];
  salaryLabel: string | null;
};

export type ActivityItem = {
  id: string;
  icon: "sparkle" | "external" | "whatsapp" | "file" | "eye";
  title: string;
  time: string;
};

export const MOCK_DASHBOARD = {
  userName: "Chanda",
  whatsappMatchesToday: 3,
  stats: [
    { label: "Matches this period", value: "12/25" },
    { label: "Applications sent", value: "7" },
    { label: "CV views", value: "12", detail: "by 4 companies" },
    { label: "CVs generated", value: "4" },
  ] satisfies DashboardStat[],
  topMatches: [
    {
      id: "job-1",
      title: "Senior Financial Analyst",
      company: "Zanaco",
      location: "Lusaka",
      matchScore: 92,
      matchedSkills: ["Excel", "IFRS", "Financial modelling"],
      salaryLabel: "K18k–K22k",
    },
    {
      id: "job-2",
      title: "Operations Manager",
      company: "Trade Kings",
      location: "Ndola",
      matchScore: 87,
      matchedSkills: ["Supply chain", "Leadership", "SAP"],
      salaryLabel: "K15k–K20k",
    },
    {
      id: "job-3",
      title: "Marketing Coordinator",
      company: "Airtel Zambia",
      location: "Lusaka",
      matchScore: 81,
      matchedSkills: ["Campaigns", "Social media", "Analytics"],
      salaryLabel: null,
    },
  ] satisfies CondensedMatchJob[],
  profileCompleteness: 78,
  profileHints: ["Add salary expectation", "Upload a second CV version"],
  recentActivity: [
    {
      id: "a1",
      icon: "sparkle",
      title: "New match: Senior Financial Analyst at Zanaco",
      time: "2h ago",
    },
    {
      id: "a2",
      icon: "external",
      title: "You applied via email — Operations Manager, Trade Kings",
      time: "Yesterday",
    },
    {
      id: "a3",
      icon: "whatsapp",
      title: "WhatsApp summary delivered (3 matches)",
      time: "07:30 today",
    },
    {
      id: "a4",
      icon: "eye",
      title: "CV viewed by 2 recruiters",
      time: "Mon",
    },
  ] satisfies ActivityItem[],
  currentTier: "Mwezi",
  upgradeTier: "Bwino",
} as const;
