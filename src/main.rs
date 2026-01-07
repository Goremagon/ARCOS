use serde::Deserialize;
use std::fs;
use std::thread;
use std::time::Duration;
use lettre::transport::smtp::authentication::Credentials;
use lettre::{Message, SmtpTransport, Transport};

// --- CONFIGURATION ---
const SMTP_USER: &str = "whogormagon@gmail.com"; 
const SMTP_PASS: &str = "sxfb ixti odqf arko"; 
const ALERT_RECIPIENT: &str = "Goremagon@proton.me";

#[derive(Debug, Deserialize)]
#[serde(rename_all = "PascalCase")]
struct ArcosMessage {
    header: Header,
    body: Body,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "PascalCase")]
struct Header {
    #[serde(rename = "MessageID")]
    message_id: String,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "PascalCase")]
struct Body {
    ticker: String,
    signal: String,
    probability: f64,
    uncertainty: f64,
    sample_size: u32, // Simplified type to avoid parsing errors
    rationale: String,
    signature: String,
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

fn main() {
    println!("---------------------------------------");
    println!("   ARCOS Maestro: Risk Engine Online   ");
    println!("---------------------------------------");

    let mut last_id = String::new();

    loop {
        if let Ok(entries) = fs::read_dir("workspace") {
            for entry in entries {
                if let Ok(entry) = entry {
                    let path = entry.path();
                    let path_str = path.to_string_lossy();
                    
                    if path_str.ends_with(".xml") && path_str.contains("message_") {
                        if let Ok(xml_content) = fs::read_to_string(&path) {
                            
                            match quick_xml::de::from_str::<ArcosMessage>(&xml_content) {
                                Ok(message) => {
                                    if message.header.message_id != last_id {
                                        println!("\n🔔 NEW SIGNAL: {} ({})", message.body.ticker, message.body.signal);
                                        
                                        // LOGIC: Send if Buy Candidate OR Urgent OR Info Briefing
                                        let sig = message.body.signal.as_str();
                                        if (sig == "BUY_CANDIDATE" || sig == "INFO" || sig.starts_with("URGENT")) && message.body.probability > 0.60 {
                                            send_email_alert(&message);
                                        }

                                        last_id = message.header.message_id.clone();
                                    }
                                },
                                Err(e) => {
                                    println!("   ❌ [Error] Parser failed on {}: {:?}", path_str, e);
                                }
                            }
                        }
                    }
                }
            }
        }
        thread::sleep(Duration::from_secs(2));
    }
}