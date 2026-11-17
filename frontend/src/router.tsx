import { lazy, Suspense, type ReactNode } from "react";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import { RequireAuth, RedirectIfAuthenticated } from "@/router-guards";
import { FullPageLoader } from "@/components/FullPageLoader";
import NotFoundPage from "@/pages/NotFoundPage";

const LoginPage = lazy(() => import("@/pages/LoginPage"));
const RegisterPage = lazy(() => import("@/pages/RegisterPage"));
const DashboardPage = lazy(() => import("@/pages/DashboardPage"));
const DocumentsPage = lazy(() => import("@/pages/DocumentsPage"));
const DocumentReviewPage = lazy(() => import("@/pages/DocumentReviewPage"));

const router = createBrowserRouter([
  {
    element: (
      <Suspense fallback={<FullPageLoader />}>
        <RedirectIfAuthenticated />
      </Suspense>
    ),
    children: [
      { path: "/login", element: <LoginPage /> },
      { path: "/register", element: <RegisterPage /> },
    ],
  },
  {
    element: (
      <Suspense fallback={<FullPageLoader />}>
        <RequireAuth />
      </Suspense>
    ),
    children: [
      { path: "/", element: <DashboardPage /> },
      { path: "/documents", element: <DocumentsPage /> },
      { path: "/documents/:documentId", element: <DocumentReviewPage /> },
    ],
  },
  { path: "*", element: <NotFoundPage /> },
]);

export function AppRouter(): ReactNode {
  return <RouterProvider router={router} />;
}
