/**
 * Trinity MCP Server - Entry Point
 *
 * Starts the MCP server with Streamable HTTP transport for remote access.
 */

import { createServer } from "./server.js";

async function main() {
  console.log("Starting Trinity MCP Server...\n");

  try {
    const { server, port, requireApiKey } = await createServer();

    // Determine transport type from environment
    const transportType = process.env.MCP_TRANSPORT || "httpStream";

    if (transportType === "stdio") {
      // STDIO transport for direct integration (e.g., local Claude Code)
      console.log("Starting in STDIO mode...");
      server.start({
        transportType: "stdio",
      });
    } else {
      // HTTP Streaming transport for remote access
      // Bind to 0.0.0.0 to allow connections from outside the container
      const host = process.env.MCP_HOST || "0.0.0.0";
      console.log(`Starting HTTP stream server on ${host}:${port}...`);
      server.start({
        transportType: "httpStream",
        httpStream: {
          port,
          host,
        },
      });
      console.log(`\nTrinity MCP Server running at http://localhost:${port}/mcp`);
      console.log(`Authentication: ${requireApiKey ? "API KEY REQUIRED" : "DISABLED (dev mode)"}`);
      console.log(`\nTo test with MCP Inspector:`);
      console.log(`  npx @modelcontextprotocol/inspector http://localhost:${port}/mcp`);
      console.log(`\nTo connect from Claude Code, add to .mcp.json:`);

      if (requireApiKey) {
        console.log(
          JSON.stringify(
            {
              mcpServers: {
                trinity: {
                  url: `http://localhost:${port}/mcp`,
                  headers: {
                    Authorization: "Bearer YOUR_API_KEY",
                  },
                },
              },
            },
            null,
            2
          )
        );
        console.log(`\nGet your API key from the Trinity web UI: http://localhost:3000/api-keys`);
      } else {
        console.log(
          JSON.stringify(
            {
              mcpServers: {
                trinity: {
                  url: `http://localhost:${port}/mcp`,
                },
              },
            },
            null,
            2
          )
        );
        console.log(`\nTo enable API key authentication, set MCP_REQUIRE_API_KEY=true`);
      }
    }
  } catch (error) {
    console.error("Failed to start server:", error);
    process.exit(1);
  }
}

main();
