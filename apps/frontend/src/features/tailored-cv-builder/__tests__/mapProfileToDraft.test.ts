import { describe, expect, it } from "vitest";
import { mapProfileToDraft } from "../mapProfileToDraft";
import type { UserProfile } from "@/lib/api";

const baseProfile: UserProfile = {
  id: "u1",
  phone: "+260971234567",
  full_name: "Jane Doe",
  email: "jane@example.com",
  skills: ["Excel", "IFRS"],
  cv_uploaded: true,
  subscription_tier: "starter",
  location: "Lusaka",
  cv_sections: {
    professional_summary: { text: "Experienced accountant." },
    work_experience: [
      {
        title: "Accountant",
        company: "ZANACO",
        location: "Lusaka",
        start_date: "2020",
        end_date: "Present",
        achievements: ["Closed books monthly"],
      },
    ],
    education: [
      {
        degree: "BAcc",
        institution: "UNZA",
        location: "Lusaka",
        start_date: "2014",
        end_date: "2018",
      },
    ],
    certifications: [],
    languages: [],
    projects: [],
    achievements: [],
    publications: [],
    memberships: [],
    volunteer_work: [],
    references: [],
  },
};

describe("mapProfileToDraft", () => {
  it("returns null without structured CV", () => {
    expect(mapProfileToDraft({ ...baseProfile, cv_sections: null })).toBeNull();
    expect(mapProfileToDraft({ ...baseProfile, cv_uploaded: false })).toBeNull();
  });

  it("maps profile fields into draft shape", () => {
    const draft = mapProfileToDraft(baseProfile);
    expect(draft).not.toBeNull();
    expect(draft?.basics.fullName).toBe("Jane Doe");
    expect(draft?.basics.summary).toBe("Experienced accountant.");
    expect(draft?.experience[0]?.company).toBe("ZANACO");
    expect(draft?.education[0]?.degree).toBe("BAcc");
    expect(draft?.skills).toEqual(["Excel", "IFRS"]);
  });
});
