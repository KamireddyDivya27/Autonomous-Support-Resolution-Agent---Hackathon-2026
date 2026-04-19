import os
os.environ["OPENAI_API_KEY"] = os.environ.get("OPENROUTER_API_KEY", "dummy")

from flask import Flask, render_template_string, request, jsonify
import asyncio, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from src.agents.support_agent import SupportAgent

app = Flask(__name__)
agent = SupportAgent()

HTML = """<!DOCTYPE html>
<html>
<head>
    <title>Autonomous Support Agent</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: Segoe UI, sans-serif; background: #0f172a; color: #e2e8f0; padding: 30px; }
        h1 { text-align: center; color: #38bdf8; margin-bottom: 8px; font-size: 2rem; }
        .subtitle { text-align: center; color: #94a3b8; margin-bottom: 30px; }
        .container { max-width: 900px; margin: 0 auto; }
        .card { background: #1e293b; border-radius: 12px; padding: 24px; margin-bottom: 20px; border: 1px solid #334155; }
        label { display: block; margin-bottom: 6px; color: #94a3b8; font-size: 0.85rem; text-transform: uppercase; }
        input, textarea { width: 100%; padding: 10px 14px; background: #0f172a; border: 1px solid #334155; border-radius: 8px; color: #e2e8f0; font-size: 1rem; margin-bottom: 16px; }
        textarea { height: 100px; resize: vertical; }
        button { width: 100%; padding: 14px; background: #0ea5e9; border: none; border-radius: 8px; color: white; font-size: 1rem; font-weight: bold; cursor: pointer; }
        button:hover { background: #0284c7; }
        button:disabled { background: #334155; cursor: not-allowed; }
        .result { display: none; }
        .badge { display: inline-block; padding: 4px 14px; border-radius: 20px; font-weight: bold; }
        .RESOLVED { background: #064e3b; color: #34d399; }
        .ESCALATED { background: #451a03; color: #fb923c; }
        .tool-item { display: flex; align-items: center; gap: 10px; padding: 10px; background: #0f172a; border-radius: 8px; margin-bottom: 8px; }
        .tool-name { font-weight: bold; color: #38bdf8; min-width: 220px; }
        .tool-time { color: #64748b; font-size: 0.85rem; margin-left: auto; }
        .success { color: #34d399; }
        .failure { color: #f87171; }
        .section-title { color: #94a3b8; font-size: 0.8rem; text-transform: uppercase; margin: 16px 0 10px; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
        .stat { background: #0f172a; border-radius: 8px; padding: 12px; }
        .stat-label { color: #64748b; font-size: 0.8rem; }
        .stat-value { font-size: 1.1rem; font-weight: bold; margin-top: 4px; }
        .spinner { text-align: center; padding: 40px; display: none; color: #94a3b8; }
        .reply-box { background: #0f172a; border-radius: 8px; padding: 14px; border-left: 3px solid #38bdf8; color: #cbd5e1; }
        .presets { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 16px; }
        .preset-btn { width: auto; padding: 6px 12px; font-size: 0.8rem; background: #334155; }
    </style>
</head>
<body>
<div class="container">
    <h1>Autonomous Support Agent</h1>
    <p class="subtitle">AI-powered ticket resolution with multi-step reasoning</p>
    <div class="card">
        <div class="section-title">Quick Test Tickets</div>
        <div class="presets">
            <button class="preset-btn" onclick="loadPreset('refund')">Refund Request</button>
            <button class="preset-btn" onclick="loadPreset('order')">Order Status</button>
            <button class="preset-btn" onclick="loadPreset('old')">Late Return</button>
        </div>
        <label>Customer Email</label>
        <input type="email" id="email" value="customer1@example.com" />
        <label>Subject</label>
        <input type="text" id="subject" value="Request refund for order ORD-001" />
        <label>Message</label>
        <textarea id="message">Hi, I would like to request a refund for my laptop order ORD-001. I received it but it is not what I expected. Can you process a refund?</textarea>
        <button id="submitBtn" onclick="submitTicket()">Submit Ticket</button>
    </div>
    <div class="spinner" id="spinner"><p>Agent is processing your ticket...</p></div>
    <div class="card result" id="result">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
            <h2>Result</h2>
            <span class="badge" id="statusBadge"></span>
        </div>
        <div class="section-title">Classification</div>
        <div class="grid">
            <div class="stat"><div class="stat-label">Category</div><div class="stat-value" id="category"></div></div>
            <div class="stat"><div class="stat-label">Urgency</div><div class="stat-value" id="urgency"></div></div>
            <div class="stat"><div class="stat-label">Confidence</div><div class="stat-value" id="confidence"></div></div>
            <div class="stat"><div class="stat-label">Reasoning</div><div class="stat-value" style="font-size:0.9rem;" id="reasoning"></div></div>
        </div>
        <div class="section-title">Tool Chain Execution</div>
        <ul id="toolList" style="list-style:none;"></ul>
        <div class="section-title">Agent Response</div>
        <div class="reply-box" id="replyBox"></div>
    </div>
</div>
<script>
const presets = {
    refund: { email: "customer1@example.com", subject: "Request refund for order ORD-001", message: "Hi, I would like to request a refund for my laptop order ORD-001. I received it but it is not what I expected. Can you process a refund?" },
    order:  { email: "customer2@example.com", subject: "Where is my order?", message: "I ordered a mouse order ORD-002 five days ago and have not received tracking information. When will it arrive?" },
    old:    { email: "customer3@example.com", subject: "Can I still return my keyboard?", message: "I bought a keyboard ORD-003 about 45 days ago. Is it too late to return it? It stopped working." }
};
function loadPreset(type) {
    const p = presets[type];
    document.getElementById('email').value = p.email;
    document.getElementById('subject').value = p.subject;
    document.getElementById('message').value = p.message;
}
async function submitTicket() {
    const btn = document.getElementById('submitBtn');
    btn.disabled = true;
    document.getElementById('spinner').style.display = 'block';
    document.getElementById('result').style.display = 'none';
    const ticket = {
        ticket_id: "TKT-" + Math.floor(Math.random() * 9000 + 1000),
        customer_email: document.getElementById('email').value,
        subject: document.getElementById('subject').value,
        message: document.getElementById('message').value,
        created_at: new Date().toISOString()
    };
    try {
        const res = await fetch('/process', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(ticket) });
        const data = await res.json();
        displayResult(data);
    } catch(e) { alert('Error: ' + e.message); }
    btn.disabled = false;
    document.getElementById('spinner').style.display = 'none';
}
function displayResult(data) {
    const resultDiv = document.getElementById('result');
    resultDiv.style.display = 'block';
    const status = data.is_resolved ? 'RESOLVED' : 'ESCALATED';
    const badge = document.getElementById('statusBadge');
    badge.textContent = data.is_resolved ? 'RESOLVED' : 'ESCALATED';
    badge.className = 'badge ' + status;
    const cls = data.classification || {};
    document.getElementById('category').textContent = cls.category || 'N/A';
    document.getElementById('urgency').textContent = cls.urgency || 'N/A';
    document.getElementById('confidence').textContent = Math.round((cls.confidence||0)*100) + '%';
    document.getElementById('reasoning').textContent = cls.reasoning || 'N/A';
    const toolList = document.getElementById('toolList');
    toolList.innerHTML = '';
    (data.tool_calls || []).forEach(tool => {
        const li = document.createElement('li');
        li.className = 'tool-item';
        li.innerHTML = `<span class="${tool.success?'success':'failure'}">${tool.success ? 'OK' : 'FAIL'}</span><span class="tool-name">${tool.tool_name}</span><span class="tool-time">${tool.duration_ms}ms</span>`;
        toolList.appendChild(li);
    });
    document.getElementById('replyBox').textContent = data.customer_message || data.escalation_summary || 'No message.';
    resultDiv.scrollIntoView({behavior:'smooth'});
}
</script>
</body>
</html>"""

@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/process', methods=['POST'])
def process():
    ticket = request.json
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(agent.process_ticket(ticket))
        return jsonify({
            "is_resolved": result["is_resolved"],
            "requires_escalation": result["requires_escalation"],
            "classification": result["classification"],
            "tool_calls": result["tool_calls"],
            "customer_message": result["customer_message"],
            "escalation_summary": result["escalation_summary"]
        })
    finally:
        loop.close()

if __name__ == '__main__':
    print("\n Starting Support Agent Web UI...")
    print("Open your browser: http://localhost:5000\n")
    app.run(debug=False, port=5000)
