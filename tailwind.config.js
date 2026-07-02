module.exports = {
  content: ["./frontend/**/*.html"],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['Fira Code', 'monospace'],
      },
      textColor: {
        slate: {
          400: 'var(--text-slate-400)',
          500: 'var(--text-slate-500)',
          600: 'var(--text-slate-600)',
          700: 'var(--text-slate-700)',
          800: 'var(--text-slate-800)',
          900: 'var(--text-slate-900)',
        }
      },
      backgroundColor: {
        white: 'var(--bg-white)',
        slate: {
          50: 'var(--bg-slate-50)',
          100: 'var(--bg-slate-100)',
        }
      },
      borderColor: {
        slate: {
          100: 'var(--border-slate-100)',
          200: 'var(--border-slate-200)',
        }
      }
    }
  },
  plugins: [],
}
