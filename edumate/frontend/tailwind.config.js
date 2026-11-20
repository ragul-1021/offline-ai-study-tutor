/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        dark: {
          950: '#0a0a0b',
          900: '#0f0f10',
          850: '#141415',
          800: '#19191b',
          750: '#1f1f21',
          700: '#232325',
          600: '#2e2e31',
          500: '#3a3a3d',
        },
        accent: {
          DEFAULT: '#d4956a',
          hover: '#c4855a',
        },
        positive: '#4cc38a',
        negative: '#e5484d',
      },
    },
  },
  plugins: [],
}
