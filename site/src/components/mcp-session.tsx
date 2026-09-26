import type { AskEvidence } from "@/lib/project-data";

function JsonValue({ value, emphasis = false }: { value: unknown; emphasis?: boolean }) {
  if (value === null) return <span className="mcp-json__literal">null</span>;
  if (typeof value === "number") return <span className="mcp-json__literal">{value}</span>;
  if (Array.isArray(value)) {
    return (
      <>
        [{value.map((item, index) => (
          <span key={String(item)}>
            {index ? ", " : null}
            <JsonValue value={item} />
          </span>
        ))}]
      </>
    );
  }
  return (
    <span className={emphasis ? "mcp-json__string mcp-json__string--flag" : "mcp-json__string"}>
      &quot;{String(value)}&quot;
    </span>
  );
}

/** A typographic call log of one real trace_payment call: question, call,
 *  returned fields, answer. Steps reveal in sequence; static without motion. */
export function McpSession({ ask }: { ask: AskEvidence }) {
  const entries = Object.entries(ask.result);
  return (
    <figure className="mcp-session" aria-labelledby="mcp-session-caption">
      <ol className="mcp-session__log">
        <li className="mcp-step" style={{ "--i": 0 } as React.CSSProperties}>
          <span className="mcp-step__label">Question</span>
          <p className="mcp-step__question">{ask.question}</p>
        </li>
        <li className="mcp-step" style={{ "--i": 1 } as React.CSSProperties}>
          <span className="mcp-step__label">Tool call</span>
          <div className="mcp-step__call">
            <code>
              {ask.call.tool}({"{"}
              <span className="mcp-json__key">&quot;payment_id&quot;</span>: <span className="mcp-json__literal">{ask.call.arguments.payment_id}</span>
              {"}"})
            </code>
            <span className="mcp-status" aria-hidden="true">
              <span className="mcp-status__running"><i />running</span>
              <span className="mcp-status__done">returned 1 row</span>
            </span>
            <span className="visually-hidden">Returned 1 row.</span>
          </div>
        </li>
        <li className="mcp-step" style={{ "--i": 2 } as React.CSSProperties}>
          <span className="mcp-step__label">Result excerpt</span>
          <pre className="mcp-json" tabIndex={0} aria-label="trace_payment result excerpt">
            <code>
              {"{\n"}
              {entries.map(([key, value], index) => (
                <span key={key}>
                  {"  "}<span className="mcp-json__key">&quot;{key}&quot;</span>: <JsonValue value={value} emphasis={key === "primary_reason"} />
                  {index < entries.length - 1 ? ",\n" : "\n"}
                </span>
              ))}
              {"}"}
            </code>
          </pre>
        </li>
        <li className="mcp-step" style={{ "--i": 3 } as React.CSSProperties}>
          <span className="mcp-step__label">Answer</span>
          <p className="mcp-step__answer">{ask.answer}</p>
        </li>
      </ol>
      <figcaption id="mcp-session-caption">
        One <code>trace_payment</code> call against this snapshot, with the answer written from the fields it returned. CI makes the same call on every push and fails if the result changes.
      </figcaption>
    </figure>
  );
}
