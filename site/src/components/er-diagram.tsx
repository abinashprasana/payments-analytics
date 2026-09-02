export function ErDiagram() {
  return (
    <figure className="er-figure">
      <div className="er-scroll" tabIndex={0} aria-label="Scrollable entity relationship diagram">
        <svg viewBox="0 0 1000 560" role="img" aria-labelledby="er-title er-desc">
          <title id="er-title">Payment Observatory entity relationship diagram</title>
          <desc id="er-desc">
            Customers own accounts. Accounts originate transactions. Transactions can reference merchants and can have up to one settlement and one fraud flag.
          </desc>
          <g className="er-links" fill="none">
            <path d="M246 144H360" />
            <path d="M500 206V278" />
            <path d="M640 350H758" />
            <path d="M500 422V494" />
            <path d="M360 350H246" />
          </g>
          <g className="er-card" transform="translate(40 84)">
            <rect width="206" height="120" rx="18" />
            <text className="er-card__table" x="20" y="34">customers</text>
            <text x="20" y="65">PK customer_id</text>
            <text x="20" y="90">country · segment</text>
          </g>
          <g className="er-card" transform="translate(360 84)">
            <rect width="280" height="122" rx="18" />
            <text className="er-card__table" x="20" y="34">accounts</text>
            <text x="20" y="65">PK account_id</text>
            <text x="20" y="90">FK customer_id · currency</text>
          </g>
          <g className="er-card er-card--core" transform="translate(360 278)">
            <rect width="280" height="144" rx="20" />
            <text className="er-card__table" x="20" y="36">transactions</text>
            <text x="20" y="68">PK transaction_id</text>
            <text x="20" y="94">FK account_id · merchant_id?</text>
            <text x="20" y="120">amount · status · timestamp</text>
          </g>
          <g className="er-card" transform="translate(758 290)">
            <rect width="202" height="120" rx="18" />
            <text className="er-card__table" x="20" y="34">merchants</text>
            <text x="20" y="65">PK merchant_id</text>
            <text x="20" y="90">category · country</text>
          </g>
          <g className="er-card er-card--settled" transform="translate(360 494)">
            <rect width="280" height="58" rx="18" />
            <text className="er-card__table" x="20" y="36">settlements · 0..1</text>
          </g>
          <g className="er-card er-card--review" transform="translate(40 290)">
            <rect width="206" height="120" rx="18" />
            <text className="er-card__table" x="20" y="34">fraud_flags</text>
            <text x="20" y="65">FK transaction_id</text>
            <text x="20" y="90">reason · resolved</text>
          </g>
          <g className="er-cardinality" aria-hidden="true">
            <text x="264" y="133">1</text><text x="336" y="133">0..n</text>
            <text x="512" y="239">1</text><text x="512" y="267">0..n</text>
            <text x="663" y="338">0..n</text><text x="725" y="338">0..1</text>
            <text x="512" y="456">1</text><text x="512" y="482">0..1</text>
            <text x="272" y="338">0..1</text><text x="322" y="338">1</text>
          </g>
        </svg>
      </div>
      <figcaption>
        Six linked tables preserve source-level joins. A nullable merchant key keeps transfer activity honest instead of forcing a retail relationship.
      </figcaption>
    </figure>
  );
}
