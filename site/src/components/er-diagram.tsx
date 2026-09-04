import type { SourceEntity, SourceRelationship } from "@/lib/project-data";

export function ErDiagram({
  entities,
  relationships,
}: {
  entities: SourceEntity[];
  relationships: SourceRelationship[];
}) {
  return (
    <figure className="er-figure">
      <div className="entity-map" aria-label="Settlement reconciliation source model">
        {entities.map((entity) => (
          <article
            className={`entity-node${entity.name === "transactions" ? " entity-node--core" : ""}`}
            key={entity.name}
          >
            <p>{entity.role}</p>
            <h3>{entity.name}</h3>
            <dl>
              <div><dt>Grain</dt><dd>{entity.grain}</dd></div>
              <div><dt>Key</dt><dd><code>{entity.key}</code></dd></div>
            </dl>
          </article>
        ))}
      </div>
      <div className="relationship-list" aria-label="Source relationships">
        {relationships.map((relationship) => (
          <p key={`${relationship.from}-${relationship.to}`}>
            <code>{relationship.from}</code>
            <span aria-hidden="true">→</span>
            <code>{relationship.to}</code>
            <strong>{relationship.cardinality}</strong>
            <span>{relationship.note}</span>
          </p>
        ))}
      </div>
      <figcaption>
        The event spine, effective merchant term, and recorded settlement remain separate evidence before the reconciliation models join them.
      </figcaption>
    </figure>
  );
}
