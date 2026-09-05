import type { ModelDefinition } from "@/lib/project-data";

function Arrow({ pulse = false }: { pulse?: boolean }) {
  return (
    <svg
      className={`architecture-map__arrow diagram-arrow${pulse ? " diagram-arrow--pulse" : ""}`}
      viewBox="0 0 24 24"
      preserveAspectRatio="none"
      aria-hidden="true"
      focusable="false"
    >
      <path d="M3 12h16m-6-7l7 7-7 7" pathLength="1" />
      {pulse && <path className="diagram-arrow__pulse" d="M3 12h16" />}
    </svg>
  );
}

export function ArchitectureDiagram({
  engines,
  models,
}: {
  engines: string[];
  models: ModelDefinition[];
}) {
  return (
    <figure className="architecture-figure">
      <div className="architecture-map" role="img" aria-label="Canonical SQL model chain">
        <div className="architecture-map__sources">
          {engines.map((engine) => <span key={engine}>{engine}</span>)}
        </div>
        <Arrow />
        <div className="architecture-map__models">
          {models.map((model) => (
            <div key={model.name}>
              <code>{model.name}</code>
              <span>{model.grain}</span>
            </div>
          ))}
        </div>
        <Arrow pulse />
        <div className="architecture-map__stage architecture-map__stage--final">
          <strong>Snapshot payload</strong>
          <span>Workbench queries</span>
        </div>
      </div>
      <figcaption>
        The engines execute the same SQL chain. Presentation code consumes model results instead of redefining business rules.
      </figcaption>
    </figure>
  );
}
