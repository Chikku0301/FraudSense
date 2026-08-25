// Import React and the useState hook for managing component state
import React, { useState } from "react";

// React Hook Form is used to manage form inputs and submission
import { useForm } from "react-hook-form";

// Connects Zod validation with React Hook Form
import { zodResolver } from "@hookform/resolvers/zod";

// Zod is used to define and validate the login form schema
import * as z from "zod";

// React Router utilities:
// - useNavigate → programmatically navigate to another route
// - Link → navigate between pages without reloading the application
import { useNavigate, Link } from "react-router-dom";

// Custom authentication context.
// The login() function here is responsible for communicating
// with the backend and authenticating the user.
import { useAuth } from "../../context/AuthContext";

// Icons used in the login page
import { Shield, AlertCircle } from "lucide-react";

// -----------------------------------------------------------------------------
// FORM VALIDATION SCHEMA
// -----------------------------------------------------------------------------

// Define the validation rules for the login form.
//
// email:
//   Must be a valid email address.
//
// password:
//   Must contain at least 6 characters.
//
// If any validation fails, React Hook Form will receive the
// corresponding error through the `errors` object.
const loginSchema = z.object({
  email: z.string().email({ message: "Invalid email address" }),
  password: z.string().min(6, {
    message: "Password must be at least 6 characters",
  }),
});

// Automatically create a TypeScript type from the Zod schema.
//
// This means LoginFormValues will become:
//
// {
//   email: string
//   password: string
// }
//
// So we don't need to manually define the interface.
type LoginFormValues = z.infer<typeof loginSchema>;

// -----------------------------------------------------------------------------
// LOGIN COMPONENT
// -----------------------------------------------------------------------------

export const Login: React.FC = () => {
  // Get the login function from our authentication context.
  //
  // The AuthContext is responsible for the actual authentication logic,
  // such as sending the email/password to the backend and storing
  // authentication information.
  const { login } = useAuth();

  // React Router hook used to navigate programmatically
  // after successful login.
  const navigate = useNavigate();

  // Stores an authentication/API error message.
  //
  // Example:
  // "Invalid email or password."
  const [error, setError] = useState<string | null>(null);

  // Tracks whether the login request is currently running.
  //
  // Used to:
  // 1. Disable the Sign In button
  // 2. Display a loading spinner
  const [loading, setLoading] = useState(false);

  // ---------------------------------------------------------------------------
  // REACT HOOK FORM SETUP
  // ---------------------------------------------------------------------------

  const {
    // register connects each input field to React Hook Form
    register,

    // handleSubmit validates the form before calling onSubmit
    handleSubmit,

    // errors contains validation errors for individual fields
    formState: { errors },
  } = useForm<LoginFormValues>({
    // Use the Zod schema to validate the form
    resolver: zodResolver(loginSchema),

    // Initial values for the form fields
    defaultValues: {
      email: "",
      password: "",
    },
  });

  // ---------------------------------------------------------------------------
  // FORM SUBMISSION
  // ---------------------------------------------------------------------------

  // This function is called only after React Hook Form
  // successfully validates the form.
  const onSubmit = async (data: LoginFormValues) => {
    // Clear any previous login/API error
    setError(null);

    // Start loading state
    setLoading(true);

    try {
      // Send the user's credentials to the authentication system.
      //
      // The login function will typically call the backend API,
      // verify the credentials, and store the authentication token.
      await login(data.email, data.password);

      // Login was successful, so stop the loading state.
      setLoading(false);

      // Redirect the user to the home/dashboard page.
      navigate("/");
    } catch (err: any) {
      // Stop the loading spinner when authentication fails.
      setLoading(false);

      // Try to extract the error message returned by the backend.
      //
      // For example, FastAPI might return:
      //
      // {
      //   "detail": "Invalid credentials"
      // }
      //
      // If the backend doesn't provide a message,
      // use the default message.
      const errMsg = err.response?.data?.detail || "Invalid email or password.";

      // Display the error message on the login page.
      setError(errMsg);
    }
  };

  // ---------------------------------------------------------------------------
  // LOGIN PAGE UI
  // ---------------------------------------------------------------------------

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#070A13] px-4">
      {/* 
        Background decorative blue radial glow.

        pointer-events-none ensures this decorative element
        doesn't interfere with clicking or typing.
      */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-blue-500/10 rounded-full blur-[120px] pointer-events-none"></div>

      {/* 
        Main login card.

        glass-panel is presumably a custom Tailwind/CSS class
        that gives the card its glass-like appearance.
      */}
      <div className="w-full max-w-md glass-panel p-8 rounded-2xl shadow-2xl relative z-10">
        {/* -------------------------------------------------------------------
            BRAND / HEADER
        ------------------------------------------------------------------- */}

        <div className="flex flex-col items-center mb-8">
          {/* Shield icon representing security/fraud protection */}
          <div className="w-14 h-14 bg-blue-600/20 border border-blue-500/30 rounded-2xl flex items-center justify-center text-blue-500 mb-4 shadow-lg shadow-blue-500/10">
            <Shield className="w-8 h-8" />
          </div>

          {/* Application name */}
          <h1 className="text-2xl font-bold text-slate-100 font-display">
            FraudSense
          </h1>

          {/* Application description */}
          <p className="text-slate-400 text-sm mt-1">
            Transaction Risk & Monitoring Portal
          </p>
        </div>

        {/* -------------------------------------------------------------------
            API / LOGIN ERROR
        ------------------------------------------------------------------- */}

        {/* 
          Display this section only when `error` is not null.

          Example:
          Invalid email or password.
        */}
        {error && (
          <div className="mb-6 p-4 bg-red-900/20 border border-red-500/30 text-red-400 rounded-xl flex items-start gap-3 text-sm">
            {/* Warning/error icon */}
            <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />

            {/* Actual error message */}
            <span>{error}</span>
          </div>
        )}

        {/* -------------------------------------------------------------------
            LOGIN FORM
        ------------------------------------------------------------------- */}

        {/* 
          handleSubmit(onSubmit) performs validation first.

          If validation succeeds:
              onSubmit(data)
          
          If validation fails:
              onSubmit is not called and the errors object is populated.
        */}
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          {/* -----------------------------------------------------------------
              EMAIL FIELD
          ----------------------------------------------------------------- */}

          <div>
            {/* Email label */}
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
              Email Address
            </label>

            {/* 
              Email input.

              {...register('email')} connects this input
              to React Hook Form.

              React Hook Form will automatically track:
              - value
              - changes
              - validation
              - errors
            */}
            <input
              type="email"
              placeholder="e.g. analyst1@fraudsense.com"
              {...register("email")}
              // Change the border color when validation fails.
              className={`w-full px-4 py-3 bg-slate-950 border rounded-xl text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all ${
                errors.email
                  ? "border-red-500/50"
                  : "border-slate-800 focus:border-slate-700"
              }`}
            />

            {/* 
              Display the Zod validation error for email.

              Example:
              "Invalid email address"
            */}
            {errors.email && (
              <p className="mt-1 text-xs text-red-500">
                {errors.email.message}
              </p>
            )}
          </div>

          {/* -----------------------------------------------------------------
              PASSWORD FIELD
          ----------------------------------------------------------------- */}

          <div>
            {/* Password label */}
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
              Password
            </label>

            {/* 
              Password input.

              type="password" hides the characters entered by the user.
            */}
            <input
              type="password"
              placeholder="••••••••"
              {...register("password")}
              // Red border is shown when password validation fails.
              className={`w-full px-4 py-3 bg-slate-950 border rounded-xl text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all ${
                errors.password
                  ? "border-red-500/50"
                  : "border-slate-800 focus:border-slate-700"
              }`}
            />

            {/* 
              Display password validation error.

              Example:
              "Password must be at least 6 characters"
            */}
            {errors.password && (
              <p className="mt-1 text-xs text-red-500">
                {errors.password.message}
              </p>
            )}
          </div>

          {/* -----------------------------------------------------------------
              SIGN IN BUTTON
          ----------------------------------------------------------------- */}

          <button
            type="submit"
            // Prevent multiple login requests while one is already running.
            disabled={loading}
            className="w-full py-3 px-4 bg-blue-600 hover:bg-blue-500 disabled:bg-blue-800 text-white font-semibold rounded-xl transition-all shadow-lg shadow-blue-500/20 flex items-center justify-center"
          >
            {/* 
              If login is in progress:
                  Show spinner

              Otherwise:
                  Show "Sign In"
            */}
            {loading ? (
              // Loading spinner
              <svg
                className="animate-spin h-5 w-5 text-white"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />

                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
            ) : (
              // Normal button state
              "Sign In"
            )}
          </button>
        </form>

        {/* -------------------------------------------------------------------
            REGISTER LINK
        ------------------------------------------------------------------- */}

        <div className="mt-6 text-center">
          <p className="text-sm text-slate-400">
            {/* Message shown below the form */}
            Don't have an account?{" "}
            {/* 
              Link to registration page.

              React Router handles this navigation without
              performing a full browser page reload.
            */}
            <Link to="/register" className="text-blue-500 hover:underline">
              Create an account
            </Link>
          </p>
        </div>

        {/* -------------------------------------------------------------------
            DEMO CREDENTIALS
        ------------------------------------------------------------------- */}

        {/* 
          This section is useful during development/demo presentations.

          It provides pre-created accounts that can be used
          to test the application without registering new users.
        */}
        <div className="mt-8 pt-6 border-t border-slate-900/60 text-xs text-slate-400">
          {/* Section title */}
          <p className="font-semibold text-slate-300 mb-2">
            Seeded Demo Credentials:
          </p>

          {/* 
            Two-column layout containing credentials
            for the Analyst and Merchant roles.
          */}
          <div className="grid grid-cols-2 gap-2 text-slate-400">
            {/* ---------------------------------------------------------------
                ANALYST CREDENTIALS
            --------------------------------------------------------------- */}

            <div>
              {/* Role */}
              <p className="font-medium text-slate-300">Analyst:</p>

              {/* Demo email */}
              <p>analyst1@fraudsense.com</p>

              {/* Demo password */}
              <p>password123</p>
            </div>

            {/* ---------------------------------------------------------------
                MERCHANT CREDENTIALS
            --------------------------------------------------------------- */}

            <div>
              {/* Role */}
              <p className="font-medium text-slate-300">Merchant:</p>

              {/* Demo email */}
              <p>merchant1@fraudsense.com</p>

              {/* Demo password */}
              <p>password123</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
