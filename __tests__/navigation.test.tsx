/**
 * The four app sections are real, linked pages: the sidebar and mobile bar link to each one,
 * the active section is marked, and the Research and About pages render their content.
 */
import React from 'react';
import { render, screen, within } from '@testing-library/react';
import { AppSidebar, MobileNav, NAV_ITEMS } from '../src/components/shell/AppNav';
import ResearchPage from '../src/app/research/page';
import AboutPage from '../src/app/about/page';

let mockPath = '/';
jest.mock('next/navigation', () => ({
  ...jest.requireActual('next/navigation'),
  usePathname: () => mockPath,
}));

const EXPECTED = [
  ['Overview', '/'],
  ['Heart Analysis', '/assessment'],
  ['Research', '/research'],
  ['About', '/about'],
] as const;

describe('Sidebar navigation', () => {
  it('links every section to its route (no inert items)', () => {
    render(<AppSidebar />);
    const nav = screen.getByRole('navigation', { name: 'Main Navigation' });
    const links = within(nav).getAllByRole('link');
    expect(links.map((l) => [l.textContent, l.getAttribute('href')])).toEqual(EXPECTED);
    expect(nav.querySelectorAll('div.ax-nav-item')).toHaveLength(0);
  });

  it.each([
    ['/assessment', 'Heart Analysis'],
    ['/research', 'Research'],
    ['/about', 'About'],
  ])('marks %s as the current page', (path, label) => {
    mockPath = path;
    render(<AppSidebar />);
    const nav = screen.getByRole('navigation', { name: 'Main Navigation' });
    const current = within(nav).getAllByRole('link').filter((l) => l.getAttribute('aria-current') === 'page');
    expect(current.map((l) => l.textContent)).toEqual([label]);
    expect(current[0]).toHaveClass('ax-nav-active');
  });

  it('does not mark Overview as current inside the app', () => {
    mockPath = '/research';
    render(<AppSidebar />);
    expect(screen.getByRole('link', { name: 'Overview' })).not.toHaveAttribute('aria-current');
  });

  it('offers the same four sections on narrow screens', () => {
    mockPath = '/about';
    render(<MobileNav />);
    const nav = screen.getByRole('navigation', { name: 'Sections' });
    const links = within(nav).getAllByRole('link');
    expect(links.map((l) => [l.textContent, l.getAttribute('href')])).toEqual(EXPECTED);
    expect(within(nav).getByRole('link', { name: 'About' })).toHaveAttribute('aria-current', 'page');
  });

  it('keeps the section list in one place', () => {
    expect(NAV_ITEMS.map((i) => [i.label, i.href])).toEqual(EXPECTED);
  });
});

describe('Research page', () => {
  beforeEach(() => {
    mockPath = '/research';
  });

  it('renders the evidence sections', () => {
    render(<ResearchPage />);
    expect(screen.getByRole('heading', { level: 1, name: 'Research & Evidence' })).toBeInTheDocument();
    for (const name of [
      'An auditable model, not a black box',
      'What has been done, in order',
      'How the training recipe performs on its own data',
      'Reading a probability and its explanation',
      'Where the evidence stops',
      'Read the sources',
    ]) {
      expect(screen.getByRole('heading', { level: 2, name })).toBeInTheDocument();
    }
  });

  it('reports the H2.1 figures exactly as published, framed as development-cohort results', () => {
    render(<ResearchPage />);
    const table = screen.getByRole('table');
    const row = (name: string) => within(table).getByRole('row', { name: new RegExp(`^${name}`) });
    expect(row('ROC-AUC')).toHaveTextContent('0.911');
    expect(row('Calibration slope')).toHaveTextContent('1.267');
    expect(row('Calibration slope')).toHaveTextContent('1.003');
    expect(row('Brier score')).toHaveTextContent('0.117');
    expect(row('Log loss')).toHaveTextContent('0.380');
    expect(screen.getByText(/These are development-cohort results, not external validation/)).toBeInTheDocument();
  });

  it('links every source to a file in the project repository, opening in a new tab', () => {
    render(<ResearchPage />);
    const docs = screen.getByRole('heading', { level: 2, name: 'Read the sources' }).closest('section')!;
    const links = within(docs).getAllByRole('link');
    expect(links.length).toBeGreaterThanOrEqual(10);
    for (const link of links) {
      expect(link.getAttribute('href')).toMatch(/^https:\/\/github\.com\/septilex\/CardioVanta\/blob\//);
      expect(link).toHaveAttribute('target', '_blank');
      expect(link.getAttribute('rel')).toContain('noopener');
    }
  });
});

describe('About page', () => {
  beforeEach(() => {
    mockPath = '/about';
  });

  it('renders identity, workflow and the intended-use statement', () => {
    render(<AboutPage />);
    expect(screen.getByRole('heading', { level: 1, name: 'About CardioVanta' })).toBeInTheDocument();
    expect(screen.getByText('Know the risk. Know the why. Know how far to trust it.')).toBeInTheDocument();
    const flow = screen.getByRole('heading', { level: 2, name: 'From measurements to an explained estimate' }).closest('section')!;
    expect(within(flow).getAllByRole('listitem').map((li) => li.querySelector('h3')?.textContent)).toEqual([
      'Clinical inputs',
      'Feature processing',
      'Machine-learning model',
      'Probability estimation',
      'Explanation',
    ]);
    expect(
      screen.getByText(/not clinically validated and must not be used for diagnosis, treatment decisions or emergency medical decisions/)
    ).toBeInTheDocument();
  });

  it('links on to Research, Heart Analysis and Overview', () => {
    render(<AboutPage />);
    const next = screen.getByRole('navigation', { name: 'Continue' });
    expect(within(next).getAllByRole('link').map((l) => l.getAttribute('href'))).toEqual(['/research', '/assessment', '/']);
  });
});
