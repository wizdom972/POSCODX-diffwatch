/* ─── 세션 ID (대화 맥락 유지) ────────────────────────────── */
const SESSION_ID = crypto.randomUUID();

/* ─── 페이지 전환 ─────────────────────────────────────────── */
function navigate(page) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.getElementById(`page-${page}`).classList.add('active');
  document.querySelector(`[data-page="${page}"]`).classList.add('active');

  if (page === 'dashboard') loadAll();
  if (page === 'commits') loadChanges();
  if (page === 'notifications') loadNotifications();
}

/* ─── 데이터 로드 ─────────────────────────────────────────── */
async function loadAll() {
  await Promise.all([loadStats(), loadRecentCommits()]);
}

async function loadStats() {
  const res = await fetch('/api/stats');
  const d = await res.json();
  document.getElementById('stat-total').textContent = d.total_commits;
  document.getElementById('stat-high').textContent = d.high_impact;
  document.getElementById('stat-mid').textContent = d.mid_impact;
  document.getElementById('stat-low').textContent = d.low_impact;
  document.getElementById('stat-notif').textContent = d.total_notifications;
}

async function loadRecentCommits() {
  const res = await fetch('/api/changes');
  const data = await res.json();
  document.getElementById('recent-commits').innerHTML =
    renderCommitsTable(data.slice(0, 5));
}

async function loadChanges() {
  const res = await fetch('/api/changes');
  const data = await res.json();
  document.getElementById('all-commits').innerHTML = renderCommitsTable(data);
}

async function loadNotifications() {
  const res = await fetch('/api/notifications');
  const data = await res.json();
  const el = document.getElementById('notif-list');

  if (!data.length) {
    el.innerHTML = '<div class="empty">발송된 알림이 없습니다.</div>';
    return;
  }

  el.innerHTML = data.map(n => `
    <div class="notif-card">
      <div class="notif-meta">
        <span>🕐 ${n.sent_at || ''}</span>
        <span>👤 ${n.recipients || ''}</span>
      </div>
      <div class="notif-subject">${n.subject || ''}</div>
      <div class="notif-body">${n.body || ''}</div>
    </div>
  `).join('');
}

/* ─── 테이블 렌더 ─────────────────────────────────────────── */
function badgeHtml(level) {
  const map = { '높음': 'high', '중간': 'mid', '낮음': 'low' };
  const cls = map[level] || 'unknown';
  return `<span class="badge badge-${cls}">${level || '미분류'}</span>`;
}

function renderCommitsTable(data) {
  if (!data.length) return '<div class="empty">분석된 커밋이 없습니다.</div>';

  const rows = data.map(c => `
    <tr onclick="openModal(${JSON.stringify(c).replace(/"/g, '&quot;')})">
      <td><span class="hash">${c.short_hash || ''}</span></td>
      <td>${c.summary || ''}</td>
      <td>${badgeHtml(c.impact_level)}</td>
      <td>${(c.affected_files || []).length}개</td>
      <td>${c.saved_at || ''}</td>
    </tr>
  `).join('');

  return `
    <table>
      <thead>
        <tr>
          <th>커밋</th>
          <th>요약</th>
          <th>영향도</th>
          <th>변경 파일</th>
          <th>분석 일시</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}

/* ─── 커밋 상세 모달 ──────────────────────────────────────── */
function openModal(commit) {
  const files = (commit.affected_files || [])
    .map(f => `<div>${f}</div>`).join('');
  const stakeholders = (commit.stakeholders || []).join(', ');

  document.getElementById('modal-content').innerHTML = `
    <h2 style="margin-bottom:20px">${commit.summary || '커밋 상세'}</h2>
    <div class="modal-row">
      <strong>커밋 해시</strong>
      <span class="hash">${commit.commit_hash || commit.short_hash}</span>
    </div>
    <div class="modal-row">
      <strong>영향도</strong>
      ${badgeHtml(commit.impact_level)}
    </div>
    <div class="modal-row">
      <strong>분석 일시</strong>${commit.saved_at || ''}
    </div>
    <div class="modal-row">
      <strong>변경 파일 (${(commit.affected_files||[]).length}개)</strong>
      <div class="files-list">${files}</div>
    </div>
    <div class="modal-row">
      <strong>알림 담당자</strong>${stakeholders || '없음'}
    </div>
    ${commit.details ? `
    <div class="modal-row">
      <strong>상세 분석</strong>
      <div style="white-space:pre-wrap;font-size:13px;line-height:1.6;color:#a0a8c0">${commit.details}</div>
    </div>` : ''}
  `;
  document.getElementById('commit-modal').classList.remove('hidden');
}

function closeModal() {
  document.getElementById('commit-modal').classList.add('hidden');
}

document.addEventListener('keydown', e => {
  if (e.key === 'Escape') closeModal();
});

/* ─── 챗봇 패널 ───────────────────────────────────────────── */
let chatOpen = false;

function toggleChat() {
  chatOpen = !chatOpen;
  document.getElementById('chat-panel').classList.toggle('open', chatOpen);
  document.getElementById('fab-icon').textContent = chatOpen ? '✕' : '💬';
  if (chatOpen) document.getElementById('chat-input').focus();
}

async function sendMessage() {
  const input = document.getElementById('chat-input');
  const text = input.value.trim();
  if (!text) return;

  appendMessage('user', text);
  input.value = '';
  input.disabled = true;
  document.querySelector('.chat-input-row button').disabled = true;

  const typingEl = appendMessage('assistant', '답변 생성 중...', true);

  try {
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text, session_id: SESSION_ID }),
    });

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let fullText = '';
    typingEl.classList.remove('typing');
    typingEl.textContent = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value, { stream: true });
      for (const line of chunk.split('\n')) {
        if (!line.startsWith('data:')) continue;
        const data = JSON.parse(line.slice(5).trim());
        if (data.token) {
          fullText += data.token;
          typingEl.textContent = fullText;
          scrollChat();
        }
      }
    }

    if (!fullText) typingEl.textContent = '(응답 없음)';
  } catch (e) {
    typingEl.textContent = '오류가 발생했습니다. 서버를 확인해주세요.';
    typingEl.classList.remove('typing');
  }

  input.disabled = false;
  document.querySelector('.chat-input-row button').disabled = false;
  input.focus();
}

function appendMessage(role, text, isTyping = false) {
  const el = document.createElement('div');
  el.className = `chat-msg ${role}${isTyping ? ' typing' : ''}`;
  el.textContent = text;
  const container = document.getElementById('chat-messages');
  container.appendChild(el);
  scrollChat();
  return el;
}

function scrollChat() {
  const c = document.getElementById('chat-messages');
  c.scrollTop = c.scrollHeight;
}

/* ─── 초기 로드 ───────────────────────────────────────────── */
loadAll();
