import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import AIExplanation from '../src/app/assessment/AIExplanation';
import { aiEnabled, explainResult, minimizeResult } from '../src/lib/aiExplanation';
import type { PredictResponse } from '../src/types';
jest.mock('../src/lib/aiExplanation', () => ({ ...jest.requireActual('../src/lib/aiExplanation'), aiEnabled: jest.fn(), explainResult: jest.fn() }));
const result = { explanation_token: "signed-capability", prediction: { probability: 0.4, outcome: 'significant_obstructive_cad_present' }, explanation: { contributions: { age: 0.2 } } } as PredictResponse;
beforeEach(() => { jest.clearAllMocks(); (aiEnabled as jest.Mock).mockResolvedValue(true); });
test('disabled availability', async () => {
  (aiEnabled as jest.Mock).mockResolvedValue(false);
  render(<AIExplanation result={result} />);
  expect(screen.getByRole('button')).toBeDisabled();
});
test('loading, failure, retry and success preserve result', async () => {
  let reject!: (e: Error) => void;
  (explainResult as jest.Mock).mockImplementationOnce(() => new Promise((_, no) => { reject = no; }));
  const before = JSON.stringify(result);
  render(<><p>Original prediction: 40%</p><AIExplanation result={result} /></>);
  await waitFor(() => expect(screen.getByRole('button')).toBeEnabled());
  fireEvent.click(screen.getByRole('button'));
  expect(screen.getByRole('status')).toHaveTextContent('Generating');
  reject(new Error('unavailable'));
  expect(await screen.findByRole('alert')).toBeVisible();
  expect(screen.getByText('Original prediction: 40%')).toBeVisible();
  (explainResult as jest.Mock).mockResolvedValue({ summary: 'Simple explanation', prediction_interpretation: 'Estimate only', contributing_factors: [], limitations: ['Uncertain'], disclaimer: 'Educational', recommended_next_step: 'Discuss with a clinician', prompt_version: 'explanation-v1' });
  fireEvent.click(screen.getByRole('button', { name: 'Retry AI explanation' }));
  expect(await screen.findByText('Simple explanation')).toBeVisible();
  expect(explainResult).toHaveBeenCalledTimes(2);
  expect(JSON.stringify(result)).toBe(before);
});
test('request contains only derived fields, no keys or raw values', () => {
  const data = minimizeResult(result);
  expect(data).toEqual({ token: 'signed-capability' });
  expect(JSON.stringify(data)).not.toMatch(/api_key|patient|probability|0.2/);
});
