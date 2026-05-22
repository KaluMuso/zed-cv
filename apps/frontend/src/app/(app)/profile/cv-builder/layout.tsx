/** Wider canvas for the split-pane CV builder (parent (app) layout caps at 5xl). */
export default function CvBuilderLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="relative left-1/2 -translate-x-1/2 w-[min(100vw,1280px)] max-w-none px-4 sm:px-6">
      {children}
    </div>
  );
}
