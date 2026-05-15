import { permanentRedirect } from "next/navigation";

// Canonical location moved to /legal/terms. Kept as a redirect so any
// previously-shared /terms links continue to resolve.
export default function TermsPage() {
  permanentRedirect("/legal/terms");
}
