import React from 'react';

type ErrorBoundaryProps = {
  children: React.ReactNode;
};

type ErrorBoundaryState = {
  hasError: boolean;
  message?: string;
};

export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, message: error.message };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo): void {
    // Keep details in console for diagnostics while presenting
    // a safe fallback UI to users.
    console.error('Unhandled UI error:', error, info);
  }

  private handleReload = () => {
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-dental-surface dark:bg-gray-950 flex items-center justify-center p-6">
          <div className="max-w-lg w-full bg-white dark:bg-gray-900 border border-red-200 dark:border-red-900 rounded-2xl p-6 shadow-card">
            <h1 className="text-lg font-semibold text-red-700 dark:text-red-400">Ein Fehler ist aufgetreten</h1>
            <p className="mt-2 text-sm text-gray-600 dark:text-gray-300">
              Die Oberfläche konnte nicht korrekt geladen werden. Bitte Seite neu laden.
            </p>
            {this.state.message && (
              <p className="mt-3 text-xs text-gray-500 dark:text-gray-400 break-words">
                Technischer Hinweis: {this.state.message}
              </p>
            )}
            <button className="btn-primary mt-5" onClick={this.handleReload}>
              Neu laden
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
