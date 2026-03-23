/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        "primary-green": "#2F8F46",
        "primary-green-dark": "#1F6B33",
        "primary-green-soft": "#E6F5EA",
        "accent-leaf": "#8FD694",
        "ink": "#1D2B22"
      },
      fontFamily: {
        display: ["'Kumbh Sans'", "sans-serif"],
        body: ["'Kumbh Sans'", "sans-serif"]
      },
      boxShadow: {
        "panel": "0 20px 40px rgba(31, 107, 51, 0.12)"
      }
    }
  },
  plugins: []
};
