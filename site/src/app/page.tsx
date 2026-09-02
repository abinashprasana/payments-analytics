import Image from "next/image";

import { ArchitectureDiagram } from "@/components/architecture-diagram";
import { ChapterNav } from "@/components/chapter-nav";
import { ErDiagram } from "@/components/er-diagram";
import { FlowDiagram } from "@/components/flow-diagram";
import { publicConfig } from "@/lib/config";
import { projectData } from "@/lib/project-data";

const number = new Intl.NumberFormat("en-IE");
const compactNumber = new Intl.NumberFormat("en-IE", { notation: "compact", maximumFractionDigits: 1 });
const date = new Intl.DateTimeFormat("en-IE", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });

const formatDate = (value: string) => date.format(new Date(`${value}T00:00:00Z`));
const formatPercent = (value: number) => `${(value <= 1 ? value * 100 : value).toFixed(1)}%`;
const labView = (view: string) => `${publicConfig.labUrl}/?view=${view}`;
const settlementTone = (status: string) => {
  if (/complete|settled|success/i.test(status)) return "settled";
  if (/dispute|review|fail/i.test(status)) return "review";
  return "delayed";
};

const completedSettlement = projectData.settlementOutcomes.find(({ status }) =>
  /complete|settled|success/i.test(status),
);

const structuredData = JSON.stringify({
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "SoftwareApplication",
      name: "Payment Observatory",
      applicationCategory: "BusinessApplication",
      operatingSystem: "Web",
      isAccessibleForFree: true,
      url: publicConfig.labUrl,
      codeRepository: publicConfig.repositoryUrl,
      description: "A deployable payments intelligence application spanning transaction activity, merchant settlement, review outcomes, retention, and relational data design.",
    },
    {
      "@type": "Dataset",
      name: "Payment Observatory synthetic payments dataset",
      description: "A generated relational dataset used to demonstrate payment analytics without representing real people or commercial activity.",
      temporalCoverage: `${projectData.datasetWindow.firstTransactionDate}/${projectData.datasetWindow.lastTransactionDate}`,
      distribution: { "@type": "DataDownload", encodingFormat: "text/csv", contentUrl: `${publicConfig.repositoryUrl}/tree/main/data/raw` },
      isBasedOn: publicConfig.repositoryUrl,
    },
  ],
}).replace(/</g, "\\u003c");

export default function Home() {
  return (
    <>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: structuredData }} />

      <header className="site-header">
        <a className="brand" href="#top" aria-label="Payment Observatory case study home">
          <Image src="/brand/payment-observatory-mark.svg" width={42} height={42} alt="" priority />
          <span>
            <strong>Payment Observatory</strong>
            <small>System case study</small>
          </span>
        </a>
        <nav className="site-header__nav" aria-label="Primary navigation">
          <a href="#system">System</a>
          <a href="#overview">Analysis</a>
          <a href="#methodology">Method</a>
          <a className="text-link text-link--arrow" href={labView("overview")} target="_blank" rel="noreferrer">
            Open lab <span aria-hidden="true">↗</span>
          </a>
        </nav>
      </header>

      <main id="main-content">
        <section className="hero" id="top" aria-labelledby="hero-title">
          <div className="hero__copy">
            <p className="eyebrow"><span>System dossier</span> Payments intelligence</p>
            <h1 id="hero-title">Observe every link around <em>{number.format(projectData.recordCounts.transactions)} payment events</em></h1>
          </div>

          <aside className="hero__brief" aria-label="Case study brief">
            <p className="kicker">Observation brief</p>
            <p className="hero__lede">
              A deployable analytical system that follows transaction activity from customer accounts through merchant, settlement, review, and retention outcomes.
            </p>
            <div className="hero__actions">
              <a className="button button--primary" href={labView("overview")} target="_blank" rel="noreferrer">Open interactive lab <span aria-hidden="true">↗</span></a>
              <a className="button button--quiet" href="#system">Read the system story <span aria-hidden="true">↓</span></a>
            </div>
            <p className="hero__reference"><span>PAY / OBS—01</span> Verified repository evidence</p>
          </aside>

          <dl className="evidence-strip" aria-label="Verified project evidence">
            <div>
              <dt>Observed window</dt>
              <dd>{formatDate(projectData.datasetWindow.firstTransactionDate)}<span>to {formatDate(projectData.datasetWindow.lastTransactionDate)}</span></dd>
            </div>
            <div>
              <dt>Transaction records</dt>
              <dd>{number.format(projectData.recordCounts.transactions)}<span>synthetic events</span></dd>
            </div>
            <div>
              <dt>Relational model</dt>
              <dd>6 tables<span>linked end to end</span></dd>
            </div>
            <div>
              <dt>Verification</dt>
              <dd>Deterministic<span>generated evidence</span></dd>
            </div>
          </dl>

          <figure className="hero__visual">
            <div className="hero__visual-index" aria-hidden="true">
              <span>Observation plate / 01</span>
              <span>Interactive system surface</span>
            </div>
            <div className="hero__image-frame">
              <Image
                src="/media/reactor-poster.png"
                width={1440}
                height={1000}
                sizes="(max-width: 900px) 100vw, 1180px"
                alt="Payment Observatory dark interface showing the transaction lifecycle and linked record counts"
                priority
              />
            </div>
            <figcaption>
              <span>Live analytical lab</span>
              The interface keeps the payment lifecycle visible before any chart is read.
            </figcaption>
          </figure>
        </section>

        <section className="problem section-shell" id="system" aria-labelledby="problem-title">
          <div className="section-heading section-heading--split">
            <p className="kicker">The system problem</p>
            <div>
              <h2 id="problem-title">A payment is not one row</h2>
              <p>
                Operational meaning is distributed across ownership, transaction, merchant, settlement, and review records. The design keeps those relationships legible while every analytical view uses one shared filter and calculation path.
              </p>
            </div>
          </div>

          <div className="problem-ledger">
            <div className="problem-ledger__statement">
              <span className="problem-ledger__number" aria-hidden="true">01</span>
              <h3>Preserve the event spine</h3>
              <p>Transactions remain the central fact. Optional merchant, settlement, and review links stay optional instead of being silently filled.</p>
            </div>
            <div className="problem-ledger__statement">
              <span className="problem-ledger__number" aria-hidden="true">02</span>
              <h3>Keep comparisons honest</h3>
              <p>Date, currency, and category filters apply once. Previous-period comparisons use an equal-length window.</p>
            </div>
            <div className="problem-ledger__statement">
              <span className="problem-ledger__number" aria-hidden="true">03</span>
              <h3>Separate observation from prediction</h3>
              <p>Review views describe generated fraud flags. They do not present a production risk score or predictive model.</p>
            </div>
          </div>

          <FlowDiagram />
        </section>

        <ChapterNav />

        <div className="chapters section-shell">
          <section className="chapter chapter--overview" id="overview" aria-labelledby="overview-title">
            <div className="chapter__heading">
              <span className="chapter__number" aria-hidden="true">01</span>
              <div>
                <p className="kicker">Overview</p>
                <h2 id="overview-title">Start with operating context, not decoration</h2>
              </div>
              <p>
                Volume, completion, customer reach, and nominal completed value sit together so a movement can be checked before it is interpreted.
              </p>
            </div>

            <div className="chapter__evidence chapter__evidence--wide">
              <figure className="product-figure product-figure--dark">
                <Image src="/media/overview.png" width={1440} height={1000} sizes="(max-width: 900px) 100vw, 72vw" alt="Overview of the Payment Observatory interface" />
                <figcaption><span>Interactive lab · Overview</span> Relationship context and operational KPIs share the opening view.</figcaption>
              </figure>
              <aside className="evidence-note">
                <p className="kicker">Evidence read</p>
                <strong>{compactNumber.format(projectData.recordCounts.transactions)}</strong>
                <p>transactions remain filterable by date, currency, and merchant category.</p>
                <a className="text-link text-link--arrow" href={labView("overview")} target="_blank" rel="noreferrer">Inspect overview <span aria-hidden="true">↗</span></a>
              </aside>
            </div>

            <figure className="chart-figure chart-figure--band">
              <div>
                <p className="kicker">Recorded movement</p>
                <h3>Monthly volume stays connected to status context</h3>
                <p>The exported analytical figure is generated from the same repository snapshot used by the fallback application path.</p>
              </div>
              <Image src="/media/transaction-trends.png" width={1600} height={900} sizes="(max-width: 800px) 100vw, 58vw" alt="Monthly transaction trend analytical chart" />
            </figure>
          </section>

          <section className="chapter chapter--merchant" id="merchant-flow" aria-labelledby="merchant-title">
            <div className="chapter__heading chapter__heading--reverse">
              <span className="chapter__number" aria-hidden="true">02</span>
              <div>
                <p className="kicker">Merchant flow</p>
                <h2 id="merchant-title">Settlement outcomes stay attached to the merchants that produced them</h2>
              </div>
              <p>
                Rankings, processing fees, and outcome composition reveal where money moved and how the recorded settlement path completed.
              </p>
            </div>

            <div className="chapter__split">
              <div className="outcome-ledger" aria-label="Settlement outcome distribution">
                <div className="outcome-ledger__header">
                  <span>Status</span><span>Records</span><span>Share</span>
                </div>
                {projectData.settlementOutcomes.map((outcome) => (
                  <div className="outcome-ledger__row" key={outcome.status}>
                    <span className={`status-dot status-dot--${settlementTone(outcome.status)}`}>
                      {outcome.status.replaceAll("_", " ")}
                    </span>
                    <strong>{number.format(outcome.count)}</strong>
                    <span>{formatPercent(outcome.share)}</span>
                    <span className="outcome-ledger__bar" aria-hidden="true"><i style={{ width: formatPercent(outcome.share) }} /></span>
                  </div>
                ))}
                {completedSettlement ? (
                  <p className="outcome-ledger__takeaway">
                    <strong>{number.format(completedSettlement.count)}</strong> records carry the {completedSettlement.status.replaceAll("_", " ").toLowerCase()} outcome in the generated settlement table.
                  </p>
                ) : null}
              </div>

              <figure className="product-figure product-figure--chart">
                <Image src="/media/merchant-flow.png" width={1600} height={900} sizes="(max-width: 900px) 100vw, 54vw" alt="Merchant settlement performance chart" />
                <figcaption><span>Analytical output · Merchant flow</span> Ranking remains secondary to the recorded status and fee measures.</figcaption>
              </figure>
            </div>
            <a className="chapter-link" href={labView("merchant")} target="_blank" rel="noreferrer">Open the merchant-flow view <span aria-hidden="true">↗</span></a>
          </section>

          <section className="chapter chapter--risk" id="risk-monitor" aria-labelledby="risk-title">
            <div className="chapter__heading">
              <span className="chapter__number" aria-hidden="true">03</span>
              <div>
                <p className="kicker">Risk monitor</p>
                <h2 id="risk-title">Explain the review queue before calling it risk</h2>
              </div>
              <p>
                Category flag rates and recorded reasons are split into resolved and unresolved outcomes. The view is descriptive by design.
              </p>
            </div>

            <div className="risk-layout">
              <div className="risk-readout">
                <p className="kicker">Generated review sample</p>
                <dl>
                  <div><dt>Total flags</dt><dd>{number.format(projectData.reviewOutcomes.total)}</dd></div>
                  <div><dt>Resolved</dt><dd>{number.format(projectData.reviewOutcomes.resolved)}</dd></div>
                  <div><dt>Unresolved</dt><dd>{number.format(projectData.reviewOutcomes.unresolved)}</dd></div>
                  <div><dt>Resolution rate</dt><dd>{formatPercent(projectData.reviewOutcomes.resolutionRate)}</dd></div>
                </dl>
                <p className="risk-readout__note"><span aria-hidden="true">!</span> A fraud flag is a generated review record, not proof of fraud and not a model prediction.</p>
              </div>
              <figure className="product-figure product-figure--chart">
                <Image src="/media/risk-monitor.png" width={1600} height={900} sizes="(max-width: 900px) 100vw, 60vw" alt="Fraud review rates by merchant category chart" />
                <figcaption><span>Analytical output · Risk monitor</span> Color is paired with explicit resolved and unresolved labels.</figcaption>
              </figure>
            </div>
            <a className="chapter-link" href={labView("risk")} target="_blank" rel="noreferrer">Open the risk-monitor view <span aria-hidden="true">↗</span></a>
          </section>

          <section className="chapter chapter--retention" id="retention" aria-labelledby="retention-title">
            <div className="chapter__heading chapter__heading--reverse">
              <span className="chapter__number" aria-hidden="true">04</span>
              <div>
                <p className="kicker">Retention</p>
                <h2 id="retention-title">Absence and unavailability are different states</h2>
              </div>
              <p>
                The cohort view preserves observed zero activity while leaving future, unobservable periods blank. That distinction prevents incomplete cohorts from reading as churn.
              </p>
            </div>

            <figure className="retention-figure">
              <div className="retention-figure__copy">
                <p className="kicker">Cohort contract</p>
                <ul className="plain-list">
                  <li><span className="legend-swatch legend-swatch--retained" aria-hidden="true" />Observed activity</li>
                  <li><span className="legend-swatch legend-swatch--zero" aria-hidden="true" />Observed zero</li>
                  <li><span className="legend-swatch legend-swatch--future" aria-hidden="true" />Future period unavailable</li>
                </ul>
                <a className="text-link text-link--arrow" href={labView("retention")} target="_blank" rel="noreferrer">Inspect retention <span aria-hidden="true">↗</span></a>
              </div>
              <Image src="/media/retention.png" width={1600} height={900} sizes="(max-width: 900px) 100vw, 68vw" alt="Twelve-month customer cohort retention heatmap" />
              <figcaption>Analytical output · Retention. The accessible lab includes a table alternative to the heatmap.</figcaption>
            </figure>
          </section>

          <section className="chapter chapter--model" id="data-model" aria-labelledby="model-title">
            <div className="chapter__heading">
              <span className="chapter__number" aria-hidden="true">05</span>
              <div>
                <p className="kicker">Data model</p>
                <h2 id="model-title">The schema is part of the interface</h2>
              </div>
              <p>
                Cardinality, nullability, and source continuity explain why each analytical measure can be trusted and where it must be qualified.
              </p>
            </div>

            <ErDiagram />

            <figure className="product-figure product-figure--dark model-product-figure">
              <Image
                src="/media/data-model.png"
                width={1440}
                height={1000}
                sizes="(max-width: 900px) 100vw, 72vw"
                alt="Payment Observatory Data Model view showing six related payment tables and their cardinalities"
              />
              <figcaption><span>Interactive lab · Data model</span>The analytical interface exposes the same relationship and source-continuity contract.</figcaption>
            </figure>

            <dl className="relationship-ledger">
              {Object.entries(projectData.relationships).map(([key, relationship]) => (
                <div key={key}>
                  <dt>{key.replace(/([A-Z])/g, " $1").replace(/^./, (letter) => letter.toUpperCase())}</dt>
                  <dd><strong>{relationship.cardinality}</strong>{relationship.description}</dd>
                  <dd className="relationship-ledger__count">{number.format(relationship.linkedRecords)} linked records</dd>
                </div>
              ))}
            </dl>
            <a className="chapter-link" href={labView("model")} target="_blank" rel="noreferrer">Open the data-model view <span aria-hidden="true">↗</span></a>
          </section>
        </div>

        <section className="source-section section-shell" aria-labelledby="source-title">
          <div className="section-heading section-heading--split">
            <p className="kicker">Source continuity</p>
            <div>
              <h2 id="source-title">One analytical contract, two source paths</h2>
              <p>PostgreSQL is attempted first. If it is unavailable within the configured timeout, the repository snapshot rebuilds the same views without changing the calculation layer.</p>
            </div>
          </div>
          <ArchitectureDiagram />
        </section>

        <section className="methodology section-shell" id="methodology" aria-labelledby="method-title">
          <div className="methodology__intro">
            <p className="kicker">Methodology</p>
            <h2 id="method-title">Boundaries are part of the result</h2>
            <p>
              Every visible number is generated from the checked-in analytical snapshot. The site presents project evidence, not claims about live financial activity.
            </p>
          </div>
          <ol className="methodology__list">
            {projectData.limitations.map((limitation, index) => (
              <li key={limitation}>
                <span>{String(index + 1).padStart(2, "0")}</span>
                <p>{limitation}</p>
              </li>
            ))}
          </ol>
        </section>

        <section className="artifacts section-shell" aria-labelledby="artifacts-title">
          <div className="artifacts__main">
            <p className="kicker">Project artifacts</p>
            <h2 id="artifacts-title">Analysis that can be inspected, run, and challenged</h2>
            <p>
              The repository includes the relational schema, analytical SQL, a deterministic data generator, dashboard logic, a Power BI reporting layer, and regression coverage for calculation boundaries.
            </p>
            <div className="artifacts__actions">
              <a className="button button--ink" href={publicConfig.repositoryUrl} target="_blank" rel="noreferrer">View source on GitHub <span aria-hidden="true">↗</span></a>
              <a className="text-link" href={`${publicConfig.repositoryUrl}/blob/main/README.md`} target="_blank" rel="noreferrer">Read technical notes</a>
            </div>
          </div>
          <div className="technology-list">
            <p className="kicker">Technology</p>
            <ul>
              {projectData.technology.map((technology) => <li key={technology}>{technology}</li>)}
            </ul>
            <p className="technology-list__note">The analytical lab keeps one locally served OGL WebGL context. Charts and diagrams remain two-dimensional and readable without it.</p>
          </div>
        </section>

        <section className="final-cta section-shell" aria-labelledby="cta-title">
          <div className="final-cta__mark" aria-hidden="true">
            <Image src="/brand/payment-observatory-mark-mono.svg" width={84} height={84} alt="" />
          </div>
          <p className="kicker">Interactive laboratory</p>
          <h2 id="cta-title">Follow a payment through the whole system</h2>
          <p>Change the operating scope, compare periods, inspect records, and move between all five analytical views.</p>
          <div className="final-cta__actions">
            <a className="button button--light" href={labView("overview")} target="_blank" rel="noreferrer">Open interactive lab <span aria-hidden="true">↗</span></a>
            <a className="text-link text-link--light" href={publicConfig.repositoryUrl} target="_blank" rel="noreferrer">View repository</a>
          </div>
        </section>
      </main>

      <footer className="site-footer">
        <div><Image src="/brand/payment-observatory-mark.svg" width={34} height={34} alt="" /><span>Payment Observatory</span></div>
        <p>Synthetic payment records. Evidence generated from the repository snapshot.</p>
        <a href="#top">Back to top <span aria-hidden="true">↑</span></a>
      </footer>
    </>
  );
}
