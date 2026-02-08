# 🦅 ARCOS Grandmaster v3.5
### Sovereign Financial Intelligence System

**ARCOS** is a local-first, privacy-focused investment intelligence platform. It combines autonomous Python agents ("The Swarm") with a strict Rust-based Risk Orchestrator ("The Maestro") to generate, validate, and audit financial signals.

## 🚀 Quick Start
1. **Prerequisites**: Install Docker Desktop.
2. **Setup**: Create a `.env` file with your `SMTP` and `RISK` parameters.
3. **Launch**: Run `docker compose up --build`.
   - **War Room UI**: http://localhost:8501

## 🖥️ Mission Control
- **Live Feed**: Monitor real-time AI-generated signals.
- **Audit Manifests**: Verify signal "Chain of Custody" using SHA256 hashes.
- **Portfolio**: Real-time tracking of simulated/live exposure and risk.

## 🛠 Maintenance
- **Memory Wipe**: Delete `workspace/arcos_vault.db` to reset the neural state.
- **Watchlist**: Auto-refreshes every 30 minutes via `discovery.py`.

---
