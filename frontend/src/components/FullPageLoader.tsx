export function FullPageLoader() {
  return (
    <div className="flex min-h-screen items-center justify-center" data-testid="full-page-loader">
      <div
        className="h-8 w-8 animate-spin rounded-full border-4 border-slate-300 border-t-slate-700"
        aria-label="Loading"
      />
    </div>
  );
}

export function InlineSpinner({ label }: { label?: string }) {
  return (
    <span className="inline-flex items-center gap-2 text-sm text-slate-500">
      <span
        className="h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-slate-700"
        aria-hidden
      />
      {label ?? "Loading…"}
    </span>
  );
}
