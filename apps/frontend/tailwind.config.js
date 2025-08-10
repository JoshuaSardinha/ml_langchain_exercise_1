/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/**/*.{js,jsx,ts,tsx}',
    './index.html'
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#eff6ff',
          100: '#dbeafe',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8'
        },
        chat: {
          user: '#dcf8c6',
          assistant: '#ffffff',
          system: '#f3f4f6',
          error: '#fee2e2'
        }
      },
      maxWidth: {
        'chat': '800px'
      },
      animation: {
        'typing': 'typing 1.5s ease-in-out infinite',
        'fadeIn': 'fadeIn 0.3s ease-in-out',
        'slideInFromLeft': 'slideInFromLeft 0.4s ease-out',
        'shimmer': 'shimmer 2s linear infinite'
      },
      keyframes: {
        typing: {
          '0%, 60%': { opacity: '1' },
          '30%': { opacity: '0.5' }
        },
        fadeIn: {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' }
        },
        slideInFromLeft: {
          '0%': { opacity: '0', transform: 'translateX(-20px)' },
          '100%': { opacity: '1', transform: 'translateX(0)' }
        },
        shimmer: {
          '0%': { transform: 'translateX(-100%)' },
          '100%': { transform: 'translateX(200%)' }
        }
      }
    },
  },
  plugins: [],
}