import { Component, type ErrorInfo, type ReactNode } from "react";

/** Catches render-time crashes in an island so a bug in one surface degrades to a
 *  fallback instead of a blank island (FE-06). Error boundaries must be class
 *  components in React. */
export class ErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };

  static getDerivedStateFromError(): { failed: boolean } {
    return { failed: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error("[scree] island crashed", error, info);
  }

  render(): ReactNode {
    if (this.state.failed) {
      return <p role="alert">Something went wrong loading this view. Please reload the page.</p>;
    }
    return this.props.children;
  }
}
