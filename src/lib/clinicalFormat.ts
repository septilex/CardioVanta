/**
 * Plain-language wording for a modelled probability ("About 12 in 100").
 *
 * Hoisting: `NO_ESTIMATE` below is built while this module is being evaluated, by calling
 * `describeEstimate`, whose declaration appears further down the file. That works only because
 * function declarations are hoisted: the whole function is created when the module scope is set up,
 * before any line runs. Had `describeEstimate` been written as `const describeEstimate = () => …`,
 * the same call would throw a ReferenceError, because `const` and `let` bindings exist from the start
 * of the scope but cannot be read until their line has run (the "temporal dead zone").
 * `__tests__/clinicalFormat.test.ts` demonstrates both behaviours.
 */

export interface EstimateText {
  /** The probability as a percentage with one decimal, e.g. "12.3", or "--" when there is none. */
  percentText: string;
  /** Whole people out of 100, clamped to 0-100, or null when there is no estimate. */
  inHundred: number | null;
  /** The headline before "in 100", e.g. "About 12", "Fewer than 1" or "--". */
  headline: string;
}

/** Wording shown while there is no estimate. Evaluated at module load, before the declarations below. */
export const NO_ESTIMATE: Readonly<EstimateText> = Object.freeze(describeEstimate(null));

/** Wording for one modelled probability (0 to 1). Missing or non-finite values give `NO_ESTIMATE`'s text. */
export function describeEstimate(probability: number | null | undefined): EstimateText {
  if (probability == null || !Number.isFinite(probability)) {
    return { percentText: "--", inHundred: null, headline: "--" };
  }
  const inHundred = outOfHundred(probability);
  return { percentText: percentText(probability), inHundred, headline: headlineFor(inHundred) };
}

/** Whole people out of 100, clamped so rounding can never show more than 100 or less than 0. */
function outOfHundred(probability: number): number {
  return Math.min(100, Math.max(0, Math.round(probability * 100)));
}

function headlineFor(inHundred: number): string {
  return inHundred === 0 ? "Fewer than 1" : `About ${inHundred}`;
}

function percentText(probability: number): string {
  return (probability * 100).toFixed(1);
}
