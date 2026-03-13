const actor = process.env.GITHUB_ACTOR || "";

function isBotActor() {
  return [
    "actions-user",
    "dependabot[bot]",
  ].indexOf(actor) !== -1;
}

function isDependencyUpdateCommit(message) {
  return message.startsWith("chore(deps):");
}

function shouldIgnoreCommit(message) {
  return isBotActor() || isDependencyUpdateCommit(message);
}

export default {
  extends: ["@commitlint/config-conventional"],
  defaultIgnores: false,

  ignores: [(message) => shouldIgnoreCommit(message)],

  rules: {
    "body-max-line-length": [2, "always", 72],
    "header-max-length": [2, "always", 72],
    "subject-max-length": [2, "always", 50],
    "subject-full-stop": [2, "never", "."],
    "jira-ticket": [2, "always"],
    "type-enum": [
      2,
      "always",
      ["build", "chore", "ci", "docs", "feat", "fix", "perf", "refactor", "revert", "style", "test", "temp"],
    ],

  },

  plugins: [
    "commitlint-plugin-function-rules",
    {
      rules: {
        "jira-ticket": ({ header, body, footer }) => {
          const regex = /\b[A-Z]{2,}\-[0-9]{1,}\b/;

          if (shouldIgnoreCommit(header)) {
            return [true];
          }

          if (regex.test(header)) {
            return [false, "JIRA ticket must be in the commit body or footer."];
          }

          if (regex.test(body) === false && regex.test(footer) === false) {
            return [
              false,
              "JIRA ticket is missing. Add it to commit body or footer.",
            ];
          }

          return [true];
        },
      },
    },
  ],
};
