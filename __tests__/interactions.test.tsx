/**
 * Interaction states added by the motion redesign: loading, error + retry, the API's containment
 * response, the results tabs (keyboard), returning to the form, and hidden steps staying out of
 * the keyboard order. The containment switch is opened for this file only, as in page.test.tsx;
 * the shipped closed state is covered by containment.test.tsx.
 */
import React from 'react';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import { MotionGlobalConfig } from 'framer-motion';
import Page from '../src/app/assessment/page';
import { predict, ApiError } from '../src/lib/api';
import type { PredictResponse } from '../src/types';

jest.mock('../src/lib/predictionAvailability', () => ({
  ...jest.requireActual('../src/lib/predictionAvailability'),
  PREDICTION_AVAILABILITY: { enabled: true, notice: 'test notice' },
}));

jest.mock('../src/lib/api', () => ({
  predict: jest.fn(),
  ApiError: class ApiError extends Error {
    status?: number;
    code?: string;
    constructor(msg: string, status?: number, code?: string) {
      super(msg);
      this.status = status;
      this.code = code;
    }
  },
}));

const mockPredict = predict as jest.MockedFunction<typeof predict>;

const contributions = {
  age: 0.12, sex: 0.3, cp: -0.45, trestbps: 0.05, chol: -0.02, fbs: 0.01, restecg: 0.04,
  thalach: -0.2, exang: 0.15, oldpeak: 0.22, slope: -0.08, ca: 0.33, thal: -0.1,
};

const RESPONSE: PredictResponse = {
  prediction: { probability: 0.2984019984, threshold_applied: null, class: null, threshold_status: 'no_validated_production_threshold_configured' },
  development_range_warning: { outside_development_range: false, features: [], note: null },
  explanation: { intercept: -0.5, contributions, decision_function_log_odds: -0.85, note: 'Audit note for test' },
  shap_equivalent_explanation: { expected_value: -0.4, contributions, decision_function_log_odds: -0.85, note: 'shap note' },
  metadata: { package_version: '1.0', model_type: 'LogisticRegression', calibration_method: 'Platt' },
};

beforeAll(() => {
  MotionGlobalConfig.skipAnimations = true;
});
afterAll(() => {
  MotionGlobalConfig.skipAnimations = false;
});
beforeEach(() => {
  jest.clearAllMocks();
});

/** Goes to the last step, as a person would, before generating. */
function openLastStep() {
  fireEvent.click(screen.getByRole('button', { name: /04 Diagnostic Markers/i }));
}

async function generate() {
  openLastStep();
  fireEvent.click(screen.getByRole('button', { name: /Generate Analysis/i }));
  await screen.findByRole('tablist', { name: /Result views/i });
}

describe('Loading state', () => {
  it('marks the form busy and announces that it is waiting, without inventing progress', async () => {
    mockPredict.mockImplementationOnce(() => new Promise(() => {}));
    const { container } = render(<Page />);
    openLastStep();
    expect(screen.getByRole('status')).toHaveTextContent(/All 13 inputs ready/i);
    fireEvent.click(screen.getByRole('button', { name: /Generate Analysis/i }));

    expect(container.querySelector('form')).toHaveAttribute('aria-busy', 'true');
    expect(screen.getByRole('status')).toHaveTextContent(/Waiting for the model/i);
    expect(container.textContent).not.toMatch(/\d+\s?%/);
  });
});

describe('Errors', () => {
  it('keeps the message on screen and retries the same request on "Try again"', async () => {
    mockPredict.mockRejectedValueOnce(new ApiError('Backend is down', 500)).mockResolvedValueOnce(RESPONSE);
    render(<Page />);
    fireEvent.click(screen.getByRole('button', { name: /Generate Analysis/i }));

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('Backend is down');
    fireEvent.click(within(alert).getByRole('button', { name: /Try again/i }));

    await screen.findByRole('tablist', { name: /Result views/i });
    expect(mockPredict).toHaveBeenCalledTimes(2);
    expect(mockPredict.mock.calls[1][0]).toEqual(mockPredict.mock.calls[0][0]);
  });

  it('treats the API containment response as a pause: notice shown, no retry offered', async () => {
    mockPredict.mockRejectedValueOnce(
      new ApiError('Predictions are paused (test).', 503, 'predictions_temporarily_unavailable')
    );
    render(<Page />);
    fireEvent.click(screen.getByRole('button', { name: /Generate Analysis/i }));

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('Predictions are paused (test).');
    expect(within(alert).queryByRole('button')).toBeNull();
  });
});

describe('Results panel', () => {
  it('shows exactly the returned probability (text for assistive technology and the sentence)', async () => {
    mockPredict.mockResolvedValueOnce(RESPONSE);
    render(<Page />);
    await generate();

    const summary = screen.getByRole('tabpanel', { name: /Result/i });
    expect(within(summary).getAllByText('29.8%').length).toBeGreaterThanOrEqual(2);
    expect(summary).toHaveTextContent('No validated decision threshold is configured. Probability only.');
  });

  it('supports arrow keys, Home and End with a roving tab index; inactive panels are hidden', async () => {
    mockPredict.mockResolvedValueOnce(RESPONSE);
    render(<Page />);
    await generate();

    const tabs = screen.getAllByRole('tab');
    expect(tabs.map((t) => t.textContent)).toEqual(['Result', 'Why', 'Technical audit']);
    expect(tabs.map((t) => t.tabIndex)).toEqual([0, -1, -1]);

    tabs[0].focus();
    fireEvent.keyDown(tabs[0], { key: 'ArrowRight' });
    await waitFor(() => expect(screen.getByRole('tab', { name: 'Why' })).toHaveAttribute('aria-selected', 'true'));
    expect(document.activeElement).toBe(screen.getByRole('tab', { name: 'Why' }));
    expect(screen.getByRole('tab', { name: 'Why' }).tabIndex).toBe(0);
    expect(document.getElementById('ax-tabpanel-summary')).toHaveAttribute('hidden');
    expect(document.getElementById('ax-tabpanel-why')).not.toHaveAttribute('hidden');

    fireEvent.keyDown(document.activeElement as Element, { key: 'End' });
    await waitFor(() => expect(screen.getByRole('tab', { name: 'Technical audit' })).toHaveAttribute('aria-selected', 'true'));

    fireEvent.keyDown(document.activeElement as Element, { key: 'ArrowRight' });
    await waitFor(() => expect(screen.getByRole('tab', { name: 'Result' })).toHaveAttribute('aria-selected', 'true'));

    fireEvent.keyDown(document.activeElement as Element, { key: 'Home' });
    expect(screen.getByRole('tab', { name: 'Result' })).toHaveAttribute('aria-selected', 'true');
  });

  it('returns to the form with the same inputs, and can reopen the last result', async () => {
    mockPredict.mockResolvedValueOnce(RESPONSE);
    render(<Page />);
    fireEvent.change(screen.getByLabelText(/Age/i), { target: { value: '61' } });
    await generate();

    fireEvent.click(screen.getByRole('button', { name: /Edit inputs/i }));
    await waitFor(() => expect(screen.getByLabelText(/Age/i)).toHaveValue(61));

    fireEvent.click(screen.getByRole('button', { name: /View last result/i }));
    await screen.findByRole('tablist', { name: /Result views/i });
    expect(mockPredict).toHaveBeenCalledTimes(1);
  });
});

describe('Keyboard order', () => {
  it('keeps hidden steps and the hidden submit buttons out of the tab order', () => {
    const { container } = render(<Page />);
    const grids = container.querySelectorAll('.ax-fields-grid');
    expect(grids).toHaveLength(4);
    expect(grids[0]).not.toHaveAttribute('inert');
    [grids[1], grids[2], grids[3]].forEach((g) => expect(g).toHaveAttribute('inert'));
    expect(container.querySelector('.ax-final-btn-group')).toHaveAttribute('inert');

    fireEvent.click(screen.getByRole('button', { name: /04 Diagnostic Markers/i }));
    expect(grids[3]).not.toHaveAttribute('inert');
    expect(grids[0]).toHaveAttribute('inert');
    expect(container.querySelector('.ax-final-btn-group')).not.toHaveAttribute('inert');
  });
});
