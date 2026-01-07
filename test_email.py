import os
import datetime
import time

# Create a fake high-conviction signal
# Signal: BUY_CANDIDATE
# Probability: 0.99 (Guaranteed to trigger the >0.60 check)

message_id = f"TEST-{int(time.time())}"
xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<ArcosMessage xmlns="http://arcos.ai/core">
    <Header>
        <MessageID>{message_id}</MessageID>
        <Sender>MANUAL_TRIGGER</Sender>
    </Header>
    <Body>
        <Ticker>TEST-ALERT</Ticker>
        <Signal>BUY_CANDIDATE</Signal>
        <Probability>0.99</Probability>
        <Uncertainty>0.01</Uncertainty>
        <SampleSize>999</SampleSize>
        <Rationale>This is a forced test to verify your email settings are correct.</Rationale>
        <Signature>Administrator</Signature>
    </Body>
</ArcosMessage>
"""

# Save it to the workspace where Maestro is watching
file_path = f"workspace/message_{message_id}.xml"
with open(file_path, "w", encoding="utf-8") as f:
    f.write(xml_content)

print(f"✅ Test Signal Injected: {file_path}")
print("👉 Check your Docker logs now. You should see '[Alert] Preparing email...'")