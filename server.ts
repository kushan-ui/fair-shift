import express from 'express';
import { createProxyMiddleware } from 'http-proxy-middleware';
import { spawn } from 'child_process';
import http from 'http';
import path from 'path';

const app = express();
const PORT = 3000;
const STREAMLIT_PORT = 8501;

// Initialize Streamlit background process
console.log('Starting FAIRSHIFT Streamlit application engine on port', STREAMLIT_PORT);
const streamlitProcess = spawn('python3', [
  '-m', 'streamlit', 'run', 'app.py',
  '--server.port', String(STREAMLIT_PORT),
  '--server.address', '127.0.0.1',
  '--server.enableCORS', 'false',
  '--server.enableXsrfProtection', 'false',
  '--browser.gatherUsageStats', 'false',
  '--server.headless', 'true'
], {
  stdio: 'inherit',
  env: { ...process.env, PYTHONUNBUFFERED: '1' }
});

process.on('exit', () => {
  streamlitProcess.kill();
});
process.on('SIGINT', () => {
  streamlitProcess.kill();
  process.exit();
});
process.on('SIGTERM', () => {
  streamlitProcess.kill();
  process.exit();
});

// Enable CORS and strip iframe restrictions
app.use((req, res, next) => {
  res.header('Access-Control-Allow-Origin', '*');
  res.header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS, HEAD');
  res.header('Access-Control-Allow-Headers', '*');
  if (req.method === 'OPTIONS') {
    return res.sendStatus(204);
  }
  next();
});

// Configure Streamlit proxy with WebSocket support and iframe security header stripping
const streamlitProxy = createProxyMiddleware({
  target: `http://127.0.0.1:${STREAMLIT_PORT}`,
  ws: true,
  changeOrigin: true,
  on: {
    proxyRes: (proxyRes) => {
      // Allow embedding in AI Studio preview iframe
      delete proxyRes.headers['x-frame-options'];
      delete proxyRes.headers['content-security-policy'];
      proxyRes.headers['access-control-allow-origin'] = '*';
      proxyRes.headers['access-control-allow-methods'] = 'GET, POST, PUT, DELETE, OPTIONS, HEAD';
      proxyRes.headers['access-control-allow-headers'] = '*';
    },
    error: (err, req, res) => {
      if (res && 'writeHead' in res && typeof res.writeHead === 'function') {
        res.writeHead(503, { 'Content-Type': 'text/html' });
        res.end(`
          <html>
            <head><meta http-equiv="refresh" content="2"></head>
            <body style="font-family:sans-serif; text-align:center; padding-top:100px; background:#f8fafc; color:#1e293b;">
              <h2>Initializing FAIRSHIFT Allocation Engine...</h2>
              <p>Starting Google OR-Tools and Streamlit components. Reloading in 2 seconds...</p>
            </body>
          </html>
        `);
      }
    }
  }
});

app.use(streamlitProxy);

const server = http.createServer(app);
server.on('upgrade', (req, socket, head) => {
  streamlitProxy.upgrade(req, socket as any, head);
});

server.listen(PORT, '0.0.0.0', () => {
  console.log(`FAIRSHIFT Gateway active on http://0.0.0.0:${PORT}`);
});
