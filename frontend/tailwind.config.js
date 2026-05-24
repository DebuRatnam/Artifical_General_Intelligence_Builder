/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'SFMono-Regular', 'monospace'],
      },
      colors: {
        accent: {
          DEFAULT: '#a78bfa',
          dim:     '#7c3aed',
        },
      },
      keyframes: {
        'pulse-ring': {
          '0%':   { transform: 'scale(0.6)', opacity: '0.7' },
          '80%':  { transform: 'scale(2.2)', opacity: '0'   },
          '100%': { transform: 'scale(2.2)', opacity: '0'   },
        },
        'fade-in': {
          '0%':   { opacity: '0', transform: 'translateY(4px)' },
          '100%': { opacity: '1', transform: 'translateY(0)'   },
        },
      },
      animation: {
        'pulse-ring': 'pulse-ring 1.6s cubic-bezier(0.4,0,0.6,1) infinite',
        'fade-in':    'fade-in 0.18s ease-out',
      },
    },
  },
  plugins: [],
}
