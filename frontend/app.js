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
      score: item.score || (evidenceCount / 8.0 * 10)
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
    
    return `
      <div class="company-item ${selectedCompany?.org === c.org ? 'selected' : ''}" onclick="selectCompany('${c.org}')">
        <div class="item-name">${c.name}</div>
        <div class="item-desc">${c.municipality} — ${c.industry}</div>
        <div class="${badgeClass}">
          <span class="material-symbols-outlined">${c.bankrupt || c.liquidating ? 'warning' : 'verified'}</span>
          ${badgeText}
        </div>
      </div>
    `;
  }).join('');
}

function setupSearch() {
  document.getElementById('directorySearch').addEventListener('input', (e) => {
    const q = e.target.value.toLowerCase();
    filteredCompanies = COMPANIES.filter(c => 
      c.name.toLowerCase().includes(q) || 
      c.org.includes(q) || 
      c.municipality.toLowerCase().includes(q)
    );
    renderDirectory();
  });
}

function selectCompany(org) {
  selectedCompany = COMPANIES.find(c => c.org === org);
  renderDirectory(); // Update selection highlight
  renderProfile();
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
        <span class="label">REGISTERED WORKPLACES</span>
        <span class="value">${locs.length > 0 ? locs.length : 1}</span>
        <span class="desc">Official subunits</span>
      </div>
      <div class="data-item">
        <span class="label">IDENTITY SCORE</span>
        <span class="value">${(c.score).toFixed(1)}/10</span>
        <span class="desc">Confidence rating</span>
      </div>
    </div>
  `;
  
  // Financials Tab
  let htmlFin = `
    <h2 class="section-title">Financial snapshot</h2>
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
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
      
      btn.classList.add('active');
      document.getElementById(`tab-${btn.dataset.tab}`).classList.add('active');
    });
  });
  
  document.querySelectorAll('.suggestion-tab').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.suggestion-tab').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      simulateAgent(btn.textContent);
    });
  });
}

function simulateAgent(query) {
  if (!selectedCompany) return;
  const input = document.getElementById('agentInput');
  const text = query || input.value || 'Company brief';
  input.value = '';
  
  const responseBox = document.getElementById('agentResponse');
  responseBox.innerHTML = `
    <h3 class="response-title">${text}</h3>
    <p class="response-text">
      <span class="material-symbols-outlined" style="animation: pulse 1.5s infinite; vertical-align: middle;">smart_toy</span>
      Analyzing registry data...
    </p>
  `;
  
  setTimeout(() => {
    let reply = "";
    if (text.toLowerCase().includes('run')) {
      reply = `${selectedCompany.name} is primarily operating in the "${selectedCompany.industry}" sector in ${selectedCompany.municipality}. The board and executive leadership can be seen in the Leadership tab.`;
    } else if (text.toLowerCase().includes('financial')) {
      reply = `According to the latest accounts, the operating result was registered as ${selectedCompany.score > 0 ? 'available' : 'unavailable'} in Regnskapsregisteret.`;
    } else {
      reply = `${selectedCompany.name} is a ${selectedCompany.form} registered in ${selectedCompany.municipality}. It is ${selectedCompany.bankrupt ? 'currently bankrupt' : (selectedCompany.liquidating ? 'under liquidation' : 'an active entity')}. We found ${selectedCompany.evidenceCount} out of 8 possible evidence modules in the Enhetsregisteret bulk run.`;
    }
    
    responseBox.innerHTML = `
      <h3 class="response-title">${text}</h3>
      <p class="response-text">${reply}</p>
    `;
  }, 800);
}
