# Fitness Coach Prospecting Pipeline - Documentation

## Table of Contents

| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | System architecture, tech stack, directory structure, data flow, and concurrency model |
| [PIPELINE.md](PIPELINE.md) | Detailed pipeline flow: all 7 phases from discovery through export, with data transformations at each stage |
| [DATA_MODEL.md](DATA_MODEL.md) | Complete Lead dataclass reference (44 fields), serialization, identity keys, and lifecycle |
| [CONFIGURATION.md](CONFIGURATION.md) | All environment variables, Settings dataclass, keyword tiers, cache files, and hardcoded constants |
| [MODULES.md](MODULES.md) | Module-by-module API reference for all 20 source files across 8 packages |
| [UI.md](UI.md) | Streamlit web UI pages, components, data sources, state management, and known issues |
| [SETUP.md](SETUP.md) | Installation guide, dependency setup, Google Sheets configuration, and troubleshooting |
| [CODE_REVIEW.md](CODE_REVIEW.md) | Comprehensive code review: 44 findings across bugs, security, architecture, quality, performance, testing, and dependencies |

---

## Quick Links

### Getting Started
- [Installation & Setup](SETUP.md)
- [Configuration Reference](CONFIGURATION.md)

### Understanding the System
- [Architecture Overview](ARCHITECTURE.md)
- [Pipeline Flow (7 phases)](PIPELINE.md)
- [Data Model (Lead fields)](DATA_MODEL.md)

### Developer Reference
- [Module API Reference](MODULES.md)
- [Streamlit UI Details](UI.md)
- [Code Review & Technical Debt](CODE_REVIEW.md)

---

## Project Summary

An automated B2B lead generation tool that discovers English-speaking fitness coaches globally, extracts their contact data, scores them by ICP fit, and exports results to Google Sheets for cold email outreach.

**Key metrics:**
- ~3,100 lines of Python across 20 source files
- 7-phase pipeline: Discovery -> Filter -> Enrich -> Verify -> Score -> Dedup -> Export
- 44-field Lead data model
- ~1,274 search query pool with rotation across runs
- Parallel SMTP verification (5 workers)
- Target: 30-50 fresh leads per run

---

## Code Review Summary

The [Code Review](CODE_REVIEW.md) identified **44 issues**:

| Severity | Count | Top Issues |
|----------|-------|------------|
| Critical | 5 | Broken UI tabs, unreachable code, exposed credentials, incomplete requirements.txt, zero tests |
| Major | 17 | God module (980 lines), contradictory domain lists, unused dead code, missing follower regex for "M" suffix |
| Minor | 15 | Redundant imports, inconsistent logging, magic numbers in scoring, unused settings |
| Info | 7 | Missing docstrings, artifact files, export field gaps |

See [CODE_REVIEW.md](CODE_REVIEW.md) for the full findings and prioritized remediation plan.
