/** Registration page (Phase 15.1) — creates the org + first admin user. */
import { useState, type FormEvent, type ReactNode } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { errorMessage } from "@/api/client";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const MIN_PASSWORD = 8; // mirrors backend RegisterRequest constraint

export default function RegisterPage(): ReactNode {
  const { register } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [organizationName, setOrganizationName] = useState("");
  const [fieldErrors, setFieldErrors] = useState<{ email?: string; password?: string; organizationName?: string }>({});
  const [submitting, setSubmitting] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);

  const validate = (): boolean => {
    const errors: { email?: string; password?: string; organizationName?: string } = {};
    if (!EMAIL_RE.test(email)) errors.email = "Enter a valid email address.";
    if (password.length < MIN_PASSWORD) errors.password = `At least ${MIN_PASSWORD} characters.`;
    if (organizationName.trim().length < 1) errors.organizationName = "Organization name is required.";
    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setServerError(null);
    if (!validate()) return;
    setSubmitting(true);
    try {
      await register(email, password, organizationName.trim());
      void navigate("/documents", { replace: true });
    } catch (err) {
      setServerError(errorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
      <div className="w-full max-w-sm">
        <h1 className="mb-1 text-center text-2xl font-bold text-slate-900">Register</h1>
        <p className="mb-6 text-center text-xs text-slate-500">
          Creates your organization — you become its first admin.
        </p>
        <form onSubmit={handleSubmit} className="space-y-4 rounded-lg border border-slate-200 bg-white p-6 shadow-sm" noValidate>
          <div>
            <label htmlFor="org-name" className="mb-1 block text-sm font-medium text-slate-700">
              Organization name
            </label>
            <input
              id="org-name"
              value={organizationName}
              onChange={(e) => setOrganizationName(e.target.value)}
              className="w-full rounded border border-slate-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none"
            />
            {fieldErrors.organizationName && (
              <p className="mt-1 text-xs text-red-600">{fieldErrors.organizationName}</p>
            )}
          </div>
          <div>
            <label htmlFor="email" className="mb-1 block text-sm font-medium text-slate-700">
              Email
            </label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded border border-slate-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none"
            />
            {fieldErrors.email && <p className="mt-1 text-xs text-red-600">{fieldErrors.email}</p>}
          </div>
          <div>
            <label htmlFor="password" className="mb-1 block text-sm font-medium text-slate-700">
              Password
            </label>
            <input
              id="password"
              type="password"
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded border border-slate-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none"
            />
            {fieldErrors.password && <p className="mt-1 text-xs text-red-600">{fieldErrors.password}</p>}
          </div>
          {serverError && (
            <p role="alert" data-testid="register-error" className="text-sm text-red-600">
              {serverError}
            </p>
          )}
          <button
            type="submit"
            disabled={submitting}
            data-testid="register-submit"
            className="w-full rounded bg-slate-800 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
          >
            {submitting ? "Creating…" : "Create organization"}
          </button>
          <p className="text-center text-xs text-slate-500">
            Already have an account?{" "}
            <Link to="/login" className="font-medium text-slate-700 underline">
              Log in
            </Link>
          </p>
        </form>
      </div>
    </div>
  );
}
