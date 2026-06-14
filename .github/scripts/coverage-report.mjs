import fs from "fs";

export async function updateCoverage() {
  const marker = "<!-- coverage-delta-report -->";
  const current = JSON.parse(fs.readFileSync(process.env.PR_COVERAGE_JSON));
  const report = fs.readFileSync(process.env.PR_COVERAGE_MARKDOWN, "utf8");
  const currentPercent = current.totals.percent_covered;
  const currentDisplay = `${currentPercent.toFixed(2)}%`;

  let comparison = `| Current coverage | ${currentDisplay} |\n`;
  if (context.eventName === "pull_request") {
    const base = JSON.parse(fs.readFileSync(process.env.BASE_COVERAGE_JSON));
    const basePercent = base.totals.percent_covered;
    const delta = currentPercent - basePercent;
    const deltaDisplay = `${delta >= 0 ? "+" : ""}${delta.toFixed(2)} pp`;
    comparison += `| Base coverage | ${basePercent.toFixed(2)}% |\n`;
    comparison += `| Coverage delta | **${deltaDisplay}** |\n`;
  }

  const body = [
    marker,
    "## Code coverage",
    "",
    "| Metric | Value |",
    "| --- | ---: |",
    comparison.trimEnd(),
    "",
    "<details>",
    "<summary>Coverage by file</summary>",
    "",
    report.trim(),
    "",
    "</details>",
  ].join("\n");

  await core.summary.addRaw(body.replace(`${marker}\n`, "")).write();

  if (context.eventName === "pull_request") {
    try {
      const comments = await github.paginate(github.rest.issues.listComments, {
        owner: context.repo.owner,
        repo: context.repo.repo,
        issue_number: context.issue.number,
      });
      const previous = comments.find(
        (comment) =>
          comment.user?.type === "Bot" && comment.body?.includes(marker),
      );
      const params = {
        owner: context.repo.owner,
        repo: context.repo.repo,
        body,
      };

      if (previous) {
        await github.rest.issues.updateComment({
          ...params,
          comment_id: previous.id,
        });
      } else {
        await github.rest.issues.createComment({
          ...params,
          issue_number: context.issue.number,
        });
      }
    } catch (error) {
      if (error.status !== 403) {
        throw error;
      }
      core.warning(
        "Unable to update the coverage comment with a read-only token.",
      );
    }
  }
}
