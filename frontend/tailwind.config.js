/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          dark: "#0F172A", // Deep Navy / Slate
          light: "#F8FAFC", // Light background Slate
          accent: "#2563EB", // Royal Blue
          card: "#1E293B", // Darker Slate card background
          border: "#334155" // Slate border
        },
        risk: {
          clear: "#10B981", // Green
          flag: "#F59E0B", // Amber
          block: "#EF4444" // Red
        }
      }
    },
  },
  plugins: [],
}
