/**
 * Returns a "yyyy-mm" representation of a given combination of year and month.
 */
export function format_yyyy_mm(year: number, month: number): string {
  const yearStr = year.toString().padStart(4, '0');
  const monthStr = month.toString().padStart(2, '0');
  return `${yearStr}-${monthStr}`;
}

