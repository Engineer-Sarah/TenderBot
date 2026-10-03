import { useState, useCallback, useMemo, useEffect } from 'react';
import { Loader2, RefreshCw, Sparkles } from 'lucide-react';
import { Header } from '@/components/Header';
import { Dashboard } from '@/components/Dashboard';
import { TenderDetails } from '@/components/TenderDetails';
import { MyCompany } from '@/components/MyCompany';
import { mockTenders, companyProfile, initialUploadedFiles } from '@/mockData';
import { api } from '@/api';
import type { Tender, UploadedFile, AppNotification } from '@/types';

type Tab = 'dashboard' | 'details' | 'company';

function App() {
  const [activeTab, setActiveTab] = useState<Tab>('dashboard');
  const [selectedTender, setSelectedTender] = useState<Tender | null>(null);
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>(initialUploadedFiles);
  // Keep the actual File objects for this browser session so Vercel serverless
  // analysis can index the same PDF in the same request (no /tmp persistence dependency).
  const [companyFiles, setCompanyFiles] = useState<File[]>([]);

  const [readIds, setReadIds] = useState<Set<string>>(new Set());

  // Backend connection: live data when the API is running, demo data otherwise
  const [tenders, setTenders] = useState<Tender[]>(mockTenders);
  const [live, setLive] = useState(false);
  const [connecting, setConnecting] = useState(true);
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadTenders = useCallback(async () => {
    setLoading(true);
    setConnecting(true);
    setError(null);
    try {
      // Health is intentionally checked first so the UI can switch to Live
      // as soon as the Vercel backend wakes up, instead of waiting for the
      // slower tender scraper and document listing.
      await api.health();
      setLive(true);

      try {
        const [list, docs] = await Promise.all([api.tenders('IT'), api.documents().catch(() => null)]);
        if (list.length > 0) setTenders(list);
        if (docs) setUploadedFiles(docs);
      } catch {
        // The backend is connected even if a slower data source temporarily fails.
      }
    } catch {
      setLive(false); // backend not reachable -> keep demo data
    } finally {
      setConnecting(false);
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadTenders();
  }, [loadTenders]);

  const handleAnalyze = useCallback(async () => {
    setAnalyzing(true);
    setError(null);
    try {
      const list = await api.analyze('IT', companyFiles);
      if (list.length > 0) setTenders(list);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'AI analysis failed');
    } finally {
      setAnalyzing(false);
    }
  }, [companyFiles]);

  // Mock tenders se notifications banti hain: deadline qareeb ya high match
  const notifications = useMemo<AppNotification[]>(() => {
    const list: AppNotification[] = [];
    for (const t of tenders) {
      if (t.daysLeft <= 10 && t.matchPercentage >= 60) {
        list.push({
          id: `deadline_${t.id}`,
          type: 'deadline',
          heading: `Closing in ${t.daysLeft} days`,
          message: t.title,
          tenderId: t.id,
          read: readIds.has(`deadline_${t.id}`),
        });
      }
      if (t.matchPercentage >= 90) {
        list.push({
          id: `match_${t.id}`,
          type: 'match',
          heading: `${t.matchPercentage}% match found`,
          message: t.title,
          tenderId: t.id,
          read: readIds.has(`match_${t.id}`),
        });
      }
    }
    return list;
  }, [readIds, tenders]);

  const handleOpenNotification = useCallback((n: AppNotification) => {
    setReadIds((prev) => new Set(prev).add(n.id));
    const tender = tenders.find((t) => t.id === n.tenderId);
    if (tender) {
      setSelectedTender(tender);
      setActiveTab('details');
    }
  }, [tenders]);

  const handleMarkAllRead = useCallback(() => {
    setReadIds(new Set(notifications.map((n) => n.id)));
  }, [notifications]);

  const handleSignOut = useCallback(() => {
    // TODO: yahan real auth (Supabase signOut) connect karna hai
    setSelectedTender(null);
    setActiveTab('dashboard');
  }, []);

  const handleSelectTender = useCallback((tender: Tender) => {
    setSelectedTender(tender);
    setActiveTab('details');
  }, []);

  const handleBack = useCallback(() => {
    setActiveTab('dashboard');
  }, []);

  const handleGoToCompany = useCallback(() => {
    setActiveTab('company');
  }, []);

  const handleAddFiles = useCallback(
    async (files: File[]) => {
      if (live) {
        try {
          setCompanyFiles((prev) => {
            const byName = new Map(prev.map((f) => [f.name, f]));
            files.forEach((f) => byName.set(f.name, f));
            return Array.from(byName.values());
          });
          const results = await api.upload(files);
          const failed = results.filter((r) => r.status !== 'ok');
          if (failed.length) setError(`Upload failed: ${failed.map((f) => f.filename).join(', ')}`);
          const docs = await api.documents();
          // keep real sizes for files uploaded in this session
          setUploadedFiles(
            docs.map((d) => {
              const f = files.find((x) => x.name === d.name);
              return f ? { ...d, size: f.size } : d;
            }),
          );
          return;
        } catch (e) {
          setError(e instanceof Error ? e.message : 'Upload failed');
          return;
        }
      }
      const newFiles: UploadedFile[] = files.map((file, index) => ({
        id: `f_${Date.now()}_${index}`,
        name: file.name,
        size: file.size,
        type: file.type || 'application/octet-stream',
        uploadDate: new Date().toISOString().slice(0, 10),
      }));
      setUploadedFiles((prev) => [...prev, ...newFiles]);
    },
    [live],
  );

  const handleDeleteFile = useCallback(
    async (id: string) => {
      if (live) {
        try {
          await api.deleteDocument(id);
        } catch (e) {
          setError(e instanceof Error ? e.message : 'Delete failed');
          return;
        }
      }
      setUploadedFiles((prev) => prev.filter((f) => f.id !== id));
    },
    [live],
  );

  return (
    <div className="min-h-screen bg-canvas">
      <Header
        activeTab={activeTab}
        onTabChange={setActiveTab}
        selectedTenderTitle={selectedTender?.title}
        notifications={notifications}
        onOpenNotification={handleOpenNotification}
        onMarkAllRead={handleMarkAllRead}
        companyName={companyProfile.name}
        onSignOut={handleSignOut}
      />

      <main>
        {activeTab === 'dashboard' && (
          <>
            <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 pt-4 flex flex-wrap items-center gap-3 text-sm">
              <span
                className={`rounded-full px-3 py-1 text-xs font-medium ${
                  connecting
                    ? 'bg-amber-100 text-amber-800'
                    : live
                      ? 'bg-green-100 text-green-800'
                      : 'bg-amber-100 text-amber-800'
                }`}
              >
                {connecting ? 'Connecting to backend...' : live ? 'Live data from backend' : 'Demo data - backend not running'}
              </span>
              {live && (
                <>
                  <button
                    onClick={() => void loadTenders()}
                    disabled={loading || analyzing}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-edge bg-card px-3 py-1.5 text-ink hover:bg-canvas disabled:opacity-50"
                  >
                    <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} /> Refresh
                  </button>
                  <button
                    onClick={() => void handleAnalyze()}
                    disabled={loading || analyzing}
                    className="inline-flex items-center gap-1.5 rounded-lg bg-ink px-3 py-1.5 text-white hover:opacity-90 disabled:opacity-50"
                  >
                    {analyzing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                    {analyzing ? 'Analyzing (1-5 min)...' : 'Run AI analysis'}
                  </button>
                </>
              )}
              {error && <span className="text-red-600">{error}</span>}
            </div>
            <Dashboard tenders={tenders} onSelectTender={handleSelectTender} />
          </>
        )}

        {activeTab === 'details' && selectedTender && (
          <TenderDetails
            tender={selectedTender}
            onBack={handleBack}
            onGoToCompany={handleGoToCompany}
          />
        )}

        {activeTab === 'company' && (
          <MyCompany
            profile={companyProfile}
            uploadedFiles={uploadedFiles}
            onAddFiles={handleAddFiles}
            onDeleteFile={handleDeleteFile}
          />
        )}
      </main>

      <footer className="border-t border-edge bg-card">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-4">
          <p className="text-center text-xs text-muted">
            TenderBot Pakistan &middot; Smart Tender Matching for Pakistani Businesses
          </p>
        </div>
      </footer>
    </div>
  );
}

export default App;
