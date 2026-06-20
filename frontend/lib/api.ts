// All API calls hit the Flask backend directly (since Flask has CORS enabled)
const API = 'http://127.0.0.1:5000/api';

// ── Auth ──────────────────────────────────────────────────────────────────────
export async function apiLogin(email: string, password: string) {
  const res = await fetch(`${API}/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  return { res, data: await res.json() };
}

export async function apiRegister(name: string, email: string, password: string) {
  const res = await fetch(`${API}/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, email, password }),
  });
  return { res, data: await res.json() };
}

// ── Health ────────────────────────────────────────────────────────────────────
export async function apiHealth() {
  const res = await fetch(`${API}/health`, { signal: AbortSignal.timeout(5000) });
  return res.ok;
}

// ── Resume Upload ─────────────────────────────────────────────────────────────
export async function apiUploadResume(
  file: File,
  userId: string,
  signal: AbortSignal,
) {
  const form = new FormData();
  form.append('file', file);
  form.append('user_id', userId);
  const res = await fetch(`${API}/upload-resume`, { method: 'POST', body: form, signal });
  return { res, data: await res.json() };
}

// ── Job Roles ─────────────────────────────────────────────────────────────────
export async function apiGetJobRoles() {
  const res = await fetch(`${API}/job-roles`);
  const data = await res.json();
  return data.roles as { role_id: string; role_name: string; industry: string }[];
}

// ── Analyze vs Role ───────────────────────────────────────────────────────────
export async function apiAnalyzeRole(userId: string, resumeId: string, roleId: string) {
  const res = await fetch(`${API}/analyze-role`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: userId, resume_id: resumeId, role_id: roleId }),
  });
  return { res, data: await res.json() };
}

// ── Analyze vs Free Text ──────────────────────────────────────────────────────
export async function apiAnalyzeText(userId: string, resumeId: string, jobDescription: string) {
  const res = await fetch(`${API}/analyze-text`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: userId, resume_id: resumeId, job_description: jobDescription }),
  });
  return { res, data: await res.json() };
}

// ── Latest Analysis ───────────────────────────────────────────────────────────
export async function apiGetLatestAnalysis(userId: string) {
  const res = await fetch(`${API}/analysis/latest?user_id=${userId}`);
  if (!res.ok) return null;
  return await res.json();
}

// ── Clear Data ────────────────────────────────────────────────────────────────
export async function apiClearData(userId: string) {
  const res = await fetch(`${API}/clear-data`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: userId }),
  });
  return { res, data: await res.json() };
}
