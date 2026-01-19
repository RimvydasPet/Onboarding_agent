from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from backend.config import settings
from backend.database.connection import init_db
from backend.api.demo import router as demo_router

app = FastAPI(
    title=settings.APP_NAME,
    description="Onboarding Agent with Memory Systems and Agentic RAG",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()

app.include_router(demo_router)


@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Onboarding Agent - Demo</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
            }
            .header {
                text-align: center;
                color: white;
                margin-bottom: 40px;
            }
            .header h1 {
                font-size: 3em;
                margin-bottom: 10px;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            }
            .header p {
                font-size: 1.2em;
                opacity: 0.9;
            }
            .grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
                gap: 20px;
                margin-bottom: 20px;
            }
            .card {
                background: white;
                border-radius: 12px;
                padding: 25px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                transition: transform 0.3s ease;
            }
            .card:hover {
                transform: translateY(-5px);
            }
            .card h2 {
                color: #667eea;
                margin-bottom: 15px;
                font-size: 1.5em;
            }
            .card p {
                color: #666;
                line-height: 1.6;
                margin-bottom: 15px;
            }
            .badge {
                display: inline-block;
                padding: 5px 12px;
                background: #667eea;
                color: white;
                border-radius: 20px;
                font-size: 0.85em;
                margin: 5px 5px 5px 0;
            }
            .badge.success { background: #48bb78; }
            .badge.warning { background: #ed8936; }
            .badge.info { background: #4299e1; }
            .btn {
                display: inline-block;
                padding: 10px 20px;
                background: #667eea;
                color: white;
                text-decoration: none;
                border-radius: 6px;
                border: none;
                cursor: pointer;
                font-size: 1em;
                transition: background 0.3s ease;
            }
            .btn:hover {
                background: #5568d3;
            }
            .status {
                display: flex;
                align-items: center;
                gap: 10px;
                margin: 10px 0;
            }
            .status-dot {
                width: 12px;
                height: 12px;
                border-radius: 50%;
                background: #48bb78;
                animation: pulse 2s infinite;
            }
            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.5; }
            }
            .feature-list {
                list-style: none;
                padding: 0;
            }
            .feature-list li {
                padding: 8px 0;
                border-bottom: 1px solid #eee;
                color: #555;
            }
            .feature-list li:last-child {
                border-bottom: none;
            }
            .feature-list li:before {
                content: "✓ ";
                color: #48bb78;
                font-weight: bold;
                margin-right: 8px;
            }
            .test-section {
                background: #f7fafc;
                padding: 20px;
                border-radius: 8px;
                margin-top: 15px;
            }
            .test-result {
                background: white;
                padding: 15px;
                border-radius: 6px;
                margin-top: 10px;
                border-left: 4px solid #667eea;
                font-family: monospace;
                font-size: 0.9em;
                white-space: pre-wrap;
                max-height: 300px;
                overflow-y: auto;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🤖 Onboarding Agent</h1>
                <p>AI-Powered Onboarding with Memory Systems & Agentic RAG</p>
                <div class="status">
                    <div class="status-dot"></div>
                    <span style="color: white;">System Operational</span>
                </div>
            </div>

            <div class="grid">
                <div class="card">
                    <h2>📊 System Status</h2>
                    <p>Core components are initialized and running</p>
                    <span class="badge success">Database: Connected</span>
                    <span class="badge success">Redis: Ready</span>
                    <span class="badge success">Memory: Active</span>
                    <div class="test-section">
                        <button class="btn" onclick="checkHealth()">Check Health</button>
                        <div id="health-result" class="test-result" style="display:none;"></div>
                    </div>
                </div>

                <div class="card">
                    <h2>🧠 Memory Systems</h2>
                    <p>Dual-layer memory architecture for context retention</p>
                    <ul class="feature-list">
                        <li>Short-term: Redis-based session storage</li>
                        <li>Long-term: SQL persistent memories</li>
                        <li>Importance scoring & access tracking</li>
                        <li>Context-aware retrieval</li>
                    </ul>
                    <div class="test-section">
                        <button class="btn" onclick="testShortTermMemory()">Test Short-term</button>
                        <button class="btn" onclick="testLongTermMemory()">Test Long-term</button>
                        <div id="memory-result" class="test-result" style="display:none;"></div>
                    </div>
                </div>

                <div class="card">
                    <h2>🗄️ Database Schema</h2>
                    <p>6 tables managing users, conversations, and memories</p>
                    <ul class="feature-list">
                        <li>users - Authentication & profiles</li>
                        <li>onboarding_profiles - Progress tracking</li>
                        <li>conversations - Session management</li>
                        <li>messages - Chat history</li>
                        <li>long_term_memories - Persistent data</li>
                        <li>documents - Knowledge base</li>
                    </ul>
                    <div class="test-section">
                        <button class="btn" onclick="getDatabaseStats()">View Stats</button>
                        <div id="db-result" class="test-result" style="display:none;"></div>
                    </div>
                </div>

                <div class="card">
                    <h2>🎯 Onboarding Stages</h2>
                    <p>Structured user journey through onboarding</p>
                    <span class="badge info">Welcome</span>
                    <span class="badge info">Profile Setup</span>
                    <span class="badge info">Learning Preferences</span>
                    <span class="badge info">First Steps</span>
                    <span class="badge success">Completed</span>
                    <div class="test-section">
                        <button class="btn" onclick="getStages()">View Details</button>
                        <div id="stages-result" class="test-result" style="display:none;"></div>
                    </div>
                </div>

                <div class="card">
                    <h2>📦 Data Models</h2>
                    <p>Type-safe schemas with Pydantic validation</p>
                    <ul class="feature-list">
                        <li>User & Authentication models</li>
                        <li>Chat & Message models</li>
                        <li>Agent State management</li>
                        <li>Onboarding profiles</li>
                    </ul>
                    <div class="test-section">
                        <button class="btn" onclick="getModelsInfo()">View Models</button>
                        <div id="models-result" class="test-result" style="display:none;"></div>
                    </div>
                </div>

                <div class="card">
                    <h2>🚀 Next Steps</h2>
                    <p>Upcoming features in development</p>
                    <span class="badge warning">Agentic RAG System</span>
                    <span class="badge warning">LangGraph Agent</span>
                    <span class="badge warning">JWT Authentication</span>
                    <span class="badge warning">React Frontend</span>
                    <div style="margin-top: 15px;">
                        <a href="/docs" class="btn">API Documentation</a>
                    </div>
                </div>
            </div>
        </div>

        <script>
            async function checkHealth() {
                const result = document.getElementById('health-result');
                result.style.display = 'block';
                result.textContent = 'Loading...';
                try {
                    const response = await fetch('/demo/health');
                    const data = await response.json();
                    result.textContent = JSON.stringify(data, null, 2);
                } catch (error) {
                    result.textContent = 'Error: ' + error.message;
                }
            }

            async function testShortTermMemory() {
                const result = document.getElementById('memory-result');
                result.style.display = 'block';
                result.textContent = 'Testing short-term memory...';
                try {
                    const response = await fetch('/demo/memory/short-term/test?message=Hello from UI!', {
                        method: 'POST'
                    });
                    const data = await response.json();
                    result.textContent = JSON.stringify(data, null, 2);
                } catch (error) {
                    result.textContent = 'Error: ' + error.message;
                }
            }

            async function testLongTermMemory() {
                const result = document.getElementById('memory-result');
                result.style.display = 'block';
                result.textContent = 'Testing long-term memory...';
                try {
                    const response = await fetch('/demo/memory/long-term/test', {
                        method: 'POST'
                    });
                    const data = await response.json();
                    result.textContent = JSON.stringify(data, null, 2);
                } catch (error) {
                    result.textContent = 'Error: ' + error.message;
                }
            }

            async function getDatabaseStats() {
                const result = document.getElementById('db-result');
                result.style.display = 'block';
                result.textContent = 'Loading database stats...';
                try {
                    const response = await fetch('/demo/database/stats');
                    const data = await response.json();
                    result.textContent = JSON.stringify(data, null, 2);
                } catch (error) {
                    result.textContent = 'Error: ' + error.message;
                }
            }

            async function getStages() {
                const result = document.getElementById('stages-result');
                result.style.display = 'block';
                result.textContent = 'Loading onboarding stages...';
                try {
                    const response = await fetch('/demo/onboarding/stages');
                    const data = await response.json();
                    result.textContent = JSON.stringify(data, null, 2);
                } catch (error) {
                    result.textContent = 'Error: ' + error.message;
                }
            }

            async function getModelsInfo() {
                const result = document.getElementById('models-result');
                result.style.display = 'block';
                result.textContent = 'Loading models info...';
                try {
                    const response = await fetch('/demo/models/info');
                    const data = await response.json();
                    result.textContent = JSON.stringify(data, null, 2);
                } catch (error) {
                    result.textContent = 'Error: ' + error.message;
                }
            }
        </script>
    </body>
    </html>
    """


@app.get("/api/info")
async def api_info():
    return {
        "name": settings.APP_NAME,
        "version": "1.0.0",
        "status": "operational",
        "features": {
            "memory_systems": "implemented",
            "database": "initialized",
            "authentication": "pending",
            "rag_system": "pending",
            "langgraph_agent": "pending"
        }
    }
