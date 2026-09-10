let COMPANIES = [];
let filteredCompanies = [];
let selectedCompany = null;

document.addEventListener('DOMContentLoaded', async () => {
  try {
    const res = await fetch('data.json');
    const rawData = await res.json();
    parseData(rawData);
  } catch (err) {
    console.error("Failed to load data.json:", err);
  }
  
  filteredCompanies = [...COMPANIES];
  document.getElementById('totalCount').textContent = COMPANIES.length;
  
  renderDirectory();
  setupSearch();
  setupTabs();
});

function parseData(rawData) {
  COMPANIES = rawData.map(item => {
    const p = item.profile || (item.attributes ? item.attributes.company : item);
    const evidence = p.evidence || item.evidence || {};
    
    const liveData = evidence.registry_live?.value || {};
    const employees = liveData.employees !== undefined && liveData.employees !== null ? liveData.employees : p.employees;
    
    let bankrupt = p.bankrupt === true;
    let liquidating = p.liquidating === true;
    if (evidence.registry_live?.value) {
        if (evidence.registry_live.value.bankrupt !== undefined) bankrupt = evidence.registry_live.value.bankrupt;
        if (evidence.registry_live.value.liquidating !== undefined) liquidating = evidence.registry_live.value.liquidating;
    }
    
    let evidenceCount = 0;
    Object.keys(evidence).forEach(k => {
      if (evidence[k] && evidence[k].status === 'available') evidenceCount++;
    });
    
    let web = p.website;
    if (!web && evidence.website?.value?.url) {
      try { web = new URL(evidence.website.value.url).hostname; } catch(e){ web = evidence.website.value.url; }
    }
    
    return {
      _raw: item,
      name: p.name || item.name || 'Ukjent Firma',
      org: p.organisation_number || item.organisation_number,
      form: p.legal_form || item.legal_form || 'AS',
      employees: employees,
      municipality: p.municipality || p.business_address?.kommune || 'Ukjent',
      website: web || null,
      industry: p.industry_label || p.industry?.beskrivelse || 'Uoppgitt',
      bankrupt: bankrupt,
      liquidating: liquidating,
      evidenceCount: evidenceCount,
      score: item.score || (evidenceCount / 8.0 * 10),
      finHealth: p.financial_health || item.financial_health || null,
      compliance: p.compliance || item.compliance || null
    };
  });
  
  COMPANIES.sort((a, b) => b.evidenceCount - a.evidenceCount);
}

function renderDirectory() {
  const list = document.getElementById('companyList');
  list.innerHTML = filteredCompanies.map(c => {
    let badgeClass = 'data-badge';
    if (c.bankrupt || c.liquidating) badgeClass += ' warning';
    const badgeText = c.bankrupt ? 'Bankrupt' : (c.liquidating ? 'Liquidating' : `${c.evidenceCount}/8 data`);
    
    let extraBadge = '';
    const compTier = c.compliance?.compliance_tier;
    if (compTier === 'low_risk' || c.compliance?.badge_color === 'green') {
      extraBadge = `<div class="data-badge" style="color:var(--success); background:rgba(16,185,129,0.1);"><span class="material-symbols-outlined">shield</span>Clean</div>`;
    } else if (compTier === 'high_risk' || c.compliance?.badge_color === 'red' || c.bankrupt) {
      extraBadge = `<div class="data-badge warning"><span class="material-symbols-outlined">gavel</span>High Risk</div>`;
    }

    return `
      <div class="company-item ${selectedCompany?.org === c.org ? 'selected' : ''}" onclick="selectCompany('${c.org}')">
        <div class="item-name">${c.name}</div>
        <div class="item-desc">${c.municipality} — ${c.industry}</div>
        <div style="display:flex; gap:6px; flex-wrap:wrap;">
          <div class="${badgeClass}">
            <span class="material-symbols-outlined">${c.bankrupt || c.liquidating ? 'warning' : 'verified'}</span>
            ${badgeText}
          </div>
          ${extraBadge}
        </div>
      </div>
    `;
  }).join('');
}

function applyFilters() {
  const q = document.getElementById('directorySearch').value.toLowerCase();
  const sort = document.getElementById('sortFilter') ? document.getElementById('sortFilter').value : 'data';
  const status = document.getElementById('statusFilter') ? document.getElementById('statusFilter').value : 'all';
  
  filteredCompanies = COMPANIES.filter(c => {
    const matchesSearch = c.name.toLowerCase().includes(q) || c.org.includes(q) || c.municipality.toLowerCase().includes(q);
    let matchesStatus = true;
    if (status === 'bankrupt') matchesStatus = c.bankrupt === true;
    else if (status === 'liquidating') matchesStatus = c.liquidating === true;
    else if (status === 'active') matchesStatus = !c.bankrupt && !c.liquidating;
    return matchesSearch && matchesStatus;
  });
  
  if (sort === 'name') {
    filteredCompanies.sort((a, b) => a.name.localeCompare(b.name));
  } else {
    filteredCompanies.sort((a, b) => b.evidenceCount - a.evidenceCount);
  }
  
  renderDirectory();
}

function setupSearch() {
  document.getElementById('directorySearch').addEventListener('input', applyFilters);
}

function selectCompany(org) {
  selectedCompany = COMPANIES.find(c => c.org === org);
  renderDirectory(); // Update selection highlight
  renderProfile();
  
  // Clear the agent response text when switching companies
  const responseBox = document.getElementById('agentResponse');
  if (responseBox) {
    responseBox.innerHTML = `
      <h3 class="response-title">Agent Response</h3>
      <p class="response-text" id="agentResponseText">
        Select a question or ask above to query the live Python API.
      </p>
    `;
  }
}

function formatCurrency(num) {
  if (num === null || num === undefined) return 'N/A';
  return (num / 1000000).toFixed(1) + 'M NOK';
}

function renderProfile() {
  if (!selectedCompany) return;
  document.getElementById('profileEmpty').style.display = 'none';
  document.getElementById('profileContent').style.display = 'block';
  
  const c = selectedCompany;
  const raw = c._raw || {};
  const evidence = raw.evidence || (raw.profile ? raw.profile.evidence : {}) || {};
  
  document.getElementById('pName').textContent = c.name;
  document.getElementById('pOrg').textContent = c.org;
  document.getElementById('pForm').textContent = c.form;
  document.getElementById('pCity').textContent = c.municipality;
  document.getElementById('pDesc').textContent = c.industry;
  
  let badgesHTML = '';
  if (evidence.financials?.status === 'available') badgesHTML += `<div class="status-badge green"><span class="material-symbols-outlined">check_circle</span>Latest annual filing</div>`;
  if (c.website) badgesHTML += `<div class="status-badge green"><span class="material-symbols-outlined">check_circle</span>Verified website</div>`;
  if (evidence.roles?.status === 'available') badgesHTML += `<div class="status-badge green"><span class="material-symbols-outlined">check_circle</span>Roles verified</div>`;
  
  const finH = c.finHealth || {};
  const finLatest = finH.latest || finH;
  const comp = c.compliance || {};

  // Compliance & AML badge
  if (comp && comp.compliance_tier) {
    const color = comp.badge_color || (comp.compliance_tier === 'low_risk' ? 'green' : (comp.compliance_tier === 'high_risk' ? 'red' : 'amber'));
    const label = comp.status_label || (comp.compliance_tier === 'low_risk' ? 'AML/KYC: Low Risk' : (comp.compliance_tier === 'high_risk' ? 'AML/KYC: High Risk' : 'AML/KYC: Standard Diligence'));
    const icon = comp.compliance_tier === 'low_risk' ? 'verified_user' : (comp.compliance_tier === 'high_risk' ? 'gavel' : 'shield');
    badgesHTML += `<div class="status-badge ${color}"><span class="material-symbols-outlined">${icon}</span>${label}</div>`;
  }

  // Financial Health badge
  if (finLatest && finLatest.altman_z_score) {
    let zTier = finLatest.credit_risk_tier || 'low_risk';
    let zClass = zTier === 'low_risk' ? 'blue' : (zTier === 'high_risk' ? 'red' : 'amber');
    let zIcon = zTier === 'low_risk' ? 'trending_up' : (zTier === 'high_risk' ? 'trending_down' : 'swap_horiz');
    badgesHTML += `<div class="status-badge ${zClass}"><span class="material-symbols-outlined">${zIcon}</span>Altman Z'': ${finLatest.altman_z_score.toFixed(2)} (${finLatest.solvency_status || 'solid'})</div>`;
  }
  
  document.getElementById('pBadges').innerHTML = badgesHTML;
  
  // Extract specific evidence points
  const fin = evidence.financials?.value?.records?.[0] || {};
  const roles = evidence.roles?.value?.roles || [];
  const locs = evidence.locations?.value?.locations || [];
  
  // Overview Tab
  let htmlOverview = `
    <h2 class="section-title">Company overview <span class="material-symbols-outlined" style="color:var(--text-muted);font-size:18px">info</span></h2>
    <div class="data-grid">
      <div class="data-item">
        <span class="label">LATEST REPORTED REVENUE</span>
        <span class="value nok">${formatCurrency(fin.revenue)}</span>
        <span class="desc">Official financial record</span>
      </div>
      <div class="data-item">
        <span class="label">LATEST OPERATING RESULT</span>
        <span class="value nok">${formatCurrency(fin.operating_result)}</span>
        <span class="desc">Official financial record</span>
      </div>
      <div class="data-item">
        <span class="label">EMPLOYEES IN REGISTER</span>
        <span class="value">${c.employees !== null ? c.employees : 'N/A'}</span>
        <span class="desc">Official company record</span>
      </div>
      <div class="data-item">
        <span class="label">SOLVENCY STATUS</span>
        <span class="value" style="color:${finLatest.solvency_status === 'solid' ? 'var(--success)' : (finLatest.solvency_status === 'vulnerable' || finLatest.solvency_status === 'negative_equity' ? 'var(--danger)' : '#38bdf8')}">${(finLatest.solvency_status || 'Satisfactory').toUpperCase()}</span>
        <span class="desc">Equity ratio: ${finLatest.equity_ratio_pct !== null && finLatest.equity_ratio_pct !== undefined ? finLatest.equity_ratio_pct + '%' : 'N/A'}</span>
      </div>
      <div class="data-item">
        <span class="label">AML & REGULATORY RISK</span>
        <span class="value" style="color:${comp.badge_color === 'green' ? 'var(--success)' : (comp.badge_color === 'red' ? 'var(--danger)' : '#f59e0b')}">${(comp.compliance_tier || 'STANDARD').replace('_', ' ').toUpperCase()}</span>
        <span class="desc">Risk score: ${comp.risk_score !== undefined ? comp.risk_score + '/100' : 'Clean'}</span>
      </div>
      <div class="data-item">
        <span class="label">IDENTITY SCORE</span>
        <span class="value">${(c.score).toFixed(1)}/10</span>
        <span class="desc">Confidence rating</span>
      </div>
    </div>
  `;
  
  // Financials Tab
  let zColor = 'var(--text-main)';
  if (finLatest.credit_risk_tier === 'low_risk') zColor = 'var(--success)';
  else if (finLatest.credit_risk_tier === 'high_risk') zColor = 'var(--danger)';
  else if (finLatest.credit_risk_tier === 'grey_zone') zColor = '#f59e0b';

  let htmlFin = `
    <h2 class="section-title">Solvency & Credit Health Analytics <span class="material-symbols-outlined" style="color:var(--primary-accent);font-size:18px">query_stats</span></h2>
    <div class="card-grid three-col" style="margin-bottom:32px;">
      <div class="info-card">
        <h4>Altman Z''-Score</h4>
        <p style="font-size:1.5rem; font-weight:700; color:${zColor}; margin:6px 0;">${finLatest.altman_z_score !== null && finLatest.altman_z_score !== undefined ? finLatest.altman_z_score.toFixed(2) : 'N/A'}</p>
        <p>${finH.rating_label || (finLatest.credit_risk_tier || 'Statutory Baseline')}</p>
      </div>
      <div class="info-card">
        <h4>Equity Ratio</h4>
        <p style="font-size:1.5rem; font-weight:700; color:var(--success); margin:6px 0;">${finLatest.equity_ratio_pct !== null && finLatest.equity_ratio_pct !== undefined ? finLatest.equity_ratio_pct + '%' : 'N/A'}</p>
        <p>Solvency: ${(finLatest.solvency_status || 'Satisfactory').toUpperCase()}</p>
      </div>
      <div class="info-card">
        <h4>Debt-to-Equity Ratio</h4>
        <p style="font-size:1.5rem; font-weight:700; color:#38bdf8; margin:6px 0;">${finLatest.debt_to_equity !== null && finLatest.debt_to_equity !== undefined ? finLatest.debt_to_equity.toFixed(2) + 'x' : 'N/A'}</p>
        <p>Revenue trend: ${(finH.revenue_trend || 'Active').toUpperCase()}</p>
      </div>
    </div>

    <h2 class="section-title">Official statutory filings</h2>
    <div class="data-list">
      <div class="data-row"><span class="key">Revenue</span><span class="val">${formatCurrency(fin.revenue)}</span></div>
      <div class="data-row"><span class="key">Operating result</span><span class="val">${formatCurrency(fin.operating_result)}</span></div>
      <div class="data-row"><span class="key">Annual result</span><span class="val">${formatCurrency(fin.annual_result)}</span></div>
      <div class="data-row"><span class="key">Total assets</span><span class="val">${formatCurrency(fin.assets)}</span></div>
      <div class="data-row"><span class="key">Total equity</span><span class="val">${formatCurrency(fin.equity)}</span></div>
      <div class="data-row"><span class="key">Total debt</span><span class="val">${formatCurrency(fin.debt)}</span></div>
    </div>
  `;
  
  // Leadership Tab
  let htmlLead = `
    <h2 class="section-title">Leadership</h2>
    <div class="card-grid three-col">
      ${roles.length > 0 ? roles.map(r => `
        <div class="info-card">
          <h4>${r.name}</h4>
          <p>${r.role}</p>
        </div>
      `).join('') : '<p class="text-muted">No leadership data available.</p>'}
    </div>
  `;
  
  // Locations Tab
  let htmlLoc = `
    <h2 class="section-title">Locations</h2>
    <div class="card-grid">
      ${locs.length > 0 ? locs.map(l => `
        <div class="info-card">
          <h4>${l.name}</h4>
          <p>${l.address?.adresse?.[0] || ''}, ${l.address?.kommune || ''}</p>
        </div>
      `).join('') : `
        <div class="info-card">
          <h4>${c.name}</h4>
          <p>${c.municipality}</p>
        </div>
      `}
    </div>
  `;
  
  // Evidence Tab
  let htmlEvid = `
    <h2 class="section-title">Run & identity evidence</h2>
    <div class="data-list">
  `;
  Object.keys(evidence).forEach(key => {
    const e = evidence[key];
    htmlEvid += `<div class="data-row"><span class="key">${key.toUpperCase()}</span><span class="val" style="color:${e?.status === 'available' ? 'var(--success)' : 'var(--text-muted)'}">${e?.status || 'unknown'}</span></div>`;
  });
  htmlEvid += `</div>`;
  
  document.getElementById('tabContent').innerHTML = `
    <div id="tab-overview" class="tab-pane active">${htmlOverview}</div>
    <div id="tab-financials" class="tab-pane">${htmlFin}</div>
    <div id="tab-leadership" class="tab-pane">${htmlLead}</div>
    <div id="tab-locations" class="tab-pane">${htmlLoc}</div>
    <div id="tab-evidence" class="tab-pane">${htmlEvid}</div>
  `;
  
  // Reset tabs
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.classList.remove('active');
    if (btn.dataset.tab === 'overview') btn.classList.add('active');
  });
  
  // Reset Agent
  document.getElementById('agentResponseText').textContent = "Select a question or ask above to query the Signalpost agent.";
}

function setupTabs() {
  document.querySelectorAll('.tab-btn').forEach(btn => {
    // Only target center panel tabs if they don't have an ID (which the right sidebar ones do)
    if (btn.id) return;
    
    btn.addEventListener('click', () => {
      document.querySelectorAll('.center-panel .tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
      
      btn.classList.add('active');
      document.getElementById(`tab-${btn.dataset.tab}`).classList.add('active');
    });
  });
}

function switchRightTab(tab) {
  if (tab === 'agent') {
    document.getElementById('btnAgentTab').classList.add('active');
    document.getElementById('btnScreenerTab').classList.remove('active');
    document.getElementById('agentTabContent').style.display = 'block';
    document.getElementById('screenerTabContent').style.display = 'none';
  } else {
    document.getElementById('btnScreenerTab').classList.add('active');
    document.getElementById('btnAgentTab').classList.remove('active');
    document.getElementById('screenerTabContent').style.display = 'block';
    document.getElementById('agentTabContent').style.display = 'none';
  }
}

async function runScreener() {
  const query = document.getElementById('screenerInput').value;
  if (!query) return;
  
  const responseBox = document.getElementById('screenerResponse');
  responseBox.innerHTML = `
    <p class="response-text">
      <span class="material-symbols-outlined" style="animation: pulse 1.5s infinite; vertical-align: middle;">search</span>
      Screening companies...
    </p>
  `;
  
  try {
    const res = await fetch('/api/screen', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: query })
    });
    const data = await res.json();
    
    if (data.abstained) {
      responseBox.innerHTML = `<p class="response-text warning" style="color:var(--danger);">${data.reason}</p>`;
      return;
    }
    
    let html = `<p class="response-text" style="color:var(--success); margin-bottom:10px;">Found ${data.result_count} companies matching query.</p>`;
    data.results.forEach(c => {
       html += `
         <div style="background:var(--bg-lighter); padding:10px; border-radius:6px; margin-bottom:8px; cursor:pointer; border:1px solid var(--border-color);" onclick="selectCompany('${c.organisation_number}')">
           <h4 style="margin:0; font-size:14px;">${c.name}</h4>
           <p style="margin:4px 0 0; font-size:12px; color:var(--text-muted);">${c.municipality} | Rev: ${formatCurrency(c.revenue)}</p>
         </div>
       `;
    });
    responseBox.innerHTML = html;
  } catch (err) {
    responseBox.innerHTML = `<p class="response-text error">Error contacting API backend. Is server.py running?</p>`;
  }
}

async function simulateAgent() {
  if (!selectedCompany) return;
  const input = document.getElementById('agentInput');
  const text = input.value || 'Company brief';
  input.value = '';
  
  const responseBox = document.getElementById('agentResponse');
  responseBox.innerHTML = `
    <h3 class="response-title">${text}</h3>
    <p class="response-text">
      <span class="material-symbols-outlined" style="animation: pulse 1.5s infinite; vertical-align: middle;">smart_toy</span>
      Analyzing registry data via Python API...
    </p>
  `;
  
  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        organisation_number: selectedCompany.org,
        question: text
      })
    });
    const data = await res.json();
    
    let html = `<h3 class="response-title">${text}</h3>`;
    if (data.facts && data.facts.length > 0) {
      html += `<ul style="margin:10px 0; padding-left:20px;">`;
      data.facts.forEach(f => {
        let val = typeof f.value === 'object' ? JSON.stringify(f.value) : f.value;
        html += `<li style="font-size:13px; color:var(--text-light); margin-bottom:6px;">
          <strong style="color:var(--text-main);">${f.claim}:</strong> ${val}
        </li>`;
      });
      html += `</ul>`;
    } else {
      html += `<p class="response-text">No facts could be definitively retrieved for this query.</p>`;
    }
    
    if (data.unsupported_or_uncertain && data.unsupported_or_uncertain.length > 0) {
      html += `<div style="background: rgba(255,100,100,0.1); border-left: 3px solid var(--danger); padding: 8px 12px; margin-top:10px; border-radius:4px;">`;
      data.unsupported_or_uncertain.forEach(u => {
        html += `<p style="font-size:12px; color:var(--danger); margin:0 0 4px;">${u}</p>`;
      });
      html += `</div>`;
    }
    
    responseBox.innerHTML = html;
  } catch (err) {
    responseBox.innerHTML = `
      <h3 class="response-title">${text}</h3>
      <p class="response-text error" style="color:var(--danger);">Error contacting API backend. Is server.py running?</p>
    `;
  }
}
