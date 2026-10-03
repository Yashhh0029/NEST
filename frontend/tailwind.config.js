/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        brand: {
          primary: "#0F766E",
          "primary-hover": "#0D665F",
          "primary-light": "#E6F4F1",
          accent: "#F59E0B",
          "accent-hover": "#D97706",
          success: "#16A34A",
          danger: "#DC2626",
          light: "#FAFAF7",
          dark: "#0B1210",
          "dark-card": "#13211D",
          "dark-surface": "#182C26",
          "dark-border": "#1F352E",
          "dark-muted": "#2A453C",
        },
      },
      fontFamily: {
        heading: ["'Plus Jakarta Sans'", "system-ui", "-apple-system", "sans-serif"],
        sans: ["Inter", "system-ui", "-apple-system", "sans-serif"],
      },
      borderRadius: {
        card: "16px",
        input: "12px",
      },
      boxShadow: {
        soft: "0 4px 20px -2px rgba(15, 118, 110, 0.08)",
        "soft-lg": "0 10px 25px -3px rgba(15, 118, 110, 0.12)",
      },
    },
  },
  plugins: [],
};
