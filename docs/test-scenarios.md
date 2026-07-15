# Test scenarios

Use forty `a` characters for release A and forty `b` characters for release B.

## Ordered approval

Build release A, then promote its synthetic digest through TEST, UAT, and production. Approve each required reviewer gate. Confirm that every environment records the same digest.

## Rejected review

Start any promotion and reject the waiting review. Confirm that the job never starts and `lab-state` does not change.

## Wrong order

Build release B and request UAT before TEST. After approving the native gate, confirm that the contract rejects the transition because TEST does not contain release B.

## Digest substitution

Combine release A's source identity with release B's digest. Confirm that the transition is rejected.

## Rollback

Promote A and then B to TEST. Request a TEST rollback using A's registered identity and digest. Approve the gate and confirm that TEST returns to A without rebuilding anything.
