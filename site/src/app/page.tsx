import Image from "next/image";

import { ArchitectureDiagram } from "@/components/architecture-diagram";
import { ChapterNav } from "@/components/chapter-nav";
import { ErDiagram } from "@/components/er-diagram";
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
      <span>Query ID <code>{queryId}</code></span>
      <span>Model <code>{model}</code></span>
    </div>
  );
}

function SqlBlock({ sql, label }: { sql: string; label: string }) {
  return (
    <pre className="sql-block" aria-label={label} tabIndex={0}>
      <code>{sql}</code>
    </pre>
  );
}

function SectionHeading({
  id,
  eyebrow,
  title,
  children,
}: {
  id: string;
  eyebrow: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="section-heading">
      <p className="kicker">{eyebrow}</p>
      <div>
        <h2 id={id}>{title}</h2>
        <p>{children}</p>
      </div>
    </div>
  );
}

export default function Home() {
  const exceptionMax = Math.max(...projectData.exceptionSummary.map(({ count }) => count), 1);

  return (
    <>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: structuredData }} />

      <header className="site-header">
        <a className="brand" href="#top" aria-label="The Settlement Gap case study home">
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
          <a href="#contract">Metric contract</a>
          <a href="#validation">Reproduce</a>
          <a className="text-link" href="#workbench">See the workbench preview <span aria-hidden="true">↓</span></a>
        </nav>
      </header>

      <main id="main-content">
        <section className="hero" id="top" aria-labelledby="hero-title">
          <div className="hero__copy">
            <p className="eyebrow"><span>SQL case study</span> Settlement reconciliation</p>
            <h1 id="hero-title">The <em>Settlement Gap</em></h1>
            <p className="hero__question">{projectData.question.stakeholder}</p>
          </div>

          <aside className="hero__brief" aria-label="Investigation answer">
            <p className="kicker">Concise answer</p>
            <p className="hero__lede">{projectData.question.conciseAnswer}</p>
            <div className="hero__actions">
              <a className="button button--primary" href="#baseline">Follow the SQL <span aria-hidden="true">↓</span></a>
              <a className="button button--quiet" href="#contract">Read the contract</a>
              <a className="button button--link" href="#workbench">See it traced in the workbench <span aria-hidden="true">↓</span></a>
            </div>
          </aside>

          <dl className="evidence-strip" aria-label="Dataset identity">
            <div><dt>Snapshot</dt><dd>{projectData.dataset.label}<span>{projectData.dataset.version}</span></dd></div>
            <div><dt>As of</dt><dd>{formatDate(projectData.dataset.asOfDate)}<span>{projectData.build.commitSha}</span></dd></div>
            <div><dt>Population</dt><dd>{numberFormat.format(projectData.dataset.recordCounts.eligiblePurchases)}<span>eligible purchases</span></dd></div>
            <div><dt>Source model</dt><dd>{numberFormat.format(projectData.dataset.recordCounts.sourceTables)}<span>source tables</span></dd></div>
          </dl>
        </section>

        <ChapterNav items={projectData.navigation} />

        <section className="case-section section-shell" id="question" aria-labelledby="question-title">
          <SectionHeading id="question-title" eyebrow="Stakeholder question" title="A completed purchase can still fail the close">
            Purchase status answers whether the customer event completed. Reconciliation asks whether the later settlement evidence agrees with the expected money, currency, fee term, and SLA.
          </SectionHeading>
          <div className="answer-ledger">
            <div>
              <span>Observed</span>
              <p>{projectData.question.conciseAnswer}</p>
            </div>
            <div>
              <span>Decision</span>
              <p>{projectData.question.operationalDecision}</p>
            </div>
          </div>
        </section>

        <section className="case-section case-section--paper" id="contract" aria-labelledby="contract-title">
          <div className="section-shell">
            <SectionHeading id="contract-title" eyebrow="Metric contract" title="Define the close before measuring it">
              The flagship population has one explicit grain and one currency boundary. Refunds and transfers remain valid source events, but do not enter this settlement ratio.
            </SectionHeading>

            <div className="metric-ledger">
              {projectData.metricDefinitions.map((metric) => (
                <article id={`metric-${metric.id}`} key={metric.id}>
                  <div className="metric-ledger__title">
                    <h3>{metric.label}</h3>
                    <code>{metric.id}</code>
                  </div>
                  <p>{metric.definition}</p>
                  <dl>
                    <div><dt>Population</dt><dd>{metric.population}</dd></div>
                    <div><dt>Grain</dt><dd>{metric.grain}</dd></div>
                    <div><dt>Currency</dt><dd>{metric.currencyBoundary}</dd></div>
                    <div><dt>Lineage</dt><dd><code>{metric.model}</code> · <code>{metric.queryId}</code></dd></div>
                    {metric.toleranceMinorUnits === undefined ? null : (
                      <div><dt>Match tolerance</dt><dd>{formatMoney({ currency: selectedScenario.currency, minorUnits: metric.toleranceMinorUnits })}</dd></div>
                    )}
                  </dl>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="case-section section-shell" id="model" aria-labelledby="model-title">
          <SectionHeading id="model-title" eyebrow="Relational model" title="Expected terms and recorded money are different evidence">
            Effective dates decide which merchant fee and settlement SLA applied when a purchase completed. A left join keeps missing settlement evidence visible instead of dropping it.
          </SectionHeading>

          <ErDiagram entities={projectData.sourceModel.entities} relationships={projectData.sourceModel.relationships} />

          <div className="scenario-block">
            <div className="scenario-block__intro">
              <p className="kicker">Synthetic scenario manifest</p>
              <h3>Known signals, versioned with the data</h3>
              <p>{selectedScenario.disclosure}</p>
            </div>
            <div className="scenario-list">
              {projectData.scenarios.map((scenario) => (
                <article className={scenario.id === selectedScenario.id ? "is-selected" : ""} key={scenario.id}>
                  <div><span>{scenario.kind}</span><strong>{scenario.label}</strong></div>
                  <dl>
                    <div><dt>Date</dt><dd>{formatDate(scenario.date)}</dd></div>
                    <div><dt>Scope</dt><dd>{scenario.merchantCategory} · {scenario.currency}</dd></div>
                  </dl>
                  <p>{scenario.expectedSignal}</p>
                  <small>{scenario.disclosure}</small>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="case-section case-section--ink" id="baseline" aria-labelledby="baseline-title">
          <div className="section-shell">
            <SectionHeading id="baseline-title" eyebrow={baselineStep.label} title={baselineStep.question}>
              {baselineStep.reading}
            </SectionHeading>
            <QueryHeader queryId={baselineStep.queryId} model={baselineStep.model} />

            <div className="query-layout">
              <SqlBlock sql={baselineStep.sql} label={`${baselineStep.label} SQL`} />
              <figure className="coverage-chart">
                <figcaption>Coverage recovery after the {formatDate(selectedScenario.date)} close · {selectedScenario.currency}</figcaption>
                <p className="classification-note">The purchase close stays fixed; each row re-evaluates the same batch at a later analysis as-of date.</p>
                <div className="coverage-chart__plot" role="img" aria-label={`${selectedScenario.currency} settlement coverage by analysis as-of date`}>
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
                <div className="table-scroll" tabIndex={0} aria-label="Scrollable daily close result table">
                  <table>
                    <thead><tr><th>Purchase close</th><th>Analysis as of</th><th>Currency</th><th>Eligible</th><th>Matched</th><th>Coverage</th><th>Overdue value</th><th>Fee delta</th></tr></thead>
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
              </figure>
            </div>
          </div>
        </section>

        <section className="case-section section-shell" id="isolation" aria-labelledby="isolation-title">
          <SectionHeading id="isolation-title" eyebrow={isolationStep.label} title={isolationStep.question}>
            {isolationStep.reading}
          </SectionHeading>
          <QueryHeader queryId={isolationStep.queryId} model={isolationStep.model} />

          <div className="query-layout query-layout--reverse">
            <div className="table-scroll result-table" tabIndex={0} aria-label="Scrollable segment result table">
              <table>
                <thead><tr><th>Category</th><th>Currency</th><th>Eligible</th><th>Exceptions</th><th>Rate</th><th>Primary reason</th><th>Overdue value</th></tr></thead>
                <tbody>
                  {projectData.segmentFindings.map((row) => (
                    <tr key={row.merchantCategory}>
                      <th scope="row">{row.merchantCategory}</th><td>{row.currency}</td>
                      <td>{numberFormat.format(row.eligibleCount)}</td><td>{numberFormat.format(row.exceptionCount)}</td>
                      <td>{formatPercent(row.exceptionRateBps)}</td><td>{titleCase(row.primaryReason)}</td><td>{formatMoney(row.overdueValue)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <SqlBlock sql={isolationStep.sql} label={`${isolationStep.label} SQL`} />
          </div>
        </section>

        <section className="case-section case-section--paper" id="classification" aria-labelledby="classification-title">
          <div className="section-shell">
            <SectionHeading id="classification-title" eyebrow={classificationStep.label} title={classificationStep.question}>
              {classificationStep.reading}
            </SectionHeading>
            <QueryHeader queryId={classificationStep.queryId} model={classificationStep.model} />

            <div className="classification-layout">
              <div>
                <ol className="precedence" aria-label="Primary exception label precedence">
                  {projectData.primaryLabelPrecedence.map((label) => <li key={label}>{titleCase(label)}</li>)}
                </ol>
                <div className="exception-bars" aria-label={`Exception composition in ${selectedScenario.currency}`}>
                  {projectData.exceptionSummary.map((reason) => (
                    <div key={reason.id}>
                      <span>{reason.label}</span>
                      <span className="exception-bars__track" aria-hidden="true"><i style={{ width: `${Math.max((reason.count / exceptionMax) * 100, reason.count ? 3 : 0)}%` }} /></span>
                      <strong>{numberFormat.format(reason.count)}</strong>
                      <small>{formatMoney(reason.affectedValue)}</small>
                    </div>
                  ))}
                </div>
              </div>
              <div>
                <SqlBlock sql={classificationStep.sql} label={`${classificationStep.label} SQL`} />
                <p className="classification-note">A payment may occupy several bars. Precedence stabilizes sorting; it does not erase evidence.</p>
              </div>
            </div>

            <article className="trace-card" aria-labelledby="trace-title">
              <div className="trace-card__heading">
                <div><p className="kicker">Payment trace</p><h3 id="trace-title"><code>{projectData.trace.paymentId}</code></h3></div>
                <div className="tag-list">{projectData.trace.flags.map((flag) => <span key={flag}>{titleCase(flag)}</span>)}</div>
              </div>
              <div className="trace-grid">
                <dl>
                  <div><dt>Completed</dt><dd>{formatDate(projectData.trace.transactionDate)}</dd></div>
                  <div><dt>Scope</dt><dd>{projectData.trace.merchantCategory} · {projectData.trace.currency}</dd></div>
                  <div><dt>Gross</dt><dd>{formatMoney(projectData.trace.gross)}</dd></div>
                  <div><dt>Status</dt><dd>{titleCase(projectData.trace.status)}</dd></div>
                </dl>
                <dl>
                  <div><dt>Effective term</dt><dd>{formatDate(projectData.trace.applicableTerm.validFrom)} to {projectData.trace.applicableTerm.validTo ? formatDate(projectData.trace.applicableTerm.validTo) : "Open ended"}</dd></div>
                  <div><dt>Fee rate</dt><dd>{formatPercent(projectData.trace.applicableTerm.feeRateBps)}</dd></div>
                  <div><dt>Expected fee</dt><dd>{formatMoney(projectData.trace.expectedFee)}</dd></div>
                  <div><dt>Recorded fee</dt><dd>{formatMoney(projectData.trace.recordedFee)}</dd></div>
                </dl>
                <dl>
                  <div><dt>SLA</dt><dd>{numberFormat.format(projectData.trace.applicableTerm.settlementSlaDays)} days</dd></div>
                  <div><dt>Expected settlement</dt><dd>{formatDate(projectData.trace.expectedSettlementDate)}</dd></div>
                  <div><dt>Recorded settlement</dt><dd>{formatOptionalDate(projectData.trace.recordedSettlementDate)}</dd></div>
                  <div><dt>Primary label</dt><dd>{titleCase(projectData.trace.primaryLabel)}</dd></div>
                </dl>
              </div>
              <p className="trace-card__why">{projectData.trace.whyFlagged}</p>
              <QueryHeader queryId={projectData.trace.queryId} model={projectData.trace.model} />
            </article>
          </div>
        </section>

        <section className="case-section section-shell" id="recommendation" aria-labelledby="recommendation-title">
          <SectionHeading id="recommendation-title" eyebrow="Finding and recommendation" title="Treat the batch first, then its residual payments">
            The analytical result becomes an operational sequence without claiming that this synthetic incident occurred in a real payments system.
          </SectionHeading>
          <div className="recommendation-grid">
            <article><span>Finding</span><p>{projectData.recommendation.finding}</p></article>
            <article><span>Action</span><p>{projectData.recommendation.action}</p></article>
            <dl>
              <div><dt>Owner</dt><dd>{projectData.recommendation.owner}</dd></div>
              <div><dt>Success metric</dt><dd><a href={`#metric-${successMetric.id}`}>{successMetric.label}</a></dd></div>
            </dl>
          </div>
        </section>

        <section className="case-section case-section--ink" id="validation" aria-labelledby="validation-title">
          <div className="section-shell">
            <SectionHeading id="validation-title" eyebrow="Validation and reproduction" title="The result is inspectable beyond the chart">
              SQL runs through one model chain on both compatibility engines. Quality checks assert grain, effective-date joins, identities, and currency isolation before the case payload is exported.
            </SectionHeading>

            <ArchitectureDiagram engines={projectData.reproduction.compatibilityEngines} models={projectData.models} />

            <div className="validation-grid">
              <article className="explain-panel">
                <QueryHeader queryId={projectData.validation.explainQueryId} model={projectData.validation.explainModel} />
                <h3>EXPLAIN ANALYZE</h3>
                <SqlBlock sql={projectData.validation.explainSql} label="EXPLAIN ANALYZE example" />
                <ol>{projectData.validation.plan.map((step) => <li key={step}>{step}</li>)}</ol>
                <p>The checked-in payload records the inspection target without presenting one local run as a benchmark.</p>
              </article>
              <div className="quality-ledger">
                {projectData.validation.qualityResults.map((result) => (
                  <article key={result.checkId}>
                    <span className={`quality-status quality-status--${result.status}`}>{result.status}</span>
                    <h3>{result.label}</h3>
                    <p>{result.detail}</p>
                    <small>{numberFormat.format(result.checkedRows)} checked rows · <code>{result.checkId}</code></small>
                  </article>
                ))}
              </div>
            </div>

            <div className="reproduction-grid">
              <div>
                <p className="kicker">Reproduce</p>
                <ol className="command-list">
                  {projectData.reproduction.commands.map((command) => <li key={command}><code>{command}</code></li>)}
                </ol>
              </div>
              <div>
                <p className="kicker">Limitations</p>
                <ul className="limitation-list">
                  {projectData.limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}
                </ul>
              </div>
            </div>
          </div>
        </section>

        <section className="case-section section-shell" id="workbench" aria-labelledby="workbench-title">
          <SectionHeading id="workbench-title" eyebrow="Operational handoff" title="The workbench, in full">
            Everything above ran once, on paper. Below is the same reconciliation, live: filter the queue, open a payment, and see the SQL rule that flagged it.
          </SectionHeading>

          <div className="workbench-preview">
            <div className="workbench-preview__head">
              <div><span>{projectData.dataset.label}</span><strong>Settlement Operations Workbench</strong></div>
              <code>{projectData.dataset.version} · {projectData.build.commitSha} · {projectData.build.runtimeLabel}</code>
            </div>
            <div className="workbench-preview__evidence">
              <dl className="workbench-preview__trace">
                <div><dt>Scenario</dt><dd>{selectedScenario.label}</dd></div>
                <div><dt>Payment</dt><dd><code>{projectData.trace.paymentId}</code></dd></div>
                <div><dt>Primary label</dt><dd>{titleCase(projectData.trace.primaryLabel)}</dd></div>
                <div><dt>Lineage</dt><dd><code>{projectData.trace.queryId}</code></dd></div>
              </dl>
              <ol className="journey-list">
                {projectData.workbench.journey.map((step) => <li key={step}>{step}</li>)}
              </ol>
            </div>
          </div>

          <div className="handoff">
            <div>
              <p className="kicker">Deep-linked evidence</p>
              <p>Open <code>{projectData.trace.paymentId}</code> inside <code>{projectData.trace.scenarioId}</code>. Review notes and resolution actions in the demo are session-only.</p>
              <small>{projectData.workbench.sleepDisclosure}</small>
            </div>
            <a className="button button--primary" href={workbenchUrl} target="_blank" rel="noreferrer">Trace this payment <span aria-hidden="true">↗</span></a>
          </div>
        </section>

        <section className="final-cta section-shell" aria-labelledby="artifacts-title">
          <Image src={assetUrl("/brand/payment-observatory-mark-mono.svg")} width={74} height={74} alt="" />
          <div><p className="kicker">Repository evidence</p><h2 id="artifacts-title">Challenge the SQL, not a screenshot</h2></div>
          <p>Inspect the canonical models, deterministic scenario manifest, engine parity tests, and generated case payload in the repository.</p>
          <a className="button button--light" href={publicConfig.repositoryUrl} target="_blank" rel="noreferrer">View source on GitHub <span aria-hidden="true">↗</span></a>
        </section>
      </main>

      <footer className="site-footer">
        <div><Image src={assetUrl("/brand/payment-observatory-mark-mono.svg")} width={34} height={34} alt="" /><span>The Settlement Gap</span></div>
        <p>{projectData.dataset.label} · {projectData.dataset.version} · As of {formatDate(projectData.dataset.asOfDate)} · {projectData.build.commitSha} · {projectData.build.runtimeLabel}</p>
        <a href="#top">Back to top <span aria-hidden="true">↑</span></a>
      </footer>
    </>
  );
}
