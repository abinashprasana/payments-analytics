import { Arrow } from "@/components/architecture-diagram";

/** The only path a question can take: client, MCP tools, the query registry,
 *  the in-memory snapshot. Raw SQL stops at the registry. */
export function McpFlow() {
  return (
    <figure className="mcp-flow">
      <div className="mcp-flow__map" role="img" aria-label="Request path from Claude through the MCP server and query registry to the DuckDB snapshot; raw SQL is refused at the registry">
        <div className="mcp-flow__node">
          <span className="mcp-flow__step">01</span>
          <strong>Claude</strong>
          <span>Asks in plain English</span>
        </div>
        <Arrow />
        <div className="mcp-flow__node">
          <span className="mcp-flow__step">02</span>
          <strong>MCP server</strong>
          <span>3 read-only tools</span>
        </div>
        <Arrow pulse />
        <div className="mcp-flow__node mcp-flow__node--gate">
          <span className="mcp-flow__step">03</span>
          <strong>Query registry</strong>
          <span><code>AnalyticsEngine.query</code></span>
        </div>
        <Arrow />
        <div className="mcp-flow__node">
          <span className="mcp-flow__step">04</span>
          <strong>DuckDB snapshot</strong>
          <span>In memory, rebuilt each start</span>
        </div>

        <div className="mcp-flow__aside mcp-flow__aside--audit">
          <span aria-hidden="true">↳</span> Every call, allowed or refused, writes one audit line
        </div>
        <div className="mcp-flow__aside mcp-flow__aside--refused">
          <span aria-hidden="true">✕</span> Refused here: raw SQL, unknown query IDs, extra arguments
        </div>
      </div>
      <figcaption>
        The server has no query logic of its own. It reaches the data only through the registry the workbench already uses, so Claude can only run queries that already exist.
      </figcaption>
    </figure>
  );
}
