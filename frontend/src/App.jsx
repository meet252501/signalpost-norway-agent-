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
        <h1>Signalpost Norway</h1>
        <p>Verified company intelligence from official sources.</p>
      </header>

      <div className="dashboard-grid">
        {/* Left Sidebar - List */}
        <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', height: '80vh' }}>
          <div className="sidebar-header">
            <h3>Processed Companies</h3>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              {companies.length} snapshots available
            </p>
          </div>
          
          <div className="company-list" style={{ overflowY: 'auto', flex: 1 }}>
            {loading ? (
              <div className="empty-state">
                <div className="loading-spinner"></div>
                <p>Loading companies...</p>
              </div>
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
        <div className="glass-panel profile-details" style={{ height: '80vh', overflowY: 'auto' }}>
          {!selectedOrg ? (
            <div className="empty-state">
              <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="var(--surface-border)" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round" style={{marginBottom: '1rem'}}>
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                <polyline points="17 8 12 3 7 8"></polyline>
                <line x1="12" y1="3" x2="12" y2="15"></line>
              </svg>
              <h2>Select a company to view its profile</h2>
            </div>
          ) : profileLoading ? (
            <div className="empty-state">
              <div className="loading-spinner"></div>
              <p>Loading profile...</p>
            </div>
          ) : profile ? (
            <div>
              <div className="profile-header">
                <h2>{profile.entity.legal_name}</h2>
                <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                  <span className="data-label" style={{marginBottom: 0}}>ORG: {profile.entity.org_number}</span>
                  <span className={`status-badge status-${profile.entity.status}`}>
                    {profile.entity.status}
                  </span>
                </div>
                <div style={{ marginTop: '1rem', color: 'var(--text-secondary)' }}>
                  📍 {profile.entity.registered_address}
                </div>
              </div>

              <div className="data-grid">
                <div className="data-card">
                  <div className="data-label">🌐 Official Website</div>
                  {renderClaim(profile.official_site)}
                </div>
                <div className="data-card">
                  <div className="data-label">💼 LinkedIn</div>
                  {renderClaim(profile.linkedin_url)}
                </div>
                <div className="data-card">
                  <div className="data-label">👥 Headcount Band</div>
                  {renderClaim(profile.headcount_band)}
                </div>
                <div className="data-card">
                  <div className="data-label">🚀 Hiring Signal</div>
                  {renderClaim(profile.hiring_signal)}
                </div>
              </div>

              {/* Diffs / What Changed Section */}
              {profile.refresh && profile.refresh.material_changes.length > 0 && (
                <div className="diff-section">
                  <h3>What Changed</h3>
                  <div>
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
