# Challenge Authoring Guide

## Quality bar

A useful infrastructure challenge must:

1. Begin with an operational event, not a list of technologies.
2. Include constraints that prevent trivial deletion or bypass.
3. Score observable outcomes rather than preferred syntax.
4. Weight controls by blast-radius reduction.
5. Include one known-bad fixture and one known-good fixture.
6. Produce evidence that helps a reviewer explain the score.

## Add a rule

1. Add a pure check function to `checks.py`.
2. Register it in `CHECKS`.
3. Add the weighted rule to `challenge.yaml`.
4. Update secure and insecure fixtures.
5. Add a focused regression test.

Weights must total 100. A passing score near 80 generally permits one reasonable
tradeoff while still rejecting solutions with several weak controls.

## Candidate isolation

Never execute untrusted candidate code on a persistent runner. For live tests,
use an ephemeral cloud account, workload identity, a maximum job duration, a
budget alarm, explicit service-control policies, and teardown from an independent
cleanup identity.

## Review rubric

- Technical correctness: Does the rule reflect provider and platform behavior?
- Evasion resistance: Can cosmetic source changes satisfy it?
- Signal quality: Does it distinguish materially safer infrastructure?
- Explanation: Can a reviewer defend the weight and evidence?
- Reproducibility: Do fixtures exercise both branches deterministically?

