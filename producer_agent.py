import os
import datetime
import random

# --- Configuration ---
OUTPUT_FILE = "examples/message.xml"

# --- The "Work" Generator ---
def generate_content(role):
    if role == "PRODUCER":
        return random.choice(["Drafting code.", "Writing article.", "Designing UI."])
    elif role == "VALIDATOR":
        return random.choice(["Checking compliance.", "Verifying security keys.", "Auditing logs."])
    elif role == "SPECULUS":
        return random.choice(["Analyzing market trends.", "Predicting user behavior.", "Scanning for patterns."])
    return "Unknown task"

# --- XML Generator ---
def create_xml_message():
    # 1. Randomly decide WHO is sending the message
    agent_role = random.choice(["PRODUCER", "VALIDATOR", "SPECULUS"])
    
    # 2. Get dynamic data
    message_id = f"MSG-{random.randint(1000, 9999)}"
    timestamp = datetime.datetime.now().isoformat()
    content = generate_content(agent_role)
    
    # 3. Construct the XML
    xml_data = f"""<?xml version="1.0" encoding="UTF-8"?>
<ArcosMessage xmlns="http://arcos.ai/core">
    <Header>
        <MessageID>{message_id}</MessageID>
        <Sender>{agent_role}</Sender>
        <Timestamp>{timestamp}</Timestamp>
    </Header>
    <Body>
        <Content>{content}</Content>
        <Signature>Signed_By_{agent_role}_Bot</Signature>
    </Body>
</ArcosMessage>
"""
    
    # 4. Save to file
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(xml_data)
        
    print(f"🤖 [Simulated {agent_role}] Task: '{content}'")
    print(f"📄 Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    create_xml_message()