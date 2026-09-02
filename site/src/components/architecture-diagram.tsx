const sources = ["PostgreSQL", "Repository CSV"];

export function ArchitectureDiagram() {
  return (
    <figure className="architecture-figure">
      <div className="architecture-map" role="img" aria-label="PostgreSQL or repository CSV data enters one normalization and analytics path before the Observatory interface">
        <div className="architecture-map__sources">
          {sources.map((source) => (
            <span key={source}>{source}</span>
          ))}
        </div>
        <span className="architecture-map__arrow" aria-hidden="true">→</span>
        <div className="architecture-map__stage">
          <span>Source loader</span>
          <small>bounded fallback</small>
        </div>
        <span className="architecture-map__arrow" aria-hidden="true">→</span>
        <div className="architecture-map__stage">
          <span>Normalization</span>
          <small>shared types</small>
        </div>
        <span className="architecture-map__arrow" aria-hidden="true">→</span>
        <div className="architecture-map__stage architecture-map__stage--final">
          <span>Observatory</span>
          <small>one analytical path</small>
        </div>
      </div>
      <figcaption>
        Database access changes the source, not the calculation contract. CSV fallback feeds the same normalization, filters, and analytical functions.
      </figcaption>
    </figure>
  );
}
