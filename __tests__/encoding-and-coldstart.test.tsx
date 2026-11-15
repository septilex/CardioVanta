/**
 * Regression tests for the 2026-11-15 audit:
 * - contract 2.1.0 patient-matched labels for restecg, slope and thal, shown in clinical order;
 * - the source data's missing-value codes (ca 4, thal 0) are not offered as findings;
 * - the defaults describe a normal resting ECG, upsloping ST segment and normal thallium scan;
 * - the page wakes the serverless model on open, without sending clinical data.
 */
import React from 'react';
import { render, screen, within } from '@testing-library/react';
import Page, { initialData } from '../src/app/assessment/page';
import { warmUpPredictionService } from '../src/lib/api';
import { CATEGORICAL_LABELS } from '../src/types/generated-features';

jest.mock('../src/lib/predictionAvailability', () => ({
  ...jest.requireActual('../src/lib/predictionAvailability'),
  PREDICTION_AVAILABILITY: { enabled: true, notice: 'unused' },
}));

jest.mock('../src/lib/api', () => ({
  predict: jest.fn(),
  warmUpPredictionService: jest.fn(),
  ApiError: class ApiError extends Error {},
}));

const optionTexts = (id: string) =>
  within(document.getElementById(id) as HTMLElement)
    .getAllByRole('option')
    .map((o) => o.textContent);

describe('Categorical encoding (contract 2.1.0)', () => {
  it('labels the training codes with their patient-matched meaning', () => {
    expect(CATEGORICAL_LABELS.restecg).toEqual({ 0: 'Left Ventricular Hypertrophy', 1: 'Normal', 2: 'ST-T Wave Abnormality' });
    expect(CATEGORICAL_LABELS.slope).toEqual({ 0: 'Downsloping', 1: 'Flat', 2: 'Upsloping' });
    expect(CATEGORICAL_LABELS.thal).toEqual({ 0: 'Not recorded', 1: 'Fixed Defect', 2: 'Normal', 3: 'Reversible Defect' });
  });

  it('lists options in clinical order, normal finding first, and sends the training code', () => {
    render(<Page />);
    expect(optionTexts('restecg')).toEqual(['Normal', 'ST-T Wave Abnormality', 'Left Ventricular Hypertrophy']);
    expect(optionTexts('slope')).toEqual(['Upsloping', 'Flat', 'Downsloping']);
    expect(optionTexts('thal')).toEqual(['Normal', 'Fixed Defect', 'Reversible Defect']);
    const normalEcg = within(document.getElementById('restecg') as HTMLElement).getByRole('option', { name: 'Normal' });
    expect((normalEcg as HTMLOptionElement).value).toBe('1');
  });

  it('does not offer missing-value codes as findings', () => {
    render(<Page />);
    expect(optionTexts('ca')).toEqual(['0', '1', '2', '3']);
    expect(optionTexts('thal')).not.toContain('Not recorded');
  });

  it('defaults to normal findings', () => {
    expect(CATEGORICAL_LABELS.restecg[initialData.restecg]).toBe('Normal');
    expect(CATEGORICAL_LABELS.slope[initialData.slope]).toBe('Upsloping');
    expect(CATEGORICAL_LABELS.thal[initialData.thal]).toBe('Normal');
    expect(initialData.oldpeak).toBe(0);
  });
});

describe('Cold start', () => {
  it('wakes the prediction service when the page opens', () => {
    render(<Page />);
    expect(warmUpPredictionService).toHaveBeenCalled();
  });
});
