use serde::Deserialize;
use std::env;
use std::thread;
use std::time::Duration;
use lettre::transport::smtp::authentication::Credentials;
use lettre::{Message, SmtpTransport, Transport};
use redis::Commands;
use warp::Filter;

// --- CONFIGURATION ---
const SMTP_USER: &str = "whogormagon@gmail.com"; 
const SMTP_PASS: &str = "sxfb ixti odqf arko"; 
const ALERT_RECIPIENT: &str = "Goremagon@proton.me";

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
    uncertainty: f64,
    sample_size: u32,
    rationale: String,
    signature: String,
    #[serde(default)]
    tags: Vec<String>,
}

fn send_email_alert(msg: &ArcosMessage) {
    println!("   📧 [Alert] Sending email for {}...", msg.body.ticker);
    
    let subject_line = if msg.body.signal == "INFO" {
        format!("🏛️ ARCOS Briefing: Market Summary")
    } else if msg.body.signal.contains("URGENT") {
        format!("🚨 URGENT: {} Moving Fast!", msg.body.ticker)
    } else {
        format!("🚀 ARCOS Signal: {} ({:.0}%)", msg.body.ticker, msg.body.probability * 100.0)
    };

    let email = Message::builder()
        .from(SMTP_USER.parse().unwrap())
        .to(ALERT_RECIPIENT.parse().unwrap())
        .subject(subject_line)
        .body(format!("Ticker: {}\nSignal: {}\nConfidence: {:.2}%\n\nREPORT:\n{}", 
            msg.body.ticker, msg.body.signal, msg.body.probability * 100.0, msg.body.rationale))
        .unwrap();

    let creds = Credentials::new(SMTP_USER.to_string(), SMTP_PASS.to_string());
    let mailer = SmtpTransport::relay("smtp.gmail.com").unwrap().credentials(creds).build();

    match mailer.send(&email) {
        Ok(_) => println!("   ✅ [Alert] Email Sent!"),
        Err(e) => println!("   ❌ [Alert] Error: {:?}", e),
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
                        println!("\n🔔 NEW SIGNAL: {} ({})", message.body.ticker, message.body.signal);
                        
                        let sig = message.body.signal.as_str();
                        if (sig == "BUY_CANDIDATE" || sig == "INFO" || sig.starts_with("URGENT")) && message.body.probability > 0.60 {
                            // Run email in blocking task to avoid dropping async runtime
                            tokio::task::spawn_blocking(move || {
                                send_email_alert(&message);
                            });
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