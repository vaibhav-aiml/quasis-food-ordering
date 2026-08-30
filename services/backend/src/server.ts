import cors from 'cors';
import dotenv from 'dotenv';
import express, { Express } from 'express';
import http from 'http';
import { WebSocket, WebSocketServer } from 'ws';
import { PipelineOrchestrator } from './agent/pipelineOrchestrator.js';
import { createRouter } from './api/routes.js';
import { SwiggySearchService } from './tools/swiggy/searchService.js';
import { PipelineEvent } from './tools/swiggy/types.js';

dotenv.config();

const app: Express = express();
const PORT = parseInt(process.env.PORT || '3001', 10);
const HOST = '0.0.0.0';

// Middleware
app.use(
  cors({
    origin: '*',
    methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'Authorization'],
  })
);
app.use(express.json({ limit: '25mb' }));
app.use(express.urlencoded({ extended: true, limit: '25mb' }));

// Initialize domain services
const searchService = new SwiggySearchService();
const orchestrator = new PipelineOrchestrator(searchService);

// Mount API routes
app.use(createRouter(orchestrator, searchService));

// HTTP Server
const server = http.createServer(app);

// WebSocket Server for dual transport (SSE + WebSocket)
const wss = new WebSocketServer({ server, path: '/ws' });

wss.on('connection', (ws: WebSocket, req) => {
  const url = new URL(req.url || '', `http://${req.headers.host}`);
  const sessionId = url.searchParams.get('sessionId');

  if (sessionId) {
    // Replay existing events
    const history = orchestrator.getSessionEvents(sessionId);
    for (const ev of history) {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(ev));
      }
    }

    // Subscribe to new events
    const unsubscribe = orchestrator.subscribe(sessionId, (event: PipelineEvent) => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(event));
      }
    });

    ws.on('close', () => {
      unsubscribe();
    });
  }

  ws.on('message', (message: string) => {
    try {
      const data = JSON.parse(message.toString());
      if (data.type === 'SUBSCRIBE' && data.sessionId) {
        const history = orchestrator.getSessionEvents(data.sessionId);
        for (const ev of history) {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify(ev));
          }
        }
        orchestrator.subscribe(data.sessionId, (event: PipelineEvent) => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify(event));
          }
        });
      }
    } catch {
      // Ignore malformed messages
    }
  });
});

server.listen(PORT, HOST, () => {
  console.log('====================================================');
  console.log(`🚀 Swiggy Food Ordering Pipeline Backend Running!`);
  console.log(`📡 Host Binding: http://${HOST}:${PORT}`);
  console.log(`🔌 Local URL:    http://localhost:${PORT}`);
  console.log(`⚡ SSE Endpoint: http://localhost:${PORT}/api/order/pipeline/:sessionId`);
  console.log(`🌐 WebSocket:    ws://localhost:${PORT}/ws?sessionId=:sessionId`);
  console.log('====================================================');
});

export { app, orchestrator, searchService, server };
