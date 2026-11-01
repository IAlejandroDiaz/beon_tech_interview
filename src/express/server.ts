/**
 * Express HTTP server.
 *
 * Minimal REST backend for the interview boilerplate. Exposes a health check
 * (GET) and a simple echo endpoint (POST) that acts as the seed for the live
 * AI exercise. Runs independently from the GraphQL server (separate directory,
 * separate port) so either can be started on its own.
 *
 * Start: `npm run dev:express` (watch) or `npm run start:express`.
 */
import express, { type Request, type Response } from "express";

// Exported so tests can import the configured app without starting a listener.
export const app = express();

// Port is configurable via env (handy for running both servers at once);
// falls back to 3000. `??` keeps an explicit `PORT=0` or empty handling clean.
const PORT = Number(process.env.PORT ?? 3000);

// Parse incoming JSON bodies into `req.body`. Must be registered before any
// route that reads the body — middleware order matters in Express.
app.use(express.json());

/**
 * GET /health — liveness/readiness probe.
 * Returns a fixed 200 payload. Used by the Bruno collection and as the
 * canonical "is the service up?" check.
 */
app.get("/health", (_req: Request, res: Response) => {
  res.status(200).json({
    status: "ok",
    service: "express",
    timestamp: new Date().toISOString(),
  });
});

/**
 * POST /echo — the write seed for the interview exercise.
 *
 * Accepts `{ "message": string }`, validates it, and echoes it back. This is
 * the hook to evolve into a real AI endpoint live: e.g. rename `message` to
 * `prompt`, call the LLM, and return the completion instead of the echo.
 *
 * Validation returns 400 with a descriptive error — the REST convention of
 * signalling bad input through the HTTP status code (contrast with the
 * GraphQL server, which surfaces errors in the `errors` array instead).
 */
app.post("/echo", (req: Request, res: Response) => {
  const { message } = req.body ?? {};

  if (typeof message !== "string" || message.trim() === "") {
    return res.status(400).json({
      error: "Body must include a non-empty string field `message`.",
    });
  }

  res.status(200).json({
    received: message,
    length: message.length,
    timestamp: new Date().toISOString(),
  });
});

// Only bind a port when this file is run directly (e.g. `npm run start:express`),
// not when it's imported by a test. `import.meta.main` is true for the entry
// module. The callback fires once the server is actively listening.
if (import.meta.main) {
  app.listen(PORT, () => {
    console.log(`[express] server listening on http://localhost:${PORT}`);
    console.log(`[express] health check: http://localhost:${PORT}/health`);
    console.log(`[express] POST echo:     http://localhost:${PORT}/echo`);
  });
}
