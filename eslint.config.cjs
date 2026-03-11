module.exports = [
  {
    ignores: [
      'node_modules/**',
      'playwright-report/**',
      'test-results/**',
      '.venv/**',
    ],
  },
  {
    files: ['**/*.js'],
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'commonjs',
    },
    rules: {
      'no-undef': 'error',
      'no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
    },
  },
];
