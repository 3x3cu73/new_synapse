import React, { useMemo, useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import FullCalendar from '@fullcalendar/react';
import dayGridPlugin from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import listPlugin from '@fullcalendar/list';
import interactionPlugin from '@fullcalendar/interaction';
import api from '../api/axios';
import Loader from '../components/UI/Loader';
import {
  Star, MessageSquare, Calendar as CalendarIcon, Download, Link,
  Trash2, Copy, Check, X, MapPin, Clock, ChevronRight, Sparkles
} from 'lucide-react';
import { formatDate } from '../utils/dateUtils';
import FeedbackCard from '../components/Events/FeedbackCard';
import toast from 'react-hot-toast';

const EVENT_PALETTE = [
  { bg: 'rgba(90, 159, 207, 0.18)', border: '#5a9fcf', text: '#7eb8e0' },
  { bg: 'rgba(90, 158, 111, 0.18)', border: '#5a9e6f', text: '#7ec492' },
  { bg: 'rgba(212, 162, 74, 0.18)', border: '#d4a24a', text: '#e0b86a' },
  { bg: 'rgba(180, 120, 200, 0.16)', border: '#a87cc4', text: '#c4a0d8' },
  { bg: 'rgba(90, 180, 180, 0.16)', border: '#4eb0b0', text: '#7ad0d0' },
  { bg: 'rgba(216, 93, 76, 0.14)', border: '#d85d4c', text: '#e8887a' },
];

const colorForKey = (key = '') => {
  let hash = 0;
  for (let i = 0; i < key.length; i++) hash = (hash * 31 + key.charCodeAt(i)) >>> 0;
  return EVENT_PALETTE[hash % EVENT_PALETTE.length];
};

const formatTime = (iso) => {
  if (!iso) return '';
  try {
    return new Intl.DateTimeFormat('en-IN', {
      timeZone: 'Asia/Kolkata',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    }).format(new Date(iso));
  } catch {
    return '';
  }
};

const StudentDashboard = () => {
  const navigate = useNavigate();
  const calendarRef = useRef(null);
  const [loading, setLoading] = useState(true);
  const [calendarEvents, setCalendarEvents] = useState([]);
  const [rawEvents, setRawEvents] = useState([]);
  const [recommendations, setRecommendations] = useState([]);
  const [feedbackNeeded, setFeedbackNeeded] = useState([]);
  const [recsLoading, setRecsLoading] = useState(true);
  const [feedbackLoading, setFeedbackLoading] = useState(true);

  const [syncLink, setSyncLink] = useState('');
  const [copied, setCopied] = useState(false);
  const [syncLoading, setSyncLoading] = useState(false);
  const [showSyncModal, setShowSyncModal] = useState(false);

  useEffect(() => {
    fetchCalendar();
    fetchRecommendations();
    fetchFeedback();
  }, []);

  const fetchCalendar = async () => {
    try {
      setLoading(true);
      const calRes = await api.get('/user/calendar');
      const events = Array.isArray(calRes.data) ? calRes.data : [];
      setRawEvents(events);
      const formattedEvents = events.map((event) => {
        const orgKey = event.organization?.name || event.org_id || 'event';
        const colors = colorForKey(String(orgKey));
        const start = event.date?.endsWith?.('Z') ? event.date : `${event.date}Z`;
        return {
          id: String(event.id),
          title: event.name,
          start,
          backgroundColor: colors.bg,
          borderColor: colors.border,
          textColor: colors.text,
          extendedProps: {
            venue: event.venue,
            orgName: event.organization?.name || '',
            eventId: event.id,
            color: colors,
          },
        };
      });
      setCalendarEvents(formattedEvents);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const fetchRecommendations = async () => {
    try {
      setRecsLoading(true);
      const recRes = await api.get('/events/recommendations');
      setRecommendations(recRes.data);
    } catch (err) { console.error(err); }
    finally { setRecsLoading(false); }
  };

  const fetchFeedback = async () => {
    try {
      setFeedbackLoading(true);
      const feedbackRes = await api.get('/user/feedback-pending');
      setFeedbackNeeded(feedbackRes.data);
    } catch (err) { console.error(err); }
    finally { setFeedbackLoading(false); }
  };

  const fetchDashboardData = () => {
    fetchCalendar();
    fetchRecommendations();
    fetchFeedback();
  };

  const upcoming = useMemo(() => {
    const now = Date.now();
    return [...rawEvents]
      .filter((e) => {
        const t = new Date(e.date?.endsWith?.('Z') ? e.date : `${e.date}Z`).getTime();
        return !Number.isNaN(t) && t >= now - 60 * 60 * 1000;
      })
      .sort((a, b) => new Date(a.date) - new Date(b.date))
      .slice(0, 4);
  }, [rawEvents]);

  const downloadICS = () => {
    const lines = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//Synapse//Events//EN'];
    calendarEvents.forEach((evt) => {
      const dt = new Date(evt.start);
      const stamp = dt.toISOString().replace(/[-:]/g, '').replace(/\.\d{3}/, '');
      lines.push('BEGIN:VEVENT');
      lines.push(`DTSTART:${stamp}`);
      lines.push(`SUMMARY:${(evt.title || '').replace(/[\r\n]/g, ' ')}`);
      if (evt.extendedProps?.venue) lines.push(`LOCATION:${evt.extendedProps.venue.replace(/[\r\n]/g, ' ')}`);
      lines.push(`UID:${stamp}-${Math.random().toString(36).slice(2)}@synapse`);
      lines.push('END:VEVENT');
    });
    lines.push('END:VCALENDAR');
    const blob = new Blob([lines.join('\r\n')], { type: 'text/calendar;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = 'synapse-calendar.ics'; a.click();
    URL.revokeObjectURL(url);
  };

  const handleGenerateSyncLink = async () => {
    try {
      setSyncLoading(true);
      const res = await api.post('/calendar/generate-link');
      const fullUrl = `${window.location.protocol}//${window.location.host}/api/v1/calendar/${res.data.share_token}.ics`;
      setSyncLink(fullUrl);
      toast.success('Calendar link generated!');
    } catch {
      toast.error('Failed to generate link');
    } finally {
      setSyncLoading(false);
    }
  };

  const handleRevokeSyncLink = async () => {
    try {
      setSyncLoading(true);
      await api.post('/calendar/revoke-link');
      setSyncLink('');
      toast.success('Calendar links revoked');
    } catch {
      toast.error('Failed to revoke links');
    } finally {
      setSyncLoading(false);
    }
  };

  const copyToClipboard = () => {
    navigator.clipboard.writeText(syncLink);
    setCopied(true);
    toast.success('Link copied to clipboard!');
    setTimeout(() => setCopied(false), 2000);
  };

  const renderEventContent = (arg) => {
    const time = formatTime(arg.event.start);
    const venue = arg.event.extendedProps?.venue;
    if (arg.view.type === 'listWeek') {
      return (
        <div className="cal-list-event">
          <span className="cal-list-event-title">{arg.event.title}</span>
          {venue && <span className="cal-list-event-venue"><MapPin size={12} /> {venue}</span>}
        </div>
      );
    }
    return (
      <div className="cal-month-event">
        {time && <span className="cal-month-event-time">{time}</span>}
        <span className="cal-month-event-title">{arg.event.title}</span>
      </div>
    );
  };

  if (loading) return <Loader />;

  return (
    <div className="container-fluid student-dashboard">
      <div className="row g-4">

        <div className="col-12 col-lg-8">
          <div className="widget-card calendar-card h-100">

            <div className="calendar-hero">
              <div className="calendar-hero-copy">
                <div className="calendar-kicker">
                  <Sparkles size={14} /> Personal schedule
                </div>
                <h2 className="calendar-title">
                  <CalendarIcon size={22} /> Your Calendar
                </h2>
                <p className="calendar-subtitle">
                  {rawEvents.length === 0
                    ? 'Register for events to see them here.'
                    : `${rawEvents.length} registered event${rawEvents.length === 1 ? '' : 's'} · ${upcoming.length} upcoming`}
                </p>
              </div>
              <div className="calendar-hero-actions">
                <button className="cal-action-btn" onClick={() => setShowSyncModal(true)}>
                  <Link size={15} />
                  <span>Sync</span>
                </button>
                <button className="cal-action-btn cal-action-btn-primary" onClick={downloadICS}>
                  <Download size={15} />
                  <span>Export .ics</span>
                </button>
              </div>
            </div>

            {upcoming.length > 0 && (
              <div className="calendar-upcoming">
                <div className="calendar-upcoming-label">Up next</div>
                <div className="calendar-upcoming-rail">
                  {upcoming.map((event) => {
                    const colors = colorForKey(String(event.organization?.name || event.org_id));
                    const start = event.date?.endsWith?.('Z') ? event.date : `${event.date}Z`;
                    return (
                      <button
                        key={event.id}
                        type="button"
                        className="calendar-upcoming-chip"
                        style={{ '--chip-accent': colors.border }}
                        onClick={() => navigate(`/events/${event.id}`)}
                      >
                        <span className="calendar-upcoming-date">
                          {formatDate(event.date)}
                          <small>{formatTime(start)}</small>
                        </span>
                        <span className="calendar-upcoming-body">
                          <strong>{event.name}</strong>
                          <span>
                            {event.organization?.name || 'Event'}
                            {event.venue ? ` · ${event.venue}` : ''}
                          </span>
                        </span>
                        <ChevronRight size={16} className="calendar-upcoming-chevron" />
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            <div className="calendar-shell">
              <FullCalendar
                ref={calendarRef}
                plugins={[dayGridPlugin, timeGridPlugin, listPlugin, interactionPlugin]}
                initialView="dayGridMonth"
                headerToolbar={{
                  left: 'prev,next today',
                  center: 'title',
                  right: 'dayGridMonth,timeGridWeek,listWeek',
                }}
                buttonText={{
                  today: 'Today',
                  month: 'Month',
                  week: 'Week',
                  listWeek: 'Agenda',
                }}
                events={calendarEvents}
                height="auto"
                aspectRatio={1.35}
                dayMaxEvents={3}
                nowIndicator
                eventDisplay="block"
                eventContent={renderEventContent}
                eventClick={(info) => {
                  info.jsEvent.preventDefault();
                  const id = info.event.extendedProps?.eventId || info.event.id;
                  if (id) navigate(`/events/${id}`);
                }}
                eventClassNames={() => ['cal-event-modern']}
              />
              {calendarEvents.length === 0 && (
                <div className="calendar-empty">
                  <CalendarIcon size={32} />
                  <h4>No events on your calendar yet</h4>
                  <p>Browse events on the home page and register to fill your schedule.</p>
                  <button className="cal-action-btn cal-action-btn-primary" onClick={() => navigate('/')}>
                    Explore events
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="col-12 col-lg-4 d-flex flex-column gap-4">
          <div className="widget-card">
            <h5 className="section-heading-sm mb-3">
              <Star size={18} className="text-warning" /> Recommended For You
            </h5>
            {recsLoading ? (
              <div className="d-flex justify-content-center py-4"><Loader /></div>
            ) : recommendations.length > 0 ? (
              <div className="recommendation-list">
                {recommendations.slice(0, 3).map((event) => (
                  <div
                    key={event.id}
                    className="recommendation-item"
                    onClick={() => navigate(`/events/${event.id}`)}
                    style={{ cursor: 'pointer' }}
                  >
                    <h6 className="mb-1 fw-semibold">{event.name}</h6>
                    <span className="text-secondary small">{formatDate(event.date)}</span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty-placeholder" style={{ border: 'none', padding: '32px 16px' }}>
                <Star size={28} style={{ opacity: 0.2 }} />
                <p>No recommendations yet. Add interests in your profile!</p>
              </div>
            )}
          </div>

          <div className="widget-card">
            <h5 className="section-heading-sm mb-3">
              <MessageSquare size={18} className="text-info" /> Feedback Needed
            </h5>
            {feedbackLoading ? (
              <div className="d-flex justify-content-center py-4"><Loader /></div>
            ) : feedbackNeeded.length > 0 ? (
              <div className="feedback-list">
                {feedbackNeeded.map((event) => (
                  <FeedbackCard
                    key={event.id}
                    eventId={event.id}
                    eventName={event.name}
                    onFeedbackSubmitted={fetchDashboardData}
                  />
                ))}
              </div>
            ) : (
              <div className="empty-placeholder" style={{ border: 'none', padding: '32px 16px' }}>
                <MessageSquare size={28} style={{ opacity: 0.2 }} />
                <p>You're all caught up!</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {showSyncModal && (
        <div className="cal-sync-overlay" onClick={() => setShowSyncModal(false)}>
          <div className="cal-sync-modal" onClick={(e) => e.stopPropagation()}>
            <div className="cal-sync-header">
              <div>
                <div className="calendar-kicker"><Link size={13} /> External sync</div>
                <h5>Sync Calendar</h5>
              </div>
              <button className="cal-sync-close" onClick={() => setShowSyncModal(false)} aria-label="Close">
                <X size={18} />
              </button>
            </div>

            <p className="cal-sync-copy">
              Subscribe once in Google, Outlook, or Apple Calendar — new Synapse registrations appear automatically.
            </p>

            {!syncLink ? (
              <button
                className="cal-action-btn cal-action-btn-primary cal-sync-generate"
                onClick={handleGenerateSyncLink}
                disabled={syncLoading}
              >
                <Link size={16} />
                {syncLoading ? 'Generating…' : 'Generate sync link'}
              </button>
            ) : (
              <div className="cal-sync-body">
                <div className="cal-sync-link">{syncLink}</div>
                <div className="cal-sync-actions">
                  <button className="cal-action-btn cal-action-btn-primary" onClick={copyToClipboard}>
                    {copied ? <Check size={16} /> : <Copy size={16} />}
                    {copied ? 'Copied' : 'Copy link'}
                  </button>
                  <button
                    className="cal-action-btn cal-action-btn-danger"
                    onClick={handleRevokeSyncLink}
                    disabled={syncLoading}
                    title="Revoke access"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
                <div className="cal-sync-help">
                  <strong>Google Calendar</strong>
                  <ol>
                    <li>Copy the link above.</li>
                    <li>Open calendar.google.com → Other calendars → From URL.</li>
                    <li>Paste and add — events auto-sync.</li>
                  </ol>
                  <strong>Apple Calendar</strong>
                  <p>Settings → Calendar → Accounts → Add Subscribed Calendar → paste the link.</p>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default StudentDashboard;
