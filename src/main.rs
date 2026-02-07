use serde::Deserialize;
use std::env;
use std::fs;
use std::path::PathBuf;
use std::thread;
use std::time::Duration;
use lettre::transport::smtp::authentication::Credentials;
use lettre::{Message, SmtpTransport, Transport};
use redis::Commands;
use warp::Filter;
use sha2::{Digest, Sha256};

#[derive(Clone)]
struct Config {
    smtp_user: String,
    smtp_pass: String,
    alert_recipient: String,
    workspace_root: String,
    min_sample_size: u32,
    min_win_rate: f64,
    max_position_cap: f64,
    max_gross_exposure: f64,
    execution_mode: String,
}

#[derive(Debug, Deserialize)]
struct ArcosMessage {
    header: Header,
    body: Body,
}

#[derive(Debug, Deserialize)]
struct Header {
    message_id: String,
}

#[derive(Debug, Deserialize)]
struct Body {
    ticker: String,
    signal: String,
    probability: f64,
    #[serde(default)]
    win_rate: f64,
    uncertainty: f64,
    sample_size: u32,
    rationale: String,
    signature: String,
    #[serde(default)]
    tags: Vec<String>,
}

fn send_email_alert(msg: &ArcosMessage, config: &Config) {
    println!("   📧 [Alert] Sending email for {}...", msg.body.ticker);
    
    let subject_line = if msg.body.signal == "INFO" {
        format!("🏛️ ARCOS Briefing: Market Summary")
    } else if msg.body.signal.contains("URGENT") {
        format!("🚨 URGENT: {} Moving Fast!", msg.body.ticker)
    } else {
        format!("🚀 ARCOS Signal: {} ({:.0}%)", msg.body.ticker, msg.body.probability * 100.0)
    };

    let email = Message::builder()
        .from(config.smtp_user.parse().unwrap())
        .to(config.alert_recipient.parse().unwrap())
        .subject(subject_line)
        .body(format!("Ticker: {}\nSignal: {}\nConfidence: {:.2}%\n\nREPORT:\n{}", 
            msg.body.ticker, msg.body.signal, msg.body.probability * 100.0, msg.body.rationale))
        .unwrap();

    let creds = Credentials::new(config.smtp_user.to_string(), config.smtp_pass.to_string());
    let mailer = SmtpTransport::relay("smtp.gmail.com").unwrap().credentials(creds).build();

    match mailer.send(&email) {
        Ok(_) => println!("   ✅ [Alert] Email Sent!"),
        Err(e) => println!("   ❌ [Alert] Error: {:?}", e),
    }
}

fn load_config() -> Config {
    Config {
        smtp_user: env::var("SMTP_USER").unwrap_or_default(),
        smtp_pass: env::var("SMTP_PASS").unwrap_or_default(),
        alert_recipient: env::var("ALERT_RECIPIENT").unwrap_or_default(),
        workspace_root: env::var("ARCOS_WORKSPACE").unwrap_or_else(|_| "workspace".to_string()),
        min_sample_size: env::var("ARCOS_MIN_SAMPLE_SIZE")
            .ok()
            .and_then(|v| v.parse().ok())
            .unwrap_or(30),
        min_win_rate: env::var("ARCOS_MIN_WIN_RATE")
            .ok()
            .and_then(|v| v.parse().ok())
            .unwrap_or(0.65),
        max_position_cap: env::var("ARCOS_MAX_POSITION_CAP")
            .ok()
            .and_then(|v| v.parse().ok())
            .unwrap_or(0.10),
        max_gross_exposure: env::var("ARCOS_MAX_GROSS_EXPOSURE")
            .ok()
            .and_then(|v| v.parse().ok())
            .unwrap_or(1.0),
        execution_mode: env::var("ARCOS_EXECUTION_MODE").unwrap_or_else(|_| "advisory".to_string()),
    }
}

fn validate_message(msg: &ArcosMessage) -> Result<(), String> {
    if msg.body.ticker.trim().is_empty() {
        return Err("Ticker missing".to_string());
    }
    if !(0.0..=1.0).contains(&msg.body.probability) {
        return Err("Probability out of bounds".to_string());
    }
    Ok(())
}

fn compute_sha256(path: &PathBuf) -> Result<String, String> {
    let data = fs::read(path).map_err(|e| e.to_string())?;
    let mut hasher = Sha256::new();
    hasher.update(&data);
    Ok(format!("{:x}", hasher.finalize()))
}

fn latest_artifact(workspace_root: &str, category: &str) -> Option<PathBuf> {
    let mut path = PathBuf::from(workspace_root);
    path.push(category);
    let entries = fs::read_dir(&path).ok()?;
    let mut files: Vec<PathBuf> = entries
        .filter_map(|e| e.ok())
        .map(|e| e.path())
        .filter(|p| p.extension().map(|ext| ext == "json").unwrap_or(false))
        .collect();
    files.sort();
    files.pop()
}

fn apply_validity_gate(msg: &ArcosMessage, config: &Config) -> Vec<String> {
    let mut failures = Vec::new();
    if msg.body.sample_size < config.min_sample_size {
        failures.push(format!(
            "Sample size below minimum ({} < {})",
            msg.body.sample_size, config.min_sample_size
        ));
    }
    if msg.body.win_rate > 0.0 && msg.body.win_rate < config.min_win_rate {
        failures.push(format!(
            "Win rate below minimum ({:.2} < {:.2})",
            msg.body.win_rate, config.min_win_rate
        ));
    }
    failures
}

fn apply_risk_engine(config: &Config, portfolio_state: serde_json::Value) -> Vec<String> {
    let mut failures = Vec::new();
    if let Some(exposure) = portfolio_state.get("exposure") {
        let gross = exposure.get("gross").and_then(|v| v.as_f64()).unwrap_or(0.0);
        if gross > config.max_gross_exposure {
            failures.push(format!(
                "Gross exposure {:.2} exceeds cap {:.2}",
                gross, config.max_gross_exposure
            ));
        }
    }
    if let Some(positions) = portfolio_state.get("positions").and_then(|v| v.as_array()) {
        for position in positions {
            let weight = position.get("weight").and_then(|v| v.as_f64()).unwrap_or(0.0);
            if weight > config.max_position_cap {
                failures.push(format!(
                    "Position weight {:.2} exceeds cap {:.2}",
                    weight, config.max_position_cap
                ));
            }
        }
    }
    failures
}

fn write_official_output(
    config: &Config,
    msg: &ArcosMessage,
    validity_failures: &[String],
    risk_failures: &[String],
    artifacts: Vec<(String, String)>,
) -> Result<(), String> {
    let mut official_dir = PathBuf::from(&config.workspace_root);
    official_dir.push("official");
    official_dir.push("reports");
    fs::create_dir_all(&official_dir).map_err(|e| e.to_string())?;

    let status = if validity_failures.is_empty() && risk_failures.is_empty() {
        "accepted"
    } else {
        "rejected"
    };

    let output = serde_json::json!({
        "type": "OfficialRecommendation",
        "message_id": msg.header.message_id,
        "ticker": msg.body.ticker,
        "signal": msg.body.signal,
        "probability": msg.body.probability,
        "status": status,
        "execution_mode": config.execution_mode,
        "validity_failures": validity_failures,
        "risk_failures": risk_failures,
        "rationale": msg.body.rationale,
        "artifacts": artifacts,
    });

    let filename = format!("recommendation_{}_{}.json", msg.body.ticker, msg.header.message_id);
    let mut output_path = official_dir.clone();
    output_path.push(filename);
    fs::write(&output_path, serde_json::to_string_pretty(&output).unwrap()).map_err(|e| e.to_string())?;

    if msg.body.signal == "INFO" && msg.body.ticker == "MARKET_BRIEF" {
        let date = chrono::Utc::now().format("%Y-%m-%d");
        let briefing_path = official_dir.join(format!("daily_briefing_{}.md", date));
        let briefing = format!(
            "# ARCOS Daily Briefing ({})\n\n{}\n\nAudit Reference: {}\n",
            date,
            msg.body.rationale,
            msg.header.message_id
        );
        fs::write(&briefing_path, briefing).map_err(|e| e.to_string())?;
    }

    let manifest = serde_json::json!({
        "type": "AuditManifest",
        "message_id": msg.header.message_id,
        "artifacts": artifacts,
        "output_hash": compute_sha256(&output_path).ok(),
        "config": {
            "min_sample_size": config.min_sample_size,
            "min_win_rate": config.min_win_rate,
            "max_position_cap": config.max_position_cap,
            "max_gross_exposure": config.max_gross_exposure,
            "execution_mode": config.execution_mode,
        }
    });
    let mut manifest_dir = PathBuf::from(&config.workspace_root);
    manifest_dir.push("official");
    manifest_dir.push("manifests");
    fs::create_dir_all(&manifest_dir).map_err(|e| e.to_string())?;
    let manifest_path = manifest_dir.join(format!("manifest_{}.json", msg.header.message_id));
    fs::write(&manifest_path, serde_json::to_string_pretty(&manifest).unwrap()).map_err(|e| e.to_string())?;
    Ok(())
}

fn append_paper_trade(config: &Config, msg: &ArcosMessage) {
    if config.execution_mode != "paper" {
        return;
    }
    let ledger_path = PathBuf::from(&config.workspace_root).join("paper_ledger.json");
    let mut ledger: serde_json::Value = fs::read_to_string(&ledger_path)
        .ok()
        .and_then(|content| serde_json::from_str(&content).ok())
        .unwrap_or_else(|| serde_json::json!({ "type": "PaperLedger", "trades": [] }));

    if let Some(trades) = ledger.get_mut("trades").and_then(|v| v.as_array_mut()) {
        trades.push(serde_json::json!({
            "ticker": msg.body.ticker,
            "signal": msg.body.signal,
            "probability": msg.body.probability,
            "timestamp": msg.header.message_id,
        }));
    }

    if let Ok(content) = serde_json::to_string_pretty(&ledger) {
        let _ = fs::write(&ledger_path, content);
    }
}

// Separate function to run health check in a background task
async fn run_health_check() {
    let port = env::var("PORT").unwrap_or_else(|_| "8080".to_string()).parse::<u16>().unwrap();
    let health = warp::path::end().map(|| "OK");
    
    println!("   ❤️ [System] Health Check running on port {}", port);
    warp::serve(health).run(([0, 0, 0, 0], port)).await;
}

#[tokio::main]
async fn main() {
    println!("---------------------------------------");
    println!("   ARCOS Maestro: Risk Engine Online   ");
    println!("---------------------------------------");

    // Start Health Check logic in the background
    tokio::spawn(run_health_check());

    let config = load_config();
    if config.smtp_user.is_empty() || config.smtp_pass.is_empty() || config.alert_recipient.is_empty() {
        println!("   ⚠️ [Config] SMTP credentials or recipient not set; email alerts disabled.");
    }

    // Redis Connection
    let redis_url = env::var("REDIS_URL").unwrap_or_else(|_| "redis://localhost:6379".to_string());
    let mut client = match redis::Client::open(redis_url.clone()) {
        Ok(c) => {
             println!("   🔌 [System] Connected to Redis at {}", redis_url);
             c
        },
        Err(e) => {
            println!("   ❌ [System] Failed to connect to Redis: {}", e);
            return; 
        }
    };

    let mut con = match client.get_connection() {
        Ok(c) => c,
        Err(e) => {
            println!("   ❌ [System] Could not get Redis connection: {}", e);
            return;
        }
    };

    println!("   👂 [System] Listening for signals...");

    loop {
        // BLPOP blocks until an item is available. Timeout 0 = wait forever.
        // Returns tuple: (key, value)
        let result: redis::RedisResult<(String, String)> = con.blpop("arcos_signals", 0.0);

        match result {
            Ok((_key, json_str)) => {
                match serde_json::from_str::<ArcosMessage>(&json_str) {
                    Ok(message) => {
                        if let Err(err) = validate_message(&message) {
                            println!("   ❌ [Validation] {} | {}", err, json_str);
                            continue;
                        }

                        println!("\n🔔 NEW SIGNAL: {} ({})", message.body.ticker, message.body.signal);

                        let mut artifacts = Vec::new();
                        if let Some(path) = latest_artifact(&config.workspace_root, "raw") {
                            if let Ok(hash) = compute_sha256(&path) {
                                artifacts.push((path.display().to_string(), hash));
                            }
                        }
                        for category in ["features", "signals", "news", "calibration"] {
                            if let Some(path) = latest_artifact(&config.workspace_root, category) {
                                if let Ok(hash) = compute_sha256(&path) {
                                    artifacts.push((path.display().to_string(), hash));
                                }
                            }
                        }

                        let portfolio_path = PathBuf::from(&config.workspace_root).join("portfolio_state.json");
                        let portfolio_state: serde_json::Value = fs::read_to_string(&portfolio_path)
                            .ok()
                            .and_then(|content| serde_json::from_str(&content).ok())
                            .unwrap_or_else(|| serde_json::json!({ "positions": [], "exposure": { "gross": 0.0 } }));

                        let validity_failures = apply_validity_gate(&message, &config);
                        let risk_failures = apply_risk_engine(&config, portfolio_state);

                        if let Err(err) = write_official_output(&config, &message, &validity_failures, &risk_failures, artifacts) {
                            println!("   ❌ [Audit] Failed to write official output: {}", err);
                        } else if validity_failures.is_empty() && risk_failures.is_empty() {
                            append_paper_trade(&config, &message);
                        }

                        let sig = message.body.signal.as_str();
                        if (sig == "BUY_CANDIDATE" || sig == "INFO" || sig.starts_with("URGENT")) && message.body.probability > 0.60 {
                            if !config.smtp_user.is_empty() && !config.smtp_pass.is_empty() && !config.alert_recipient.is_empty() {
                                let mail_config = config.clone();
                                tokio::task::spawn_blocking(move || {
                                    send_email_alert(&message, &mail_config);
                                });
                            }
                        }
                    },
                    Err(e) => {
                         println!("   ❌ [Error] Parser failed: {:?} | Content: {}", e, json_str);
                    }
                }
            },
            Err(e) => {
                println!("   ⚠️ [Redis] Error during pop: {}. Reconnecting...", e);
                thread::sleep(Duration::from_secs(5));
                // Basic reconnect attempt
                if let Ok(new_con) = client.get_connection() {
                    con = new_con;
                }
            }
        }
    }
}
