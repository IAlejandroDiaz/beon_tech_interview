/**
 * GraphQL server (Apollo Server, standalone).
 *
 * Minimal GraphQL backend mirroring the Express server: a health query (read)
 * and an echo mutation (write). Runs independently from the Express server
 * (separate directory, separate port) so either can be started on its own.
 *
 * Start: `npm run dev:graphql` (watch) or `npm run start:graphql`.
 */
import { ApolloServer } from "@apollo/server";
import { startStandaloneServer } from "@apollo/server/standalone";
import { GraphQLError } from "graphql";

// Configurable via env; defaults to 4000 so it can run alongside Express (3000).
const PORT = Number(process.env.PORT ?? 4000);

/**
 * Schema (SDL). Defines the data shapes and the two root operations.
 * The `/* GraphQL *\/` comment tag enables syntax highlighting/formatting
 * in editors that recognise the tagged template convention.
 *
 * - Query.health   — read: service liveness check.
 * - Mutation.echo  — write: GraphQL equivalent of Express POST /echo.
 *
 * Non-null markers (`!`) are schema-level validation: `echo(message: String!)`
 * means the engine rejects a missing/null argument before the resolver runs.
 */
export const typeDefs = /* GraphQL */ `
  type Health {
    status: String!
    service: String!
    timestamp: String!
  }

  type EchoPayload {
    received: String!
    length: Int!
    timestamp: String!
  }

  type Query {
    health: Health!
  }

  type Mutation {
    # GraphQL equivalent of the Express POST /echo — the write seed.
    echo(message: String!): EchoPayload!
  }
`;

/**
 * Resolvers. One function per schema field, grouped by the root type that
 * owns it. Each returns the data matching its declared return type.
 */
export const resolvers = {
  Query: {
    // Mirrors the Express /health payload.
    health: () => ({
      status: "ok",
      service: "graphql",
      timestamp: new Date().toISOString(),
    }),
  },
  Mutation: {
    // `_parent` is unused at the root; `args` carries the typed field arguments.
    echo: (_parent: unknown, args: { message: string }) => {
      const message = args.message?.trim() ?? "";

      // The schema guarantees a string is present, but not that it's non-empty.
      // Signal bad input the GraphQL way: throw a GraphQLError with a
      // machine-readable `code`. The HTTP response stays 200 and the error
      // surfaces in the response `errors` array (unlike REST's 400 status).
      if (message === "") {
        throw new GraphQLError("`message` must be a non-empty string.", {
          extensions: { code: "BAD_USER_INPUT" },
        });
      }

      return {
        received: message,
        length: message.length,
        timestamp: new Date().toISOString(),
      };
    },
  },
};

// Only start a listener when run directly (e.g. `npm run start:graphql`), not
// when imported by a test. Tests import `typeDefs`/`resolvers` and execute
// operations against the schema in-process — no network, no open port.
if (import.meta.main) {
  // Build the executable schema from type definitions + resolvers.
  const server = new ApolloServer({ typeDefs, resolvers });

  // `startStandaloneServer` spins up a self-contained HTTP server (no Express
  // wiring needed) and serves the Apollo Sandbox UI at the returned URL. It's
  // the quick-start path; swap to `expressMiddleware(server)` once you need
  // custom middleware (auth, logging, extra routes). It's async and resolves
  // only once listening — hence the await.
  const { url } = await startStandaloneServer(server, {
    listen: { port: PORT },
  });

  console.log(`[graphql] server ready at ${url}`);
  console.log(`[graphql] try query:    { health { status service timestamp } }`);
  console.log(`[graphql] try mutation: mutation { echo(message: "hi") { received length } }`);
}
