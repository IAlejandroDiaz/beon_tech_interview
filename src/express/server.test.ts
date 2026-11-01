/**
 * Unit tests for the Express server.
 *
 * Uses Node's built-in test runner (`node:test`) + `node:assert`, and
 * `supertest` to drive the app in-process — no real port is opened because
 * `app` is exported and the listener is guarded behind `import.meta.main`.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import request from "supertest";
import { app } from "./server.ts";

describe("Express server", () => {
  describe("GET /health", () => {
    it("returns 200 with an ok status", async () => {
      const res = await request(app).get("/health");

      assert.equal(res.status, 200);
      assert.equal(res.body.status, "ok");
      assert.equal(res.body.service, "express");
      assert.ok(res.body.timestamp, "expected a timestamp");
    });
  });

  describe("POST /echo", () => {
    it("echoes a valid message back with its length", async () => {
      const res = await request(app)
        .post("/echo")
        .send({ message: "hello" });

      assert.equal(res.status, 200);
      assert.equal(res.body.received, "hello");
      assert.equal(res.body.length, 5);
      assert.ok(res.body.timestamp, "expected a timestamp");
    });

    it("rejects a missing message with 400", async () => {
      const res = await request(app).post("/echo").send({});

      assert.equal(res.status, 400);
      assert.ok(res.body.error, "expected an error message");
    });

    it("rejects an empty / whitespace message with 400", async () => {
      const res = await request(app)
        .post("/echo")
        .send({ message: "   " });

      assert.equal(res.status, 400);
      assert.ok(res.body.error, "expected an error message");
    });

    it("rejects a non-string message with 400", async () => {
      const res = await request(app)
        .post("/echo")
        .send({ message: 123 });

      assert.equal(res.status, 400);
      assert.ok(res.body.error, "expected an error message");
    });
  });
});
