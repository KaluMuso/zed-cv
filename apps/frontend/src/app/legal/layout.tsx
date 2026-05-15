export default function LegalLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <main className="max-w-3xl mx-auto px-5 sm:px-6 py-10 sm:py-16">
      {children}
    </main>
  );
}
