# Toast notification system

ZedApply uses a **single** toast stack: [Sonner](https://sonner.emilkowal.ski/) configured in `apps/frontend/src/components/shared/Toaster.tsx` and mounted once in `apps/frontend/src/app/layout.tsx`.

## Configuration

- **Position:** `top-center` (avoids mobile FAB overlap)
- **Duration:** 5000ms (5 seconds)
- **Styling:** semantic borders/icons via design tokens (`success`, `danger`, `primary`)

## Usage

Import the helper — never call Sonner directly in feature code:

```ts
import { notify } from "@/lib/toast";

notify.saved();                    // default: "Job saved"
notify.unsaved("Removed");         // error style
notify.payment("Starter plan active");
notify.info("Payment widget loading…");
notify.error("Could not refresh matches.");
notify.loading("Uploading CV…");

// Escape hatch for one-offs
notify.custom.message("No new matches this cycle.");
notify.custom.warning("Saved with warnings.");
```

## Migration from legacy patterns

| Old | New |
| --- | --- |
| `alert("…")` | `notify.error("…")` |
| `notifySuccess` / `notifyError` from `@/components/Toast` | `notify.custom.success` / `notify.error` |
| `import { toast } from "sonner"` | `import { notify } from "@/lib/toast"` |
| Inline toast components | Remove — use `notify` only |

`@/components/Toast` remains as thin deprecated wrappers for any stragglers.

## Do not

- Mount a second `<Toaster />` with different options (except tests)
- Use `position="bottom-right"` — conflicts with mobile tab bar / FABs
- Show success toasts for destructive actions (use `notify.unsaved` / `notify.error`)

## Testing

`src/test/foundation.test.tsx` smoke-renders the toaster config with buttons and skeleton primitives.
