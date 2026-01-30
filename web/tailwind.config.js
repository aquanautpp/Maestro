/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        maestro: {
          green: '#4ade80',
          'green-dark': '#16a34a',
          'green-light': '#bbf7d0',
          'green-bg': '#f0fdf4',
          child: '#60a5fa',
          'child-light': '#dbeafe',
          adult: '#fb923c',
          'adult-light': '#fed7aa',
          silence: '#9ca3af',
          'silence-light': '#f3f4f6',
        },
      },
      animation: {
        'pulse-green': 'pulse-green 1s ease-in-out',
      },
      keyframes: {
        'pulse-green': {
          '0%': { transform: 'scale(1)', boxShadow: '0 0 0 0 rgba(74, 222, 128, 0.7)' },
          '50%': { transform: 'scale(1.05)', boxShadow: '0 0 0 20px rgba(74, 222, 128, 0)' },
          '100%': { transform: 'scale(1)', boxShadow: '0 0 0 0 rgba(74, 222, 128, 0)' },
        },
      },
    },
  },
  plugins: [],
}
