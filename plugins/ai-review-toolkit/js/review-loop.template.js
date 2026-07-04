export const meta = {
  name: 'review-loop',
  description: 'Multi-agent review→synthesize→gate→fix convergence loop (qreview=1 round, qloop=until-converged)',
  phases: [
    { title: 'Review', detail: 'N clean-context reviewers in parallel per round' },
    { title: 'Fix', detail: 'single in-place fixer per round; fixes persist to next round' },
  ],
}

// @@INLINE@@ build-workflow.mjs replaces this whole line with adjudication.mjs + prompts.mjs + workflow-helpers.mjs + loop-engine.mjs

// `args` may arrive as a parsed object or a JSON string, depending on how the
// Workflow was invoked; tolerate both. The whole loop lives in the inlined
// runLoop() (loop-engine.mjs) so review-loop and pipeline-auto share one engine.
const A = typeof args === "string" ? JSON.parse(args) : (args || {})

return await runLoop(
  {
    artifact: A.artifact,
    requirements: A.requirements,
    team: A.team || [],
    threshold: A.threshold ?? 0,
    rounds: A.rounds,
    maxRounds: A.maxRounds,
    // Optional CLI-time signals: `complexity` ({files, toolTypes, contextFraction})
    // drives in-engine reviewer model tiering; `skipTests` suppresses the test
    // gate for artifacts with no executable test surface.
    complexity: A.complexity ?? null,
    skipTests: A.skipTests ?? false,
  },
  { agent, parallel, phase, log },
)
