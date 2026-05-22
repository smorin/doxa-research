// Self-contained Conventional Commits config. We do NOT extend
// `@commitlint/config-conventional` — that would force every git worktree
// to run `npm install` before its first commit (commitlint's `extends`
// resolver looks in `<cwd>/node_modules`, which is per-worktree). The
// rules below mirror the conventional-commits subset we actually enforce.
//
// Effect: `bunx commitlint --edit {1}` works with NO local node_modules
// and NO project-level package.json.

export default {
  ignores: [(message) => message === 'Clarify behavior and recommendations for --no-validate'],
  rules: {
    'type-empty': [2, 'never'],
    'type-case': [2, 'always', 'lower-case'],
    'type-enum': [
      2,
      'always',
      [
        'feat',
        'fix',
        'perf',
        'refactor',
        'docs',
        'test',
        'ci',
        'chore',
        'build',
        'style',
        'revert',
      ],
    ],
    'subject-empty': [2, 'never'],
    'subject-full-stop': [2, 'never', '.'],
    'header-max-length': [2, 'always', 100],
    'body-leading-blank': [2, 'always'],
    'footer-leading-blank': [2, 'always'],
  },
};
