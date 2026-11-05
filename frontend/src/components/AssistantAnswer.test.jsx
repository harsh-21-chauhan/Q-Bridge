import { afterEach, expect, it } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import AssistantAnswer from './AssistantAnswer';

afterEach(cleanup);
const original = `qb_${'a'.repeat(32)}`;
const alternative = `qb_${'b'.repeat(32)}`;

it('renders structured answers and readable experiment references', () => {
  const { container } = render(
    <AssistantAnswer
      text={`**Decision:** Keep the placement.\nEvidence:\n- Compare ${original} with ${alternative}.\nUncertainty:\n- Confidence was not estimated.`}
      trace={[
        {
          tool: 'compare_budget',
          evidence: {
            previous: { experiment_id: original },
            current: { experiment_id: alternative },
          },
        },
      ]}
    />,
  );
  expect(screen.getAllByRole('heading').map((h) => h.textContent)).toEqual([
    'Decision',
    'Evidence',
    'Uncertainty',
  ]);
  expect(screen.getAllByRole('listitem')).toHaveLength(2);
  expect(
    screen.getByText('Compare the original experiment with the budget alternative.'),
  ).toBeTruthy();
  expect(container.textContent).not.toContain('qb_');
});

it('keeps ordinary prose intact and displays HTML as text', () => {
  const { container } = render(
    <AssistantAnswer text={'Evidence suggests caution.\n<img src=x onerror=alert(1)>'} />,
  );
  expect(screen.queryByRole('heading')).toBeNull();
  expect(screen.getByText('Evidence suggests caution.')).toBeTruthy();
  expect(container.querySelector('img')).toBeNull();
  expect(screen.getByText('<img src=x onerror=alert(1)>')).toBeTruthy();
});

it('uses a neutral label for an identifier absent from the tool trace', () => {
  render(<AssistantAnswer text={`See ${original}.`} />);
  expect(screen.getByText('See the referenced experiment.')).toBeTruthy();
});
