# Deployment control lab

This public repository demonstrates native GitHub Environment required reviewer gates using synthetic release identities. It does not build, publish, or deploy software.

## Safety boundary

The lab has no secrets, cloud credentials, deployment keys, private endpoints, customer data, or application source. Every digest is a deterministic synthetic digest with no corresponding container or artifact. Automated tests scan the published files for deployment capabilities and private identifiers.

## Flow

```text
Arbitrary source identity
        ↓
Register synthetic immutable release candidate
        ↓
TEST required reviewer gate
        ↓
UAT required reviewer gate (same digest required in TEST)
        ↓
production required reviewer gate (same digest required in UAT)
```

The three GitHub Environments are configured outside the workflow file. For convenient individual testing, self-review is allowed in this public lab. A real production configuration should prevent self-review and use an authorized business approver or team.

## Try it

1. Run **Build mock release candidate** with any lowercase 40-character hexadecimal value.
2. Copy the source identity and digest from the resulting artifact.
3. Run **Promote mock release candidate** for `test`.
4. Open the waiting workflow run and approve the deployment review.
5. Repeat with exactly the same values for `uat` and `production`.

No step contacts an external deployment system. The only mutable data is JSON on the repository's `lab-state` branch.

See [docs/test-scenarios.md](docs/test-scenarios.md) for rejection and rollback exercises.

## Local tests

```bash
python3 -m unittest discover -s tests -v
```
