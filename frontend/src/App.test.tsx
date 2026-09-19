import { render, screen } from '@testing-library/react';
import { useTheme } from '@mui/material/styles';
import { localStorageStore } from 'react-admin';
import { afterEach, expect, it, vi } from 'vitest';
import { App } from './App';

// The grid vendor owns browser rendering tests; this test exercises the real
// React-Admin shell, dashboard, routing registration, and our API status display.
vi.mock('./resources/demo-customers/DemoCustomerList', () => ({
  DemoCustomerList: () => <div>Demo grid route</div>,
}));

// Observe the active theme through MUI's public API, rather than CSS selectors.
vi.mock('./app/Dashboard', async (importOriginal) => {
  const original = await importOriginal<typeof import('./app/Dashboard')>();
  return {
    ...original,
    Dashboard: function DashboardWithThemeProbe() {
      const theme = useTheme();
      return (
        <>
          <output aria-label="Active theme">{theme.palette.mode}</output>
          <original.Dashboard />
        </>
      );
    },
  };
});

afterEach(() => {
  vi.unstubAllGlobals();
  localStorageStore().removeItem('theme');
});

it.each(['system', 'saved'] as const)(
  'keeps the application light with a %s dark preference',
  async (preference) => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('{"status":"ready"}')));
    vi.stubGlobal('matchMedia', (query: string): MediaQueryList => ({
      matches: preference === 'system' && query === '(prefers-color-scheme: dark)',
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(() => true),
    }));
    if (preference === 'saved') localStorageStore().setItem('theme', 'dark');

    render(<App />);

    expect(await screen.findByLabelText('Active theme')).toHaveTextContent('light');
    expect(
      screen.queryByRole('button', { name: /Toggle light\/dark mode/i }),
    ).not.toBeInTheDocument();
  },
);

it('renders LedgerLens and registers the demo resource in the shell', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('{"status":"ready"}')));
  render(<App />);
  expect(await screen.findByRole('heading', { name: 'LedgerLens', level: 1 })).toBeInTheDocument();
  expect(await screen.findByRole('menuitem', { name: 'Demo customers' })).toHaveAttribute(
    'href',
    '#/demo-customers',
  );
  expect(screen.getByRole('link', { name: 'Open demo customers' })).toHaveAttribute(
    'href',
    '#/demo-customers',
  );
  expect(await screen.findByText(/Backend ready/)).toBeInTheDocument();
});

it('shows a failed readiness check without hiding the dashboard', async () => {
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('offline')));
  render(<App />);
  expect(await screen.findByText(/Backend not ready/)).toBeInTheDocument();
  expect(screen.getByRole('heading', { name: 'LedgerLens', level: 1 })).toBeInTheDocument();
});
