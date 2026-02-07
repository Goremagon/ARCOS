# ARCOS: AI Rule-Constrained Orchestration System
### Prototype v0.1.0

**ARCOS** is a multi-agent orchestration system that demonstrates "Decoupled Microservices." It uses a Python-based Agent Swarm to generate tasks and a Rust-based "Maestro" to validate, enforce rules, and execute those tasks.

---

## 📂 Project Structure

| File | Purpose |
| :--- | :--- |
| **`src/main.rs`** | The **Maestro**. Rust core that parses XML, validates agents, and executes file I/O. |
| **`auto_agent.py`** | The **Agent**. Python script that simulates autonomous behavior (Producer, Validator, Speculus). |
| **`schemas/arcos-core.xsd`** | The **Law**. XML Schema Definition that enforces strict data contracts. |
| **`docker-compose.yml`** | The **Infrastructure**. Defines how to spin up the swarm in containers. |
| **`workspace/`** | The **Output**. Shared folder where the Maestro writes the final files. |

---

## 🚀 How to Run (The "All-In-One" Way)

**Prerequisites:** [Docker Desktop](https://www.docker.com/products/docker-desktop)

1. Open a terminal in this folder.
2. Run the swarm:
   ```bash
   docker compose up --build
   ```

## 🔐 Configuration

ARCOS relies on environment variables for secrets and runtime settings:

- `SMTP_USER`, `SMTP_PASS`, `ALERT_RECIPIENT` (email alerts)
- `ARCOS_WORKSPACE` (workspace root, default `workspace`)
- `ARCOS_DB_PATH` (SQLite database path)
- `ARCOS_MIN_SAMPLE_SIZE`, `ARCOS_MIN_WIN_RATE` (validity gates)
- `ARCOS_MAX_POSITION_CAP`, `ARCOS_MAX_GROSS_EXPOSURE` (risk gates)
- `ARCOS_EXECUTION_MODE` (`advisory` by default)
