/** @type {import("tailwindcss").Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50:  "#f5f0ff",
          100: "#ede2ff",
          200: "#dcc8ff",
          300: "#c2a3ff",
          400: "#a87cff",
          500: "#8557f5",
          600: "#6839d8",
          700: "#5029a6",
          800: "#3d217c",
          900: "#2f1b61",
        },
        accent: { DEFAULT: "#fb7185", hover: "#f43f5e" },
      },
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', "system-ui", "sans-serif"],
      },
      animation: {
        "fade-in":        "fadeIn 0.3s ease-out both",
        "slide-up":       "slideUp 0.4s ease-out both",
        "slide-in-left":  "slideInLeft 0.28s cubic-bezier(0.16,1,0.3,1) both",
        "slide-in-right": "slideInRight 0.28s cubic-bezier(0.16,1,0.3,1) both",
        "pulse-soft":     "pulseSoft 2s ease-in-out infinite",
        "glow-pulse":     "glowPulse 3s ease-in-out infinite",
        "scale-in":       "scaleIn 0.2s ease-out both",
      },
      keyframes: {
        fadeIn:       { "0%": { opacity: "0" }, "100%": { opacity: "1" } },
        slideUp:      { "0%": { opacity: "0", transform: "translateY(16px)" }, "100%": { opacity: "1", transform: "translateY(0)" } },
        slideInLeft:  { "0%": { opacity: "0", transform: "translateX(-100%)" }, "100%": { opacity: "1", transform: "translateX(0)" } },
        slideInRight: { "0%": { opacity: "0", transform: "translateX(100%)" }, "100%": { opacity: "1", transform: "translateX(0)" } },
        pulseSoft:    { "0%,100%": { opacity: "1" }, "50%": { opacity: "0.6" } },
        glowPulse:    { "0%,100%": { boxShadow: "0 0 20px rgba(134,87,245,0.3)" }, "50%": { boxShadow: "0 0 40px rgba(134,87,245,0.6)" } },
        scaleIn:      { "0%": { opacity: "0", transform: "scale(0.95)" }, "100%": { opacity: "1", transform: "scale(1)" } },
      },
      backgroundImage: {
        "grid-pattern": "linear-gradient(rgba(255,255,255,0.03) 1px,transparent 1px),linear-gradient(to right,rgba(255,255,255,0.03) 1px,transparent 1px)",
      },
      backgroundSize: {
        "grid-sm": "40px 40px",
      },
    },
  },
  plugins: [],
};
