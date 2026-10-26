import React, { useState, useEffect } from 'react';
import { API_BASE_URL } from './config';

const POLL_INTERVAL_MS = 2000;

// Short scripts for each failure scenario, shown under "Demo scenarios".
const SCENARIOS = [
  {
    title: 'Tool / API down',
    steps: 'Turn on "Core banking API down" and ask to list your investments. The tool retries until you turn it off, then the answer arrives.',
  },
  {
    title: 'LLM down or rate limited',
    steps: 'Turn on an OpenAI flag and send any message. Rate-limited calls wait 15s between attempts (the Retry-After delay) instead of backing off normally.',
  },
  {
    title: 'Business rule (non-retryable)',
    steps: 'Ask to open an account with $2,000,000. Validation fails on the first attempt, with no retries, and the agent explains why.',
  },
  {
    title: 'Saga rollback',
    steps: 'Turn on "Custodian rejects new accounts" (and "Slow account-opening steps"), then open an account through compliance approval. The funds transfer and the account are undone. Without flags: as client 123, open an account with $300,000 (the linked bank account has $250,000).',
  },
  {
    title: 'Bug in workflow code',
    steps: 'Turn on "Bug in workflow code" and open an account through compliance approval. The workflow pauses on the bug while other chats keep working. Fix _welcome_bonus in open_account_workflow.py (initial_deposit → initial_amount) and restart the worker, and it carries on. Afterwards, git checkout the file to re-arm the bug.',
  },
];

function formatTime(timestamp) {
  return new Date(timestamp * 1000).toLocaleTimeString();
}

function ChaosPanel() {
  const [flags, setFlags] = useState([]);
  const [events, setEvents] = useState([]);
  const [error, setError] = useState(null);

  const fetchChaos = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/chaos`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      setFlags(data.flags);
      setEvents(data.events);
      setError(null);
    } catch (e) {
      setError('Cannot reach the API');
    }
  };

  useEffect(() => {
    fetchChaos();
    const intervalId = setInterval(fetchChaos, POLL_INTERVAL_MS);
    return () => clearInterval(intervalId);
  }, []);

  const toggleFlag = async (flag, enabled) => {
    // Optimistic update so the switch responds immediately.
    setFlags((prev) => prev.map((f) => (f.flag === flag ? { ...f, enabled } : f)));
    try {
      await fetch(`${API_BASE_URL}/chaos?flag=${flag}&enabled=${enabled}`, { method: 'POST' });
    } catch (e) {
      console.error('Error setting chaos flag:', e);
    }
    fetchChaos();
  };

  const resetAll = async () => {
    try {
      await fetch(`${API_BASE_URL}/chaos/reset`, { method: 'POST' });
    } catch (e) {
      console.error('Error resetting chaos flags:', e);
    }
    fetchChaos();
  };

  const labelFor = (flag) => flags.find((f) => f.flag === flag)?.label || flag;

  return (
    <div className="chaos-panel">
      <div className="chaos-header">
        <span>Chaos panel</span>
        <button className="chaos-reset" onClick={resetAll}>Reset all</button>
      </div>

      <div className="chaos-body">
        {error && <div className="chaos-error">{error}</div>}

        {flags.map((f) => (
          <label key={f.flag} className={`chaos-flag ${f.enabled ? 'on' : ''}`}>
            <input
              type="checkbox"
              checked={f.enabled}
              onChange={(e) => toggleFlag(f.flag, e.target.checked)}
            />
            <span className="chaos-flag-text">
              <span className="chaos-flag-label">{f.label}</span>
              <span className="chaos-flag-description">{f.description}</span>
            </span>
          </label>
        ))}

        <div className="chaos-section-title">Injected failures</div>
        {events.length === 0 ? (
          <div className="chaos-empty">None yet.</div>
        ) : (
          <ul className="chaos-events">
            {events.map((e, i) => (
              <li key={`${e.timestamp}-${i}`}>
                <span className="chaos-event-time">{formatTime(e.timestamp)}</span>{' '}
                <span className="chaos-event-source">{e.source}</span>
                {e.attempt ? ` attempt ${e.attempt}` : ''}
                <div className="chaos-event-flag">{labelFor(e.flag)}</div>
              </li>
            ))}
          </ul>
        )}

        <details className="chaos-scenarios">
          <summary>Demo scenarios</summary>
          {SCENARIOS.map((s) => (
            <div key={s.title} className="chaos-scenario">
              <strong>{s.title}</strong>
              <p>{s.steps}</p>
            </div>
          ))}
        </details>
      </div>
    </div>
  );
}

export default ChaosPanel;
