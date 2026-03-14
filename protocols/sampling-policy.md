# Sampling Policy

Semantic Harness uses visible sampling in v1.

A sampling report must always be produced before discovery continues.

Supported sampling modes:
- auto
- confirm

Optional:
- timeout

## auto
Sampling produces a report and discovery continues automatically.

## confirm
Sampling produces a report and waits for architect confirmation before discovery continues.

## timeout
If auto sampling exceeds the configured timeout, automatic continuation must stop and the workflow must switch to confirmation mode.
