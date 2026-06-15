// ===================================================================
//  API & STATE
// ===================================================================
const API_URL = 'http://localhost:5000/api';

let currentUser = null;
let currentResumeId = null;
let jobRoles = [];

// ===================================================================
//  INITIALISATION
// ===================================================================
document.addEventListener('DOMContentLoaded', () => {
    checkAuth();
    setupEventListeners();
});

// ===================================================================
//  AUTH  (unchanged)
// ===================================================================
function checkAuth() {
    const userData = localStorage.getItem('user');
    if (userData) {
        currentUser = JSON.parse(userData);
        showApp();
        loadDashboard();
    } else {
        showLogin();
    }
}

function setupEventListeners() {
    // ---- auth forms ----
    document.getElementById('login-form').addEventListener('submit', handleLogin);
    document.getElementById('register-form').addEventListener('submit', handleRegister);
    document.getElementById('show-register').addEventListener('click', () => {
        document.getElementById('login-page').style.display = 'none';
        document.getElementById('register-page').style.display = 'flex';
    });
    document.getElementById('show-login').addEventListener('click', () => {
        document.getElementById('register-page').style.display = 'none';
        document.getElementById('login-page').style.display = 'flex';
    });

    // ---- navigation ----
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const page = e.target.dataset.page;
            if (page) showPage(page);
        });
    });

    // ---- logout ----
    document.getElementById('logout-btn').addEventListener('click', handleLogout);

    // ---- dashboard ----
    document.getElementById('upload-new-btn').addEventListener('click', () => showPage('upload'));
    document.getElementById('analyze-again-btn').addEventListener('click', () => showPage('analysis'));

    // ---- upload ----
    document.getElementById('upload-form').addEventListener('submit', handleUpload);

    // ---- analysis ----
    document.getElementById('run-analysis-btn').addEventListener('click', runAnalysis);

    // ---- settings ----
    const clearBtn = document.getElementById('clear-data-btn');
    if (clearBtn) clearBtn.addEventListener('click', clearAllData);
}

// ===================================================================
//  AUTH  HELPERS
// ===================================================================
function showLogin() {
    document.getElementById('app').style.display = 'none';
    document.getElementById('register-page').style.display = 'none';
    document.getElementById('login-page').style.display = 'flex';
}

function showApp() {
    document.getElementById('login-page').style.display = 'none';
    document.getElementById('register-page').style.display = 'none';
    document.getElementById('app').style.display = 'flex';
    document.getElementById('user-info').textContent = currentUser.name;
}

function showPage(pageName) {
    document.querySelectorAll('.page').forEach(p => p.style.display = 'none');
    document.getElementById(`${pageName}-page`).style.display = 'block';
    document.getElementById('page-title').textContent = pageName.charAt(0).toUpperCase() + pageName.slice(1);

    document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
    document.querySelector(`[data-page="${pageName}"]`)?.classList.add('active');

    switch (pageName) {
        case 'dashboard':
            loadDashboard();
            break;
        case 'analysis':
            loadJobRoles();
            break;
        case 'profile':
            loadProfile();
            break;
    }
}

async function handleLogin(e) {
    e.preventDefault();
    const email = document.getElementById('login-email').value;
    const password = document.getElementById('login-password').value;

    try {
        const res = await fetch(`${API_URL}/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });
        const data = await res.json();
        if (res.ok) {
            currentUser = data;
            localStorage.setItem('user', JSON.stringify(data));
            showApp();
            loadDashboard();
        } else alert(data.error);
    } catch (e) {
        alert('Login failed. Check backend.');
    }
}

async function handleRegister(e) {
    e.preventDefault();
    const name = document.getElementById('register-name').value;
    const email = document.getElementById('register-email').value;
    const password = document.getElementById('register-password').value;

    try {
        const res = await fetch(`${API_URL}/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, email, password })
        });
        const data = await res.json();
        if (res.ok) {
            alert('Registration successful! Please login.');
            document.getElementById('show-login').click();
        } else alert(data.error);
    } catch (e) {
        alert('Registration failed.');
    }
}

function handleLogout() {
    localStorage.removeItem('user');
    currentUser = null;
    showLogin();
}

// ===================================================================
//  DASHBOARD  (with localStorage cache)
// ===================================================================
async function loadDashboard() {
    if (!currentUser) return;
    // 1.  try browser cache first (set after any analysis)
    const cached = localStorage.getItem('lastAnalysis');
    if (cached) {
        const data = JSON.parse(cached);
        document.getElementById('last-score').textContent = data.job_match_score + '%';
        document.getElementById('last-role').textContent = data.role_name;
        return;
    }
    // 2.  fall back to DB
    try {
        const res = await fetch(`${API_URL}/analysis/latest?user_id=${currentUser.user_id}`);
        if (res.ok) {
            const data = await res.json();
            document.getElementById('last-score').textContent = data.job_match_score + '%';
            document.getElementById('last-role').textContent = data.role_name;
        } else {
            document.getElementById('last-score').textContent = '--';
            document.getElementById('last-role').textContent = 'No analysis yet';
        }
    } catch (e) {
        console.error('Dashboard load error', e);
    }
}

// ===================================================================
//  UPLOAD
// ===================================================================
async function handleUpload(e) {
    e.preventDefault();
    const fileInput = document.getElementById('resume-file');
    const file = fileInput.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);
    formData.append('user_id', currentUser.user_id);

    const statusDiv = document.getElementById('upload-status');
    statusDiv.style.display = 'block';
    statusDiv.className = '';

    // Step 1: Check if backend is fully ready before uploading
    try {
        const healthRes = await fetch(`${API_URL}/health`, { signal: AbortSignal.timeout(5000) });
        if (!healthRes.ok) throw new Error('not ready');
    } catch {
        statusDiv.className = 'error';
        statusDiv.textContent = '⚠️ Backend is still loading AI models. Please wait 30-60 seconds and try again.';
        return;
    }

    // Step 2: Upload with a 150-second timeout (LLM needs ~90-120s on CPU)
    const uploadBtn = document.querySelector('#upload-form button[type="submit"]');
    if (uploadBtn) uploadBtn.disabled = true;

    let dotCount = 0;
    const loadingMessages = [
        '🤖 AI is reading your resume',
        '🧠 Extracting skills with LLM',
        '📋 Identifying projects & certifications',
        '✅ Almost done'
    ];
    let msgIndex = 0;
    statusDiv.textContent = loadingMessages[0] + '...';

    const loadingInterval = setInterval(() => {
        dotCount = (dotCount + 1) % 4;
        if (dotCount === 0) msgIndex = Math.min(msgIndex + 1, loadingMessages.length - 1);
        statusDiv.textContent = loadingMessages[msgIndex] + '.'.repeat(dotCount + 1);
    }, 1500);

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 150000); // 150s

    try {
        const res = await fetch(`${API_URL}/upload-resume`, {
            method: 'POST',
            body: formData,
            signal: controller.signal
        });
        clearTimeout(timeoutId);
        clearInterval(loadingInterval);

        const data = await res.json();
        if (res.ok) {
            statusDiv.className = 'success';
            statusDiv.textContent = `✅ Success! Found ${data.skill_count} skills. Redirecting...`;
            currentResumeId = data.resume_id;
            setTimeout(() => showPage('analysis'), 1500);
        } else {
            statusDiv.className = 'error';
            statusDiv.textContent = `❌ ${data.error || 'Upload failed.'}`;
        }
    } catch (err) {
        clearTimeout(timeoutId);
        clearInterval(loadingInterval);
        statusDiv.className = 'error';
        if (err.name === 'AbortError') {
            statusDiv.textContent = '⏱️ Request timed out. The AI model is very slow. Please try again.';
        } else {
            statusDiv.textContent = '❌ Upload failed. Make sure the backend server is running.';
        }
    } finally {
        if (uploadBtn) uploadBtn.disabled = false;
    }
}

// ===================================================================
//  ANALYSIS
// ===================================================================
async function loadJobRoles() {
    const select = document.getElementById('role-select');
    select.innerHTML = '<option value="">-- Select a role --</option>';
    try {
        const res = await fetch(`${API_URL}/job-roles`);
        const data = await res.json();
        data.roles.forEach(r => {
            const opt = document.createElement('option');
            opt.value = r.role_id;
            opt.textContent = `${r.role_name} (${r.industry})`;
            select.appendChild(opt);
        });
    } catch (e) {
        console.error('Load job-roles error', e);
    }
}

async function runAnalysis() {
    const roleId = document.getElementById('role-select').value;
    if (!roleId || !currentResumeId) {
        alert('Please select a job role and upload a resume first');
        return;
    }

    const btn = document.getElementById('run-analysis-btn');
    btn.disabled = true;
    btn.textContent = 'Analyzing...';

    try {
        const res = await fetch(`${API_URL}/analyze-role`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: currentUser.user_id,
                resume_id: currentResumeId,
                role_id: roleId
            })
        });
        const data = await res.json();
        if (res.ok) {
            displayAnalysisResults(data);
        } else {
            alert(data.error || 'Analysis failed');
        }
    } catch (e) {
        alert('Analysis failed. Check backend connection.');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Run Job Fit Analysis';
    }
}

// ------------------------------------------------------------------
//  RICH ROADMAP RENDERER  (Fix 3: steps + curated resources per skill)
// ------------------------------------------------------------------

const RESOURCE_ICONS = {
    docs:     '📖',
    course:   '🎓',
    practice: '🔨',
    video:    '▶',
};

function renderRoadmap(rec) {
    let html = '';

    // ── SHORT TERM — one card per missing skill ──────────────────────────────
    html += '<h4 class="roadmap-section-title">🚀 Short-term Learning Path (1–3 months)</h4>';

    if (!rec.short_term || !rec.short_term.length) {
        html += '<p>No specific learning path available.</p>';
    } else {
        rec.short_term.forEach((item, idx) => {
            const hours       = item.hours || 10;
            const steps       = Array.isArray(item.steps) ? item.steps : [];
            const resources   = Array.isArray(item.resources) ? item.resources : [];
            const project     = item.project || '';
            const certificate = item.certificate || '';

            // Group resources by type
            const grouped = {};
            resources.forEach(r => {
                const t = r.type || 'other';
                if (!grouped[t]) grouped[t] = [];
                grouped[t].push(r);
            });

            // Build resources HTML
            let resHtml = '';
            const order = ['docs', 'course', 'practice', 'video'];
            order.forEach(type => {
                if (!grouped[type] || !grouped[type].length) return;
                const icon  = RESOURCE_ICONS[type] || '🔗';
                const label = type === 'docs' ? 'Documentation' :
                              type === 'course' ? 'Courses' :
                              type === 'practice' ? 'Practice' : 'Video Tutorials';
                resHtml += `<div class="resource-group">`;
                resHtml += `<span class="resource-label">${icon} ${label}</span><ul class="resource-list">`;
                grouped[type].forEach(r => {
                    resHtml += `<li><a href="${r.url}" target="_blank" rel="noopener">${r.title}</a></li>`;
                });
                resHtml += `</ul></div>`;
            });

            // Build step list HTML
            const stepsHtml = steps.length
                ? '<ol class="prep-steps">' + steps.map(s => `<li>${s}</li>`).join('') + '</ol>'
                : '<p style="color:var(--text-muted)">Follow the resources below to get started.</p>';

            html += `
            <div class="roadmap-card" style="animation-delay:${idx * 0.08}s">
              <div class="roadmap-card-header">
                <h5 class="roadmap-skill-name">🎯 ${item.skill}</h5>
                <span class="hours-badge">⏱ ${hours}h est.</span>
              </div>

              <div class="roadmap-section">
                <p class="roadmap-label">📋 Preparation Steps</p>
                ${stepsHtml}
              </div>

              ${resHtml ? `<div class="roadmap-section"><p class="roadmap-label">📚 Learning Resources</p>${resHtml}</div>` : ''}

              <div class="roadmap-footer">
                ${project ? `<div class="roadmap-meta"><span>🔨</span><span><strong>Project:</strong> ${project}</span></div>` : ''}
                ${certificate ? `<div class="roadmap-meta"><span>🏅</span><span><strong>Certificate:</strong> ${certificate}</span></div>` : ''}
              </div>
            </div>`;
        });
    }

    // ── MEDIUM TERM ─────────────────────────────────────────────────────────
    if (rec.medium_term && rec.medium_term.length) {
        html += '<h4 class="roadmap-section-title" style="margin-top:1.5rem">📈 Medium-term Goals (3–6 months)</h4><ul class="roadmap-goals">';
        rec.medium_term.forEach(m => html += `<li>✅ ${m}</li>`);
        html += '</ul>';
    }

    // ── LONG TERM ────────────────────────────────────────────────────────────
    if (rec.long_term && rec.long_term.length) {
        html += '<h4 class="roadmap-section-title" style="margin-top:1.5rem">🏆 Long-term Vision (6–12 months)</h4><ul class="roadmap-goals">';
        rec.long_term.forEach(l => html += `<li>🌟 ${l}</li>`);
        html += '</ul>';
    }

    return html;
}


function displayAnalysisResults(data) {
    document.getElementById('analysis-results').style.display = 'block';
    document.getElementById('match-score').textContent = data.job_match_score + '%';

    // skills lists (unchanged)
    const matchedList = document.getElementById('matched-skills');
    matchedList.innerHTML = '';
    data.matched_skills.forEach(s => {
        const li = document.createElement('li');
        li.textContent = s;
        matchedList.appendChild(li);
    });
    const missingList = document.getElementById('missing-skills');
    missingList.innerHTML = '';
    data.missing_skills.forEach(s => {
        const li = document.createElement('li');
        li.textContent = s;
        missingList.appendChild(li);
    });

    // NEW  skill-specific roadmap
    document.getElementById('recommendations').innerHTML = renderRoadmap(data.recommendations);

    // keep last result in browser so dashboard can show it without DB
    localStorage.setItem('lastAnalysis', JSON.stringify(data));
}

// ===================================================================
//  PROFILE  (placeholder)
// ===================================================================
function loadProfile() {
    document.getElementById('profile-name').textContent = currentUser.name;
    document.getElementById('profile-email').textContent = currentUser.email;
    document.getElementById('recent-analyses').innerHTML = '<p>No recent analyses to display.</p>';
}

// ===================================================================
//  SETTINGS  –  Clear all data
// ===================================================================
async function clearAllData() {
    if (!currentUser) { alert('You must be logged in.'); return; }
    if (!confirm('Delete ALL your stored data (uploads, analyses, account)? This cannot be undone.')) return;

    try {
        const res = await fetch(`${API_URL}/clear-data`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: currentUser.user_id })
        });
        const msg = await res.json();
        if (res.ok) {
            alert(msg.message);
            localStorage.clear();
            location.href = '/';
        } else {
            alert(msg.error || 'Clear failed');
        }
    } catch (e) {
        alert('Clear failed. Check backend connection.');
    }
}

// ------------------------------------------------------------------
//  Analyse vs free-text description
// ------------------------------------------------------------------
document.getElementById('analyze-text-btn').addEventListener('click', async () => {
    const jobText = document.getElementById('job-description').value.trim();
    if (!jobText) { alert('Please paste a job description.'); return; }
    if (!currentResumeId) { alert('Upload a résumé first.'); return; }

    const btn = document.getElementById('analyze-text-btn');
    btn.disabled = true;
    btn.textContent = 'Analysing...';

    try {
        const res = await fetch(`${API_URL}/analyze-text`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: currentUser.user_id,
                resume_id: currentResumeId,
                job_description: jobText
            })
        });
        const data = await res.json();
        if (res.ok) {
            displayAnalysisResults(data);   // reuse existing renderer
        } else {
            alert(data.error || 'Analysis failed');
        }
    } catch (e) {
        alert('Analysis failed. Check backend connection.');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Analyze vs This Description';
    }
});