import React from "react";

// Import routing components from React Router.
//
// Router   -> Enables client-side routing.
// Routes   -> Container for all route definitions.
// Route    -> Defines a specific URL path and component.
// Navigate -> Programmatically redirects the user to another route.
import {
  BrowserRouter as Router,
  Routes,
  Route,
  Navigate,
} from "react-router-dom";

// Import authentication context.
//
// AuthProvider -> Makes authentication state available to the application.
// useAuth      -> Allows components to access the current user and loading state.
import { AuthProvider, useAuth } from "./context/AuthContext";

// Import WebSocket context.
//
// This provides real-time communication for the analyst dashboard,
// such as live transaction or fraud alert updates.
import { WebSocketProvider } from "./context/WebSocketContext";

// Import authentication pages.
import { Login } from "./pages/auth/Login";
import { Register } from "./pages/auth/Register";

// Import role-specific dashboards.
import { MerchantDashboard } from "./pages/merchant/MerchantDashboard";
import { AnalystDashboard } from "./pages/analyst/AnalystDashboard";

/**
 * DashboardRedirector
 *
 * This component decides which page/dashboard the user should see
 * based on their authentication status and role.
 *
 * Possible flow:
 *
 * Application loads
 *        |
 *        v
 * Check authentication status
 *        |
 *        +---- Loading ----> Show loading screen
 *        |
 *        +---- No user ----> Redirect to /login
 *        |
 *        +---- Merchant ---> MerchantDashboard
 *        |
 *        +---- Analyst/Admin -> AnalystDashboard
 */
const DashboardRedirector: React.FC = () => {
  // Get the currently authenticated user and authentication loading state.
  const { user, loading } = useAuth();

  // ------------------------------------------------------------
  // SHOW LOADING SCREEN WHILE AUTHENTICATION STATE IS BEING LOADED
  // ------------------------------------------------------------

  // For example, the application may be checking:
  // - Whether a JWT/token exists
  // - Whether the stored user session is valid
  // - Whether user information needs to be fetched
  if (loading) {
    return (
      // Full-screen loading container.
      <div className="min-h-screen bg-[#070A13] flex items-center justify-center text-slate-400">
        <div className="text-center">
          {/* 
            Loading spinner.

            animate-spin -> Rotates the SVG continuously.
            The circle and path together create a circular spinner.
          */}
          <svg
            className="animate-spin h-10 w-10 text-blue-500 mx-auto mb-4"
            fill="none"
            viewBox="0 0 24 24"
          >
            {/* Background portion of the spinner */}
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />

            {/* Visible rotating portion of the spinner */}
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>

          {/* Message displayed while the application initializes */}
          <p className="text-sm font-semibold">
            Bootstrapping security consoles...
          </p>
        </div>
      </div>
    );
  }

  // ------------------------------------------------------------
  // REDIRECT UNAUTHENTICATED USERS
  // ------------------------------------------------------------

  // If authentication loading has finished but no user exists,
  // redirect the user to the login page.
  //
  // replace removes the current route from browser history,
  // preventing the user from navigating back to a protected page.
  if (!user) {
    return <Navigate to="/login" replace />;
  }

  // ------------------------------------------------------------
  // ROLE-BASED DASHBOARD REDIRECTION
  // ------------------------------------------------------------

  // If the authenticated user is a merchant,
  // show the merchant-specific dashboard.
  if (user.role === "merchant") {
    return <MerchantDashboard />;
  }

  // If the user is an analyst or administrator,
  // show the analyst dashboard.
  if (user.role === "analyst" || user.role === "admin") {
    return (
      // Wrap the analyst dashboard with WebSocketProvider.
      //
      // This allows components inside AnalystDashboard to access
      // real-time WebSocket data and events.
      <WebSocketProvider>
        <AnalystDashboard />
      </WebSocketProvider>
    );
  }

  // ------------------------------------------------------------
  // FALLBACK REDIRECTION
  // ------------------------------------------------------------

  // If the user's role does not match any expected role,
  // redirect them back to the login page.
  return <Navigate to="/login" replace />;
};

/**
 * Main Application Component
 *
 * This is the root component of the React application.
 */
function App() {
  return (
    // Router enables navigation between different pages
    // without reloading the entire application.
    <Router>
      {/* 
        AuthProvider wraps all routes.

        This allows Login, Register, DashboardRedirector,
        and other child components to access authentication data.
      */}
      <AuthProvider>
        {/* Container for all application routes */}
        <Routes>
          {/* 
            LOGIN ROUTE

            URL:
            http://localhost:5173/login
          */}
          <Route path="/login" element={<Login />} />

          {/* 
            REGISTRATION ROUTE

            URL:
            http://localhost:5173/register
          */}
          <Route path="/register" element={<Register />} />

          {/* 
            CATCH-ALL / PROTECTED ROUTE

            The "/*" path catches every other route.

            Examples:
            /
            /dashboard
            /transactions
            /anything

            DashboardRedirector determines:
            1. Whether the user is authenticated.
            2. Which role the user has.
            3. Which dashboard should be displayed.
          */}
          <Route path="/*" element={<DashboardRedirector />} />
        </Routes>
      </AuthProvider>
    </Router>
  );
}

// Export the App component so it can be rendered
// from the application's main entry file.
export default App;
