export function formatIDR(n: number): string {
  return "Rp " + n.toLocaleString("id-ID");
}

export function formatIDRShort(n: number): string {
  if (n >= 1_000_000) return `Rp ${(n / 1_000_000).toFixed(1)} jt`;
  if (n >= 1_000) return `Rp ${(n / 1_000).toFixed(0)}k`;
  return formatIDR(n);
}
