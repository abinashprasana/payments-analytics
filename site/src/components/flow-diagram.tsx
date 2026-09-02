import type { CSSProperties } from "react";
import Script from "next/script";

const mobileStages = [
  { name: "Customer", detail: "owns one or more accounts", tone: "inbound" },
  { name: "Account", detail: "originates the transaction", tone: "inbound" },
  { name: "Transaction", detail: "preserves the event spine", tone: "transaction" },
  { name: "Merchant", detail: "receives purchases and refunds", tone: "transaction" },
  { name: "Settlement", detail: "records the financial outcome", tone: "settled" },
  { name: "Review", detail: "records a sampled fraud flag", tone: "review" },
] as const;

const FLOW_TRACE_SCRIPT = `
(() => {
  const initialisePaymentTrace = () => {
    document.querySelectorAll('[data-flow-trace]').forEach((figure) => {
      if (figure.__paymentObservatoryBound) return;
      const button = figure.querySelector('.trace-button');
      const label = figure.querySelector('[data-trace-label]');
      if (!button || !label) return;

      figure.__paymentObservatoryBound = true;
      button.disabled = false;
      let traceTimer;
      button.addEventListener('click', () => {
        window.clearTimeout(traceTimer);
        figure.classList.remove('is-tracing');
        void figure.offsetWidth;
        figure.classList.add('is-tracing');
        label.textContent = 'Tracing payment';

        const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        traceTimer = window.setTimeout(() => {
          figure.classList.remove('is-tracing');
          label.textContent = 'Replay trace';
        }, reducedMotion ? 700 : 4300);
      });
    });
  };

  initialisePaymentTrace();
})();
`;

export function FlowDiagram() {
  return (
    <>
      <figure className="flow-figure" data-flow-trace>
      <div className="flow-figure__heading">
        <div>
          <p className="kicker">Payment lifecycle</p>
          <h3>One event, several operational truths</h3>
        </div>
        <button className="trace-button" type="button" disabled>
          <span className="trace-button__signal" aria-hidden="true" />
          <span data-trace-label>Trace a payment</span>
        </button>
      </div>

      <div className="flow-canvas">
        <svg
          className="flow-map flow-map--desktop"
          viewBox="0 0 1040 470"
          role="img"
          aria-labelledby="flow-title flow-description"
        >
          <title id="flow-title">Payment record lifecycle</title>
          <desc id="flow-description">
            A customer owns an account, the account originates a transaction, and the transaction can connect to a merchant, settlement, or fraud-review record.
          </desc>
          <defs>
            <marker id="flow-arrow-blue" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
              <path d="M 0 0 L 10 5 L 0 10 z" fill="#79C1C7" />
            </marker>
            <marker id="flow-arrow-green" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
              <path d="M 0 0 L 10 5 L 0 10 z" fill="#74CFAF" />
            </marker>
            <marker id="flow-arrow-red" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
              <path d="M 0 0 L 10 5 L 0 10 z" fill="#E8849A" />
            </marker>
          </defs>

          <g className="flow-grid" aria-hidden="true">
            <path d="M20 118H1020M20 235H1020M20 352H1020" />
            <path d="M180 36V434M390 36V434M620 36V434M850 36V434" />
          </g>

          <g className="flow-routes" fill="none">
            <path className="flow-route flow-route--one" d="M178 235H288" markerEnd="url(#flow-arrow-blue)" />
            <path className="flow-route flow-route--two" d="M438 235H523" markerEnd="url(#flow-arrow-blue)" />
            <path className="flow-route flow-route--three" d="M685 221C754 202 770 118 832 118" markerEnd="url(#flow-arrow-blue)" />
            <path className="flow-route flow-route--four" d="M685 235H832" markerEnd="url(#flow-arrow-green)" />
            <path className="flow-route flow-route--five" d="M685 249C754 267 770 352 832 352" markerEnd="url(#flow-arrow-red)" />
          </g>

          <g className="flow-node flow-node--customer" transform="translate(34 185)">
            <rect width="144" height="100" rx="16" />
            <text className="flow-node__index" x="18" y="25">01</text>
            <text className="flow-node__label" x="18" y="54">Customer</text>
            <text className="flow-node__meta" x="18" y="78">owns account</text>
          </g>
          <g className="flow-node flow-node--account" transform="translate(294 185)">
            <rect width="144" height="100" rx="16" />
            <text className="flow-node__index" x="18" y="25">02</text>
            <text className="flow-node__label" x="18" y="54">Account</text>
            <text className="flow-node__meta" x="18" y="78">originates event</text>
          </g>
          <g className="flow-node flow-node--transaction" transform="translate(530 167)">
            <rect width="155" height="136" rx="20" />
            <circle cx="77.5" cy="68" r="44" />
            <text className="flow-node__index" x="18" y="26">03</text>
            <text className="flow-node__label flow-node__label--center" x="77.5" y="64">Transaction</text>
            <text className="flow-node__meta flow-node__meta--center" x="77.5" y="88">event spine</text>
          </g>
          <g className="flow-node flow-node--merchant" transform="translate(838 68)">
            <rect width="168" height="100" rx="16" />
            <text className="flow-node__index" x="18" y="25">04</text>
            <text className="flow-node__label" x="18" y="54">Merchant</text>
            <text className="flow-node__meta" x="18" y="78">optional link</text>
          </g>
          <g className="flow-node flow-node--settlement" transform="translate(838 185)">
            <rect width="168" height="100" rx="16" />
            <text className="flow-node__index" x="18" y="25">05</text>
            <text className="flow-node__label" x="18" y="54">Settlement</text>
            <text className="flow-node__meta" x="18" y="78">zero or one</text>
          </g>
          <g className="flow-node flow-node--review" transform="translate(838 302)">
            <rect width="168" height="100" rx="16" />
            <text className="flow-node__index" x="18" y="25">06</text>
            <text className="flow-node__label" x="18" y="54">Review</text>
            <text className="flow-node__meta" x="18" y="78">zero or one</text>
          </g>

          <circle className="flow-signal" r="6" cx="0" cy="0" aria-hidden="true" />
        </svg>

        <ol className="flow-map--mobile" aria-label="Payment record lifecycle">
          {mobileStages.map((stage, index) => (
            <li key={stage.name} className={`flow-step flow-step--${stage.tone}`} style={{ "--step-index": index } as CSSProperties}>
              <span>{String(index + 1).padStart(2, "0")}</span>
              <div>
                <strong>{stage.name}</strong>
                <small>{stage.detail}</small>
              </div>
            </li>
          ))}
        </ol>
      </div>

        <figcaption>
          Merchant links are optional for transfers. Settlement and review records are each constrained to zero or one record per transaction.
        </figcaption>
      </figure>
      <Script id="payment-flow-trace" strategy="afterInteractive">
        {FLOW_TRACE_SCRIPT}
      </Script>
    </>
  );
}
