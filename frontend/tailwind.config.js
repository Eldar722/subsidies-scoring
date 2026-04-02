export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        primary: '#2563EB',
        hidden: '#7C3AED',
      },
      fontFamily: {
        sans: ['Manrope', 'sans-serif'],
      },
      boxShadow: {
        xs: 'var(--shadow-xs)',
        sm: 'var(--shadow-sm)',
        DEFAULT: 'var(--shadow-md)',
        md: 'var(--shadow-md)',
        lg: 'var(--shadow-lg)',
        xl: 'var(--shadow-xl)',
      },
      borderColor: {
        DEFAULT: 'var(--color-border)',
        light: 'var(--color-border-light)',
      },
    },
  },
  plugins: [],
}
