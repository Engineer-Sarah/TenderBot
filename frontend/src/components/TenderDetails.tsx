import { useState } from 'react';
import {
  ArrowLeft,
  FileText,
  Download,
  Sparkles,
  CheckCircle2,
  XCircle,
  Building2,
  MapPin,
  Calendar,
  DollarSign,
  FileCheck,
  AlertTriangle,
  PartyPopper,
} from 'lucide-react';
import type { Tender } from '../types';
import { downloadTenderPDF, getMatchBgColor, getMatchTextColor } from '../utils/helpers';

interface TenderDetailsProps {
  tender: Tender;
  onBack: () => void;
  onGoToCompany: () => void;
}

export function TenderDetails({ tender, onBack, onGoToCompany }: TenderDetailsProps) {
  const [downloading, setDownloading] = useState(false);
  const [showCelebration, setShowCelebration] = useState(tender.matchPercentage >= 90);

  const matchedReqs = tender.requirements.filter((r) => r.matched);
  const missingReqs = tender.requirements.filter((r) => !r.matched);
  const matchBg = getMatchBgColor(tender.matchPercentage);
  const matchText = getMatchTextColor(tender.matchPercentage);

  const handleDownload = () => {
    setDownloading(true);
    setTimeout(() => {
      downloadTenderPDF(tender.title);
      setDownloading(false);
    }, 800);
  };

  return (
    <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-6 animate-fade-in">
      {showCelebration && <CelebrationOverlay onClose={() => setShowCelebration(false)} match={tender.matchPercentage} />}

      <button
        onClick={onBack}
        className="flex items-center gap-2 text-sm text-muted hover:text-primary-600 transition-colors mb-4"
      >
        <ArrowLeft className="h-4 w-4" /> Back to Dashboard
      </button>

      {/* Title Section */}
      <div className="bg-card rounded-xl border border-edge shadow-sm p-6 mb-6">
        <div className="flex items-start justify-between gap-4 mb-4">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-xs font-medium text-primary-600 bg-primary-50 px-2 py-0.5 rounded">
                {tender.category}
              </span>
              <span className="text-xs text-muted">#{tender.referenceNo}</span>
              <span className="text-xs text-muted">Published: {tender.publishedDate}</span>
            </div>
            <h2 className="text-xl font-bold text-ink leading-snug">{tender.title}</h2>
            <p className="text-sm text-muted mt-2">{tender.description}</p>
          </div>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-4">
          <InfoTile icon={<Building2 className="h-4 w-4" />} label="Organization" value={tender.organization} />
          <InfoTile icon={<MapPin className="h-4 w-4" />} label="Location" value={tender.location} />
          <InfoTile icon={<DollarSign className="h-4 w-4" />} label="Budget" value={tender.budgetLabel} />
          <InfoTile icon={<Calendar className="h-4 w-4" />} label="Deadline" value={`${tender.deadline} (${tender.daysLeft}d left)`} />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: AI Summary + Match */}
        <div className="lg:col-span-2 space-y-6">
          {/* AI Summary */}
          <div className="bg-gradient-to-br from-primary-50 to-card rounded-xl border border-primary-200 shadow-sm p-6">
            <div className="flex items-center gap-2 mb-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary-500 text-white">
                <Sparkles className="h-4 w-4" />
              </div>
              <h3 className="font-bold text-ink">AI Summary</h3>
              <span className="text-xs text-primary-600 bg-primary-100 px-2 py-0.5 rounded-full">AI Generated</span>
            </div>
            <p className="text-sm text-ink leading-relaxed">{tender.aiSummary}</p>
          </div>

          {tender.coverLetter && (
            <div className="bg-card rounded-xl border border-edge shadow-sm p-6">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-bold text-ink">Cover Letter Draft</h3>
                <button
                  onClick={() => void navigator.clipboard.writeText(tender.coverLetter ?? '')}
                  className="text-xs rounded-lg border border-edge px-3 py-1 text-ink hover:bg-canvas"
                >
                  Copy
                </button>
              </div>
              <p className="text-sm text-ink leading-relaxed whitespace-pre-line">{tender.coverLetter}</p>
            </div>
          )}

          {/* Match Percentage */}
          <div className="bg-card rounded-xl border border-edge shadow-sm p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-bold text-ink">Match Analysis</h3>
              <span
                className={`text-2xl font-bold ${matchText}`}
              >
                {tender.matchPercentage}%
              </span>
            </div>
            <div className="h-3 rounded-full bg-primary-50 overflow-hidden mb-4">
              <div
                className={`h-full rounded-full ${matchBg} transition-all duration-700`}
                style={{ width: `${tender.matchPercentage}%` }}
              />
            </div>

            <div className="flex items-center gap-3 mb-5">
              {tender.eligibilityStatus === 'eligible' ? (
                <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-success-50 text-success-700 text-sm font-medium">
                  <CheckCircle2 className="h-4 w-4" /> Eligible to Apply
                </div>
              ) : (
                <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-error-50 text-error-700 text-sm font-medium">
                  <XCircle className="h-4 w-4" /> Not Eligible
                </div>
              )}
              <span className="text-sm text-muted">
                {matchedReqs.length} of {tender.requirements.length} requirements met
              </span>
            </div>

            {/* Matched Requirements */}
            <div className="mb-4">
              <h4 className="text-xs font-semibold text-success-700 uppercase tracking-wide mb-2 flex items-center gap-1.5">
                <CheckCircle2 className="h-4 w-4" /> Matched Requirements ({matchedReqs.length})
              </h4>
              <div className="space-y-1.5">
                {matchedReqs.map((req) => (
                  <div key={req.id} className="flex items-center gap-2.5 px-3 py-2 rounded-lg bg-success-50/50 border border-success-100">
                    <CheckCircle2 className="h-4 w-4 text-success-500 flex-shrink-0" />
                    <span className="text-sm text-ink">{req.label}</span>
                    <span className="ml-auto text-xs text-muted">{req.category}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Missing Requirements */}
            {missingReqs.length > 0 && (
              <div>
                <h4 className="text-xs font-semibold text-error-700 uppercase tracking-wide mb-2 flex items-center gap-1.5">
                  <AlertTriangle className="h-4 w-4" /> Missing Requirements ({missingReqs.length})
                </h4>
                <div className="space-y-1.5">
                  {missingReqs.map((req) => (
                    <div key={req.id} className="flex items-center gap-2.5 px-3 py-2 rounded-lg bg-error-50/50 border border-error-100">
                      <XCircle className="h-4 w-4 text-error-400 flex-shrink-0" />
                      <span className="text-sm text-ink">{req.label}</span>
                      <span className="ml-auto text-xs text-muted">{req.category}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Documents + Actions */}
        <div className="space-y-6">
          {/* Required Documents */}
          <div className="bg-card rounded-xl border border-edge shadow-sm p-6">
            <div className="flex items-center gap-2 mb-3">
              <FileCheck className="h-5 w-5 text-primary-600" />
              <h3 className="font-bold text-ink">Required Documents</h3>
            </div>
            <div className="space-y-2">
              {tender.documents.map((doc) => (
                <div
                  key={doc.id}
                  className="flex items-center gap-2.5 px-3 py-2.5 rounded-lg border border-edge hover:border-primary-300 hover:bg-primary-50/30 transition-all group cursor-pointer"
                >
                  <FileText className="h-4 w-4 text-muted group-hover:text-primary-500 transition-colors flex-shrink-0" />
                  <span className="text-sm text-ink flex-1 truncate">{doc.name}</span>
                  {doc.required ? (
                    <span className="text-xs text-primary-600 bg-primary-50 px-1.5 py-0.5 rounded">Required</span>
                  ) : (
                    <span className="text-xs text-muted bg-primary-50 px-1.5 py-0.5 rounded">Optional</span>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Actions */}
          <div className="bg-card rounded-xl border border-edge shadow-sm p-6">
            <h3 className="font-bold text-ink mb-3">Actions</h3>
            <button
              onClick={handleDownload}
              disabled={downloading}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-primary-500 text-white text-sm font-medium hover:bg-primary-600 transition-colors disabled:opacity-60 mb-2"
            >
              {downloading ? (
                <>
                  <div className="h-4 w-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Preparing PDF...
                </>
              ) : (
                <>
                  <Download className="h-4 w-4" /> Download Tender PDF
                </>
              )}
            </button>
            <button
              onClick={onGoToCompany}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg border border-edge text-ink text-sm font-medium hover:bg-primary-50 transition-colors"
            >
              <FileCheck className="h-4 w-4" /> Prepare Documents
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function InfoTile({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="flex items-center gap-2.5 px-3 py-2.5 rounded-lg bg-primary-50 border border-primary-100">
      <div className="text-muted flex-shrink-0">{icon}</div>
      <div className="min-w-0">
        <p className="text-xs text-muted">{label}</p>
        <p className="text-sm font-medium text-ink truncate">{value}</p>
      </div>
    </div>
  );
}

function CelebrationOverlay({ onClose, match }: { onClose: () => void; match: number }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm animate-fade-in" onClick={onClose}>
      <div className="bg-card rounded-2xl shadow-2xl p-8 max-w-sm mx-4 text-center animate-scale-in relative overflow-hidden">
        {/* Confetti pieces */}
        {Array.from({ length: 20 }).map((_, i) => (
          <div
            key={i}
            className="absolute w-2 h-2 rounded-sm animate-confetti"
            style={{
              left: `${Math.random() * 100}%`,
              top: `${Math.random() * 30}%`,
              backgroundColor: ['#5A7DA0', '#14b8a6', '#f59e0b', '#22c55e', '#7A9AB5'][i % 5],
              animationDelay: `${Math.random() * 0.5}s`,
              animationDuration: `${0.8 + Math.random() * 0.6}s`,
            }}
          />
        ))}
        <div className="flex h-16 w-16 mx-auto items-center justify-center rounded-full bg-success-100 mb-4 relative z-10">
          <PartyPopper className="h-8 w-8 text-success-600" />
        </div>
        <h3 className="text-xl font-bold text-ink mb-2 relative z-10">Excellent Match!</h3>
        <p className="text-sm text-muted relative z-10">
          This tender has a <span className="font-bold text-success-600">{match}% match</span> with your company profile. You're a strong candidate — consider applying!
        </p>
        <button
          onClick={onClose}
          className="mt-5 px-6 py-2 rounded-lg bg-primary-500 text-white text-sm font-medium hover:bg-primary-600 transition-colors relative z-10"
        >
          View Details
        </button>
      </div>
    </div>
  );
}
