import React, { useState, useEffect } from 'react';
import { X, Clock, Trash2, FileText, Calendar } from 'lucide-react';
import { SessionSummary, SessionListResponse } from '../types';

interface SessionPanelProps {
  isOpen: boolean;
  onClose: () => void;
  onLoadSession: (sessionId: number) => void;
  apiEndpoint: string;
  currentDentistName?: string;
}

const CACHE_KEY = 'medvox-sessions-cache';
const CACHE_TTL = 24 * 60 * 60 * 1000; // 24 hours

interface SessionCache {
  sessions: SessionSummary[];
  lastFetched: string;
}

function getCachedSessions(): SessionSummary[] | null {
  try {
    const cached = localStorage.getItem(CACHE_KEY);
    if (!cached) return null;

    const { sessions, lastFetched }: SessionCache = JSON.parse(cached);
    const cacheAge = Date.now() - new Date(lastFetched).getTime();

    if (cacheAge > CACHE_TTL) {
      localStorage.removeItem(CACHE_KEY);
      return null;
    }

    return sessions;
  } catch {
    return null;
  }
}

function setCachedSessions(sessions: SessionSummary[]): void {
  const cache: SessionCache = {
    sessions,
    lastFetched: new Date().toISOString(),
  };
  localStorage.setItem(CACHE_KEY, JSON.stringify(cache));
}

export const SessionPanel: React.FC<SessionPanelProps> = ({
  isOpen,
  onClose,
  onLoadSession,
  apiEndpoint,
  currentDentistName,
}) => {
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      fetchSessions();
    }
  }, [isOpen]);

  const fetchSessions = async () => {
    setLoading(true);
    setError(null);

    // Try cache first (with dentist-specific key)
    const cacheKey = currentDentistName ? `${CACHE_KEY}-${currentDentistName}` : CACHE_KEY;
    const cached = localStorage.getItem(cacheKey);
    if (cached) {
      try {
        const { sessions, lastFetched }: SessionCache = JSON.parse(cached);
        const cacheAge = Date.now() - new Date(lastFetched).getTime();
        if (cacheAge <= CACHE_TTL) {
          console.log('📦 Using cached sessions for:', currentDentistName);
          setSessions(sessions);
          setLoading(false);
          return;
        }
      } catch {
        localStorage.removeItem(cacheKey);
      }
    }

    try {
      // Build URL with dentist filter
      const url = new URL(`${apiEndpoint}/documentation/sessions`, window.location.origin);
      url.searchParams.append('limit', '50');
      if (currentDentistName) {
        // Map dentist name to email format used in backend
        const dentistEmail = `${currentDentistName}@medvox.local`;
        url.searchParams.append('dentist_email', dentistEmail);
        console.log('🔍 Fetching sessions for dentist:', currentDentistName, 'email:', dentistEmail);
      }

      console.log('🌐 Fetching:', url.toString());
      const response = await fetch(url.toString());

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data: SessionListResponse = await response.json();
      console.log('✅ Received sessions:', data.sessions.length);
      setSessions(data.sessions);

      // Cache with dentist-specific key
      const cache: SessionCache = {
        sessions: data.sessions,
        lastFetched: new Date().toISOString(),
      };
      localStorage.setItem(cacheKey, JSON.stringify(cache));
    } catch (err) {
      console.error('Failed to fetch sessions:', err);
      setError('Fehler beim Laden der Behandlungen');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (sessionId: number) => {
    if (!confirm('Möchten Sie diese Behandlung wirklich löschen?')) {
      return;
    }

    try {
      const response = await fetch(`${apiEndpoint}/documentation/sessions/${sessionId}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      // Optimistic update
      setSessions((prev) => prev.filter((s) => s.id !== sessionId));

      // Update cache
      const updated = sessions.filter((s) => s.id !== sessionId);
      setCachedSessions(updated);
    } catch (err) {
      console.error('Failed to delete session:', err);
      alert('Fehler beim Löschen der Behandlung');
      // Refresh on error to show actual state
      fetchSessions();
    }
  };

  const handleLoad = (sessionId: number) => {
    onLoadSession(sessionId);
    onClose();
  };

  // Group sessions by date
  const groupedSessions = sessions.reduce((groups, session) => {
    const date = new Date(session.created_at).toLocaleDateString('de-DE', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });

    if (!groups[date]) {
      groups[date] = [];
    }
    groups[date].push(session);
    return groups;
  }, {} as Record<string, SessionSummary[]>);

  // Close on Escape
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    if (isOpen) window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <>
      {/* Overlay */}
      <div className="overlay" onClick={onClose} />

      {/* Panel */}
      <div className="slide-panel">
        <div className="flex flex-col h-full">
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-5 border-b border-gray-100">
            <div className="flex items-center gap-3">
              <Clock className="h-5 w-5 text-dental-primary" />
              <h2 className="text-lg font-semibold text-gray-900">Behandlungen</h2>
            </div>
            <button onClick={onClose} className="btn-icon">
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Body */}
          <div className="flex-1 overflow-y-auto px-6 py-6">
            {loading && (
              <div className="flex items-center justify-center py-12">
                <div className="text-center">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-dental-primary mx-auto mb-2" />
                  <p className="text-sm text-gray-500">Lade Behandlungen...</p>
                </div>
              </div>
            )}

            {error && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-800">
                {error}
                <button
                  onClick={fetchSessions}
                  className="ml-2 underline hover:no-underline"
                >
                  Erneut versuchen
                </button>
              </div>
            )}

            {!loading && !error && sessions.length === 0 && (
              <div className="text-center py-12">
                <FileText className="h-12 w-12 text-gray-300 mx-auto mb-3" />
                <p className="text-gray-500">Keine Behandlungen gefunden</p>
                <p className="text-sm text-gray-400 mt-1">
                  Aufnahmen werden hier angezeigt
                </p>
              </div>
            )}

            {!loading && !error && sessions.length > 0 && (
              <div className="space-y-6">
                {Object.entries(groupedSessions).map(([date, dateSessions]) => (
                  <div key={date}>
                    <div className="flex items-center gap-2 mb-3">
                      <Calendar className="h-4 w-4 text-gray-400" />
                      <h3 className="text-sm font-medium text-gray-700">{date}</h3>
                    </div>

                    <div className="space-y-2">
                      {dateSessions.map((session) => (
                        <SessionCard
                          key={session.id}
                          session={session}
                          onLoad={() => handleLoad(session.id)}
                          onDelete={() => handleDelete(session.id)}
                        />
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
};

interface SessionCardProps {
  session: SessionSummary;
  onLoad: () => void;
  onDelete: () => void;
}

const SessionCard: React.FC<SessionCardProps> = ({ session, onLoad, onDelete }) => {
  const time = new Date(session.created_at).toLocaleTimeString('de-DE', {
    hour: '2-digit',
    minute: '2-digit',
  });

  const modeLabel = session.processing_mode === 'with_billing' ? 'Mit Abrechnung' : 'Nur Transkription';
  const modeColor = session.processing_mode === 'with_billing' ? 'bg-green-100 text-green-800' : 'bg-blue-100 text-blue-800';

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 hover:border-dental-primary hover:shadow-sm transition-all group">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0" onClick={onLoad} role="button" tabIndex={0}>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-medium text-gray-500">{time}</span>
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${modeColor}`}>
              {modeLabel}
            </span>
          </div>

          {session.patient_id && (
            <div className="text-xs text-gray-500 mb-1">
              Patient: {session.patient_id}
            </div>
          )}

          <p className="text-sm text-gray-700 line-clamp-2 mb-2">
            {session.transcription_preview || 'Keine Transkription'}
          </p>

          {session.billing_codes_count > 0 && (
            <div className="text-xs text-dental-primary font-medium">
              {session.billing_codes_count} Abrechnungsposition{session.billing_codes_count !== 1 ? 'en' : ''}
            </div>
          )}
        </div>

        <button
          onClick={(e) => {
            e.stopPropagation();
            onDelete();
          }}
          className="btn-icon opacity-0 group-hover:opacity-100 transition-opacity"
          title="Löschen"
        >
          <Trash2 className="h-4 w-4 text-red-600" />
        </button>
      </div>
    </div>
  );
};
