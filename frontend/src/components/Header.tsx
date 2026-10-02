import { useEffect, useRef, useState } from 'react';
import { Bot, Bell, User, Clock, Sparkles, Building2, FileText, LogOut, CheckCheck } from 'lucide-react';
import type { AppNotification } from '@/types';

type Tab = 'dashboard' | 'details' | 'company';

interface HeaderProps {
  activeTab: Tab;
  onTabChange: (tab: Tab) => void;
  selectedTenderTitle?: string;
  notifications: AppNotification[];
  onOpenNotification: (notification: AppNotification) => void;
  onMarkAllRead: () => void;
  companyName: string;
  onSignOut: () => void;
}

type Menu = 'bell' | 'admin' | null;

export function Header({
  activeTab,
  onTabChange,
  selectedTenderTitle,
  notifications,
  onOpenNotification,
  onMarkAllRead,
  companyName,
  onSignOut,
}: HeaderProps) {
  const [openMenu, setOpenMenu] = useState<Menu>(null);
  const bellRef = useRef<HTMLDivElement>(null);
  const adminRef = useRef<HTMLDivElement>(null);

  const unreadCount = notifications.filter((n) => !n.read).length;

  const tabs: Array<{ id: Tab; label: string; disabled?: boolean }> = [
    { id: 'dashboard', label: 'Dashboard' },
    { id: 'details', label: 'Tender Details', disabled: !selectedTenderTitle },
    { id: 'company', label: 'My Company' },
  ];

  // Bahar click ya Escape par dropdown band
  useEffect(() => {
    if (!openMenu) return;

    const handleClick = (e: MouseEvent) => {
      const ref = openMenu === 'bell' ? bellRef : adminRef;
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpenMenu(null);
      }
    };
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpenMenu(null);
    };

    document.addEventListener('mousedown', handleClick);
    document.addEventListener('keydown', handleKey);
    return () => {
      document.removeEventListener('mousedown', handleClick);
      document.removeEventListener('keydown', handleKey);
    };
  }, [openMenu]);

  const toggle = (menu: Exclude<Menu, null>) =>
    setOpenMenu((current) => (current === menu ? null : menu));

  return (
    <header className="sticky top-0 z-40 bg-header text-white shadow-lg shadow-header/20">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/10 ring-1 ring-white/20">
              <Bot className="h-6 w-6 text-white" />
            </div>
            <div>
              <h1 className="text-lg font-bold leading-tight">TenderBot</h1>
              <p className="text-xs text-primary-200 leading-tight">Pakistan</p>
            </div>
          </div>

          <nav className="hidden sm:flex items-center gap-1">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                disabled={tab.disabled}
                onClick={() => onTabChange(tab.id)}
                className={[
                  'px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200',
                  tab.disabled
                    ? 'text-white/40 cursor-not-allowed'
                    : activeTab === tab.id
                    ? 'bg-white text-primary-700 shadow-md'
                    : 'text-primary-100 hover:bg-white/10',
                ].join(' ')}
              >
                {tab.label}
              </button>
            ))}
          </nav>

          <div className="flex items-center gap-3">
            {/* ---------- Bell / Notifications ---------- */}
            <div className="relative" ref={bellRef}>
              <button
                onClick={() => toggle('bell')}
                aria-label="Notifications"
                aria-haspopup="true"
                aria-expanded={openMenu === 'bell'}
                className={[
                  'relative p-2 rounded-lg transition-colors',
                  openMenu === 'bell' ? 'bg-white/20' : 'hover:bg-white/10',
                ].join(' ')}
              >
                <Bell className="h-5 w-5" />
                {unreadCount > 0 && (
                  <span className="absolute -top-0.5 -right-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-accent-400 px-1 text-[10px] font-bold leading-none text-primary-950 ring-2 ring-header">
                    {unreadCount}
                  </span>
                )}
              </button>

              {openMenu === 'bell' && (
                <div className="absolute right-0 mt-2 w-80 max-w-[calc(100vw-2rem)] origin-top-right overflow-hidden rounded-xl border border-edge bg-card text-ink shadow-xl animate-fade-in">
                  <div className="flex items-center justify-between border-b border-edge px-4 py-3">
                    <h3 className="text-sm font-semibold">Notifications</h3>
                    {unreadCount > 0 && (
                      <button
                        onClick={onMarkAllRead}
                        className="flex items-center gap-1 text-xs font-medium text-primary-600 hover:text-primary-800"
                      >
                        <CheckCheck className="h-3.5 w-3.5" />
                        Mark all read
                      </button>
                    )}
                  </div>

                  <div className="max-h-96 overflow-y-auto">
                    {notifications.length === 0 ? (
                      <p className="px-4 py-8 text-center text-sm text-muted">No notifications</p>
                    ) : (
                      <ul className="divide-y divide-edge">
                        {notifications.map((n) => (
                          <li key={n.id}>
                            <button
                              onClick={() => {
                                setOpenMenu(null);
                                onOpenNotification(n);
                              }}
                              className={[
                                'flex w-full items-start gap-3 px-4 py-3 text-left transition-colors hover:bg-primary-50',
                                n.read ? '' : 'bg-primary-50/60',
                              ].join(' ')}
                            >
                              <span
                                className={[
                                  'mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full',
                                  n.type === 'deadline'
                                    ? 'bg-warning-100 text-warning-700'
                                    : 'bg-success-100 text-success-700',
                                ].join(' ')}
                              >
                                {n.type === 'deadline' ? (
                                  <Clock className="h-4 w-4" />
                                ) : (
                                  <Sparkles className="h-4 w-4" />
                                )}
                              </span>
                              <span className="min-w-0 flex-1">
                                <span className="flex items-center gap-2">
                                  <span className="text-sm font-medium">{n.heading}</span>
                                  {!n.read && (
                                    <span className="h-1.5 w-1.5 rounded-full bg-accent-500" />
                                  )}
                                </span>
                                <span className="mt-0.5 line-clamp-2 block text-xs text-muted">
                                  {n.message}
                                </span>
                              </span>
                            </button>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* ---------- Admin menu ---------- */}
            <div className="relative pl-3 border-l border-white/20" ref={adminRef}>
              <button
                onClick={() => toggle('admin')}
                aria-haspopup="true"
                aria-expanded={openMenu === 'admin'}
                className={[
                  'flex items-center gap-2 rounded-lg px-2 py-1 transition-colors',
                  openMenu === 'admin' ? 'bg-white/20' : 'hover:bg-white/10',
                ].join(' ')}
              >
                <div className="hidden md:block text-right">
                  <p className="text-sm font-medium">TechVision</p>
                  <p className="text-xs text-primary-200">Admin</p>
                </div>
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-white/10 ring-1 ring-white/20">
                  <User className="h-4 w-4" />
                </div>
              </button>

              {openMenu === 'admin' && (
                <div className="absolute right-0 mt-2 w-60 origin-top-right overflow-hidden rounded-xl border border-edge bg-card text-ink shadow-xl animate-fade-in">
                  <div className="border-b border-edge px-4 py-3">
                    <p className="truncate text-sm font-semibold">{companyName}</p>
                    <p className="text-xs text-muted">Administrator</p>
                  </div>
                  <div className="py-1">
                    <button
                      onClick={() => {
                        setOpenMenu(null);
                        onTabChange('company');
                      }}
                      className="flex w-full items-center gap-3 px-4 py-2.5 text-left text-sm hover:bg-primary-50"
                    >
                      <Building2 className="h-4 w-4 text-primary-500" />
                      Company Profile
                    </button>
                    <button
                      onClick={() => {
                        setOpenMenu(null);
                        onTabChange('company');
                      }}
                      className="flex w-full items-center gap-3 px-4 py-2.5 text-left text-sm hover:bg-primary-50"
                    >
                      <FileText className="h-4 w-4 text-primary-500" />
                      My Documents
                    </button>
                  </div>
                  <div className="border-t border-edge py-1">
                    <button
                      onClick={() => {
                        setOpenMenu(null);
                        onSignOut();
                      }}
                      className="flex w-full items-center gap-3 px-4 py-2.5 text-left text-sm text-error-600 hover:bg-error-50"
                    >
                      <LogOut className="h-4 w-4" />
                      Sign out
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="sm:hidden flex items-center gap-1 pb-2">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              disabled={tab.disabled}
              onClick={() => onTabChange(tab.id)}
              className={[
                'flex-1 px-3 py-1.5 rounded-lg text-xs font-medium transition-all',
                tab.disabled
                  ? 'text-white/40 cursor-not-allowed'
                  : activeTab === tab.id
                  ? 'bg-white text-primary-700'
                  : 'text-primary-100 hover:bg-white/10',
              ].join(' ')}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>
    </header>
  );
}
