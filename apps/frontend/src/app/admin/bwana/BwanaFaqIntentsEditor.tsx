"use client";

import { useState } from "react";
import type { FaqIntentItem } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const EMPTY_INTENT: FaqIntentItem = {
  intent_id: "custom_intent",
  enabled: true,
  triggers: [],
  response: "",
};

function triggersToText(triggers: string[]): string {
  return triggers.join(", ");
}

function textToTriggers(text: string): string[] {
  return text
    .split(",")
    .map((t) => t.trim().toLowerCase())
    .filter(Boolean)
    .slice(0, 20);
}

interface BwanaFaqIntentsEditorProps {
  intents: FaqIntentItem[];
  onChange: (intents: FaqIntentItem[]) => void;
}

export function BwanaFaqIntentsEditor({
  intents,
  onChange,
}: BwanaFaqIntentsEditorProps) {
  const [showJson, setShowJson] = useState(false);
  const [jsonDraft, setJsonDraft] = useState("");

  const updateRow = (index: number, patch: Partial<FaqIntentItem>) => {
    const next = intents.map((row, i) =>
      i === index ? { ...row, ...patch } : row,
    );
    onChange(next);
  };

  const addRow = () => {
    const id = `custom_${intents.length + 1}`;
    onChange([...intents, { ...EMPTY_INTENT, intent_id: id }]);
  };

  const removeRow = (index: number) => {
    onChange(intents.filter((_, i) => i !== index));
  };

  const openJson = () => {
    setJsonDraft(JSON.stringify(intents, null, 2));
    setShowJson(true);
  };

  const applyJson = () => {
    try {
      const parsed: unknown = JSON.parse(jsonDraft);
      if (!Array.isArray(parsed)) {
        return;
      }
      onChange(parsed as FaqIntentItem[]);
      setShowJson(false);
    } catch {
      /* invalid — keep editor open */
    }
  };

  if (showJson) {
    return (
      <div className="space-y-2">
        <p className="text-xs text-muted-foreground">Advanced: edit raw JSON array</p>
        <textarea
          className="w-full min-h-[200px] font-mono text-xs rounded-md border border-input bg-background px-3 py-2"
          value={jsonDraft}
          onChange={(e) => setJsonDraft(e.target.value)}
        />
        <div className="flex gap-2">
          <Button type="button" size="sm" onClick={applyJson}>
            Apply JSON
          </Button>
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={() => setShowJson(false)}
          >
            Back to form
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <p className="text-xs text-muted-foreground">
        Custom intents run after built-in FAQs. Triggers are comma-separated
        substrings (case-insensitive). Max 50 intents.
      </p>
      {intents.length === 0 && (
        <p className="text-sm text-muted-foreground">No custom intents yet.</p>
      )}
      {intents.map((row, index) => (
        <div
          key={`${row.intent_id}-${index}`}
          className="rounded-lg border p-3 space-y-2 bg-muted/30"
        >
          <div className="flex flex-wrap items-center gap-2">
            <label className="text-xs flex items-center gap-1">
              <input
                type="checkbox"
                checked={row.enabled}
                onChange={(e) => updateRow(index, { enabled: e.target.checked })}
              />
              Enabled
            </label>
            <Button
              type="button"
              size="sm"
              variant="ghost"
              className="ml-auto text-destructive"
              onClick={() => removeRow(index)}
            >
              Remove
            </Button>
          </div>
          <label className="text-xs block space-y-1">
            Intent ID (snake_case)
            <Input
              value={row.intent_id}
              onChange={(e) =>
                updateRow(index, {
                  intent_id: e.target.value.replace(/\s+/g, "_").toLowerCase(),
                })
              }
            />
          </label>
          <label className="text-xs block space-y-1">
            Triggers (comma-separated)
            <Input
              value={triggersToText(row.triggers)}
              onChange={(e) =>
                updateRow(index, { triggers: textToTriggers(e.target.value) })
              }
              placeholder="refund policy, money back"
            />
          </label>
          <label className="text-xs block space-y-1">
            Response
            <textarea
              className="w-full min-h-[72px] rounded-md border border-input bg-background px-3 py-2 text-sm"
              value={row.response}
              maxLength={1200}
              onChange={(e) => updateRow(index, { response: e.target.value })}
            />
          </label>
        </div>
      ))}
      <div className="flex flex-wrap gap-2">
        <Button type="button" size="sm" variant="outline" onClick={addRow}>
          Add intent
        </Button>
        <Button type="button" size="sm" variant="ghost" onClick={openJson}>
          Edit as JSON
        </Button>
      </div>
    </div>
  );
}
