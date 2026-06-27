/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: "#4f46e5", // FlexURL Indigo Primary
          hover: "#4338ca",
          light: "#e0e7ff",
        },
        accent: "#C4F000",
      },
      fontFamily: {
        sans: ["Inter Tight", "sans-serif"],
        serif: ["Newsreader", "serif"],
      },
    },
  },
  plugins: [],
}
