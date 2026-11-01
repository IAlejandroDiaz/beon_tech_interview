/**
 * Unit tests for the GraphQL server.
 *
 * Uses Node's built-in test runner (`node:test`) + `node:assert`. Instead of
 * starting a server, it builds an executable schema from the exported
 * `typeDefs`/`resolvers` and runs operations directly with `graphql()` —
 * fastest possible, no network, no open port.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { graphql } from "graphql";
import { makeExecutableSchema } from "@graphql-tools/schema";
import { typeDefs, resolvers } from "./server.ts";

const schema = makeExecutableSchema({ typeDefs, resolvers });

// Small helper: run a GraphQL operation against the in-process schema.
const run = (source: string, variableValues?: Record<string, unknown>) =>
  graphql({ schema, source, variableValues });

describe("GraphQL server", () => {
  describe("query health", () => {
    it("returns an ok health payload", async () => {
      const result = await run(`{ health { status service timestamp } }`);

      assert.equal(result.errors, undefined);
      const health = (result.data as any).health;
      assert.equal(health.status, "ok");
      assert.equal(health.service, "graphql");
      assert.ok(health.timestamp, "expected a timestamp");
    });
  });

  describe("mutation echo", () => {
    it("echoes a valid message back with its length", async () => {
      const result = await run(
        `mutation Echo($message: String!) {
           echo(message: $message) { received length timestamp }
         }`,
        { message: "hello" },
      );

      assert.equal(result.errors, undefined);
      const echo = (result.data as any).echo;
      assert.equal(echo.received, "hello");
      assert.equal(echo.length, 5);
      assert.ok(echo.timestamp, "expected a timestamp");
    });

    it("trims surrounding whitespace before echoing", async () => {
      const result = await run(
        `mutation Echo($message: String!) {
           echo(message: $message) { received length }
         }`,
        { message: "  hi  " },
      );

      assert.equal(result.errors, undefined);
      const echo = (result.data as any).echo;
      assert.equal(echo.received, "hi");
      assert.equal(echo.length, 2);
    });

    it("rejects an empty / whitespace message with BAD_USER_INPUT", async () => {
      const result = await run(
        `mutation Echo($message: String!) {
           echo(message: $message) { received }
         }`,
        { message: "   " },
      );

      assert.ok(result.errors, "expected an errors array");
      assert.equal(result.errors?.[0]?.extensions?.code, "BAD_USER_INPUT");
    });

    it("rejects a missing required argument at the schema level", async () => {
      // No variable provided for a non-null arg: the engine rejects before the
      // resolver runs. This is schema-level validation, not our resolver guard.
      const result = await run(
        `mutation Echo($message: String!) {
           echo(message: $message) { received }
         }`,
      );

      assert.ok(result.errors, "expected a validation error");
    });
  });
});
