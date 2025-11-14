/**
 * Formate un nombre de manière sûre (protège contre undefined/null/NaN)
 */
export function formatNumber(value: any, decimals: number = 2): string {
  const num = typeof value === 'string' ? parseFloat(value) : value;
  if (typeof num !== 'number' || isNaN(num) || num === null || num === undefined) {
    return '0.' + '0'.repeat(decimals);
  }
  return num.toFixed(decimals);
}

/**
 * Formate un montant en euros
 */
export function formatEuro(value: any, decimals: number = 2): string {
  return formatNumber(value, decimals) + '€';
}
