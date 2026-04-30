"use client";

import { Icon } from "@/components/ui/Icon";

interface SkillBadgeProps {
  skill: string;
  matched?: boolean;
}

export function SkillBadge({ skill, matched = true }: SkillBadgeProps) {
  return (
    <span className={`tag tag-mono ${matched ? "tag-green" : ""}`}>
      {matched && <Icon name="check" size={10} />}
      {skill}
    </span>
  );
}
