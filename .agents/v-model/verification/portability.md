# Python Portability Verification

Mark an action `passing` only when durable evidence exercises every pass-criterion
clause; do not paste transient logs.

## SYSV-011 — Verify the generic detector dependency surface

- **Covers:** SYS-011
- **Method:** inspection
- **Procedure:** Inventory every Python API and object attribute used to own the profile
  slot and classify public and specialized rewrite frames. Compare each item with the
  official Python 3.10 and 3.13 `sys`, data-model, and `inspect` documentation. Inspect
  all detector imports and source paths for newer monitoring APIs, bytecode or opcode
  inspection, private or native frame access, frame-local mutation or concrete-type
  assumptions, and minor-version-selected detector behavior. Inspect each `f_locals`
  access to confirm that it is an immediate read-only mapping lookup.
- **Environment / configuration:** Implemented tracer source and dependency metadata,
  the pinned Kirin revision declaring Python 3.10 as its floor, and the official Python
  3.10 and 3.13 documentation. Runtime results, if cited, come from the CPython 3.13.11
  environment and remain corroborating single-environment evidence only.
- **Pass criterion:** Every version-sensitive detector dependency is in SYS-011's
  permitted documented surface; every prohibited-mechanism search has no finding; every
  frame-local access is independent of mapping concrete type and identity and performs
  no write; and no runtime result is represented as evidence for an unexecuted
  interpreter or Python version.
- **Status:** passing
- **Evidence:** [Detector portability inspection](../evidence/detector-portability-inspection.md#inspected-surface)
- **Nonconformance:** None
