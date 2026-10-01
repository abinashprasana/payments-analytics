import Image from "next/image";

import { ArchitectureDiagram } from "@/components/architecture-diagram";
import { ChapterNav } from "@/components/chapter-nav";
import { ErDiagram } from "@/components/er-diagram";
import { McpFlow } from "@/components/mcp-flow";
import { McpSession } from "@/components/mcp-session";
import { ScenarioTimeline } from "@/components/scenario-timeline";
import { assetUrl, publicConfig } from "@/lib/config";
import { projectData, type Money } from "@/lib/project-data";

const numberFormat = new Intl.NumberFormat("en-IE");
const dateFormat = new Intl.DateTimeFormat("en-IE", {
  day: "numeric",
  month: "short",
  year: "numeric",
  timeZone: "UTC",
});

const formatDate = (value: string) =>
  dateFormat.format(new Date(`${value}T00:00:00Z`));
const formatOptionalDate = (value: string | null) =>
  value ? formatDate(value) : "Not recorded";
const formatPercent = (basisPoints: number) => `${(basisPoints / 100).toFixed(2)}%`;
const formatMoney = (money: Money) =>
  new Intl.NumberFormat("en-IE", {
    style: "currency",
    currency: money.currency,
    currencyDisplay: "narrowSymbol",
  }).format(money.minorUnits / 100);
const titleCase = (value: string) =>
  value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());

const selectedScenario = projectData.scenarios.find(
  (scenario) => scenario.id === projectData.selectedScenarioId,
)!;
const baselineStep = projectData.investigationSteps.find(({ id }) => id === "baseline")!;
const isolationStep = projectData.investigationSteps.find(({ id }) => id === "isolation")!;
const classificationStep = projectData.investigationSteps.find(
  ({ id }) => id === "classification",
)!;
const successMetric = projectData.metricDefinitions.find(
  ({ id }) => id === projectData.recommendation.successMetricId,
)!;
const qualityPassed = projectData.validation.qualityResults.filter(
  ({ status }) => status === "pass",
).length;
const workbenchUrl = (() => {
  const params = new URLSearchParams({
    view: "trace",
    scenario: projectData.trace.scenarioId,
    payment_id: projectData.trace.paymentId,
  });
  return `${publicConfig.workbenchUrl}/?${params.toString()}`;
})();

const structuredData = JSON.stringify({
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "Article",
      headline: "The Settlement Gap",
      description: projectData.question.conciseAnswer,
      url: publicConfig.siteUrl,
      author: { "@type": "Person", name: "Abinash Prasana" },
      about: ["SQL", "payment settlement reconciliation", "data analytics"],
    },
    {
      "@type": "Dataset",
      name: projectData.dataset.label,
      version: projectData.dataset.version,
      temporalCoverage: `${projectData.dataset.window.firstTransactionDate}/${projectData.dataset.window.lastTransactionDate}`,
      description: selectedScenario.disclosure,
      distribution: {
        "@type": "DataDownload",
        encodingFormat: "text/csv",
        contentUrl: `${publicConfig.repositoryUrl}/tree/main/data/raw`,
      },
    },
  ],
}).replace(/</g, "\\u003c");

function QueryHeader({ queryId, model }: { queryId: string; model: string }) {
  return (
    <div className="query-header">
      <span>Query <code>{queryId}</code></span>
      <span>Model <code>{model}</code></span>
    </div>
  );
}

function SqlDetails({ sql, label }: { sql: string; label: string }) {
  return (
    <details className="reveal-details">
      <summary>Show the SQL</summary>
      <pre className="sql-block" aria-label={label} tabIndex={0}>
        <code>{sql}</code>
      </pre>
    </details>
  );
}

function SectionHeading({
  id,
  index,
  title,
  children,
}: {
  id: string;
  index: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="section-heading">
      <p className="kicker" aria-hidden="true">{index}</p>
      <div>
        <h2 id={id}>{title}</h2>
        <p>{children}</p>
      </div>
    </div>
  );
}

function Step({
  id,
  number,
  step,
  children,
}: {
  id?: string;
  number: string;
  step: typeof baselineStep;
  children: React.ReactNode;
}) {
  return (
    <article className="step" id={id} aria-labelledby={`${step.id}-title`}>
      <div className="step__text">
        <span className="step__number" aria-hidden="true">{number}</span>
        <p className="step__label">{step.label}</p>
        <h3 id={`${step.id}-title`}>{step.question}</h3>
        <p className="step__reading">{step.reading}</p>
        <QueryHeader queryId={step.queryId} model={step.model} />
        <SqlDetails sql={step.sql} label={`${step.label} SQL`} />
      </div>
      <div className="step__figure">{children}</div>
    </article>
  );
}

export default function Home() {
  const exceptionMax = Math.max(...projectData.exceptionSummary.map(({ count }) => count), 1);
  const activeReasons = projectData.exceptionSummary.filter(({ count }) => count > 0);
  const flagTotal = activeReasons.reduce((sum, { count }) => sum + count, 0);

  return (
    <>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: structuredData }} />

      <div className="scroll-progress" aria-hidden="true" />

      <header className="site-header">
        <a className="brand" href="#question" aria-label="The Settlement Gap, back to the top">
          <Image
            src={assetUrl("/brand/payment-observatory-mark-mono.svg")}
            width={42}
            height={42}
            alt=""
            priority
          />
          <span><strong>The Settlement Gap</strong><small>SQL investigation</small></span>
        </a>
        <nav className="site-header__nav" aria-label="Primary navigation">
          <a className="text-link" href={publicConfig.repositoryUrl} target="_blank" rel="noreferrer">
            Source <span aria-hidden="true">↗</span>
          </a>
        </nav>
      </header>

      <main id="main-content">
        <section className="hero" id="question" aria-labelledby="hero-title">
          <div className="hero__field" aria-hidden="true"><i /><i /></div>
          <div className="hero__copy">
            <p className="eyebrow"><span>Settlement reconciliation</span> SQL, DuckDB and PostgreSQL</p>
            <h1 id="hero-title">The <em>Settlement Gap</em></h1>
            <p className="hero__question">{projectData.question.stakeholder}</p>
          </div>

          <aside className="hero__brief" aria-label="The short answer">
            <p className="kicker">Short answer</p>
            <p className="hero__lede">{projectData.question.conciseAnswer}</p>
            <div className="hero__actions">
              <a className="button button--primary" href="#baseline">Follow the evidence <span aria-hidden="true">↓</span></a>
              <a className="button button--quiet" href="#ask">Try it live</a>
            </div>
          </aside>

          <dl className="evidence-strip" aria-label="Dataset identity">
            <div><dt>Snapshot</dt><dd>{projectData.dataset.label}<span>{projectData.dataset.version}</span></dd></div>
            <div><dt>As of</dt><dd>{formatDate(projectData.dataset.asOfDate)}<span>{formatDate(projectData.dataset.window.firstTransactionDate)} to {formatDate(projectData.dataset.window.lastTransactionDate)}</span></dd></div>
            <div><dt>Population</dt><dd>{numberFormat.format(projectData.dataset.recordCounts.eligiblePurchases)}<span>eligible purchases</span></dd></div>
          </dl>
        </section>

        <ChapterNav items={projectData.navigation} />

        <section className="case-section case-section--paper" id="contract" aria-labelledby="contract-title">
          <div className="section-shell">
            <SectionHeading id="contract-title" index="01" title="Agree on what a clean close means">
              A status report calls a purchase done once the customer pays. Operations can only close the day when the money that arrives later matches the expected amount, currency, fee and deadline. These four metrics define that check. Refunds and transfers stay in the data but sit outside it.
            </SectionHeading>

            <div className="metric-ledger">
              {projectData.metricDefinitions.map((metric) => (
                <details id={`metric-${metric.id}`} key={metric.id}>
                  <summary>
                    <span className="metric-ledger__name">
                      <strong>{metric.label}</strong>
                      <code>{metric.queryId}</code>
                    </span>
                    <span className="metric-ledger__definition">{metric.definition}</span>
                    <span className="metric-ledger__grain">{metric.grain}</span>
                  </summary>
                  <dl>
                    <div><dt>Population</dt><dd>{metric.population}</dd></div>
                    <div><dt>Currency</dt><dd>{metric.currencyBoundary}</dd></div>
                    <div><dt>Model</dt><dd><code>{metric.model}</code></dd></div>
                    {metric.toleranceMinorUnits === undefined ? null : (
                      <div><dt>Match tolerance</dt><dd>{formatMoney({ currency: selectedScenario.currency, minorUnits: metric.toleranceMinorUnits })}</dd></div>
                    )}
                  </dl>
                </details>
              ))}
            </div>
          </div>
        </section>

        <section className="case-section section-shell" id="model" aria-labelledby="model-title">
          <SectionHeading id="model-title" index="02" title="Two kinds of evidence, kept apart until the join">
            The merchant contract says what a payment should cost. The settlement record says what it did cost. Effective dates pick the contract that applied on the purchase day, and a left join keeps a missing settlement visible instead of dropping the payment.
          </SectionHeading>

          <ErDiagram entities={projectData.sourceModel.entities} relationships={projectData.sourceModel.relationships} />

          <div className="scenario-heading">
            <h3>Four scripted closes, one cause each</h3>
            <p>One ordinary day and three incidents, each with its own cause and reaching merchants in several categories. The walkthrough follows the {selectedScenario.kind} incident.</p>
          </div>
          <ScenarioTimeline
            scenarios={projectData.scenarios}
            selectedId={selectedScenario.id}
            disclosure={selectedScenario.disclosure}
          />
        </section>

        <section className="case-section case-section--ink" id="baseline" aria-labelledby="baseline-chapter-title">
          <div className="section-shell">
            <SectionHeading id="baseline-chapter-title" index="03" title="Follow one close from symptom to payment">
              Three queries, each answering the question the last one raised. The chart stays beside its explanation while you read.
            </SectionHeading>

            <div className="steps">
              <Step number="1" step={baselineStep}>
                <figure className="coverage-chart">
                  <figcaption>Coverage for the {formatDate(selectedScenario.date)} close in {selectedScenario.currency}</figcaption>
                  <div className="coverage-chart__plot" role="img" aria-label={`${selectedScenario.currency} settlement coverage by analysis date`}>
                    {projectData.dailyClose.map((row) => (
                      <div className={row.analysisAsOfDate === row.closeDate ? "is-incident" : ""} key={`${row.closeDate}-${row.analysisAsOfDate}`}>
                        <time dateTime={row.analysisAsOfDate}>{formatDate(row.analysisAsOfDate)}</time>
                        <span className="coverage-chart__track" aria-hidden="true">
                          <i style={{ width: formatPercent(row.coverageBps) }} />
                        </span>
                        <strong>{formatPercent(row.coverageBps)}</strong>
                      </div>
                    ))}
                  </div>
                  <p className="figure-note">Same purchases, read again at later dates as settlements arrive.</p>
                  <details className="reveal-details">
                    <summary>Show the result table</summary>
                    <div className="table-scroll" tabIndex={0} aria-label="Scrollable daily close result table">
                      <table>
                        <thead><tr><th>Purchase close</th><th>Read on</th><th>Currency</th><th>Eligible</th><th>Matched</th><th>Coverage</th><th>Overdue value</th><th>Fee delta</th></tr></thead>
                        <tbody>
                          {projectData.dailyClose.map((row) => (
                            <tr key={`${row.closeDate}-${row.analysisAsOfDate}`}>
                              <td>{formatDate(row.closeDate)}</td><td>{formatDate(row.analysisAsOfDate)}</td><td>{row.currency}</td>
                              <td>{numberFormat.format(row.eligibleCount)}</td><td>{numberFormat.format(row.matchedCount)}</td>
                              <td>{formatPercent(row.coverageBps)}</td><td>{formatMoney(row.overdueValue)}</td><td>{formatMoney(row.feeDelta)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </details>
                </figure>
              </Step>

              <Step id="isolation" number="2" step={isolationStep}>
                <figure className="segment-chart">
                  <figcaption>Exceptions by merchant category, {selectedScenario.currency}</figcaption>
                  <div className="segment-chart__plot">
                    {projectData.segmentFindings.map((row) => (
                      <div className={row.exceptionCount ? "has-exceptions" : ""} key={row.merchantCategory}>
                        <span>{row.merchantCategory}</span>
                        <span className="segment-chart__track" aria-hidden="true">
                          <i style={{ width: formatPercent(row.exceptionRateBps) }} />
                        </span>
                        <strong>{numberFormat.format(row.exceptionCount)} of {numberFormat.format(row.eligibleCount)}</strong>
                        <small>{row.exceptionCount ? titleCase(row.primaryReason) : "Clean"}</small>
                      </div>
                    ))}
                  </div>
                  <p className="figure-note">Bar length is the share of that category&apos;s payments with an exception.</p>
                </figure>
              </Step>

              <Step id="classification" number="3" step={classificationStep}>
                <figure className="exception-figure">
                  <figcaption>Reasons behind the {numberFormat.format(flagTotal)} flags</figcaption>
                  <div className="exception-bars" aria-label={`Exception composition in ${selectedScenario.currency}`}>
                    {projectData.exceptionSummary.map((reason) => (
                      <div key={reason.id} className={reason.count ? "" : "is-zero"}>
                        <span>{reason.label}</span>
                        <span className="exception-bars__track" aria-hidden="true"><i style={{ width: `${Math.max((reason.count / exceptionMax) * 100, reason.count ? 3 : 0)}%` }} /></span>
                        <strong>{numberFormat.format(reason.count)}</strong>
                        <small>{formatMoney(reason.affectedValue)}</small>
                      </div>
                    ))}
                  </div>
                  <ol className="precedence" aria-label="Queue order for the primary label">
                    {projectData.primaryLabelPrecedence.map((label) => <li key={label}>{titleCase(label)}</li>)}
                  </ol>
                  <p className="figure-note">
                    {activeReasons.length === 1
                      ? `One reason only: ${activeReasons[0].label.toLowerCase()}. The empty rows mean the query found nothing, not that data is missing.`
                      : "A payment can sit in several rows. The queue order above only sorts; it never drops a flag."}
                  </p>
                </figure>
              </Step>
            </div>

            <article className="trace-card" aria-labelledby="trace-title">
              <div className="trace-card__heading">
                <div><p className="kicker">One payment, end to end</p><h3 id="trace-title"><code>{projectData.trace.paymentId}</code></h3></div>
                <div className="tag-list">{projectData.trace.flags.map((flag) => <span key={flag}>{titleCase(flag)}</span>)}</div>
              </div>
              <div className="trace-grid">
                <dl>
                  <div><dt>Completed</dt><dd>{formatDate(projectData.trace.transactionDate)}</dd></div>
                  <div><dt>Scope</dt><dd>{projectData.trace.merchantCategory} in {projectData.trace.currency}</dd></div>
                  <div><dt>Gross</dt><dd>{formatMoney(projectData.trace.gross)}</dd></div>
                  <div><dt>Status</dt><dd>{titleCase(projectData.trace.status)}</dd></div>
                </dl>
                <dl>
                  <div><dt>Contract</dt><dd>{formatDate(projectData.trace.applicableTerm.validFrom)} to {projectData.trace.applicableTerm.validTo ? formatDate(projectData.trace.applicableTerm.validTo) : "open ended"}</dd></div>
                  <div><dt>Fee rate</dt><dd>{formatPercent(projectData.trace.applicableTerm.feeRateBps)}</dd></div>
                  <div><dt>Expected fee</dt><dd>{formatMoney(projectData.trace.expectedFee)}</dd></div>
                  <div><dt>Recorded fee</dt><dd>{formatMoney(projectData.trace.recordedFee)}</dd></div>
                </dl>
                <dl>
                  <div><dt>Deadline</dt><dd>{numberFormat.format(projectData.trace.applicableTerm.settlementSlaDays)} days</dd></div>
                  <div><dt>Due</dt><dd>{formatDate(projectData.trace.expectedSettlementDate)}</dd></div>
                  <div><dt>Settled</dt><dd>{formatOptionalDate(projectData.trace.recordedSettlementDate)}</dd></div>
                  <div><dt>Primary label</dt><dd>{titleCase(projectData.trace.primaryLabel)}</dd></div>
                </dl>
              </div>
              <p className="trace-card__why">{projectData.trace.whyFlagged}</p>
              <QueryHeader queryId={projectData.trace.queryId} model={projectData.trace.model} />
            </article>
          </div>
        </section>

        <section className="case-section section-shell" id="validation" aria-labelledby="validation-title">
          <SectionHeading id="validation-title" index="04" title="What to do, and why the number holds">
            The finding turns into one action with an owner. The same SQL runs on DuckDB and PostgreSQL, and quality checks run before anything is published.
          </SectionHeading>

          <div className="recommendation-grid">
            <article><span>Finding</span><p>{projectData.recommendation.finding}</p></article>
            <article><span>Action</span><p>{projectData.recommendation.action}</p></article>
            <dl>
              <div><dt>Decision</dt><dd>{projectData.question.operationalDecision}</dd></div>
              <div><dt>Owner</dt><dd>{projectData.recommendation.owner}</dd></div>
              <div><dt>Watch</dt><dd><a href={`#metric-${successMetric.id}`}>{successMetric.label}</a></dd></div>
            </dl>
          </div>

          <ArchitectureDiagram engines={projectData.reproduction.compatibilityEngines} models={projectData.models} />

          <div className="proof-grid">
            <div>
              <p className="proof-grid__stat">
                <strong>{qualityPassed} of {projectData.validation.qualityResults.length}</strong>
                <span>quality checks pass on this snapshot</span>
              </p>
              <details className="reveal-details">
                <summary>Show every check</summary>
                <ul className="quality-list">
                  {projectData.validation.qualityResults.map((result) => (
                    <li key={result.checkId}>
                      <span className={`quality-status quality-status--${result.status}`}>{result.status}</span>
                      <span>{result.label}</span>
                      <code>{result.checkId}</code>
                    </li>
                  ))}
                </ul>
              </details>
              <details className="reveal-details">
                <summary>Show the query plan target</summary>
                <QueryHeader queryId={projectData.validation.explainQueryId} model={projectData.validation.explainModel} />
                <pre className="sql-block" aria-label="EXPLAIN ANALYZE example" tabIndex={0}><code>{projectData.validation.explainSql}</code></pre>
                <ol className="plain-list">{projectData.validation.plan.map((step) => <li key={step}>{step}</li>)}</ol>
              </details>
            </div>
            <div>
              <p className="kicker">Reproduce</p>
              <ol className="command-list">
                {projectData.reproduction.commands.map((command) => <li key={command}><code>{command}</code></li>)}
              </ol>
            </div>
            <div>
              <p className="kicker">Limits</p>
              <ul className="plain-list">
                {projectData.limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}
              </ul>
            </div>
          </div>
        </section>

        <section className="case-section case-section--ink" id="ask" aria-labelledby="ask-title">
          <div className="section-shell">
            <SectionHeading id="ask-title" index="05" title="Trace it yourself, or ask Claude">
              The analysis above ran once. The same query registry also powers a live workbench and a read-only MCP server, so you can check any payment in the four scripted closes.
            </SectionHeading>

            <div className="use-grid">
              <div className="use-panel" id="workbench">
                <p className="kicker">Workbench</p>
                <h3>Open payment <code>{projectData.trace.paymentId}</code> in the workbench</h3>
                <p>Filter the queue, open a payment and read the rule that flagged it. Review notes are session-only and never change the snapshot.</p>
                <a className="button button--primary" href={workbenchUrl} target="_blank" rel="noreferrer">Trace this payment <span aria-hidden="true">↗</span></a>
                <small>{projectData.workbench.sleepDisclosure}</small>
              </div>

              <div className="use-panel use-panel--ask">
                <p className="kicker">Ask Claude</p>
                <h3>Plain-English questions, answered through the same queries</h3>
                <div className="mcp-endpoint">
                  <div className="mcp-endpoint__field">
                    <code id="mcp-endpoint-url">{publicConfig.mcpUrl}</code>
                    <button type="button" className="mcp-copy" data-copy="mcp-endpoint-url" hidden>Copy</button>
                  </div>
                  <p className="mcp-endpoint__status" aria-live="polite" data-copy-status />
                </div>
                <p className="mcp-tool-line">
                  Three read-only tools:{" "}
                  {projectData.ask.tools.map((tool, index) => (
                    <span key={tool.name}>{index ? ", " : ""}<code>{tool.name}</code></span>
                  ))}. None of them accepts SQL.
                </p>
                <details className="reveal-details">
                  <summary>How to connect</summary>
                  <dl className="mcp-clients">
                    <div><dt>Claude.ai and Claude Desktop</dt><dd>Settings, Connectors, Add custom connector, then paste the endpoint.</dd></div>
                    <div><dt>Claude Code</dt><dd><code>claude mcp add --transport http settlement-gap {publicConfig.mcpUrl}</code></dd></div>
                    <div><dt>Local, no network</dt><dd><code>cd mcp_server &amp;&amp; uv run settlement-gap-mcp</code></dd></div>
                  </dl>
                  <table className="mcp-tools">
                    <caption className="visually-hidden">Tools the server exposes</caption>
                    <thead><tr><th scope="col">Tool</th><th scope="col">What it returns</th></tr></thead>
                    <tbody>
                      {projectData.ask.tools.map((tool) => (
                        <tr key={tool.name}><th scope="row"><code>{tool.name}</code></th><td>{tool.purpose}</td></tr>
                      ))}
                    </tbody>
                  </table>
                </details>
                {projectData.evaluation ? (
                  <p className="mcp-eval">
                    Tested live with <code>{projectData.evaluation.model}</code>: through these tools it answered{" "}
                    <strong>{projectData.evaluation.toolPath.correct} of {projectData.evaluation.toolPath.total}</strong> questions
                    correctly. Writing its own SQL against the raw tables, it got{" "}
                    <strong>{projectData.evaluation.ownSql.correct} of {projectData.evaluation.ownSql.total}</strong>.{" "}
                    <a href={`${publicConfig.repositoryUrl}#-mcp-evaluation`} target="_blank" rel="noreferrer">How it was measured <span aria-hidden="true">↗</span></a>
                  </p>
                ) : null}
                <p className="mcp-scope">The free server sleeps when idle, so the first call can take 30 to 60 seconds.</p>
              </div>
            </div>

            <McpSession ask={projectData.ask} />
            <McpFlow />
          </div>
        </section>
      </main>

      <footer className="site-footer">
        <div><Image src={assetUrl("/brand/payment-observatory-mark-mono.svg")} width={34} height={34} alt="" /><span>The Settlement Gap</span></div>
        <p>
          <span>{projectData.dataset.label}</span>
          <span>{projectData.dataset.version}</span>
          <span>As of {formatDate(projectData.dataset.asOfDate)}</span>
          <span>Build <code>{projectData.build.commitSha}</code></span>
        </p>
        <div className="site-footer__links">
          <a href={publicConfig.repositoryUrl} target="_blank" rel="noreferrer">Source on GitHub <span aria-hidden="true">↗</span></a>
          <a href="#question">Back to top <span aria-hidden="true">↑</span></a>
        </div>
      </footer>
    </>
  );
}
