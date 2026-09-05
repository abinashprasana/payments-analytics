import type { NavigationItem } from "@/lib/project-data";

const CHAPTER_NAV_SCRIPT = `
(() => {
  // Fragment navigation needs exact section heights. Expand the contained
  // chapters before the parser performs an initial deep-link jump.
  if (window.location.hash) {
    document.documentElement.classList.add('case-study-expanded');
  }

  const bindNavigation = () => {
    const navigation = document.querySelector('[data-case-navigation]');
    if (!navigation || navigation.dataset.bound === 'true') return;

    const links = [...navigation.querySelectorAll('a[href^="#"]')];
    const sections = links
      .map((link) => document.querySelector(link.getAttribute('href')))
      .filter(Boolean);
    if (!sections.length) return;

    navigation.dataset.bound = 'true';
    const select = (id) => links.forEach((link) => {
      link.toggleAttribute('aria-current', link.getAttribute('href') === '#' + id);
      if (link.hasAttribute('aria-current')) link.setAttribute('aria-current', 'location');
    });
    const selectFragment = () => {
      const id = decodeURIComponent(window.location.hash.slice(1));
      if (sections.some((section) => section.id === id)) select(id);
    };

    document.querySelectorAll('a[href^="#"]').forEach((link) => {
      link.addEventListener('click', () => {
        document.documentElement.classList.add('case-study-expanded');
        if (link.hash) select(link.hash.slice(1));
      });
    });
    const observer = new IntersectionObserver((entries) => {
      const visible = entries
        .filter((entry) => entry.isIntersecting)
        .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
      if (visible?.target?.id) select(visible.target.id);
    }, { rootMargin: '-18% 0px -66%', threshold: [0.1, 0.35, 0.65] });
    sections.forEach((section) => observer.observe(section));
    window.addEventListener('hashchange', selectFragment);
    requestAnimationFrame(selectFragment);
    window.setTimeout(selectFragment, 250);
  };

  const REVEAL_SELECTOR = '.case-section, .trace-card, .workbench-preview, .handoff, ' +
    '.er-figure, .architecture-figure, .metric-ledger, .quality-ledger, .final-cta';

  const bindReveal = () => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const targets = [...document.querySelectorAll(REVEAL_SELECTOR)];
    if (!targets.length) return;
    const style = document.createElement('style');
    style.textContent =
      '[data-reveal]{opacity:0;transform:translateY(16px);' +
      'transition:opacity .5s ease-out,transform .5s ease-out}' +
      // Bars grow from zero on reveal. The target width already sits in the
      // inline width style; this only layers a scaleX grow on top, so a
      // no-JS or reduced-motion visitor still sees the correct bar at full
      // size immediately -- nothing here can leave a bar stuck invisible.
      '.coverage-chart__track i,.exception-bars__track i{' +
      'transform:scaleX(0);transform-origin:left;' +
      'transition:transform .7s cubic-bezier(.2,.6,.2,1)}' +
      '[data-reveal].is-revealed .coverage-chart__track i,' +
      '[data-reveal].is-revealed .exception-bars__track i{transform:scaleX(1)}' +
      // Connector paths draw on reveal. Default state (before this rule
      // exists) is a plain solid stroke with zero dashoffset, i.e. fully
      // drawn -- so this can only ever animate a reveal, never hide a
      // connector permanently.
      '[data-reveal]:not(.is-revealed) .diagram-arrow > path:first-child{' +
      'stroke-dasharray:1;stroke-dashoffset:1}' +
      '[data-reveal].is-revealed .diagram-arrow > path:first-child{' +
      'stroke-dashoffset:0;transition:stroke-dashoffset .9s cubic-bezier(.4,0,.2,1)}';
    document.head.appendChild(style);
    targets.forEach((el) => el.setAttribute('data-reveal', ''));
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add('is-revealed');
        observer.unobserve(entry.target);
      });
    }, { rootMargin: '0px 0px -10% 0px', threshold: 0.1 });
    targets.forEach((el) => observer.observe(el));
  };

  const init = () => {
    bindNavigation();
    bindReveal();
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init, { once: true });
  } else {
    init();
  }
})();
`;

export function ChapterNav({ items }: { items: NavigationItem[] }) {
  return (
    <>
      <nav className="chapter-nav" aria-label="Investigation chapters" data-case-navigation>
        <div className="chapter-nav__inner">
          <span className="chapter-nav__label" aria-hidden="true">Walkthrough</span>
          <ol className="chapter-nav__list">
            {items.map((item) => (
              <li key={item.id}>
                <a href={`#${item.id}`}>{item.label}</a>
              </li>
            ))}
          </ol>
        </div>
      </nav>
      <script
        id="case-study-navigation"
        data-static-behavior="chapter-navigation"
        dangerouslySetInnerHTML={{ __html: CHAPTER_NAV_SCRIPT }}
      />
    </>
  );
}
