/** @type {import("tailwindcss").Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50:  "#f0f4ff",
          100: "#e0eaff",
          200: "#c7d7fe",
          300: "#a5bbfc",
          400: "#8097f8",
          500: "#6272f1",
          600: "#4f54e5",
          700: "#4143ca",
          800: "#3537a3",
          900: "#2f3281",
        },
        accent: { DEFAULT: "#f472b6", hover: "#ec4899" },
      },
      fontFamily: { sans: ["Inter", "system-ui", "sans-serif"] },
      animation: {
        "fade-in":   "fadeIn 0.3s ease-out",
        "slide-up":  "slideUp 0.4s ease-out",
        "pulse-soft": "pulseSoft 2s ease-in-out infinite",
      },
      keyframes: {
        fadeIn:    { "0%": { opacity: "0" }, "100%": { opacity: "1" } },
        slideUp:   { "0%": { opacity: "0", transform: "translateY(16px)" }, "100%": { opacity: "1", transform: "translateY(0)" } },
        pulseSoft: { "0%,100%": { opacity: "1" }, "50%": { opacity: "0.6" } },
      },
    },
  },
  plugins: [],
};