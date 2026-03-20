import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './app/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
  ],
  plugins: [require('daisyui')],
  daisyui: {
    themes: ['corporate', 'dark'],  // corporate = 白底商務風，dark = 深色模式
  },
}

export default config
