import type { ModelDefinition } from "@/lib/project-data";

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
        <span className="architecture-map__arrow" aria-hidden="true">→</span>
        <div className="architecture-map__models">
          {models.map((model) => (
            <div key={model.name}>
              <code>{model.name}</code>
              <span>{model.grain}</span>
            </div>
          ))}
        </div>
        <span className="architecture-map__arrow" aria-hidden="true">→</span>
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
