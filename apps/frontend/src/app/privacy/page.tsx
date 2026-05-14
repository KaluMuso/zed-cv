import { permanentRedirect } from "next/navigation";

// Canonical location moved to /legal/privacy. Kept as a redirect so any
// previously-shared /privacy links continue to resolve.
export default function PrivacyPage() {
  permanentRedirect("/legal/privacy");
}
