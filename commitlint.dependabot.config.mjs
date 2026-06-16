// commitlint config for dependabot-authored PRs.
//
// Dependabot's body content is auto-generated from upstream release notes
// and embeds full GitHub compare URLs, changelog links, and dep-tree
// tables that routinely exceed the 200-char cap used for human commits.
// Dependabot exposes no knob to wrap or reformat body content
// (`commit-message:` only controls prefix/scope on the subject line).
//
// Trade-off: dependabot commits must still be valid conventional commits
// (type, scope, subject) — only the line-length checks are relaxed. The
// type-enum is inlined here (rather than imported from
// commitlint.config.mjs) to keep this file self-contained the same way
// commitlint.config.mjs is, so it works in any worktree without a
// per-worktree `node_modules`.
//
// Per-author selection happens in `.github/workflows/commitlint.yml` via
// `github.event.pull_request.user.login`.

export default {
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
        'deps',
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
    // Disable line-length caps for dependabot — see header comment.
    'body-max-line-length': [0, 'always'],
    'footer-max-line-length': [0, 'always'],
    'body-leading-blank': [2, 'always'],
    'footer-leading-blank': [2, 'always'],
  },
};
