import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import prettierConfig from 'eslint-config-prettier'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
      prettierConfig,
    ],
    languageOptions: {
      globals: globals.browser,
    },
    rules: {
      // Airbnb-style: prefer const
      'prefer-const': 'error',
      'no-var': 'error',

      // Airbnb-style: arrow functions
      'arrow-body-style': ['error', 'as-needed'],
      'prefer-arrow-callback': 'error',

      // Airbnb-style: object & destructuring
      'object-shorthand': ['error', 'always'],
      'prefer-destructuring': ['error', { array: false, object: true }],

      // Airbnb-style: imports
      'no-duplicate-imports': 'error',

      // Airbnb-style: TypeScript
      '@typescript-eslint/no-explicit-any': 'warn',
      '@typescript-eslint/explicit-function-return-type': 'off',
      '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_' }],

      // Airbnb-style: React
      'react-hooks/rules-of-hooks': 'error',
      'react-hooks/exhaustive-deps': 'warn',
    },
  },
])
