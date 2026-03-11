module.exports = {
  root: true,
  env: {
    node: true,
    es2022: true,
  },
  extends: ['eslint:recommended'],
  parserOptions: {
    ecmaVersion: 'latest',
  },
  ignorePatterns: ['node_modules/', 'playwright-report/', 'test-results/'],
};
