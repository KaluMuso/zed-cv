import HomePageClient from "./HomePageClient";

// Server entry for the landing page. The interactive body lives in
// HomePageClient (state, hooks, scroll reveal). Title falls through to
// the root layout's `title.default` — no per-page suffix
// because the root URL "/" is the brand homepage.
export default function HomePage() {
  return <HomePageClient />;
}
