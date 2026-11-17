import { useAuth } from "@/hooks/useAuth";

export default function DashboardPage() {
  const { org, user } = useAuth();
  return (
    <div>
      <h1 className="mb-1 text-2xl font-bold text-slate-900">Dashboard</h1>
      <p className="mb-6 text-sm text-slate-600">
        {org?.name ?? ""} · signed in as {user?.email ?? ""}
      </p>
      <p className="text-sm text-slate-600">
        Start with your documents: upload a contract, run extraction, then review the clauses.
      </p>
    </div>
  );
}
