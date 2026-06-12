import Link from "next/link";

const PLANS = [
  {
    name: "Employer Lite",
    price: "K500",
    period: "/month",
    detail: "5 candidate contacts per month",
    tier: "lite",
  },
  {
    name: "Employer Pro",
    price: "K2,500",
    period: "/month",
    detail: "Unlimited contacts + bulk WhatsApp outreach",
    tier: "pro",
    featured: true,
  },
];

export default function EmployerLandingPage() {
  return (
    <div className="max-w-4xl mx-auto px-4 py-16">
      <p className="text-sm font-medium text-muted-foreground uppercase tracking-wide">Zed Apply Employer</p>
      <h1 className="text-3xl sm:text-4xl font-bold tracking-tight mt-2">
        Reach pre-matched candidates in Zambia
      </h1>
      <p className="text-muted-foreground mt-4 text-lg max-w-2xl">
        Search our talent pool, request contact with explicit candidate consent via WhatsApp and
        email, and only see phone numbers after they reply YES.
      </p>

      <div className="mt-10 grid sm:grid-cols-2 gap-6">
        {PLANS.map((plan) => (
          <div
            key={plan.tier}
            className={`rounded-xl border p-6 ${plan.featured ? "border-primary shadow-sm" : ""}`}
          >
            <h2 className="font-semibold text-lg">{plan.name}</h2>
            <p className="text-2xl font-bold mt-2">
              {plan.price}
              <span className="text-sm font-normal text-muted-foreground">{plan.period}</span>
            </p>
            <p className="text-sm text-muted-foreground mt-2">{plan.detail}</p>
          </div>
        ))}
      </div>

      <div className="mt-16">
        <h2 className="text-2xl font-bold tracking-tight">Recruiter / CV Database Access</h2>
        <p className="text-muted-foreground mt-2 mb-6">
          Packages to download or access candidate CVs with varying access periods and filters.
        </p>
        <div className="grid sm:grid-cols-3 gap-6">
          <div className="rounded-xl border p-6">
            <h3 className="font-semibold text-lg">Starter</h3>
            <p className="text-2xl font-bold mt-2">ZMW 2,200</p>
            <p className="text-sm text-muted-foreground mt-2">Access to 20 CVs</p>
          </div>
          <div className="rounded-xl border p-6 border-primary shadow-sm">
            <h3 className="font-semibold text-lg">Standard</h3>
            <p className="text-2xl font-bold mt-2">ZMW 4,500</p>
            <p className="text-sm text-muted-foreground mt-2">Access to 50 CVs</p>
          </div>
          <div className="rounded-xl border p-6">
            <h3 className="font-semibold text-lg">Enterprise</h3>
            <p className="text-2xl font-bold mt-2">ZMW 6,500</p>
            <p className="text-sm text-muted-foreground mt-2">Access to 100 CVs</p>
          </div>
        </div>
      </div>

      <div className="mt-10 flex flex-wrap gap-4">
        <Link
          href="/employer/signup"
          className="inline-flex items-center justify-center rounded-lg bg-primary text-primary-foreground px-5 py-2.5 text-sm font-medium"
        >
          Register your company
        </Link>
        <Link
          href="/auth?next=/employer/dashboard"
          className="inline-flex items-center justify-center rounded-lg border px-5 py-2.5 text-sm font-medium"
        >
          Sign in
        </Link>
      </div>
    </div>
  );
}
