/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          teal: '#14b8a6',
          orange: '#f97316',
        },
        ipc: {
          1: '#c6ffc6',
          2: '#ffe252',
          3: '#e67800',
          4: '#c80000',
          5: '#640000',
        },
        severity: {
          low: '#14b8a6',
          moderate: '#f59e0b',
          high: '#f97316',
          critical: '#ef4444',
          catastrophic: '#7f1d1d',
        },
      },
    },
  },
  plugins: [],
};
