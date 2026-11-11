/**
 * Phase 10 production-incident containment. Predictions were re-enabled after the corrected (R0.3)
 * serving code was deployed, so the shipped switch (configs/prediction_service.json) is open. The
 * contained behaviour is still tested here with the switch closed for this file only.
 */
import React from 'react';
import { render, screen } from '@testing-library/react';
import AssessmentPage from '../src/app/assessment/page';
import LandingPage from '../src/app/page';
import { predict, ApiError } from '../src/lib/api';
import {
  PREDICTION_AVAILABILITY,
  DEFAULT_UNAVAILABLE_NOTICE,
  UNAVAILABLE_CODE,
  resolvePredictionAvailability,
} from '../src/lib/predictionAvailability';
import serviceConfig from '../configs/prediction_service.json';
import type { PredictRequest } from '../src/types';

jest.mock('../src/lib/predictionAvailability', () => ({
  ...jest.requireActual('../src/lib/predictionAvailability'),
  PREDICTION_AVAILABILITY: {
    enabled: false,
    notice:
      'CardioVanta predictions are temporarily unavailable while we verify the prediction service. No risk estimate can currently be generated.',
  },
}));

const NOTICE =
  'CardioVanta predictions are temporarily unavailable while we verify the prediction service. No risk estimate can currently be generated.';

const HIGH: PredictRequest = {
  age: 67, sex: 1, cp: 0, trestbps: 160, chol: 286, fbs: 0, restecg: 0,
  thalach: 108, exang: 1, oldpeak: 3, slope: 1, ca: 3, thal: 3,
};

describe('Shipped switch', () => {
  it('ships with predictions enabled and the agreed notice', () => {
    const actual = jest.requireActual('../src/lib/predictionAvailability');
    expect(serviceConfig.predictions_enabled).toBe(true);
    expect(actual.PREDICTION_AVAILABILITY).toEqual({ enabled: true, notice: NOTICE });
  });
});

describe('Prediction containment (switch closed)', () => {
  const realFetch = global.fetch;
  let fetchMock: jest.Mock;

  beforeEach(() => {
    fetchMock = jest.fn();
    global.fetch = fetchMock as unknown as typeof fetch;
  });

  afterEach(() => {
    global.fetch = realFetch;
  });

  it('uses the agreed notice while closed', () => {
    expect(PREDICTION_AVAILABILITY).toEqual({ enabled: false, notice: NOTICE });
  });

  it('shows the unavailability notice instead of the assessment form', () => {
    const { container } = render(<AssessmentPage />);

    expect(screen.getByRole('heading', { level: 1, name: /Predictions are temporarily unavailable/i })).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent(NOTICE);
    expect(screen.getByRole('link', { name: /Return to the home page/i })).toHaveAttribute('href', '/');

    // no form, no inputs, no submit control: nothing can be entered or submitted
    expect(container.querySelector('form')).toBeNull();
    expect(container.querySelectorAll('input, select, textarea')).toHaveLength(0);
    expect(screen.queryByRole('button')).toBeNull();
    expect(screen.queryByLabelText(/Age/i)).toBeNull();
    expect(screen.queryByLabelText(/Chest Pain Type/i)).toBeNull();
  });

  it('displays no probability or risk estimate', () => {
    const { container } = render(<AssessmentPage />);
    const text = container.textContent ?? '';
    expect(text).not.toMatch(/\d+(\.\d+)?\s?%/);
    expect(text).not.toMatch(/0\.\d{3,}/);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('blocks prediction requests in the API client without contacting the server', async () => {
    const attempt = predict(HIGH);
    await expect(attempt).rejects.toBeInstanceOf(ApiError);
    await expect(predict(HIGH)).rejects.toMatchObject({ message: NOTICE, status: 503, code: UNAVAILABLE_CODE });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('keeps the landing page and its links working', () => {
    render(<LandingPage />);
    expect(screen.getByText(/Understand the signals behind cardiovascular risk/i)).toBeInTheDocument();
    const links = screen.getAllByRole('link', { name: /HEART ANALYSIS/i });
    expect(links.length).toBeGreaterThan(0);
    links.forEach(link => expect(link.getAttribute('href')).toBe('/assessment'));
  });
});

describe('Prediction availability switch is fail-safe', () => {
  it.each([
    ['missing value', {}],
    ['string "true"', { predictions_enabled: 'true' }],
    ['number 1', { predictions_enabled: 1 }],
    ['null', { predictions_enabled: null }],
    ['false', { predictions_enabled: false }],
    ['not an object', [true]],
    ['null config', null],
    ['string config', 'predictions_enabled'],
  ])('stays disabled for %s', (_label, raw) => {
    expect(resolvePredictionAvailability(raw).enabled).toBe(false);
  });

  it('enables only for exactly true', () => {
    expect(resolvePredictionAvailability({ predictions_enabled: true }).enabled).toBe(true);
  });

  it.each([[undefined], [''], ['   '], [42]])('falls back to the default notice for %p', notice => {
    expect(resolvePredictionAvailability({ predictions_enabled: false, notice }).notice).toBe(DEFAULT_UNAVAILABLE_NOTICE);
    expect(DEFAULT_UNAVAILABLE_NOTICE).toBe(NOTICE);
  });
});

describe('API client when the web app is enabled but the API is contained', () => {
  it('surfaces the API notice and code from the structured 503', async () => {
    let isolatedPredict: typeof predict | undefined;
    jest.isolateModules(() => {
      jest.doMock('../src/lib/predictionAvailability', () => ({
        ...jest.requireActual('../src/lib/predictionAvailability'),
        PREDICTION_AVAILABILITY: { enabled: true, notice: NOTICE },
      }));
      // eslint-disable-next-line @typescript-eslint/no-require-imports
      isolatedPredict = require('../src/lib/api').predict;
    });
    const realFetch = global.fetch;
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      status: 503,
      json: async () => ({ detail: NOTICE, code: UNAVAILABLE_CODE, predictions_available: false }),
    }) as unknown as typeof fetch;
    try {
      await expect(isolatedPredict!(HIGH)).rejects.toMatchObject({ message: NOTICE, status: 503, code: UNAVAILABLE_CODE });
    } finally {
      global.fetch = realFetch;
    }
  });
});
