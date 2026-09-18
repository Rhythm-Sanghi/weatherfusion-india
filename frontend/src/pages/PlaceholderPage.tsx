type PlaceholderPageProps = {
  title: string;
  description: string;
  phase: string;
};

export function PlaceholderPage({ title, description, phase }: PlaceholderPageProps) {
  return (
    <section className="page-panel" aria-labelledby="page-title">
      <p className="eyebrow">{phase}</p>
      <h2 id="page-title">{title}</h2>
      <p>{description}</p>
      <div className="placeholder-grid" aria-hidden="true">
        <div />
        <div />
        <div />
      </div>
    </section>
  );
}
