export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function getMatchColor(percentage: number): string {
  if (percentage >= 80) return 'success';
  if (percentage >= 60) return 'warning';
  return 'error';
}

export function getMatchBgColor(percentage: number): string {
  if (percentage >= 80) return 'bg-success-500';
  if (percentage >= 60) return 'bg-warning-500';
  return 'bg-error-500';
}

export function getMatchTextColor(percentage: number): string {
  if (percentage >= 80) return 'text-success-700';
  if (percentage >= 60) return 'text-warning-700';
  return 'text-error-700';
}

export function getMatchBadgeBg(percentage: number): string {
  if (percentage >= 80) return 'bg-success-100 text-success-700';
  if (percentage >= 60) return 'bg-warning-100 text-warning-700';
  return 'bg-error-100 text-error-700';
}

export function exportToCSV(
  tenders: Array<{
    title: string;
    organization: string;
    industry: string;
    location: string;
    budgetLabel: string;
    deadline: string;
    daysLeft: number;
    matchPercentage: number;
    referenceNo: string;
    category: string;
  }>
): void {
  const headers = [
    'Reference No',
    'Title',
    'Organization',
    'Category',
    'Industry',
    'Location',
    'Budget',
    'Deadline',
    'Days Left',
    'Match %',
  ];

  const rows = tenders.map((t) => [
    t.referenceNo,
    `"${t.title.replace(/"/g, '""')}"`,
    t.organization,
    t.category,
    t.industry,
    t.location,
    t.budgetLabel,
    t.deadline,
    String(t.daysLeft),
    String(t.matchPercentage),
  ]);

  const csv = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `tenderbot_export_${new Date().toISOString().slice(0, 10)}.csv`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export function downloadTenderPDF(tenderTitle: string): void {
  const content = `TENDERBOT PAKISTAN - TENDER DETAILS REPORT
==========================================

Tender: ${tenderTitle}
Generated: ${new Date().toLocaleString()}

This is a simulated PDF export for demonstration purposes.
In production, this would generate a formatted PDF document
containing full tender details, requirements, and match analysis.
`;
  const blob = new Blob([content], { type: 'application/pdf' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `${tenderTitle.slice(0, 40).replace(/[^a-zA-Z0-9]/g, '_')}.pdf`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
