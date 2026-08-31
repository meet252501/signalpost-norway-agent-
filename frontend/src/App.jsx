import React, { useState, useEffect } from 'react';

const API_BASE = 'http://localhost:8000';

function App() {
  const [companies, setCompanies] = useState([]);
  const [selectedOrg, setSelectedOrg] = useState(null);
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [profileLoading, setProfileLoading] = useState(false);

  useEffect(() => {
    fetch(`${API_BASE}/companies`)
      .then(res => res.json())
      .then(data => {
        setCompanies(data.companies || []);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  }, []);

  const loadProfile = (orgNumber) => {
    setProfileLoading(true);
    setSelectedOrg(orgNumber);
    fetch(`${API_BASE}/companies/${orgNumber}`)
      .then(res => res.json())
      .then(data => {
        setProfile(data);
        setProfileLoading(false);
      })
      .catch(err => {
        console.error(err);
        setProfileLoading(false);
      });
  };

  const renderClaim = (claim) => {
    if (!claim) return <span className="avail-missing">Missing</span>;
    if (claim.availability === "available") {
      return (
        <div>
          <div className="data-value">
            {typeof claim.value === 'string' && claim.value.startsWith('http') ? (
              <a href={claim.value} target="_blank" rel="noreferrer">{claim.value}</a>
            ) : (
              String(claim.value)
            )}
          </div>
          <div className="avail-found">Found</div>
        </div>
      );
    }
    return <span className={`avail-${claim.availability}`}>{claim.availability}</span>;
  };

  return (
    <div className="container">
      <header>
        <h1>Signalpost Norway Agent</h1>
        <p>Verified company intelligence from official sources.</p>
      </header>

      <div className="dashboard-grid">
        {/* Left Sidebar - List */}
        <div className="glass-panel">
          <div style={{ padding: '1.25rem', borderBottom: '1px solid var(--surface-border)' }}>
            <h3 style={{ marginBottom: '0.5rem' }}>Processed Companies</h3>
            <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
              {companies.length} snapshots available
            </p>
          </div>
          
          <div className="company-list" style={{ padding: '1.25rem', maxHeight: '70vh', overflowY: 'auto' }}>
            {loading ? (
              <div className="loading">Loading...</div>
            ) : companies.length === 0 ? (
              <div className="empty-state">No companies processed yet.</div>
            ) : (
              companies.map(c => (
                <div 
                  key={c.org_number} 
                  className={`company-card ${selectedOrg === c.org_number ? 'active' : ''}`}
                  onClick={() => loadProfile(c.org_number)}
                >
                  <div className="company-name">{c.legal_name}</div>
                  <div className="company-org">{c.org_number}</div>
                  <span className={`status-badge status-${c.status}`}>{c.status}</span>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right Area - Profile Details */}
        <div className="glass-panel profile-details">
          {!selectedOrg ? (
            <div className="empty-state">
              <h2>Select a company to view its profile</h2>
            </div>
          ) : profileLoading ? (
            <div className="loading">Loading profile...</div>
          ) : profile ? (
            <div>
              <div className="profile-header">
                <h2>{profile.entity.legal_name}</h2>
                <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                  <span className="data-label">ORG: {profile.entity.org_number}</span>
                  <span className={`status-badge status-${profile.entity.status}`}>
                    {profile.entity.status}
                  </span>
                </div>
                <div style={{ marginTop: '0.5rem', color: 'var(--text-secondary)' }}>
                  {profile.entity.registered_address}
                </div>
              </div>

              <div className="data-grid">
                <div className="data-card">
                  <div className="data-label">Official Website</div>
                  {renderClaim(profile.official_site)}
                </div>
                <div className="data-card">
                  <div className="data-label">LinkedIn</div>
                  {renderClaim(profile.linkedin_url)}
                </div>
                <div className="data-card">
                  <div className="data-label">Headcount Band</div>
                  {renderClaim(profile.headcount_band)}
                </div>
                <div className="data-card">
                  <div className="data-label">Hiring Signal</div>
                  {renderClaim(profile.hiring_signal)}
                </div>
              </div>

              {/* Diffs / What Changed Section */}
              {profile.refresh && profile.refresh.material_changes.length > 0 && (
                <div className="diff-section">
                  <h3>What Changed Since Last Snapshot</h3>
                  <div className="diff-list">
                    {profile.refresh.material_changes.map((diff, i) => (
                      <div key={i} className="diff-item">
                        <div className="diff-field">{diff.field}</div>
                        <div className="diff-changes">
                          <span className="diff-old">{JSON.stringify(diff.old)}</span>
                          <span className="diff-arrow">→</span>
                          <span className="diff-new">{JSON.stringify(diff.new)}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}

export default App;
