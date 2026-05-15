import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeSanitize from "rehype-sanitize";

// Markdown renderer for static legal copy. Mirrors the InterviewPrepModal
// pattern but tuned for long-form documents: looser line-height, brand
// headings, and footnote-friendly typography. Content is author-written
// (not LLM output) so rehype-sanitize is defensive rather than essential.
export function LegalMarkdown({ markdown }: { markdown: string }) {
  return (
    <div className="legal-body">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeSanitize]}
        components={{
          h1: ({ children }) => (
            <h1
              className="font-display mt-0 mb-3"
              style={{
                fontSize: "clamp(36px, 5vw, 56px)",
                lineHeight: 1.05,
                letterSpacing: "-0.02em",
                color: "var(--ink)",
              }}
            >
              {children}
            </h1>
          ),
          h2: ({ children }) => (
            <h2
              className="font-display mt-10 mb-3"
              style={{
                fontSize: "clamp(22px, 2.4vw, 28px)",
                letterSpacing: "-0.01em",
                color: "var(--copper-600)",
              }}
            >
              {children}
            </h2>
          ),
          h3: ({ children }) => (
            <h3
              className="font-display mt-6 mb-2 font-semibold"
              style={{ fontSize: 18, color: "var(--ink)" }}
            >
              {children}
            </h3>
          ),
          p: ({ children }) => (
            <p
              className="mb-4"
              style={{ lineHeight: 1.75, color: "var(--ink-2)" }}
            >
              {children}
            </p>
          ),
          ul: ({ children }) => (
            <ul
              className="list-disc pl-6 mb-5 space-y-2"
              style={{ color: "var(--ink-2)" }}
            >
              {children}
            </ul>
          ),
          ol: ({ children }) => (
            <ol
              className="list-decimal pl-6 mb-5 space-y-2"
              style={{ color: "var(--ink-2)" }}
            >
              {children}
            </ol>
          ),
          li: ({ children }) => (
            <li style={{ lineHeight: 1.7 }}>{children}</li>
          ),
          strong: ({ children }) => (
            <strong
              className="font-semibold"
              style={{ color: "var(--ink)" }}
            >
              {children}
            </strong>
          ),
          em: ({ children }) => (
            <em style={{ color: "var(--ink-2)" }}>{children}</em>
          ),
          a: ({ children, href }) => {
            const isExternal = href?.startsWith("http");
            return (
              <a
                href={href}
                target={isExternal ? "_blank" : undefined}
                rel={isExternal ? "noopener noreferrer" : undefined}
                style={{
                  color: "var(--green-700)",
                  textDecoration: "underline",
                }}
              >
                {children}
              </a>
            );
          },
          hr: () => (
            <hr
              className="my-8"
              style={{ border: "none", borderTop: "1px solid var(--line)" }}
            />
          ),
          table: ({ children }) => (
            <div className="overflow-x-auto my-5">
              <table className="w-full text-sm" style={{ borderCollapse: "collapse" }}>
                {children}
              </table>
            </div>
          ),
          th: ({ children }) => (
            <th
              className="text-left px-3 py-2 font-semibold"
              style={{
                borderBottom: "1px solid var(--line)",
                color: "var(--ink)",
              }}
            >
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td
              className="px-3 py-2 align-top"
              style={{
                borderBottom: "1px solid var(--line)",
                color: "var(--ink-2)",
              }}
            >
              {children}
            </td>
          ),
        }}
      >
        {markdown}
      </ReactMarkdown>
    </div>
  );
}
