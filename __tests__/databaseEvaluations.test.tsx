/**
 * Research page section that loads PostgreSQL JOIN results in a useEffect.
 */
import React from 'react';
import { render, screen } from '@testing-library/react';
import { DatabaseEvaluations } from '../src/components/research/DatabaseEvaluations';
import { ApiError, fetchResearchEvaluations, type ResearchEvaluations } from '../src/lib/api';

jest.mock('../src/lib/api', () => {
  const actual = jest.requireActual('../src/lib/api');
  return { ...actual, fetchResearchEvaluations: jest.fn() };
});
const mockFetch = fetchResearchEvaluations as jest.MockedFunction<typeof fetchResearchEvaluations>;

const DATA: ResearchEvaluations = {
  evaluations: [
    { version: '1.1.0', serialization: 'joblib', cohort: 'cleveland_dev', cohort_name: 'Cleveland Clinic development rows',
      cohort_role: 'development', n_patients: 242, method: 'nested CV, 20 repeats (H2.1)', evaluated_on: '2026-11-01',
      source: 'reports/h2_1_calibration_confirmation.md', metric: 'calibration_slope', value: 1.003 },
  ],
  version_coverage: [
    { version: '1.1.0', serialization: 'joblib', calibration: 'pooled', evaluation_count: 1, cohorts: ['cleveland_dev'] },
    { version: '1.1.1', serialization: 'portable_json', calibration: 'pooled', evaluation_count: 0, cohorts: [] },
  ],
  unevaluated_cohorts: [{ code: 'hungary', name: 'Hungarian Institute of Cardiology', country: 'Hungary', n_patients: 294, role: 'external' }],
};

beforeEach(() => mockFetch.mockReset());

it('shows a loading state, then the joined rows and the gaps', async () => {
  mockFetch.mockResolvedValueOnce(DATA);
  render(<DatabaseEvaluations />);
  expect(screen.getByRole('status')).toHaveTextContent(/Loading evaluations/);
  expect(await screen.findByRole('rowheader', { name: 'Calibration slope' })).toBeInTheDocument();
  expect(screen.getByText('1.003')).toBeInTheDocument();
  expect(screen.getByText(/Model 1\.1\.1 has no evaluations of its own/)).toBeInTheDocument();
  expect(screen.getByText(/Hungarian Institute of Cardiology \(294 patients\)/)).toBeInTheDocument();
  expect(mockFetch).toHaveBeenCalledTimes(1);
});

it('explains when the database is not connected', async () => {
  mockFetch.mockRejectedValueOnce(new ApiError('not configured', 503, 'research_database_not_configured'));
  render(<DatabaseEvaluations />);
  expect(await screen.findByText(/not connected in this environment/)).toBeInTheDocument();
});

it('shows a generic message for other failures', async () => {
  mockFetch.mockRejectedValueOnce(new TypeError('Failed to fetch'));
  render(<DatabaseEvaluations />);
  expect(await screen.findByText(/could not be loaded right now/)).toBeInTheDocument();
});

it('cancels the request when the reader leaves the page', () => {
  let signal: AbortSignal | undefined;
  mockFetch.mockImplementationOnce((s) => {
    signal = s;
    return new Promise(() => {});
  });
  const { unmount } = render(<DatabaseEvaluations />);
  expect(signal?.aborted).toBe(false);
  unmount();
  expect(signal?.aborted).toBe(true);
});
