"use client";

import { useCallback, useEffect, useState } from "react";
import {
  adminBwana,
  type BwanaConfig,
  type BwanaConfigPatch,
  type FaqIntentItem,
} from "@/lib/api";
import { BwanaAnalyticsPanel } from "./BwanaAnalyticsPanel";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { notify } from "@/lib/toast";

const TEMPLATE_HINT =
  "Variables: {email}, {phone}, {sla}, {operator}, {chatbot_name}, {ticket_id}";

type EditableConfig = BwanaConfig;

function toForm(cfg: BwanaConfig): EditableConfig {
  return { ...cfg };
}

export function BwanaConfigTab({ token }: { token: string }) {
  const [form, setForm] = useState<EditableConfig | null>(null);
  const [preview, setPreview] = useState<string>("");
  const [previewChars, setPreviewChars] = useState(0);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [faqJson, setFaqJson] = useState("[]");
  const [faqJsonError, setFaqJsonError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const cfg = await adminBwana.getConfig(token);
      setForm(toForm(cfg));
      setFaqJson(JSON.stringify(cfg.faq_intents_json ?? [], null, 2));
      setFaqJsonError(null);
      const prev = await adminBwana.preview(token);
      setPreview(prev.system_prompt_preview);
      setPreviewChars(prev.char_count);
    } catch (e) {
      notify.error(e instanceof Error ? e.message : "Failed to load Bwana config");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    void load();
  }, [load]);

  const update = (patch: Partial<EditableConfig>) => {
    setForm((prev) => (prev ? { ...prev, ...patch } : prev));
  };

  const parseFaqJson = (): FaqIntentItem[] | null => {
    try {
      const parsed: unknown = JSON.parse(faqJson);
      if (!Array.isArray(parsed)) {
        setFaqJsonError("Must be a JSON array");
        return null;
      }
      setFaqJsonError(null);
      return parsed as FaqIntentItem[];
    } catch {
      setFaqJsonError("Invalid JSON");
      return null;
    }
  };

  const handleSave = async () => {
    if (!form) return;
    const faqIntents = parseFaqJson();
    if (faqIntents === null) return;
    setSaving(true);
    try {
      const body: BwanaConfigPatch = {
        chatbot_display_name: form.chatbot_display_name,
        operator_display_name: form.operator_display_name,
        support_email: form.support_email,
        support_phone: form.support_phone,
        escalation_whatsapp_phone: form.escalation_whatsapp_phone,
        escalation_sla_hours: form.escalation_sla_hours,
        human_escalation_reply_template: form.human_escalation_reply_template,
        unsatisfied_reply_template: form.unsatisfied_reply_template,
        contact_admin_reply_template: form.contact_admin_reply_template,
        public_knowledge_extra: form.public_knowledge_extra,
        faq_intents_json: faqIntents,
        enable_email_escalation: form.enable_email_escalation,
      };
      const saved = await adminBwana.patchConfig(token, body);
      setForm(toForm(saved));
      const prev = await adminBwana.preview(token);
      setPreview(prev.system_prompt_preview);
      setPreviewChars(prev.char_count);
      notify.custom.success("Bwana config saved");
    } catch (e) {
      notify.error(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const handleTestEscalation = async () => {
    setTesting(true);
    try {
      const res = await adminBwana.testEscalation(token);
      notify.custom.success(res.detail);
    } catch (e) {
      notify.error(e instanceof Error ? e.message : "Test escalation failed");
    } finally {
      setTesting(false);
    }
  };

  if (loading || !form) {
    return <p className="text-sm text-muted-foreground">Loading Bwana config…</p>;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Bwana</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Chatbot contact details, escalation templates, and public knowledge for
          the in-app assistant.
        </p>
      </div>

      <Card>
        <CardContent className="p-4 space-y-4">
          <h2 className="text-lg font-semibold">Identity & contact</h2>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="text-sm space-y-1">
              Chatbot name
              <Input
                value={form.chatbot_display_name}
                onChange={(e) => update({ chatbot_display_name: e.target.value })}
              />
            </label>
            <label className="text-sm space-y-1">
              Operator name
              <Input
                value={form.operator_display_name}
                onChange={(e) => update({ operator_display_name: e.target.value })}
              />
            </label>
            <label className="text-sm space-y-1">
              Support email
              <Input
                type="email"
                value={form.support_email}
                onChange={(e) => update({ support_email: e.target.value })}
              />
            </label>
            <label className="text-sm space-y-1">
              Support phone (+260)
              <Input
                value={form.support_phone}
                onChange={(e) => update({ support_phone: e.target.value })}
              />
            </label>
            <label className="text-sm space-y-1">
              Escalation WhatsApp (+260)
              <Input
                value={form.escalation_whatsapp_phone}
                onChange={(e) =>
                  update({ escalation_whatsapp_phone: e.target.value })
                }
              />
            </label>
            <label className="text-sm space-y-1">
              Escalation SLA (hours)
              <Input
                type="number"
                min={1}
                max={168}
                value={form.escalation_sla_hours}
                onChange={(e) =>
                  update({
                    escalation_sla_hours: parseInt(e.target.value, 10) || 24,
                  })
                }
              />
            </label>
          </div>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={form.enable_email_escalation}
              onChange={(e) =>
                update({ enable_email_escalation: e.target.checked })
              }
            />
            Email escalations to support address
          </label>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-4 space-y-4">
          <h2 className="text-lg font-semibold">Reply templates</h2>
          <p className="text-xs text-muted-foreground">{TEMPLATE_HINT}</p>
          {(
            [
              ["human_escalation_reply_template", "Human escalation"],
              ["unsatisfied_reply_template", "Unsatisfied user"],
              ["contact_admin_reply_template", "Contact admin (info only)"],
            ] as const
          ).map(([key, label]) => (
            <label key={key} className="text-sm block space-y-1">
              {label}
              <textarea
                className="w-full min-h-[80px] rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={form[key]}
                onChange={(e) => update({ [key]: e.target.value })}
              />
            </label>
          ))}
        </CardContent>
      </Card>

      <BwanaAnalyticsPanel token={token} />

      <Card>
        <CardContent className="p-4 space-y-3">
          <h2 className="text-lg font-semibold">Custom FAQ intents (JSON)</h2>
          <p className="text-xs text-muted-foreground">
            Matched after built-in FAQs. Each item: intent_id (snake_case), enabled,
            triggers (substring list), response. Max 50 intents.
          </p>
          <textarea
            className="w-full min-h-[160px] font-mono text-xs rounded-md border border-input bg-background px-3 py-2"
            value={faqJson}
            onChange={(e) => setFaqJson(e.target.value)}
          />
          {faqJsonError && (
            <p className="text-xs text-destructive">{faqJsonError}</p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-4 space-y-3">
          <h2 className="text-lg font-semibold">Public knowledge (system prompt)</h2>
          <p className="text-xs text-muted-foreground">
            Max 2000 characters. No API keys or internal ops details.
          </p>
          <textarea
            className="w-full min-h-[120px] rounded-md border border-input bg-background px-3 py-2 text-sm"
            maxLength={2000}
            value={form.public_knowledge_extra}
            onChange={(e) => update({ public_knowledge_extra: e.target.value })}
          />
          <p className="text-xs text-muted-foreground">
            {form.public_knowledge_extra.length}/2000
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-4 space-y-3">
          <h2 className="text-lg font-semibold">System prompt preview</h2>
          <p className="text-xs text-muted-foreground">
            Full prompt length: {previewChars.toLocaleString()} chars (truncated below)
          </p>
          <pre className="max-h-64 overflow-auto rounded-md bg-muted p-3 text-xs whitespace-pre-wrap">
            {preview || "Save to refresh preview."}
          </pre>
        </CardContent>
      </Card>

      <div className="flex flex-wrap gap-3">
        <Button onClick={() => void handleSave()} disabled={saving}>
          {saving ? "Saving…" : "Save config"}
        </Button>
        <Button
          type="button"
          variant="outline"
          onClick={() => void handleTestEscalation()}
          disabled={testing}
        >
          {testing ? "Sending…" : "Test escalation (WhatsApp)"}
        </Button>
      </div>
    </div>
  );
}
