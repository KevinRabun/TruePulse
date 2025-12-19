/**
 * Tests for utility functions
 */
import { cn } from '../utils';

describe('cn (classNames utility)', () => {
  it('combines class names', () => {
    expect(cn('class1', 'class2')).toBe('class1 class2');
  });

  it('handles conditional classes', () => {
    expect(cn('always', false && 'never', true && 'sometimes')).toBe('always sometimes');
  });

  it('handles undefined and null', () => {
    expect(cn('class', undefined, null, 'another')).toBe('class another');
  });

  it('merges Tailwind classes correctly', () => {
    // cn should use tailwind-merge to handle conflicting classes
    const result = cn('px-2 py-1', 'px-4');
    expect(result).toContain('px-4'); // Should keep the later one
    expect(result).toContain('py-1');
  });
});
