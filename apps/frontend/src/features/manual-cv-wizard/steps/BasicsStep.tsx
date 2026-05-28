"use client";

import { Icon } from "@/components/ui/Icon";
import { useManualCvWizardStore } from "../store";

const inputClass =
  "w-full h-10 px-3 rounded-md text-sm transition-colors focus:outline-none focus:ring-2 focus:ring-[var(--brand-500,#0E5C3A)]";
const fieldStyle = {
  border: "1px solid var(--line-2)",
  background: "var(--surface)",
  color: "var(--ink)",
} as const;
const labelClass = "text-xs font-medium block mb-1.5";

export function BasicsStep() {
  const basics = useManualCvWizardStore((s) => s.draft.basics);
  const updateBasics = useManualCvWizardStore((s) => s.updateBasics);
  const setStep = useManualCvWizardStore((s) => s.setStep);

  return (
    <div className="flex flex-col h-full rounded-lg p-5 sm:p-6" style={{ background: "var(--surface)", border: "1px solid var(--line-2)" }}>
      <div className="mb-5">
        <h2 className="text-lg font-semibold" style={{ color: "var(--ink)" }}>Basic info</h2>
        <p className="text-sm mt-1" style={{ color: "var(--muted)" }}>
          Your name and contact details — saved automatically as you type.
        </p>
      </div>
      <form
        className="flex flex-col flex-1 gap-4"
        onSubmit={(e) => {
          e.preventDefault();
          setStep("summary");
        }}
      >
        <div>
          <label className={labelClass} htmlFor="m-full-name">Full name</label>
          <input id="m-full-name" required value={basics.fullName} onChange={(e) => updateBasics({ fullName: e.target.value })} className={inputClass} style={fieldStyle} />
        </div>
        <div>
          <label className={labelClass} htmlFor="m-headline">Headline</label>
          <input id="m-headline" value={basics.headline} onChange={(e) => updateBasics({ headline: e.target.value })} placeholder="e.g. Software Engineer · React & Python" className={inputClass} style={fieldStyle} />
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className={labelClass} htmlFor="m-email">Email</label>
            <input id="m-email" type="email" value={basics.email} onChange={(e) => updateBasics({ email: e.target.value })} className={inputClass} style={fieldStyle} />
          </div>
          <div>
            <label className={labelClass} htmlFor="m-phone">Phone</label>
            <input id="m-phone" type="tel" value={basics.phone} onChange={(e) => updateBasics({ phone: e.target.value })} placeholder="+260XXXXXXXXX" className={inputClass} style={fieldStyle} />
          </div>
        </div>
        <div>
          <label className={labelClass} htmlFor="m-location">Location</label>
          <input id="m-location" value={basics.location} onChange={(e) => updateBasics({ location: e.target.value })} placeholder="Lusaka, Zambia" className={inputClass} style={fieldStyle} />
        </div>
        <div className="pt-2 flex justify-end">
          <button type="submit" className="btn btn-primary">
            Next: Career summary <Icon name="arrowRight" size={14} />
          </button>
        </div>
      </form>
    </div>
  );
}
