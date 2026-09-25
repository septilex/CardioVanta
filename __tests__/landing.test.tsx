import React from 'react';
import { render, screen } from '@testing-library/react';
import LandingPage from '../src/app/page';

describe('CardioVanta Landing Page', () => {
  it('renders the landing page with correct institutional headings', () => {
    render(<LandingPage />);
    
    expect(screen.getByText(/Understand the signals behind cardiovascular risk/i)).toBeInTheDocument();
    expect(screen.getByText(/A clearer way to understand the model/i)).toBeInTheDocument();
    expect(screen.getByText(/From measurements to modelled probability/i)).toBeInTheDocument();
    expect(screen.getByText(/Built around clarity/i)).toBeInTheDocument();
    expect(screen.getByText(/Explore your cardiovascular profile/i)).toBeInTheDocument();
    expect(screen.getByText(/A clearer read starts here/i)).toBeInTheDocument();
  });

  it('contains links to the assessment page', () => {
    render(<LandingPage />);
    
    // Check that there are multiple HEART ANALYSIS links pointing to /assessment
    const assessmentLinks = screen.getAllByRole('link', { name: /HEART ANALYSIS/i });
    expect(assessmentLinks.length).toBeGreaterThan(0);
    
    assessmentLinks.forEach(link => {
      expect(link.getAttribute('href')).toBe('/assessment');
    });
  });
});
