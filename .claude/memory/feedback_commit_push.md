---
name: commit_push_every_change
description: Always commit and push to GitHub after every code change in BilligTanken
type: feedback
---

After every code change in the BilligTanken project, always commit and push to GitHub (HelmutQualtinger/BilligTanken) before finishing the response.

**Why:** User explicitly requested this workflow so changes are always reflected in the public repo.

**How to apply:** After any edit to billigtanken.py, Dockerfile, docker-compose.yml, entrypoint.sh, or other project files — stage the changed files, commit with a descriptive message, and push to origin main.

Memory files live in `.claude/memory/` inside the project repo and are version-controlled alongside the code.
