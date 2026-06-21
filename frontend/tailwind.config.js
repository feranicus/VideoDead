/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        teal: { DEFAULT: "#00D7BD", mid: "#00A49A", dark: "#0C544E" },
        ink: "#121212",
        muted: "#5B6470",
      },
      fontFamily: {
        display: ["Arial Black", "Arial", "sans-serif"],
      },
    },
  },
  plugins: [],
};
