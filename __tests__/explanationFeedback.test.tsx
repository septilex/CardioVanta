/**
 * Result-page feedback control: create (POST), change (PATCH) and withdraw (DELETE) one anonymous feedback document.
 */
import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import ExplanationFeedback from '../src/app/assessment/ExplanationFeedback';
import { ApiError, createFeedback, deleteFeedback, updateFeedback } from '../src/lib/api';

jest.mock('../src/lib/api', () => {
  const actual = jest.requireActual('../src/lib/api');
  return { ...actual, createFeedback: jest.fn(), updateFeedback: jest.fn(), deleteFeedback: jest.fn() };
});
const mockCreate = createFeedback as jest.MockedFunction<typeof createFeedback>;
const mockUpdate = updateFeedback as jest.MockedFunction<typeof updateFeedback>;
const mockDelete = deleteFeedback as jest.MockedFunction<typeof deleteFeedback>;

const CREATED = {
  id: '65a0000000000000000000aa', helpful: true, section: 'why' as const, model_version: '1.1.1',
  created_at: '2026-11-26T10:00:00+00:00', updated_at: '2026-11-26T10:00:00+00:00', edit_token: 'tok-123',
};

beforeEach(() => jest.resetAllMocks());

it('creates, changes and withdraws feedback with the one-time edit token', async () => {
  mockCreate.mockResolvedValueOnce(CREATED);
  mockUpdate.mockResolvedValueOnce({ ...CREATED, helpful: false });
  mockDelete.mockResolvedValueOnce(undefined);
  render(<ExplanationFeedback section="why" modelVersion="1.1.1" />);

  fireEvent.click(screen.getByRole('button', { name: 'Yes' }));
  expect(await screen.findByText(/marked this explanation as helpful/)).toBeInTheDocument();
  expect(mockCreate).toHaveBeenCalledWith(true, 'why', '1.1.1');

  fireEvent.click(screen.getByRole('button', { name: 'Change to not helpful' }));
  expect(await screen.findByText(/marked this explanation as not helpful/)).toBeInTheDocument();
  expect(mockUpdate).toHaveBeenCalledWith(CREATED.id, 'tok-123', false);
  expect(mockCreate).toHaveBeenCalledTimes(1);                 // a change is an update, never a second document

  fireEvent.click(screen.getByRole('button', { name: 'Remove my feedback' }));
  expect(await screen.findByText('Your feedback was removed.')).toBeInTheDocument();
  expect(mockDelete).toHaveBeenCalledWith(CREATED.id, 'tok-123');
  expect(screen.getByRole('button', { name: 'Yes' })).toBeEnabled();
});

it('says feedback is unavailable when the store is not configured', async () => {
  mockCreate.mockRejectedValueOnce(new ApiError('not configured', 503, 'feedback_store_not_configured'));
  render(<ExplanationFeedback section="summary" modelVersion="1.1.1" />);
  fireEvent.click(screen.getByRole('button', { name: 'No' }));
  expect(await screen.findByText(/isn.t available right now/)).toBeInTheDocument();
});

it('lets the person retry after a failed save', async () => {
  mockCreate.mockRejectedValueOnce(new TypeError('Failed to fetch'));
  render(<ExplanationFeedback section="summary" modelVersion="1.1.1" />);
  fireEvent.click(screen.getByRole('button', { name: 'Yes' }));
  expect(await screen.findByText(/didn't save/)).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Yes' })).toBeEnabled();
});
