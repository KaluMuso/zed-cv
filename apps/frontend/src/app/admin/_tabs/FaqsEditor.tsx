"use client";

import { useEffect, useState } from "react";
import { adminFaqs, profile, type FaqRow } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { notify } from "@/lib/toast";

export function FaqsEditor({ token }: { token: string }) {
  const [isSuperadmin, setIsSuperadmin] = useState(false);
  const [faqs, setFaqs] = useState<FaqRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [savingId, setSavingId] = useState<string | null>(null);

  // New FAQ form state
  const [newQuestion, setNewQuestion] = useState("");
  const [newAnswer, setNewAnswer] = useState("");
  const [isCreating, setIsCreating] = useState(false);

  useEffect(() => {
    profile
      .get(token)
      .then((p) => setIsSuperadmin(p.role === "superadmin"))
      .catch(() => setIsSuperadmin(false));
  }, [token]);

  useEffect(() => {
    if (!isSuperadmin) {
      setLoading(false);
      return;
    }
    setLoading(true);
    adminFaqs
      .list(token)
      .then((r) => setFaqs(r.faqs))
      .catch((e) =>
        notify.error(e instanceof Error ? e.message : "Failed to load FAQs"),
      )
      .finally(() => setLoading(false));
  }, [token, isSuperadmin]);

  if (!isSuperadmin) {
    return (
      <p className="text-sm text-muted-foreground">
        FAQs configuration is available to superadmin accounts only.
      </p>
    );
  }

  const handleCreate = async () => {
    if (!newQuestion.trim() || !newAnswer.trim()) {
      notify.error("Question and answer are required");
      return;
    }
    setIsCreating(true);
    try {
      const created = await adminFaqs.create(token, {
        question: newQuestion,
        answer: newAnswer,
        is_active: true,
        sort_order: faqs.length,
      });
      setFaqs([...faqs, created]);
      setNewQuestion("");
      setNewAnswer("");
      notify.custom.success("FAQ created successfully");
    } catch (e) {
      notify.error(e instanceof Error ? e.message : "Create failed");
    } finally {
      setIsCreating(false);
    }
  };

  const updateLocalFaq = (id: string, patch: Partial<FaqRow>) => {
    setFaqs((prev) => prev.map((f) => (f.id === id ? { ...f, ...patch } : f)));
  };

  const handleSave = async (faq: FaqRow) => {
    setSavingId(faq.id);
    try {
      const updated = await adminFaqs.patch(token, faq.id, {
        question: faq.question,
        answer: faq.answer,
        sort_order: faq.sort_order,
        is_active: faq.is_active,
      });
      updateLocalFaq(faq.id, updated);
      notify.custom.success("FAQ updated successfully");
    } catch (e) {
      notify.error(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSavingId(null);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Are you sure you want to delete this FAQ?")) return;
    try {
      await adminFaqs.delete(token, id);
      setFaqs((prev) => prev.filter((f) => f.id !== id));
      notify.custom.success("FAQ deleted successfully");
    } catch (e) {
      notify.error(e instanceof Error ? e.message : "Delete failed");
    }
  };

  return (
    <Card>
      <CardContent className="p-4 space-y-6">
        <div>
          <h2 className="text-lg font-semibold">FAQs Editor</h2>
          <p className="text-sm text-muted-foreground mt-1">
            Manage the Frequently Asked Questions shown on the home page.
          </p>
        </div>

        {loading ? (
          <p className="text-sm text-muted-foreground">Loading FAQs…</p>
        ) : (
          <div className="space-y-6">
            {/* Create new FAQ */}
            <div className="border border-border rounded p-4 space-y-4">
              <h3 className="font-medium text-sm">Add New FAQ</h3>
              <div className="space-y-3">
                <div>
                  <label className="text-xs text-muted-foreground mb-1 block">Question</label>
                  <Input 
                    value={newQuestion}
                    onChange={(e) => setNewQuestion(e.target.value)}
                    placeholder="e.g. How do I get started?"
                  />
                </div>
                <div>
                  <label className="text-xs text-muted-foreground mb-1 block">Answer</label>
                  <Textarea 
                    value={newAnswer}
                    onChange={(e) => setNewAnswer(e.target.value)}
                    placeholder="e.g. Simply sign up and..."
                    className="min-h-[80px]"
                  />
                </div>
                <Button onClick={handleCreate} disabled={isCreating} size="sm">
                  {isCreating ? "Adding..." : "Add FAQ"}
                </Button>
              </div>
            </div>

            {/* List existing FAQs */}
            <div className="space-y-4">
              {faqs.map((faq) => (
                <div key={faq.id} className="border border-border/60 rounded p-4 space-y-3 relative">
                  <div className="grid grid-cols-1 md:grid-cols-12 gap-4">
                    <div className="col-span-12 md:col-span-8 space-y-3">
                      <div>
                        <label className="text-xs text-muted-foreground mb-1 block">Question</label>
                        <Input 
                          value={faq.question}
                          onChange={(e) => updateLocalFaq(faq.id, { question: e.target.value })}
                        />
                      </div>
                      <div>
                        <label className="text-xs text-muted-foreground mb-1 block">Answer</label>
                        <Textarea 
                          value={faq.answer}
                          onChange={(e) => updateLocalFaq(faq.id, { answer: e.target.value })}
                          className="min-h-[80px]"
                        />
                      </div>
                    </div>
                    
                    <div className="col-span-12 md:col-span-4 space-y-3">
                      <div>
                        <label className="text-xs text-muted-foreground mb-1 block">Sort Order</label>
                        <Input 
                          type="number"
                          value={faq.sort_order}
                          onChange={(e) => updateLocalFaq(faq.id, { sort_order: parseInt(e.target.value) || 0 })}
                        />
                      </div>
                      <div className="flex items-center space-x-2 pt-2">
                        <input
                          type="checkbox"
                          id={`active-${faq.id}`}
                          checked={faq.is_active}
                          onChange={(e) => updateLocalFaq(faq.id, { is_active: e.target.checked })}
                          className="h-4 w-4"
                        />
                        <label htmlFor={`active-${faq.id}`} className="text-sm">Active (shown on site)</label>
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex items-center space-x-3 pt-2 justify-end">
                    <Button 
                      variant="destructive" 
                      size="sm"
                      onClick={() => handleDelete(faq.id)}
                    >
                      Delete
                    </Button>
                    <Button 
                      size="sm"
                      disabled={savingId === faq.id}
                      onClick={() => handleSave(faq)}
                    >
                      {savingId === faq.id ? "Saving..." : "Save Changes"}
                    </Button>
                  </div>
                </div>
              ))}
              
              {faqs.length === 0 && (
                <p className="text-sm text-muted-foreground italic">No FAQs exist yet.</p>
              )}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
