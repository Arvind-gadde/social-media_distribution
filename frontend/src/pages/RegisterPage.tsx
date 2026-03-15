import { useState } from "react";
import toast from "react-hot-toast";
import { Link, useNavigate } from "react-router-dom";
import { Zap } from "lucide-react";
import { getGoogleUrl, register } from "../api/auth";
import { useAuthStore } from "../store/authStore";

interface FormState {
  name: string;
  email: string;
  password: string;
  confirm: string;
}

const EMPTY_FORM: FormState = { name: "", email: "", password: "", confirm: "" };

export default function RegisterPage() {
  const navigate = useNavigate();
  const setUser = useAuthStore((state) => state.setUser);
  const setAccessToken = useAuthStore((state) => state.setAccessToken);
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [errors, setErrors] = useState<Partial<FormState>>({});
  const [loading, setLoading] = useState(false);

  const validate = (): boolean => {
    const nextErrors: Partial<FormState> = {};
    if (!form.name.trim()) nextErrors.name = "Name is required";
    if (!form.email.includes("@")) nextErrors.email = "Enter a valid email";
    if (form.password.length < 8) nextErrors.password = "Minimum 8 characters";
    if (!/[a-zA-Z]/.test(form.password) || !/[0-9]/.test(form.password)) {
      nextErrors.password = "Must contain at least one letter and one number";
    }
    if (form.password !== form.confirm) nextErrors.confirm = "Passwords do not match";
    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!validate()) return;

    setLoading(true);
    try {
      const { data } = await register({
        name: form.name.trim(),
        email: form.email.trim().toLowerCase(),
        password: form.password,
      });
      if (data.access_token) setAccessToken(data.access_token);
      setUser(data.user);
      toast.success(`Welcome to ContentFlow, ${data.user.name}!`);
      navigate("/dashboard", { replace: true });
    } catch (err: any) {
      const message =
        err.response?.data?.detail ||
        err.response?.data?.message ||
        "Registration failed. Please try again.";
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  const field = (
    id: keyof FormState,
    label: string,
    type = "text",
    placeholder = ""
  ) => (
    <div>
      <label htmlFor={id} className="mb-1 block text-sm font-medium text-white/80">
        {label}
      </label>
      <input
        id={id}
        type={type}
        autoComplete={type === "password" ? "new-password" : id}
        placeholder={placeholder}
        value={form[id]}
        onChange={(event) => {
          setForm((value) => ({ ...value, [id]: event.target.value }));
          if (errors[id]) setErrors((value) => ({ ...value, [id]: undefined }));
        }}
        className={`input ${errors[id] ? "border-red-400/70" : ""}`}
      />
      {errors[id] && <p className="mt-1 text-xs text-red-300">{errors[id]}</p>}
    </div>
  );

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="card space-y-6 p-8">
          <div className="space-y-2 text-center">
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl gradient-bg shadow-md">
              <Zap size={24} className="text-white" />
            </div>
            <h1 className="text-2xl font-bold text-white">Create account</h1>
            <p className="text-sm text-white/55">
              Start distributing your content to every connected channel.
            </p>
          </div>

          <form onSubmit={handleSubmit} noValidate className="space-y-4">
            {field("name", "Full name", "text", "Arjun Sharma")}
            {field("email", "Email", "email", "you@example.com")}
            {field("password", "Password", "password", "Min. 8 characters")}
            {field("confirm", "Confirm password", "password", "Repeat password")}

            <button
              type="submit"
              disabled={loading}
              className="btn-primary w-full rounded-xl py-3 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loading ? "Creating account..." : "Create account"}
            </button>
          </form>

          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-white/10" />
            </div>
            <div className="relative flex justify-center">
              <span className="bg-[#090b11] px-3 text-xs text-white/45">or</span>
            </div>
          </div>

          <GoogleButton />

          <p className="text-center text-sm text-white/55">
            Already have an account?{" "}
            <Link to="/login" className="font-medium text-brand-200 hover:underline">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}

function GoogleButton() {
  const [loading, setLoading] = useState(false);

  const handleGoogle = async () => {
    setLoading(true);
    try {
      const { data } = await getGoogleUrl();
      window.location.href = data.url;
    } catch {
      toast.error("Could not reach Google. Try again.");
      setLoading(false);
    }
  };

  return (
    <button
      type="button"
      onClick={handleGoogle}
      disabled={loading}
      className="flex w-full items-center justify-center gap-3 rounded-xl border-2 border-white/10 bg-white/5 px-5 py-3 text-sm font-semibold text-white/85 transition-all duration-150 hover:border-white/20 hover:bg-white/10 active:scale-95 disabled:opacity-50"
    >
      <svg width="18" height="18" viewBox="0 0 24 24">
        <path
          fill="#4285F4"
          d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
        />
        <path
          fill="#34A853"
          d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
        />
        <path
          fill="#FBBC05"
          d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
        />
        <path
          fill="#EA4335"
          d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
        />
      </svg>
      {loading ? "Redirecting..." : "Continue with Google"}
    </button>
  );
}
