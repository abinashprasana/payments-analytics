import type { Scenario } from "@/lib/project-data";

const DAY = 86_400_000;
const monthFormat = new Intl.DateTimeFormat("en-IE", { month: "short", timeZone: "UTC" });
const dayFormat = new Intl.DateTimeFormat("en-IE", { day: "numeric", month: "short", timeZone: "UTC" });

const toTime = (value: string) => new Date(`${value}T00:00:00Z`).getTime();

/** The four scripted closes on one axis. Positions come from the manifest
 *  dates, so moving a close in data/scenarios.json moves its marker. */
export function ScenarioTimeline({
  scenarios,
  selectedId,
  disclosure,
}: {
  scenarios: Scenario[];
  selectedId: string;
  disclosure: string;
}) {
  const times = scenarios.map(({ date }) => toTime(date));
  const start = Math.min(...times) - 10 * DAY;
  const end = Math.max(...times) + 10 * DAY;
  const at = (time: number) => `${(((time - start) / (end - start)) * 100).toFixed(2)}%`;

  const months: { label: string; left: string }[] = [];
  const cursor = new Date(start);
  cursor.setUTCDate(1);
  cursor.setUTCMonth(cursor.getUTCMonth() + 1);
  while (cursor.getTime() < end) {
    months.push({ label: monthFormat.format(cursor), left: at(cursor.getTime()) });
    cursor.setUTCMonth(cursor.getUTCMonth() + 1);
  }

  return (
    <figure className="scenario-timeline">
      <div className="scenario-timeline__axis" aria-hidden="true">
        <span className="scenario-timeline__track" />
        {months.map((month) => (
          <span className="scenario-timeline__month" key={month.label} style={{ left: month.left }}>
            {month.label}
          </span>
        ))}
      </div>
      <ol className="scenario-timeline__list">
        {scenarios.map((scenario, index) => (
          <li
            className={scenario.id === selectedId ? "is-selected" : undefined}
            key={scenario.id}
            style={{ "--at": at(toTime(scenario.date)), "--i": index } as React.CSSProperties}
          >
            <span className="scenario-timeline__dot" aria-hidden="true" />
            <time dateTime={scenario.date}>{dayFormat.format(new Date(`${scenario.date}T00:00:00Z`))}</time>
            <strong>{scenario.label}</strong>
            <span className="scenario-timeline__scope">{scenario.merchantCategory} · {scenario.currency}</span>
            <p>{scenario.expectedSignal}</p>
            {scenario.id === selectedId ? <span className="scenario-timeline__tag">Followed below</span> : null}
          </li>
        ))}
      </ol>
      <figcaption>{disclosure}</figcaption>
    </figure>
  );
}
