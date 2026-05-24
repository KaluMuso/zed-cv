"use client";

import React from "react";
import * as Sentry from "@sentry/nextjs";
import { AlertCircle } from "lucide-react";

import { Button } from "@/components/ui/button";

interface Props {
  children: React.ReactNode;
}

interface State {
  hasError: boolean;
}

export class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error("[ZedApply] Uncaught error:", error, info.componentStack);
    if (process.env.NEXT_PUBLIC_SENTRY_DSN) {
      Sentry.captureException(error, {
        contexts: { react: { componentStack: info.componentStack } },
        tags: { boundary: "layout-error-boundary" },
      });
    }
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-[60vh] items-center justify-center bg-background px-6">
          <div className="max-w-md text-center">
            <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-md bg-accent/15 text-accent">
              <AlertCircle className="h-7 w-7" aria-hidden />
            </div>
            <h2 className="font-display text-2xl font-semibold text-foreground">
              Something went wrong
            </h2>
            <p className="mt-2 text-sm text-muted-foreground">
              We&apos;re on it. Try reloading the page — if this keeps happening, contact support.
            </p>
            <Button
              type="button"
              variant="primary"
              size="lg"
              className="mt-6"
              onClick={() => window.location.reload()}
            >
              Reload page
            </Button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
