import { useMemo, useState } from 'react';
import {
  Search,
  Filter,
  Download,
  TrendingUp,
  Target,
  Clock,
  Building2,
  MapPin,
  Calendar,
  ChevronRight,
  X,
  CheckCircle2,
  XCircle,
} from 'lucide-react';
import type { Tender } from '../types';
import { industries, locations, budgetRanges } from '../mockData';
import { exportToCSV, getMatchBadgeBg, getMatchBgColor } from '../utils/helpers';

interface DashboardProps {
  tenders: Tender[];
  onSelectTender: (tender: Tender) => void;
}

export function Dashboard({ tenders, onSelectTender }: DashboardProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [industry, setIndustry] = useState('All Industries');
  const [location, setLocation] = useState('All Locations');
  const [budget, setBudget] = useState('All Budgets');

  const filtered = useMemo(() => {
    return tenders.filter((t) => {
      const matchesSearch =
        t.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        t.organization.toLowerCase().includes(searchQuery.toLowerCase()) ||
        t.referenceNo.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesIndustry = industry === 'All Industries' || t.industry === industry;
      const matchesLocation = location === 'All Locations' || t.location === location;
      const matchesBudget =
        budget === 'All Budgets' ||
        (budget === 'Under PKR 20M' && t.budget < 20000000) ||
        (budget === 'PKR 20M – 50M' && t.budget >= 20000000 && t.budget < 50000000) ||
        (budget === 'PKR 50M – 100M' && t.budget >= 50000000 && t.budget < 100000000) ||
        (budget === 'PKR 100M – 500M' && t.budget >= 100000000 && t.budget < 500000000) ||
        (budget === 'Over PKR 500M' && t.budget >= 500000000);
      return matchesSearch && matchesIndustry && matchesLocation && matchesBudget;
    });
  }, [tenders, searchQuery, industry, location, budget]);

  const topMatches = filtered.filter((t) => t.matchPercentage >= 80).length;
  const avgMatch = filtered.length > 0 ? Math.round(filtered.reduce((sum, t) => sum + t.matchPercentage, 0) / filtered.length) : 0;
  const closingSoon = filtered.filter((t) => t.daysLeft <= 10).length;

  const sorted = [...filtered].sort((a, b) => b.matchPercentage - a.matchPercentage);
  const activeFilters = industry !== 'All Industries' || location !== 'All Locations' || budget !== 'All Budgets';

  const clearFilters = () => {
    setIndustry('All Industries');
    setLocation('All Locations');
    setBudget('All Budgets');
  };

  return (
    <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-6 animate-fade-in">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-ink">Tender Dashboard</h2>
        <p className="text-sm text-muted mt-1">Discover and track government tenders matched to your company profile</p>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
        <StatCard
          icon={<Target className="h-5 w-5" />}
          label="Top Matches"
          value={String(topMatches)}
          subtitle="Tenders with 80%+ match"
          color="primary"
        />
        <StatCard
          icon={<TrendingUp className="h-5 w-5" />}
          label="Avg Match %"
          value={`${avgMatch}%`}
          subtitle="Across all filtered tenders"
          color="accent"
        />
        <StatCard
          icon={<Clock className="h-5 w-5" />}
          label="Closing Soon"
          value={String(closingSoon)}
          subtitle="Deadlines within 10 days"
          color="warning"
        />
      </div>

      {/* Search + Filters */}
      <div className="bg-card rounded-xl border border-edge shadow-sm p-4 mb-6">
        <div className="relative mb-4">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by title, organization, or reference number..."
            className="w-full pl-11 pr-4 py-2.5 rounded-lg border border-edge text-sm bg-card text-ink focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all"
          />
        </div>

        <div className="flex flex-col sm:flex-row gap-3 items-stretch sm:items-end">
          <div className="flex-1">
            <label className="flex items-center gap-1.5 text-xs font-medium text-muted mb-1.5">
              <Filter className="h-3.5 w-3.5" /> Industry
            </label>
            <select
              value={industry}
              onChange={(e) => setIndustry(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-edge text-sm bg-card text-ink focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all"
            >
              {industries.map((ind) => (
                <option key={ind} value={ind}>{ind}</option>
              ))}
            </select>
          </div>
          <div className="flex-1">
            <label className="flex items-center gap-1.5 text-xs font-medium text-muted mb-1.5">
              <MapPin className="h-3.5 w-3.5" /> Location
            </label>
            <select
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-edge text-sm bg-card text-ink focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all"
            >
              {locations.map((loc) => (
                <option key={loc} value={loc}>{loc}</option>
              ))}
            </select>
          </div>
          <div className="flex-1">
            <label className="flex items-center gap-1.5 text-xs font-medium text-muted mb-1.5">
              <Calendar className="h-3.5 w-3.5" /> Budget Range
            </label>
            <select
              value={budget}
              onChange={(e) => setBudget(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-edge text-sm bg-card text-ink focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all"
            >
              {budgetRanges.map((bgt) => (
                <option key={bgt} value={bgt}>{bgt}</option>
              ))}
            </select>
          </div>
          <div className="flex gap-2">
            {activeFilters && (
              <button
                onClick={clearFilters}
                className="px-3 py-2 rounded-lg border border-edge text-sm text-muted hover:bg-primary-50 transition-colors flex items-center gap-1.5"
              >
                <X className="h-4 w-4" /> Clear
              </button>
            )}
            <button
              onClick={() => exportToCSV(filtered)}
              disabled={filtered.length === 0}
              className="px-4 py-2 rounded-lg bg-primary-500 text-white text-sm font-medium hover:bg-primary-600 transition-colors flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
            >
              <Download className="h-4 w-4" /> Export CSV
            </button>
          </div>
        </div>
      </div>

      {/* Results */}
      <div className="flex items-center justify-between mb-3">
        <p className="text-sm text-muted">
          <span className="font-semibold text-ink">{sorted.length}</span> tender{sorted.length !== 1 ? 's' : ''} found
        </p>
      </div>

      {sorted.length === 0 ? (
        <div className="bg-card rounded-xl border border-edge p-12 text-center">
          <p className="text-muted text-lg">No tenders match your filters</p>
          <p className="text-sm text-muted mt-1">Try adjusting your search or clearing filters</p>
        </div>
      ) : (
        <div className="space-y-3">
          {sorted.map((tender, index) => (
            <TenderCard
              key={tender.id}
              tender={tender}
              onClick={() => onSelectTender(tender)}
              index={index}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function StatCard({
  icon,
  label,
  value,
  subtitle,
  color,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  subtitle: string;
  color: 'primary' | 'accent' | 'warning';
}) {
  const colorMap = {
    primary: 'bg-primary-50 text-primary-700 ring-primary-200',
    accent: 'bg-accent-50 text-accent-700 ring-accent-200',
    warning: 'bg-warning-50 text-warning-700 ring-warning-200',
  };

  return (
    <div className="bg-card rounded-xl border border-edge shadow-sm p-5 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-medium text-muted">{label}</p>
          <p className="text-3xl font-bold text-ink mt-1">{value}</p>
          <p className="text-xs text-muted mt-1">{subtitle}</p>
        </div>
        <div className={`flex h-10 w-10 items-center justify-center rounded-lg ring-1 ${colorMap[color]}`}>
          {icon}
        </div>
      </div>
    </div>
  );
}

function TenderCard({
  tender,
  onClick,
  index,
}: {
  tender: Tender;
  onClick: () => void;
  index: number;
}) {
  const matchBg = getMatchBgColor(tender.matchPercentage);
  const matchBadge = getMatchBadgeBg(tender.matchPercentage);

  return (
    <div
      onClick={onClick}
      className="bg-card rounded-xl border border-edge shadow-sm hover:shadow-md hover:border-primary-300 transition-all duration-200 cursor-pointer group animate-slide-up"
      style={{ animationDelay: `${index * 50}ms` }}
    >
      <div className="p-4 sm:p-5">
        <div className="flex items-start justify-between gap-4 mb-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1.5">
              <span className="text-xs font-medium text-primary-600 bg-primary-50 px-2 py-0.5 rounded">
                {tender.category}
              </span>
              <span className="text-xs text-muted">#{tender.referenceNo}</span>
            </div>
            <h3 className="font-semibold text-ink text-sm sm:text-base leading-snug group-hover:text-primary-700 transition-colors">
              {tender.title}
            </h3>
          </div>
          <div className={`flex-shrink-0 px-2.5 py-1 rounded-lg text-sm font-bold ${matchBadge}`}>
            {tender.matchPercentage}%
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs text-muted mb-3">
          <span className="flex items-center gap-1.5">
            <Building2 className="h-3.5 w-3.5" /> {tender.organization}
          </span>
          <span className="flex items-center gap-1.5">
            <MapPin className="h-3.5 w-3.5" /> {tender.location}
          </span>
          <span className="flex items-center gap-1.5 font-medium text-ink">
            {tender.budgetLabel}
          </span>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex-1">
            <div className="h-2 rounded-full bg-primary-50 overflow-hidden">
              <div
                className={`h-full rounded-full ${matchBg} transition-all duration-500`}
                style={{ width: `${tender.matchPercentage}%` }}
              />
            </div>
          </div>
          <div className="flex items-center gap-3 text-xs">
            {tender.eligibilityStatus === 'eligible' ? (
              <span className="flex items-center gap-1 text-success-600 font-medium">
                <CheckCircle2 className="h-3.5 w-3.5" /> Eligible
              </span>
            ) : (
              <span className="flex items-center gap-1 text-error-500 font-medium">
                <XCircle className="h-3.5 w-3.5" /> Not Eligible
              </span>
            )}
            <span className={`flex items-center gap-1 font-medium ${tender.daysLeft <= 10 ? 'text-warning-600' : 'text-muted'}`}>
              <Clock className="h-3.5 w-3.5" /> {tender.daysLeft}d left
            </span>
            <ChevronRight className="h-4 w-4 text-primary-300 group-hover:text-primary-500 transition-colors" />
          </div>
        </div>
      </div>
    </div>
  );
}
