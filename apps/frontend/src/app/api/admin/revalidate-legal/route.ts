import { NextResponse } from "next/server";
import { revalidatePath } from "next/cache";

/**
 * Server route handler the admin Legal tab calls after a successful
 * PATCH to /api/v1/admin/legal/<slug>. Runs revalidatePath() against
 * the /legal/<slug> page so the next visitor gets the updated copy
 * within the same second rather than waiting for the page's
 * ISR window (currently 300s).
 *
 * Not auth-protected on its own surface: it's only callable from the
 * admin UI flow, which already required a valid superadmin JWT to
 * land the PATCH. The handler validates the slug whitelist to keep
 * a stray call from bypassing routing assumptions.
 */
export async function POST(req: Request) {
  let slug: string | undefined;
  try {
    const body = (await req.json()) as { slug?: string };
    slug = body.slug;
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
  }

  // Whitelist mirrors the backend (/api/v1/admin/legal allowed slugs)
  // so a typo or hostile slug can't trigger revalidation of an
  // unrelated path.
  if (!slug || !["privacy", "terms", "cookies"].includes(slug)) {
    return NextResponse.json(
      { error: "Unknown slug. Accepted: privacy, terms, cookies." },
      { status: 400 },
    );
  }

  revalidatePath(`/legal/${slug}`);
  return NextResponse.json({ revalidated: true, slug });
}
