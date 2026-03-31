/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './templates/**/*.html',
    './**/templates/**/*.html',
    './static/js/**/*.js',
  ],
  theme: {
    extend: {
      colors: {
        bg: '#0A0A0A',
        fg: '#FAFAFA',
        muted: '#1A1A1A',
        'muted-fg': '#737373',
        accent: '#FF3D00',
        'accent-fg': '#0A0A0A',
        border: '#262626',
        input: '#1A1A1A',
        card: '#0F0F0F',
        'card-fg': '#FAFAFA',
        ring: '#FF3D00',
        /* Semantic colors preserved for financial status */
        'status-success': '#10b981',
        'status-danger': '#ef4444',
        'status-warning': '#f59e0b',
        'status-info': '#3b82f6',
        'status-purple': '#8b5cf6',
      },
      fontFamily: {
        display: ['"Inter Tight"', 'Inter', 'system-ui', 'sans-serif'],
        body: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', '"Fira Code"', 'monospace'],
      },
      letterSpacing: {
        tighter: '-0.06em',
        tight: '-0.04em',
        normal: '-0.01em',
        wide: '0.05em',
        wider: '0.1em',
        widest: '0.2em',
      },
      lineHeight: {
        none: '1',
        tight: '1.1',
        snug: '1.25',
        normal: '1.6',
        relaxed: '1.75',
      },
      borderRadius: {
        DEFAULT: '0px',
        none: '0px',
        xs: '0px',
      },
      fontSize: {
        xs: ['0.75rem', { lineHeight: '1.5' }],
        sm: ['0.875rem', { lineHeight: '1.5' }],
        base: ['1rem', { lineHeight: '1.6' }],
        lg: ['1.125rem', { lineHeight: '1.6' }],
        xl: ['1.25rem', { lineHeight: '1.25' }],
        '2xl': ['1.5rem', { lineHeight: '1.25' }],
        '3xl': ['2rem', { lineHeight: '1.1' }],
        '4xl': ['2.5rem', { lineHeight: '1.1' }],
        '5xl': ['3.5rem', { lineHeight: '1.1' }],
        '6xl': ['4.5rem', { lineHeight: '1.1' }],
        '7xl': ['6rem', { lineHeight: '1' }],
        '8xl': ['8rem', { lineHeight: '1' }],
        '9xl': ['10rem', { lineHeight: '1' }],
      },
      spacing: {
        '18': '4.5rem',
        '22': '5.5rem',
      },
      borderWidth: {
        DEFAULT: '1px',
        thick: '2px',
      },
      boxShadow: {
        none: 'none',
      },
    },
  },
  plugins: [],
}
