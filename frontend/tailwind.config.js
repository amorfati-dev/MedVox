/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
    "./public/index.html"
  ],
  theme: {
    extend: {
      colors: {
        dental: {
          primary: '#2563eb',
          secondary: '#64748b',
          success: '#22c55e',
          warning: '#f59e0b',
          error: '#ef4444'
        }
      }
    },
  },
  plugins: [],
} 