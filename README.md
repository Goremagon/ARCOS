# 🦅 ARCOS Grandmaster v4.0
### Sovereign Financial Intelligence System

**ARCOS** is a local-first, privacy-focused investment intelligence platform. It combines autonomous Python agents ("The Swarm") with a strict Rust-based Risk Orchestrator ("The Maestro") to generate, validate, and audit financial signals.

---

## 🚀 Quick Start
1. **Prerequisites**: Install Docker Desktop.
2. **Setup**: Create a `.env` file (see below).
3. **Launch**: Run `docker compose up --build`.
   - **War Room UI**: http://localhost:8501

### .env Configuration
Create a `.env` file in the project root:
```env
# Email & notifications
SMTP_USER=your_smtp_user
SMTP_PASS=your_smtp_password
ALERT_RECIPIENT=alerts@yourdomain.com

# Execution mode
ARCOS_EXECUTION_MODE=advisory

# Validation gates
ARCOS_MIN_SAMPLE_SIZE=30
ARCOS_MIN_WIN_RATE=0.65

# Risk limits
ARCOS_MAX_POSITION_CAP=0.15
ARCOS_MAX_GROSS_EXPOSURE=1.50

# Paths (optional overrides)
ARCOS_WORKSPACE=/app/workspace
ARCOS_DB_PATH=/app/workspace/arcos_vault.db
```

---

## 🧠 System Architecture (Overview)
ARCOS is built on a **decoupled swarm + Maestro** pattern with strict data contracts and auditability.

### Analyst Layer (Python Swarm)
- **data_fetcher** → produces raw, normalized snapshots (market, fundamentals, news, flows, macro).
- **feature_engine** → produces standardized features (momentum, trend, regime, cross-asset context).
- **signal_engine** → generates candidate signals from bounded templates.
- **news_reader** → scores and flags news impact (sentiment + hard flags).
- **calibrator** → nightly evaluation and drift detection with guardrails.

Each agent writes **typed, append-only artifacts** into the workspace. No agent can overwrite official outputs.

### Maestro (Rust Orchestrator)
- Validates input contracts and enforces **hard-rule gates**.
- Runs statistical validity checks (sample size, win-rate thresholds).
- Applies deterministic risk rules (position caps, concentration, turnover, volatility limits).
- Emits **official recommendations** and **audit manifests** with hashes.

### Outputs
- **Daily Briefing**: ranked recommendations + rationale + audit references.
- **War Room UI**: live signals, portfolio exposure, and manifest browsing.

---

## 🖥️ Mission Control
- **Intelligence Briefing**: Monitor live AI-generated signals with full asset names, confidence scores, and clean rationale text.
- **Asset Ledger**: Review gross/net exposure and current holdings in a streamlined table view.
- **System Tuning**: Adjust execution mode and validation gates directly in the UI. Click **Apply Configuration** to persist changes to `.env`, then run `docker compose restart` to apply changes to the swarm.
- **Audit Manifests**: Verify signal "Chain of Custody" using SHA256 hashes.
- **Portfolio**: Real-time tracking of simulated/live exposure and risk.

## 🛠 Maintenance
- **Memory Wipe**: Delete `workspace/arcos_vault.db` to reset the neural state.
- **Watchlist**: Auto-refreshes every 30 minutes via `discovery.py`.

---
