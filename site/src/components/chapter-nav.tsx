import Script from "next/script";

const chapters = [
  { id: "overview", label: "Overview" },
  { id: "merchant-flow", label: "Merchant flow" },
  { id: "risk-monitor", label: "Risk monitor" },
  { id: "retention", label: "Retention" },
  { id: "data-model", label: "Data model" },
] as const;

const CHAPTER_NAV_SCRIPT = `
(() => {
  const initialiseChapterNav = () => {
    const navigation = document.querySelector('[data-chapter-navigation]');
    if (!navigation || navigation.__paymentObservatoryBound) return;

    const links = [...navigation.querySelectorAll('a[href^="#"]')];
    const sections = links
      .map((link) => document.querySelector(link.getAttribute('href')))
      .filter(Boolean);
    if (!sections.length) return;

    navigation.__paymentObservatoryBound = true;
    const selectChapter = (id) => {
      links.forEach((link) => {
        if (link.getAttribute('href') === '#' + id) {
          link.setAttribute('aria-current', 'location');
        } else {
          link.removeAttribute('aria-current');
        }
      });
    };

    links.forEach((link) => {
      link.addEventListener('click', () => selectChapter(link.getAttribute('href').slice(1)));
    });

    const observer = new IntersectionObserver((entries) => {
      const visible = entries
        .filter((entry) => entry.isIntersecting)
        .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
      if (visible?.target?.id) selectChapter(visible.target.id);
    }, { rootMargin: '-18% 0px -67%', threshold: [0.1, 0.35, 0.65] });

    sections.forEach((section) => observer.observe(section));
  };

  initialiseChapterNav();
})();
`;

export function ChapterNav() {
  return (
    <>
      <nav className="chapter-nav" aria-label="Case study chapters" data-chapter-navigation>
        <div className="chapter-nav__inner">
          <span className="chapter-nav__label" aria-hidden="true">
            Analysis
          </span>
          <ol className="chapter-nav__list">
            {chapters.map((chapter, index) => (
              <li key={chapter.id}>
                <a
                  href={`#${chapter.id}`}
                  aria-current={index === 0 ? "location" : undefined}
                >
                  <span aria-hidden="true">{String(index + 1).padStart(2, "0")}</span>
                  {chapter.label}
                </a>
              </li>
            ))}
          </ol>
        </div>
      </nav>
      <Script id="chapter-navigation" strategy="afterInteractive">
        {CHAPTER_NAV_SCRIPT}
      </Script>
    </>
  );
}
