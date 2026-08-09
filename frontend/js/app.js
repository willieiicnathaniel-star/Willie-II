/* THEeye - Frontend Application Logic v2.0
   Auth + Quick Generate + Literature Discovery + Extraction + Drafting + Audit */

const API_BASE = '';
const TOKEN_KEY = 'theeye_token';
const USER_KEY = 'theeye_user';

let authToken = localStorage.getItem(TOKEN_KEY);
let currentUser = null;
try { currentUser = JSON.parse(localStorage.getItem(USER_KEY)); } catch { currentUser = null; }

let currentSearchResults = [];
let selectedPaperIndices = new Set();

// ---------------------------------------------------------------------------
// Auth wrapper: all API calls go through this
// ---------------------------------------------------------------------------

async function apiFetch(url, options = {}) {
    const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
    if (authToken) {
        headers['Authorization'] = `Bearer ${authToken}`;
    }
    const resp = await fetch(`${API_BASE}${url}`, { ...options, headers });
    if (resp.status === 401) {
        // Token expired or invalid — force re-login
        clearAuth();
        showAuthScreen();
        throw new Error('Session expired. Please login again.');
    }
    return resp;
}

// ---------------------------------------------------------------------------
// Auth state management
// ---------------------------------------------------------------------------

function saveAuth(token, user) {
    authToken = token;
    currentUser = user;
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(USER_KEY, JSON.stringify(user));
}

function clearAuth() {
    authToken = null;
    currentUser = null;
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
}

function showAuthScreen() {
    document.getElementById('authScreen').style.display = 'flex';
    document.getElementById('mainApp').style.display = 'none';
}

function showMainApp() {
    document.getElementById('authScreen').style.display = 'none';
    document.getElementById('mainApp').style.display = 'block';
    if (currentUser) {
        document.getElementById('userName').textContent = currentUser.name || 'User';
        document.getElementById('userEmail').textContent = currentUser.email || '';
    }
    updateAdminVisibility();
}

// Admin tab visibility: only show admin tab/panel if currentUser.role === 'admin'
function updateAdminVisibility() {
    const isAdmin = currentUser && currentUser.role === 'admin';
    document.querySelectorAll('.admin-only').forEach(el => {
        el.style.display = isAdmin ? '' : 'none';
    });
    const adminPanel = document.getElementById('admin');
    if (adminPanel && !isAdmin) {
        adminPanel.classList.remove('active');
    }
}

function showAuthError(elementId, message) {
    const el = document.getElementById(elementId);
    el.style.display = 'block';
    el.textContent = message;
}

function hideAuthError(elementId) {
    document.getElementById(elementId).style.display = 'none';
}

// Login
document.getElementById('loginBtn').addEventListener('click', async () => {
    const email = document.getElementById('loginEmail').value.trim();
    const password = document.getElementById('loginPassword').value;
    hideAuthError('loginError');

    if (!email || !password) {
        showAuthError('loginError', 'Please enter your email and password.');
        return;
    }

    const btn = document.getElementById('loginBtn');
    btn.disabled = true;
    btn.textContent = 'Logging in...';

    try {
        const resp = await fetch(`${API_BASE}/api/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password }),
        });
        const data = await resp.json();
        if (!resp.ok) throw new Error(data.detail || 'Login failed');

        saveAuth(data.token, data.user);
        showMainApp();
    } catch (err) {
        showAuthError('loginError', err.message);
    } finally {
        btn.disabled = false;
        btn.textContent = 'Login';
    }
});

// Register
document.getElementById('registerBtn').addEventListener('click', async () => {
    const name = document.getElementById('regName').value.trim();
    const email = document.getElementById('regEmail').value.trim();
    const password = document.getElementById('regPassword').value;
    const institution = document.getElementById('regInstitution').value.trim();
    const research_field = document.getElementById('regField').value.trim();
    hideAuthError('registerError');

    if (!name || !email || !password) {
        showAuthError('registerError', 'Name, email, and password are required.');
        return;
    }

    const btn = document.getElementById('registerBtn');
    btn.disabled = true;
    btn.textContent = 'Registering...';

    try {
        const resp = await fetch(`${API_BASE}/api/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, email, password, institution, research_field }),
        });
        const data = await resp.json();
        if (!resp.ok) throw new Error(data.detail || 'Registration failed');

        saveAuth(data.token, data.user);
        showMainApp();
    } catch (err) {
        showAuthError('registerError', err.message);
    } finally {
        btn.disabled = false;
        btn.textContent = 'Register';
    }
});

// Switch between login and register
document.getElementById('switchToRegister').addEventListener('click', (e) => {
    e.preventDefault();
    document.getElementById('loginForm').classList.remove('active');
    document.getElementById('registerForm').classList.add('active');
    hideAuthError('loginError');
});

document.getElementById('switchToLogin').addEventListener('click', (e) => {
    e.preventDefault();
    document.getElementById('registerForm').classList.remove('active');
    document.getElementById('loginForm').classList.add('active');
    hideAuthError('registerError');
});

// Logout
document.getElementById('logoutBtn').addEventListener('click', async () => {
    try {
        await apiFetch('/api/auth/logout', { method: 'POST' });
    } catch { /* ignore — we clear locally anyway */ }
    clearAuth();
    showAuthScreen();
});

// Enter key on login
document.getElementById('loginPassword').addEventListener('keypress', e => {
    if (e.key === 'Enter') document.getElementById('loginBtn').click();
});
document.getElementById('loginEmail').addEventListener('keypress', e => {
    if (e.key === 'Enter') document.getElementById('loginPassword').focus();
});

// On page load: check if already authenticated
(async function init() {
    if (authToken) {
        try {
            const resp = await apiFetch('/api/auth/me');
            if (resp.ok) {
                const user = await resp.json();
                currentUser = user;
                localStorage.setItem(USER_KEY, JSON.stringify(user));
                showMainApp();
                return;
            }
        } catch { /* fall through */ }
        clearAuth();
    }
    showAuthScreen();
})();

// ---------------------------------------------------------------------------
// Tab navigation
// ---------------------------------------------------------------------------

document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => switchTab(tab));
});

function switchTab(tab) {
    // Guard admin tab: only admins may open it
    if (tab.dataset.tab === 'admin' && !(currentUser && currentUser.role === 'admin')) {
        return;
    }
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    tab.classList.add('active');
    document.getElementById(tab.dataset.tab).classList.add('active');
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function showStatus(elementId, message, type = 'loading') {
    const el = document.getElementById(elementId);
    el.style.display = 'block';
    el.className = `status-message ${type}`;
    el.innerHTML = type === 'loading'
        ? `<span class="spinner"></span>${message}`
        : message;
}

function hideStatus(elementId) {
    document.getElementById(elementId).style.display = 'none';
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ---------------------------------------------------------------------------
// AI-enhanced content helpers
// Renders a lightweight, safe subset of Markdown to HTML for AI output.
// ---------------------------------------------------------------------------
function renderMarkdown(md) {
    if (!md) return '';
    let html = escapeHtml(md);

    // Protect fenced code blocks so their contents are not reformatted
    const codeBlocks = [];
    html = html.replace(/```([\s\S]*?)```/g, (m, code) => {
        codeBlocks.push(code);
        return '\u0000CB' + (codeBlocks.length - 1) + '\u0000';
    });

    // Headings (longest first so prefixes don't shadow shorter ones)
    html = html.replace(/^######\s+(.+)$/gm, '<h6>$1</h6>')
        .replace(/^#####\s+(.+)$/gm, '<h5>$1</h5>')
        .replace(/^####\s+(.+)$/gm, '<h4>$1</h4>')
        .replace(/^###\s+(.+)$/gm, '<h3>$1</h3>')
        .replace(/^##\s+(.+)$/gm, '<h2>$1</h2>')
        .replace(/^#\s+(.+)$/gm, '<h1>$1</h1>');

    // Horizontal rule
    html = html.replace(/^---+\s*$/gm, '<hr>');

    // Inline formatting
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
        .replace(/\*([^*]+)\*/g, '<em>$1</em>')
        .replace(/`([^`]+)`/g, '<code>$1</code>');

    // Blockquotes (the '>' is escaped to '&gt;')
    html = html.replace(/^&gt;\s?(.+)$/gm, '<blockquote>$1</blockquote>');

    // List items (unordered + ordered)
    html = html.replace(/^\s*[-*+]\s+(.+)$/gm, '<li>$1</li>')
        .replace(/^\s*\d+\.\s+(.+)$/gm, '<li>$1</li>');

    // Wrap consecutive list items in <ul> and strip stray newlines inside
    html = html.replace(/(?:<li>[\s\S]*?<\/li>\n?)+/g, m => '<ul>' + m + '</ul>');
    html = html.replace(/<ul>([\s\S]*?)<\/ul>/g, (m, inner) => '<ul>' + inner.replace(/\n/g, '') + '</ul>');

    // Line breaks
    html = html.replace(/\n/g, '<br>');

    // Restore fenced code blocks
    html = html.replace(/\u0000CB(\d+)\u0000/g, (m, i) => '<pre><code>' + codeBlocks[+i] + '</code></pre>');

    return '<div class="ai-markdown">' + html + '</div>';
}

// Badge that identifies which AI model produced a given piece of content
function aiModelBadge(modelUsed) {
    if (!modelUsed) return '';
    return '<span class="ai-model-badge">&#10024; AI: ' + escapeHtml(modelUsed) + '</span>';
}

// "AI Enhanced" badge for drafts whose disclaimer signals AI assistance
function aiEnhancedBadge(disclaimer) {
    if (disclaimer && disclaimer.indexOf('AI-assisted content generated by') !== -1) {
        return '<span class="ai-model-badge">&#10024; AI Enhanced</span>';
    }
    return '';
}

function formatAuthors(authors, max = 3) {
    if (!authors || authors.length === 0) return 'Unknown';
    const names = authors.slice(0, max).map(a => a.name);
    if (authors.length > max) return `${names[0]} et al.`;
    if (names.length === 1) return names[0];
    return names.slice(0, -1).join(', ') + ' & ' + names[names.length - 1];
}

// ---------------------------------------------------------------------------
// Quick Generate (single prompt -> final output)
// ---------------------------------------------------------------------------

document.getElementById('quickGenBtn').addEventListener('click', quickGenerate);

document.getElementById('quickPrompt').addEventListener('keydown', e => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
        e.preventDefault();
        quickGenerate();
    }
});


async function quickGenerate() {
    const prompt = document.getElementById('quickPrompt').value.trim();
    if (!prompt) {
        showStatus('quickGenStatus', 'Please type a research prompt first.', 'error');
        return;
    }

    const sectionType = document.getElementById('quickSectionType').value;
    const maxResults = parseInt(document.getElementById('quickMaxResults').value) || 15;
    const maxWords = parseInt(document.getElementById('quickMaxWords').value) || 1000;
    const quartiles = Array.from(document.querySelectorAll('.quick-q'))
        .filter(cb => cb.checked).map(cb => cb.value);
    const yearFrom = document.getElementById('quickYearFrom').value;
    const yearTo = document.getElementById('quickYearTo').value;

    const body = {
        prompt,
        section_type: sectionType,
        databases: ['openalex', 'crossref', 'semantic_scholar', 'google_scholar', 'econpapers', 'eric'],
        quartiles: quartiles.length ? quartiles : ['Q1', 'Q2', 'Q3'],
        year_from: yearFrom ? parseInt(yearFrom) : null,
        year_to: yearTo ? parseInt(yearTo) : null,
        max_results: maxResults,
        max_words: maxWords,
    };

    const btn = document.getElementById('quickGenBtn');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Generating...';

    showStatus('quickGenStatus',
        `Searching databases, extracting data, and generating your ${sectionType.replace('_', ' ')}... This may take 30-60 seconds.`,
        'loading');
    document.getElementById('quickGenResults').innerHTML = '';

    try {
        const resp = await apiFetch('/api/research/quick-generate', {
            method: 'POST',
            body: JSON.stringify(body),
        });

        const data = await resp.json();
        if (!resp.ok) throw new Error(data.detail || 'Generation failed');

        hideStatus('quickGenStatus');
        showStatus('quickGenStatus',
            `Done! Found ${data.total_sources} papers, generated ${data.draft.word_count} words with ${data.draft.citations.length} citations.`,
            'success');

        renderQuickGenResults(data);

        // Also populate search results so other tabs can use them
        currentSearchResults = data.papers;
        selectedPaperIndices.clear();
        updateExtractTab();
    } catch (err) {
        showStatus('quickGenStatus', `Generation failed: ${err.message}`, 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '&#9889; Generate Research Output';
    }
}

function renderQuickGenResults(data) {
    const container = document.getElementById('quickGenResults');

    // Store raw text for copying
    const rawDraftText = data.draft.content;
    window._lastQuickGenText = rawDraftText;
    window._lastQuickGenCitations = data.draft.citations || [];
    window._lastQuickGenDisclaimer = data.draft.disclaimer || '';
    window._lastQuickGenSectionType = data.section_type || '';
    window._lastQuickGenTopic = data.topic || '';
    window._lastQuickGenWordCount = data.draft.word_count || 0;
    window._lastQuickGenTotalSources = data.total_sources || 0;

    // Draft output
    let htmlContent = escapeHtml(data.draft.content)
        .replace(/^## (.+)$/gm, '<h2>$1</h2>')
        .replace(/^### (.+)$/gm, '<h3>$1</h3>')
        .replace(/\n\n/g, '</p><p>')
        .replace(/\n/g, '<br>');
    htmlContent = `<p>${htmlContent}</p>`;

    // Citations
    const citationsHtml = data.draft.citations.length > 0 ? `
        <div class="citation-list">
            <h4>References (${data.draft.citations.length})</h4>
            <ol>
                ${data.draft.citations.map(c => `
                    <li>${escapeHtml(c.authors)} (${c.year}). ${escapeHtml(c.title)}.
                        <em>${escapeHtml(c.journal)}</em>.
                        ${c.quartile && c.quartile !== 'N/A' ? `<span class="quartile-badge ${c.quartile.toLowerCase()}" style="font-size:0.7rem;">${c.quartile}</span>` : ''}
                        ${c.doi ? `<a href="https://doi.org/${c.doi}" target="_blank">${c.doi}</a>` : ''}
                    </li>
                `).join('')}
            </ol>
        </div>
    ` : '';

    // Source papers summary
    const papersHtml = data.papers.length > 0 ? `
        <div class="source-papers-section">
            <h3>Source Papers (${data.papers.length})</h3>
            <div class="results-container">
                ${data.papers.slice(0, 10).map(p => {
                    const qBadge = p.quartile
                        ? `<span class="quartile-badge ${p.quartile.toLowerCase()}">${p.quartile}</span>`
                        : '';
                    return `
                    <div class="paper-card ${p.quartile ? 'quartile-' + p.quartile.toLowerCase() : ''}">
                        <div class="paper-title">${escapeHtml(p.title)}</div>
                        <div class="paper-meta">
                            <span>&#9998; ${escapeHtml(formatAuthors(p.authors))}</span>
                            <span>&#128197; ${p.year || 'N/A'}</span>
                            <span>&#128218; ${escapeHtml(p.journal || 'N/A')}</span>
                            <span>&#128202; ${p.cited_by_count} citations</span>
                            ${qBadge}
                            ${p.doi ? `<a href="https://doi.org/${p.doi}" target="_blank" style="color:var(--accent);text-decoration:none;">DOI</a>` : ''}
                        </div>
                    </div>`;
                }).join('')}
                ${data.papers.length > 10 ? `<p style="text-align:center;color:var(--text-light);font-size:0.85rem;">...and ${data.papers.length - 10} more papers</p>` : ''}
            </div>
        </div>
    ` : '';

    // Comparison table (if extracted data exists)
    const tableHtml = data.comparison_table && data.comparison_table.length > 0 ? `
        <div class="comparison-section">
            <h3>Data Extraction Comparison</h3>
            <table class="extract-table">
                <thead>
                    <tr>
                        <th>Paper</th>
                        <th>Methodology</th>
                        <th>Sample</th>
                        <th>Variables</th>
                        <th>Key Finding</th>
                    </tr>
                </thead>
                <tbody>
                    ${data.comparison_table.slice(0, 10).map(row => `
                        <tr>
                            <td style="max-width:200px;">${escapeHtml((row.paper || '').substring(0, 80))}${(row.paper || '').length > 80 ? '...' : ''}</td>
                            <td>${escapeHtml(row.methodology || 'N/A')}</td>
                            <td>${escapeHtml(row.sample || 'N/A')}</td>
                            <td style="font-size:0.8rem;">${escapeHtml(row.variables || 'N/A')}</td>
                            <td style="max-width:200px;font-size:0.8rem;">${escapeHtml((row.key_finding || '').substring(0, 120))}${(row.key_finding || '').length > 120 ? '...' : ''}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>
    ` : '';

    // Build citations text for copying
    const citationsText = data.draft.citations.length > 0
        ? '\n\nReferences:\n' + data.draft.citations.map((c, i) =>
            `[${i + 1}] ${c.authors} (${c.year}). ${c.title}. ${c.journal}.${c.doi ? ' https://doi.org/' + c.doi : ''}`
        ).join('\n')
        : '';

    const fullTextToCopy = rawDraftText + citationsText + '\n\n' + data.draft.disclaimer;

    container.innerHTML = `
        <div class="draft-toolbar">
            <button class="btn-copy" onclick="copyGeneratedText(this, ${JSON.stringify(fullTextToCopy).replace(/'/g, "&#39;")})">
                &#128203; Copy Text
            </button>
            <button class="btn-verify" onclick="verifyAcademicFormat(${JSON.stringify(rawDraftText).replace(/'/g, "&#39;")})">
                &#128269; Verify Academic Format
            </button>
            <button class="btn-secondary btn-sm" onclick="downloadDraft(${JSON.stringify(rawDraftText + citationsText).replace(/'/g, "&#39;")}, '${escapeHtml(data.topic).replace(/'/g, "\\'").substring(0, 50)}')">
                &#128190; Download as .txt
            </button>
            <button class="btn-secondary btn-sm" onclick="exportDocument('docx', this)">
                &#128196; Word
            </button>
            <button class="btn-secondary btn-sm" onclick="exportDocument('pdf', this)">
                &#128196; PDF
            </button>
            <button class="btn-secondary btn-sm" onclick="exportDocument('html', this)">
                &#128196; HTML
            </button>
            <button class="btn-secondary btn-sm" onclick="exportDocument('md', this)">
                &#128196; Markdown
            </button>
        </div>
        <div class="draft-output">
            ${htmlContent}
        </div>
        ${citationsHtml}
        <div class="draft-disclaimer">
            <strong>&#9888; Integrity Notice:</strong> ${escapeHtml(data.draft.disclaimer)}
        </div>
        <div class="draft-meta">
            ${aiEnhancedBadge(data.draft.disclaimer)}
            <span>Section: ${escapeHtml(data.section_type)}</span>
            <span>Topic: ${escapeHtml(data.topic)}</span>
            <span>Words: ${data.draft.word_count}</span>
            <span>Sources: ${data.total_sources}</span>
        </div>
        ${tableHtml}
        ${papersHtml}
    `;
}

// ---------------------------------------------------------------------------
// Copy / Verify / Download utility functions
// ---------------------------------------------------------------------------

function copyGeneratedText(btn, text) {
    // Use the Clipboard API with fallback
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(() => {
            const original = btn.innerHTML;
            btn.innerHTML = '&#10003; Copied!';
            btn.classList.add('copied');
            setTimeout(() => {
                btn.innerHTML = original;
                btn.classList.remove('copied');
            }, 2000);
        }).catch(() => {
            _copyFallback(btn, text);
        });
    } else {
        _copyFallback(btn, text);
    }
}

function _copyFallback(btn, text) {
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.style.position = 'fixed';
    textarea.style.opacity = '0';
    document.body.appendChild(textarea);
    textarea.select();
    try {
        document.execCommand('copy');
        const original = btn.innerHTML;
        btn.innerHTML = '&#10003; Copied!';
        btn.classList.add('copied');
        setTimeout(() => {
            btn.innerHTML = original;
            btn.classList.remove('copied');
        }, 2000);
    } catch (err) {
        alert('Copy failed. Please select the text manually and use Ctrl+C.');
    }
    document.body.removeChild(textarea);
}

function verifyAcademicFormat(text) {
    // Switch to the Literature Discovery tab (where the verification panel lives)
    switchTab('search');

    // Paste the text into the verification textarea
    const textInput = document.getElementById('verifyTextInput');
    if (textInput) {
        textInput.value = text;
        textInput.focus();
    }

    // Scroll to the verification panel
    setTimeout(() => {
        const verifyPanel = document.querySelector('.verify-panel');
        if (verifyPanel) {
            verifyPanel.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
        // Show a helpful notice
        showStatus('verifyStatus',
            'Text loaded from Quick Generate. Click "Check Academic Format" to verify your text, or click "Copy Text" to copy it.',
            'loading');
        setTimeout(() => hideStatus('verifyStatus'), 5000);
    }, 300);
}

function downloadDraft(text, topic) {
    const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `theeye_${topic.replace(/[^a-zA-Z0-9]/g, '_').substring(0, 40)}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

async function exportDocument(format, btn) {
    const text = window._lastQuickGenText || '';
    const citations = window._lastQuickGenCitations || [];
    const disclaimer = window._lastQuickGenDisclaimer || '';
    const sectionType = window._lastQuickGenSectionType || '';
    const topic = window._lastQuickGenTopic || '';
    const wordCount = window._lastQuickGenWordCount || 0;
    const totalSources = window._lastQuickGenTotalSources || 0;

    if (!text) {
        alert('No text to export. Please generate content first.');
        return;
    }

    const originalHTML = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Exporting...';

    try {
        const resp = await apiFetch('/api/research/export-document', {
            method: 'POST',
            body: JSON.stringify({
                text: text,
                title: 'THEeye Research Output',
                citations: citations,
                disclaimer: disclaimer,
                section_type: sectionType,
                topic: topic,
                word_count: wordCount,
                total_sources: totalSources,
                format: format,
            }),
        });

        if (!resp.ok) {
            const errData = await resp.json().catch(() => ({}));
            throw new Error(errData.detail || 'Export failed');
        }

        const blob = await resp.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;

        const contentDisp = resp.headers.get('Content-Disposition');
        let filename = 'THEeye_research.' + format;
        if (contentDisp) {
            const match = contentDisp.match(/filename="?(.+?)"?$/);
            if (match) filename = match[1];
        }
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    } catch (err) {
        alert('Export failed: ' + err.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalHTML;
    }
}

// ---------------------------------------------------------------------------
// Search
// ---------------------------------------------------------------------------

document.getElementById('searchBtn').addEventListener('click', performSearch);
document.getElementById('searchQuery').addEventListener('keypress', e => {
    if (e.key === 'Enter') performSearch();
});

// ---------------------------------------------------------------------------
// Academic Format Verification (Literature Discovery tab)
// ---------------------------------------------------------------------------

document.getElementById('verifyFormatBtn').addEventListener('click', verifyTextFormat);
document.getElementById('verifyCopyBtn').addEventListener('click', function() {
    const text = document.getElementById('verifyTextInput').value.trim();
    if (!text) {
        showStatus('verifyStatus', 'Nothing to copy. Paste some text first.', 'error');
        setTimeout(() => hideStatus('verifyStatus'), 3000);
        return;
    }
    copyGeneratedText(this, text);
});
document.getElementById('verifyClearBtn').addEventListener('click', function() {
    document.getElementById('verifyTextInput').value = '';
    document.getElementById('verifyResults').innerHTML = '';
    hideStatus('verifyStatus');
    document.getElementById('verifyTextInput').focus();
});

async function verifyTextFormat() {
    const text = document.getElementById('verifyTextInput').value.trim();
    if (!text) {
        showStatus('verifyStatus', 'Please paste some text to verify.', 'error');
        return;
    }

    const btn = document.getElementById('verifyFormatBtn');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Verifying...';
    showStatus('verifyStatus', 'Analyzing your text for academic format compliance...', 'loading');
    document.getElementById('verifyResults').innerHTML = '';

    try {
        const resp = await apiFetch('/api/writing/analyze', {
            method: 'POST',
            body: JSON.stringify({ text }),
        });
        if (!resp.ok) {
            const errData = await resp.json().catch(() => ({}));
            throw new Error(errData.detail || `HTTP ${resp.status}`);
        }
        const data = await resp.json();

        if (data.error) {
            throw new Error(data.error);
        }

        hideStatus('verifyStatus');
        showStatus('verifyStatus', 'Academic format verification complete.', 'success');
        setTimeout(() => hideStatus('verifyStatus'), 4000);
        renderVerifyResults(data);
    } catch (err) {
        showStatus('verifyStatus', `Verification failed: ${err.message}`, 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '&#128270; Check Academic Format';
    }
}

function renderVerifyResults(data) {
    const container = document.getElementById('verifyResults');

    const wordCount = data.word_count || 0;
    const sentenceCount = data.sentence_count || 0;
    const avgSentLen = data.avg_sentence_length || 'N/A';
    const readability = data.readability || {};
    const fleschScore = readability.flesch_reading_ease != null ? readability.flesch_reading_ease : 'N/A';
    const gradeLevel = readability.flesch_grade_level != null ? readability.flesch_grade_level : 'N/A';
    const gunningFog = readability.gunning_fog_index != null ? readability.gunning_fog_index : 'N/A';
    const readLabel = readability.label || 'N/A';
    const passiveCount = data.passive_voice_count || 0;
    const academicRatio = data.academic_ratio != null ? data.academic_ratio + '%' : 'N/A';
    const toneAssessment = data.tone_assessment || 'N/A';
    const transitionCount = data.transition_count || 0;
    const overallScore = data.overall_score != null ? data.overall_score : 'N/A';
    const suggestions = data.suggestions || [];

    const scoreColor = overallScore >= 80 ? 'var(--success)' : overallScore >= 60 ? 'var(--warning)' : 'var(--danger)';
    const scoreLabel = overallScore >= 80 ? 'Excellent academic format' : overallScore >= 60 ? 'Good, with room for improvement' : 'Needs significant revision';

    // Build checklist items
    const checklist = [];
    checklist.push({
        label: 'Academic Tone',
        status: toneAssessment.includes('Strongly') || toneAssessment.includes('Academic') ? 'pass' : (toneAssessment.includes('Somewhat') ? 'warn' : 'fail'),
        detail: toneAssessment,
    });
    checklist.push({
        label: 'Readability',
        status: readLabel === 'Good' ? 'pass' : (readLabel === 'Moderate' ? 'warn' : 'fail'),
        detail: `Flesch: ${fleschScore} (${readLabel})`,
    });
    checklist.push({
        label: 'Sentence Length',
        status: avgSentLen > 25 ? 'warn' : (avgSentLen < 10 ? 'warn' : 'pass'),
        detail: `Avg ${avgSentLen} words/sentence`,
    });
    checklist.push({
        label: 'Passive Voice',
        status: passiveCount > sentenceCount * 0.3 ? 'warn' : 'pass',
        detail: `${passiveCount} instances found`,
    });
    checklist.push({
        label: 'Transition Words',
        status: transitionCount < sentenceCount * 0.2 ? 'warn' : 'pass',
        detail: `${transitionCount} transitions detected`,
    });
    checklist.push({
        label: 'Academic Vocabulary',
        status: data.academic_ratio >= 3 ? 'pass' : (data.academic_ratio >= 1 ? 'warn' : 'fail'),
        detail: `${academicRatio} academic ratio`,
    });

    const checklistHtml = checklist.map(item => {
        const icon = item.status === 'pass' ? '&#9989;' : item.status === 'warn' ? '&#9888;' : '&#10060;';
        const color = item.status === 'pass' ? 'var(--success)' : item.status === 'warn' ? 'var(--warning)' : 'var(--danger)';
        return `
            <div style="display:flex;align-items:center;gap:0.5rem;padding:0.5rem 0;border-bottom:1px solid var(--border);">
                <span style="font-size:1.1rem;">${icon}</span>
                <span style="font-weight:600;min-width:160px;">${item.label}</span>
                <span style="color:${color};font-size:0.85rem;">${escapeHtml(item.detail)}</span>
            </div>
        `;
    }).join('');

    const suggestionsHtml = suggestions.length ? `
        <div class="paper-card" style="margin-top:1rem;">
            <div class="paper-title">Improvement Suggestions (${suggestions.length})</div>
            <ul style="margin-top:0.5rem;padding-left:1.25rem;">
                ${suggestions.map(s => {
                    const msg = typeof s === 'string' ? s : s.message || s.text || JSON.stringify(s);
                    const sev = (typeof s === 'object' && s.severity) ? s.severity : '';
                    const sevColor = sev === 'high' ? 'var(--danger)' : sev === 'medium' ? 'var(--warning)' : 'var(--text-light)';
                    return `<li style="margin-bottom:0.4rem;">${sev ? `<span style="color:${sevColor};font-weight:600;font-size:0.75rem;text-transform:uppercase;">${sev}</span> ` : ''}${escapeHtml(msg)}</li>`;
                }).join('')}
            </ul>
        </div>` : '<p style="color:var(--success);margin-top:1rem;font-weight:600;">&#9989; No issues found. Your text follows proper academic format.</p>';

    container.innerHTML = `
        <div class="writing-score-banner" style="background:var(--surface);border-radius:var(--radius);padding:1.5rem;margin-bottom:1rem;text-align:center;border:2px solid ${scoreColor};">
            <div style="font-size:0.85rem;color:var(--text-light);margin-bottom:0.25rem;">Academic Format Score</div>
            <div style="font-size:2.5rem;font-weight:700;color:${scoreColor};">${overallScore}<span style="font-size:1rem;color:var(--text-light);">/100</span></div>
            <div style="font-size:0.9rem;color:${scoreColor};margin-top:0.25rem;font-weight:600;">${escapeHtml(scoreLabel)}</div>
        </div>

        <div class="paper-card" style="margin-bottom:1rem;">
            <div class="paper-title">Format Checklist</div>
            <div style="margin-top:0.5rem;">
                ${checklistHtml}
            </div>
        </div>

        <div class="writing-stats-grid">
            <div class="stat-card">
                <span class="stat-label">Word Count</span>
                <span class="stat-value">${wordCount}</span>
            </div>
            <div class="stat-card">
                <span class="stat-label">Sentences</span>
                <span class="stat-value">${sentenceCount}</span>
            </div>
            <div class="stat-card">
                <span class="stat-label">Avg Sentence Length</span>
                <span class="stat-value">${avgSentLen}</span>
            </div>
            <div class="stat-card">
                <span class="stat-label">Flesch Reading Ease</span>
                <span class="stat-value">${fleschScore}</span>
            </div>
            <div class="stat-card">
                <span class="stat-label">Grade Level</span>
                <span class="stat-value">${gradeLevel}</span>
            </div>
            <div class="stat-card">
                <span class="stat-label">Gunning Fog</span>
                <span class="stat-value">${gunningFog}</span>
            </div>
            <div class="stat-card">
                <span class="stat-label">Passive Voice</span>
                <span class="stat-value">${passiveCount}</span>
            </div>
            <div class="stat-card">
                <span class="stat-label">Academic Ratio</span>
                <span class="stat-value">${academicRatio}</span>
            </div>
            <div class="stat-card">
                <span class="stat-label">Transition Words</span>
                <span class="stat-value">${transitionCount}</span>
            </div>
        </div>
        ${suggestionsHtml}
    `;

    // Scroll to results
    setTimeout(() => {
        container.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 200);
}

async function performSearch() {
    const query = document.getElementById('searchQuery').value.trim();
    if (!query) return;

    const databases = Array.from(document.querySelectorAll('.search-db'))
        .filter(cb => cb.checked).map(cb => cb.value);
    const quartiles = Array.from(document.querySelectorAll('.search-q'))
        .filter(cb => cb.checked).map(cb => cb.value);
    const yearFrom = document.getElementById('yearFrom').value;
    const yearTo = document.getElementById('yearTo').value;
    const minCitations = document.getElementById('minCitations').value;
    const maxResults = document.getElementById('maxResults').value;

    const body = {
        query,
        databases: databases.length ? databases : ['openalex', 'crossref', 'semantic_scholar'],
        quartiles: quartiles.length ? quartiles : ['Q1', 'Q2', 'Q3'],
        year_from: yearFrom ? parseInt(yearFrom) : null,
        year_to: yearTo ? parseInt(yearTo) : null,
        min_citations: minCitations ? parseInt(minCitations) : 0,
        max_results: maxResults ? parseInt(maxResults) : 25,
    };

    showStatus('searchStatus', `Searching ${databases.join(', ')} for "${query}"...`, 'loading');
    document.getElementById('searchResults').innerHTML = '';

    try {
        const resp = await apiFetch('/api/search', {
            method: 'POST',
            body: JSON.stringify(body),
        });

        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();

        currentSearchResults = data.papers;
        selectedPaperIndices.clear();

        hideStatus('searchStatus');

        if (data.papers.length === 0) {
            document.getElementById('searchResults').innerHTML =
                '<p class="placeholder-text">No papers found matching your criteria. Try broadening your search.</p>';
            return;
        }

        showStatus('searchStatus',
            `Found ${data.total_found} papers across ${databases.join(', ')}. Sorted by citation count.`,
            'success');

        renderSearchResults(data.papers);
        updateExtractTab();
    } catch (err) {
        showStatus('searchStatus', `Search failed: ${err.message}`, 'error');
    }
}

function renderSearchResults(papers) {
    const container = document.getElementById('searchResults');
    container.innerHTML = papers.map((p, i) => {
        const qClass = p.quartile ? `quartile-${p.quartile.toLowerCase()}` : '';
        const qBadge = p.quartile
            ? `<span class="quartile-badge ${p.quartile.toLowerCase()}">${p.quartile}</span>`
            : '<span class="quartile-badge unknown">N/A</span>';

        const abstract = p.abstract
            ? `<div class="paper-abstract">${escapeHtml(p.abstract.substring(0, 400))}${p.abstract.length > 400 ? '...' : ''}</div>`
            : '';

        const tldr = p.tldr
            ? `<div class="paper-tldr"><span class="paper-tldr-label">AI TLDR:</span> ${escapeHtml(p.tldr)}</div>`
            : '';

        const doiLink = p.doi
            ? `<a href="https://doi.org/${p.doi}" target="_blank" style="color:var(--accent);text-decoration:none;">DOI</a>`
            : '';

        const oaLink = p.is_open_access && p.oa_url
            ? `<a href="${p.oa_url}" target="_blank" style="color:var(--success);text-decoration:none;">Open Access PDF</a>`
            : '';

        const concepts = p.concepts && p.concepts.length
            ? `<span>&#127991; ${p.concepts.join(', ')}</span>`
            : '';

        return `
        <div class="paper-card ${qClass}">
            <div style="display:flex;align-items:flex-start;gap:0.5rem;">
                <input type="checkbox" class="paper-checkbox" data-index="${i}" ${selectedPaperIndices.has(i) ? 'checked' : ''}>
                <div style="flex:1;">
                    <div class="paper-title">${escapeHtml(p.title)}</div>
                    <div class="paper-meta">
                        <span>&#9998; ${escapeHtml(formatAuthors(p.authors))}</span>
                        <span>&#128197; ${p.year || 'N/A'}</span>
                        <span>&#128218; ${escapeHtml(p.journal || 'N/A')}</span>
                        <span>&#128202; ${p.cited_by_count} citations</span>
                        ${qBadge}
                        <span style="font-size:0.7rem;opacity:0.6;">${p.source_db}</span>
                        ${doiLink}
                        ${oaLink}
                    </div>
                    ${concepts}
                    ${abstract}
                    ${tldr}
                </div>
            </div>
        </div>`;
    }).join('');

    container.querySelectorAll('.paper-checkbox').forEach(cb => {
        cb.addEventListener('change', e => {
            const idx = parseInt(e.target.dataset.index);
            if (e.target.checked) selectedPaperIndices.add(idx);
            else selectedPaperIndices.delete(idx);
            updateExtractTab();
        });
    });
}

// ---------------------------------------------------------------------------
// Data Extraction
// ---------------------------------------------------------------------------

function updateExtractTab() {
    const listEl = document.getElementById('extractPapersList');
    const extractBtn = document.getElementById('extractBtn');

    // Keep the references tab paper count in sync
    const refCountEl = document.getElementById('referencesPaperCount');
    if (refCountEl) refCountEl.textContent = currentSearchResults.length;

    if (currentSearchResults.length === 0) {
        listEl.innerHTML = '<p class="placeholder-text">Run a search first, then select papers to extract data from.</p>';
        extractBtn.disabled = true;
        return;
    }

    const selected = Array.from(selectedPaperIndices);
    if (selected.length === 0) {
        listEl.innerHTML = `<p class="placeholder-text">${currentSearchResults.length} papers available from your search. Select papers using the checkboxes on the Search tab, or click "Extract from All" below.</p>`;
        extractBtn.disabled = true;
    } else {
        listEl.innerHTML = `<p style="padding:0.75rem;background:#ebf8ff;border-radius:5px;font-size:0.875rem;">
            <strong>${selected.length}</strong> paper(s) selected for extraction.
        </p>`;
        extractBtn.disabled = false;
    }

    document.getElementById('extractAllBtn').disabled = currentSearchResults.length === 0;
}

document.getElementById('extractBtn').addEventListener('click', () => extractPapers(false));
document.getElementById('extractAllBtn').addEventListener('click', () => extractPapers(true));

async function extractPapers(all) {
    const indices = all
        ? currentSearchResults.map((_, i) => i)
        : Array.from(selectedPaperIndices);

    if (indices.length === 0) return;

    const papers = indices.map(i => currentSearchResults[i]);

    showStatus('extractStatus', `Extracting structured data from ${papers.length} paper(s)...`, 'loading');
    document.getElementById('extractResults').innerHTML = '';

    try {
        const resp = await apiFetch('/api/extract/batch', {
            method: 'POST',
            body: JSON.stringify({ papers, use_llm: false }),
        });

        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();

        hideStatus('extractStatus');
        showStatus('extractStatus',
            `Successfully extracted data from ${data.total_papers} papers. Comparison table below.`,
            'success');

        renderExtractResults(data);
    } catch (err) {
        showStatus('extractStatus', `Extraction failed: ${err.message}`, 'error');
    }
}

function renderExtractResults(data) {
    const container = document.getElementById('extractResults');

    const tableHtml = `
        <table class="extract-table">
            <thead>
                <tr>
                    <th>Paper</th>
                    <th>Methodology</th>
                    <th>Sample</th>
                    <th>Variables</th>
                    <th>Key Finding</th>
                    <th>Effect Size</th>
                </tr>
            </thead>
            <tbody>
                ${data.comparison_table.map(row => `
                    <tr>
                        <td style="max-width:250px;">${escapeHtml(row.paper.substring(0, 100))}${row.paper.length > 100 ? '...' : ''}<br><span style="font-size:0.7rem;color:var(--text-light);">${row.doi}</span></td>
                        <td>${escapeHtml(row.methodology)}</td>
                        <td>${escapeHtml(row.sample)}</td>
                        <td style="font-size:0.8rem;">${escapeHtml(row.variables)}</td>
                        <td style="max-width:250px;font-size:0.8rem;">${escapeHtml(row.key_finding.substring(0, 150))}${row.key_finding.length > 150 ? '...' : ''}</td>
                        <td>${escapeHtml(row.effect_size)}</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;

    const detailsHtml = data.extracted_data.map((ext, i) => `
        <div class="paper-card">
            <div class="paper-title">${i + 1}. ${escapeHtml(ext.paper_title)}</div>
            <div class="paper-meta">
                ${ext.doi ? `<span>DOI: ${ext.doi}</span>` : ''}
                <span>Method: ${escapeHtml(ext.methodology || 'N/A')}</span>
                <span>Extraction: ${ext.extraction_method}</span>
            </div>
            ${ext.research_question ? `<div style="margin-top:0.5rem;font-size:0.875rem;"><strong>RQ:</strong> ${escapeHtml(ext.research_question)}</div>` : ''}
            ${ext.variables && ext.variables.length ? `<div style="margin-top:0.5rem;font-size:0.825rem;"><strong>Variables:</strong> ${ext.variables.map(escapeHtml).join(', ')}</div>` : ''}
            ${ext.key_findings && ext.key_findings.length ? `
                <div style="margin-top:0.5rem;font-size:0.825rem;"><strong>Key Findings:</strong>
                    <ul style="margin-top:0.25rem;padding-left:1.25rem;">
                        ${ext.key_findings.map(f => `<li>${escapeHtml(f)}</li>`).join('')}
                    </ul>
                </div>` : ''}
            ${ext.limitations ? `<div style="margin-top:0.5rem;font-size:0.825rem;color:var(--text-light);"><strong>Limitations:</strong> ${escapeHtml(ext.limitations)}</div>` : ''}
        </div>
    `).join('');

    container.innerHTML = tableHtml + '<h3 style="margin-top:1.5rem;color:var(--primary);">Detailed Extraction</h3>' + detailsHtml;
}

// ---------------------------------------------------------------------------
// Drafting
// ---------------------------------------------------------------------------

document.getElementById('draftBtn').addEventListener('click', generateDraftSection);

async function generateDraftSection() {
    const sectionType = document.getElementById('sectionType').value;
    const topic = document.getElementById('draftTopic').value.trim();
    const maxWords = parseInt(document.getElementById('maxWords').value) || 1000;

    if (!topic) {
        showStatus('draftStatus', 'Please enter a research topic.', 'error');
        return;
    }

    if (currentSearchResults.length === 0) {
        showStatus('draftStatus', 'Please run a search first to gather source papers for the draft.', 'error');
        return;
    }

    const papers = selectedPaperIndices.size > 0
        ? Array.from(selectedPaperIndices).map(i => currentSearchResults[i])
        : currentSearchResults.slice(0, 15);

    showStatus('draftStatus', `Generating ${sectionType.replace('_', ' ')} draft from ${papers.length} source papers...`, 'loading');
    document.getElementById('draftResults').innerHTML = '';

    try {
        const resp = await apiFetch('/api/draft', {
            method: 'POST',
            body: JSON.stringify({
                section_type: sectionType,
                topic,
                papers,
                extracted_data: [],
                style: 'academic',
                use_llm: false,
                max_words: maxWords,
            }),
        });

        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();

        hideStatus('draftStatus');
        showStatus('draftStatus',
            `Draft generated: ${data.word_count} words, ${data.citations.length} citations.`,
            'success');

        renderDraftResults(data);
    } catch (err) {
        showStatus('draftStatus', `Drafting failed: ${err.message}`, 'error');
    }
}

function renderDraftResults(data) {
    const container = document.getElementById('draftResults');

    let htmlContent = escapeHtml(data.content)
        .replace(/^## (.+)$/gm, '<h2>$1</h2>')
        .replace(/^### (.+)$/gm, '<h3>$1</h3>')
        .replace(/\n\n/g, '</p><p>')
        .replace(/\n/g, '<br>');

    htmlContent = `<p>${htmlContent}</p>`;

    const citationsHtml = data.citations.length > 0 ? `
        <div class="citation-list">
            <h4>References (${data.citations.length})</h4>
            <ol>
                ${data.citations.map(c => `
                    <li>${escapeHtml(c.authors)} (${c.year}). ${escapeHtml(c.title)}.
                        <em>${escapeHtml(c.journal)}</em>.
                        ${c.quartile !== 'N/A' ? `<span class="quartile-badge ${c.quartile.toLowerCase()}" style="font-size:0.7rem;">${c.quartile}</span>` : ''}
                        ${c.doi ? `<a href="https://doi.org/${c.doi}" target="_blank">${c.doi}</a>` : ''}
                    </li>
                `).join('')}
            </ol>
        </div>
    ` : '';

    // Build citations text for copying
    const citationsText = data.citations.length > 0
        ? '\n\nReferences:\n' + data.citations.map((c, i) =>
            `[${i + 1}] ${c.authors} (${c.year}). ${c.title}. ${c.journal}.${c.doi ? ' https://doi.org/' + c.doi : ''}`
        ).join('\n')
        : '';

    const fullTextToCopy = data.content + citationsText + '\n\n' + data.disclaimer;

    container.innerHTML = `
        <div class="draft-toolbar">
            <button class="btn-copy" onclick="copyGeneratedText(this, ${JSON.stringify(fullTextToCopy).replace(/'/g, "&#39;")})">
                &#128203; Copy Text
            </button>
            <button class="btn-verify" onclick="verifyAcademicFormat(${JSON.stringify(data.content).replace(/'/g, "&#39;")})">
                &#128269; Verify Academic Format
            </button>
            <button class="btn-secondary btn-sm" onclick="downloadDraft(${JSON.stringify(data.content + citationsText).replace(/'/g, "&#39;")}, '${escapeHtml(data.topic).replace(/'/g, "\\'").substring(0, 50)}')">
                &#128190; Download as .txt
            </button>
        </div>
        <div class="draft-output">
            ${htmlContent}
        </div>
        ${citationsHtml}
        <div class="draft-disclaimer">
            <strong>&#9888; Integrity Notice:</strong> ${escapeHtml(data.disclaimer)}
        </div>
        <div class="draft-meta">
            ${aiEnhancedBadge(data.disclaimer)}
            <span>Section: ${escapeHtml(data.section_type)}</span>
            <span>Topic: ${escapeHtml(data.topic)}</span>
            <span>Words: ${data.word_count}</span>
            <span>Sources: ${data.citations.length}</span>
        </div>
    `;
}

// ---------------------------------------------------------------------------
// Audit
// ---------------------------------------------------------------------------

document.getElementById('createSessionBtn').addEventListener('click', createAuditSession);
document.getElementById('refreshSessionsBtn').addEventListener('click', loadSessions);

async function createAuditSession() {
    showStatus('auditStatus', 'Creating audit session...', 'loading');
    try {
        const resp = await apiFetch('/api/audit/session', { method: 'POST' });
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();
        hideStatus('auditStatus');
        showStatus('auditStatus', `Session created: ${data.session_id}`, 'success');
        loadSessions();
    } catch (err) {
        showStatus('auditStatus', `Failed: ${err.message}`, 'error');
    }
}

async function loadSessions() {
    try {
        const resp = await apiFetch('/api/audit/sessions');
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();

        const container = document.getElementById('sessionsList');
        if (data.sessions.length === 0) {
            container.innerHTML = '<p class="placeholder-text">No audit sessions yet. Create one to start tracking.</p>';
            return;
        }

        container.innerHTML = data.sessions.map(s => `
            <div class="audit-session-card">
                <div class="session-info">
                    <span class="session-id">Session: ${s.session_id}</span>
                    <span class="session-meta">Created: ${new Date(s.created_at).toLocaleString()} | Records: ${s.record_count}</span>
                </div>
                <div style="display:flex;gap:0.5rem;align-items:center;">
                    <span class="verification-badge ${s.verification_status}">${s.verification_status}</span>
                    <button class="btn-secondary" style="padding:0.4rem 0.8rem;font-size:0.8rem;" onclick="loadAuditReport('${s.session_id}')">View Report</button>
                </div>
            </div>
        `).join('');
    } catch (err) {
        showStatus('auditStatus', `Failed to load sessions: ${err.message}`, 'error');
    }
}

async function loadAuditReport(sessionId) {
    try {
        const resp = await apiFetch(`/api/audit/${sessionId}`);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();

        const container = document.getElementById('auditReport');
        const recordsHtml = data.records.length > 0
            ? data.records.map(r => `
                <div class="audit-record ${r.ai_generated ? 'ai' : ''} ${r.human_verified ? 'verified' : ''}">
                    <span class="record-action">${r.action.toUpperCase()}</span>
                    <span class="record-time">${new Date(r.timestamp).toLocaleString()}</span>
                    <div style="margin-top:0.25rem;">${escapeHtml(r.query_or_input)}</div>
                    <div style="font-size:0.75rem;color:var(--text-light);margin-top:0.25rem;">
                        ${r.details || ''}
                        ${r.ai_generated ? ' | AI-Generated' : ''}
                        ${r.human_verified ? ' | &#10003; Verified' : ' | Pending verification'}
                    </div>
                </div>
            `).join('')
            : '<p class="placeholder-text">No records in this session yet.</p>';

        container.innerHTML = `
            <div style="margin-top:1.5rem;">
                <h3 style="color:var(--primary);margin-bottom:0.75rem;">Audit Report: ${data.session_id}</h3>
                <div class="paper-meta" style="margin-bottom:1rem;">
                    <span>Total sources: ${data.total_sources}</span>
                    <span>AI-assisted sections: ${data.ai_assisted_sections.length || 'None'}</span>
                    <span class="verification-badge ${data.verification_status}">${data.verification_status}</span>
                </div>
                <div class="disclosure-box">
                    <h4>&#128221; AI Use Disclosure Statement</h4>
                    <p>${escapeHtml(data.disclosure_statement)}</p>
                </div>
                <h4 style="margin-top:1.5rem;color:var(--primary);">Provenance Records (${data.records.length})</h4>
                <div style="margin-top:0.75rem;">
                    ${recordsHtml}
                </div>
            </div>
        `;
    } catch (err) {
        showStatus('auditStatus', `Failed to load report: ${err.message}`, 'error');
    }
}

window.loadAuditReport = loadAuditReport;

// ===========================================================================
// DATA ANALYSIS
// ===========================================================================

let currentDatasetPath = '';
let currentDatasetInfo = null;

// ---- Sub-tab switching ----
document.querySelectorAll('.analysis-subtab').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.analysis-subtab').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const target = btn.dataset.subtab;
        document.querySelectorAll('.analysis-subpanel').forEach(p => {
            p.classList.remove('active');
            p.style.display = 'none';
        });
        const panel = document.getElementById('analysis' + target);
        if (panel) { panel.classList.add('active'); panel.style.display = 'block'; }
    });
});

// ---- Upload zone ----
const uploadZone = document.getElementById('uploadZone');
const datasetFile = document.getElementById('datasetFile');

if (uploadZone) {
    uploadZone.addEventListener('click', () => datasetFile.click());
    uploadZone.addEventListener('dragover', e => { e.preventDefault(); uploadZone.classList.add('drag-over'); });
    uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('drag-over'));
    uploadZone.addEventListener('drop', e => {
        e.preventDefault();
        uploadZone.classList.remove('drag-over');
        if (e.dataTransfer.files.length > 0) {
            datasetFile.files = e.dataTransfer.files;
            uploadDataset(e.dataTransfer.files[0]);
        }
    });
}

if (datasetFile) {
    datasetFile.addEventListener('change', e => {
        if (e.target.files.length > 0) uploadDataset(e.target.files[0]);
    });
}

document.getElementById('clearDatasetBtn')?.addEventListener('click', clearDataset);

async function uploadDataset(file) {
    showStatus('analysisStatus', `Uploading ${file.name}...`, 'loading');
    const fd = new FormData();
    fd.append('file', file);
    try {
        const r = await apiFetch('/api/analysis/upload-dataset', { method: 'POST', body: fd });
        const d = await r.json();
        if (!r.ok) throw new Error(d.detail || 'Upload failed');
        currentDatasetInfo = d.dataset;
        currentDatasetPath = d.dataset._temp_path || '';
        renderDatasetPreview(d.dataset);
        hideStatus('analysisStatus');
        showStatus('analysisStatus', `Dataset loaded: ${d.dataset.n_rows} rows, ${d.dataset.n_cols} columns.`, 'success');
    } catch (err) {
        showStatus('analysisStatus', `Upload error: ${err.message}`, 'error');
    }
}

function renderDatasetPreview(ds) {
    const prev = document.getElementById('datasetPreview');
    const info = document.getElementById('datasetInfo');
    const tbl = document.getElementById('datasetTable');
    prev.style.display = 'block';

    const missingCount = Object.keys(ds.missing_values || {}).length;
    info.innerHTML = `<strong>${ds.n_rows} rows</strong> &times; <strong>${ds.n_cols} columns</strong>` +
        (missingCount > 0 ? ` &nbsp;|&nbsp; <span style="color:#e53e3e;">${missingCount} columns with missing values</span>` : '');

    if (ds.head && ds.head.length > 0) {
        const cols = Object.keys(ds.head[0]);
        let html = '<table class="data-table"><thead><tr>';
        cols.forEach(c => html += `<th>${escapeHtml(c)}</th>`);
        html += '</tr></thead><tbody>';
        ds.head.forEach(row => {
            html += '<tr>';
            cols.forEach(c => {
                const v = row[c];
                html += `<td>${v === null || v === undefined || v === 'N/A' ? '<span style="color:#cbd5e0;">N/A</span>' : escapeHtml(String(v).substring(0, 50))}</td>`;
            });
            html += '</tr>';
        });
        html += '</tbody></table>';
        tbl.innerHTML = html;
    }

    // Populate column info below table
    if (ds.dtypes) {
        let dtypeHtml = '<div style="margin-top:0.5rem;font-size:0.8rem;color:#718096;">';
        Object.entries(ds.dtypes).forEach(([col, dt]) => {
            const color = dt.includes('int') || dt.includes('float') ? '#3182ce' : '#805ad5';
            dtypeHtml += `<span style="margin-right:0.75rem;"><span style="color:${color};">${escapeHtml(col)}</span> (${dt})</span>`;
        });
        dtypeHtml += '</div>';
        tbl.innerHTML += dtypeHtml;
    }
}

function clearDataset() {
    currentDatasetPath = '';
    currentDatasetInfo = null;
    document.getElementById('datasetPreview').style.display = 'none';
    document.getElementById('datasetFile').value = '';
    document.getElementById('analysisResults').innerHTML = '';
    hideStatus('analysisStatus');
}

// ---- Quick commands ----
document.querySelectorAll('.quick-cmd').forEach(btn => {
    btn.addEventListener('click', () => {
        document.getElementById('analysisInstruction').value = btn.dataset.cmd;
        document.getElementById('analysisInstruction').focus();
    });
});

// ---- Run analysis ----
document.getElementById('runAnalysisBtn')?.addEventListener('click', async () => {
    const inst = document.getElementById('analysisInstruction').value.trim();
    if (!inst) { showStatus('analysisStatus', 'Type an analysis instruction first.', 'error'); return; }
    if (!currentDatasetPath) { showStatus('analysisStatus', 'Please upload a dataset first.', 'error'); return; }

    const btn = document.getElementById('runAnalysisBtn');
    const tool = document.getElementById('analysisTool').value;
    const fmt = document.getElementById('plotFormat').value;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Running...';
    showStatus('analysisStatus', 'Executing analysis...', 'loading');

    try {
        const r = await apiFetch('/api/analysis/run', {
            method: 'POST',
            body: JSON.stringify({ instruction: inst, tool, dataset_path: currentDatasetPath })
        });
        const d = await r.json();
        if (!r.ok) throw new Error(d.detail || 'Analysis failed');
        hideStatus('analysisStatus');
        renderAnalysisResults(d.result, fmt);
        showStatus('analysisStatus', 'Analysis complete.', 'success');
    } catch (err) {
        showStatus('analysisStatus', `Error: ${err.message}`, 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '&#9654; Run Analysis';
    }
});

function renderAnalysisResults(result, format) {
    const container = document.getElementById('analysisResults');
    let html = '';

    // Text output
    if (result.text_output && result.text_output.trim()) {
        html += `<div class="result-card"><div class="result-card-header"><h4>&#128221; Text Output</h4></div><pre class="result-text">${escapeHtml(result.text_output.trim())}</pre></div>`;
    }

    // Plots
    if (result.plots && result.plots.length > 0) {
        html += '<div class="result-card"><div class="result-card-header"><h4>&#128250; Visualizations</h4></div><div class="plots-grid">';
        result.plots.forEach((plot, i) => {
            const mime = format === 'jpg' ? 'image/jpeg' : format === 'svg' ? 'image/svg+xml' : format === 'pdf' ? 'application/pdf' : 'image/png';
            html += `<div class="plot-item">
                <div class="plot-title">${escapeHtml(plot.title)}</div>
                <img src="data:${mime};base64,${plot.image}" alt="${escapeHtml(plot.title)}" class="plot-img" />
                <button class="btn-secondary btn-sm download-plot" data-b64="${plot.image}" data-title="${escapeHtml(plot.title)}" data-fmt="${format}">&#11015; Download ${format.toUpperCase()}</button>
            </div>`;
        });
        html += '</div></div>';
    }

    // Tables
    if (result.tables && result.tables.length > 0) {
        result.tables.forEach(tbl => {
            html += `<div class="result-card"><div class="result-card-header"><h4>&#128202; ${escapeHtml(tbl.title)}</h4></div>`;
            const data = tbl.data;
            if (data && typeof data === 'object') {
                // Check if it's a dict of dicts (like describe output) or key-value
                const keys = Object.keys(data);
                if (keys.length > 0 && typeof data[keys[0]] === 'object') {
                    // Dict of dicts - render as table
                    const subKeys = Object.keys(data[keys[0]]);
                    html += '<table class="data-table"><thead><tr><th></th>';
                    subKeys.forEach(sk => html += `<th>${escapeHtml(sk)}</th>`);
                    html += '</tr></thead><tbody>';
                    keys.forEach(k => {
                        html += `<tr><td><strong>${escapeHtml(k)}</strong></td>`;
                        subKeys.forEach(sk => {
                            const v = data[k][sk];
                            html += `<td>${v !== null && v !== undefined ? (typeof v === 'number' ? v.toFixed(4) : escapeHtml(String(v))) : ''}</td>`;
                        });
                        html += '</tr>';
                    });
                    html += '</tbody></table>';
                } else {
                    // Key-value pairs
                    html += '<table class="data-table"><tbody>';
                    keys.forEach(k => {
                        const v = data[k];
                        html += `<tr><td><strong>${escapeHtml(k)}</strong></td><td>${typeof v === 'number' ? v.toFixed(4) : escapeHtml(String(v))}</td></tr>`;
                    });
                    html += '</tbody></table>';
                }
            }
            html += '</div>';
        });
    }

    // Generated code
    if (result.code_generated && result.code_generated.trim()) {
        html += `<div class="result-card"><div class="result-card-header"><h4>&#128187; Generated Code (${escapeHtml(document.getElementById('analysisTool').value)})</h4>
            <button class="btn-secondary btn-sm" onclick="navigator.clipboard.writeText(document.getElementById('genCodeBlock').textContent).then(()=>{this.innerHTML='&#10003; Copied';setTimeout(()=>{this.innerHTML='&#128203; Copy'},2000)})">&#128203; Copy</button></div>
            <pre id="genCodeBlock" class="code-output">${escapeHtml(result.code_generated)}</pre></div>`;
    }

    if (!html) {
        html = '<p class="placeholder-text">No results. Try: descriptive statistics, correlation, OLS regression, histogram, scatter plot, time series, or bar chart.</p>';
    }

    container.innerHTML = html;

    // Attach download handlers
    document.querySelectorAll('.download-plot').forEach(btn => {
        btn.addEventListener('click', () => downloadPlot(btn.dataset.b64, btn.dataset.title, btn.dataset.fmt));
    });
}

function downloadPlot(b64, title, fmt) {
    const mime = fmt === 'jpg' ? 'image/jpeg' : fmt === 'svg' ? 'image/svg+xml' : fmt === 'pdf' ? 'application/pdf' : 'image/png';
    const link = document.createElement('a');
    link.href = `data:${mime};base64,${b64}`;
    link.download = `${title.replace(/[^a-zA-Z0-9]/g, '_')}.${fmt}`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// ---- Online data ----
document.getElementById('fetchOnlineBtn')?.addEventListener('click', async () => {
    const source = document.getElementById('onlineSource').value;
    const query = document.getElementById('onlineQuery').value.trim();
    if (!query) { showStatus('onlineStatus', 'Enter an indicator/query code.', 'error'); return; }

    const country = document.getElementById('onlineCountry').value.trim() || 'all';
    const yf = document.getElementById('onlineYearFrom').value.trim();
    const yt = document.getElementById('onlineYearTo').value.trim();
    const dateRange = (yf && yt) ? `${yf}:${yt}` : '2000:2024';

    const btn = document.getElementById('fetchOnlineBtn');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Fetching...';
    showStatus('onlineStatus', `Fetching data from ${source}...`, 'loading');

    try {
        const r = await apiFetch('/api/analysis/online-data', {
            method: 'POST',
            body: JSON.stringify({ source, query, params: { country, date_range: dateRange } })
        });
        const d = await r.json();
        if (!r.ok) throw new Error(d.detail || 'Fetch failed');
        hideStatus('onlineStatus');
        renderOnlineResults(d.data);
        showStatus('onlineStatus', d.data.message || 'Data fetched successfully.', 'success');
    } catch (err) {
        showStatus('onlineStatus', `Error: ${err.message}`, 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '&#127760; Fetch Data';
    }
});

function renderOnlineResults(data) {
    const container = document.getElementById('onlineResults');
    if (data.error) {
        container.innerHTML = `<div class="result-card error"><p>${escapeHtml(data.error)}</p></div>`;
        return;
    }

    let html = `<div class="result-card"><div class="result-card-header"><h4>&#127760; ${escapeHtml(data.source || 'Online Data')}</h4></div>`;
    html += `<p><strong>Records:</strong> ${data.n_records || 'N/A'}</p>`;

    if (data.download_url) {
        html += `<p><a href="${escapeHtml(data.download_url)}" target="_blank" class="btn-secondary btn-sm">View Raw Data Source</a></p>`;
    }

    if (data.head && data.head.length > 0) {
        const cols = Object.keys(data.head[0]);
        html += '<table class="data-table"><thead><tr>';
        cols.forEach(c => html += `<th>${escapeHtml(c)}</th>`);
        html += '</tr></thead><tbody>';
        data.head.forEach(row => {
            html += '<tr>';
            cols.forEach(c => {
                const v = row[c];
                html += `<td>${v === null || v === undefined ? '<span style="color:#cbd5e0;">—</span>' : escapeHtml(String(v).substring(0, 40))}</td>`;
            });
            html += '</tr>';
        });
        html += '</tbody></table>';
    }

    if (data.columns) {
        html += `<div style="margin-top:0.5rem;font-size:0.8rem;color:#718096;">Columns: ${data.columns.map(c => escapeHtml(c)).join(', ')}</div>`;
    }

    html += '</div>';
    container.innerHTML = html;
}

// ---- Model suggestion ----
document.getElementById('suggestModelBtn')?.addEventListener('click', async () => {
    const methodology = document.getElementById('methodologyText').value.trim();
    if (!methodology) { showStatus('modelStatus', 'Paste your methodology text first.', 'error'); return; }

    const btn = document.getElementById('suggestModelBtn');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Analyzing...';
    showStatus('modelStatus', 'Analyzing methodology and suggesting models...', 'loading');

    try {
        const r = await apiFetch('/api/analysis/suggest-model', {
            method: 'POST',
            body: JSON.stringify({ methodology })
        });
        const d = await r.json();
        if (!r.ok) throw new Error(d.detail || 'Suggestion failed');
        hideStatus('modelStatus');
        renderModelSuggestions(d.suggestion);
        showStatus('modelStatus', 'Model suggestions ready.', 'success');
    } catch (err) {
        showStatus('modelStatus', `Error: ${err.message}`, 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '&#129504; Suggest Best Econometric Model';
    }
});

function renderModelSuggestions(suggestion) {
    const container = document.getElementById('modelSuggestions');
    const primary = suggestion.primary_recommendation;
    const all = suggestion.all_suggestions || [];
    const note = suggestion.note || '';

    let html = '';

    // Primary recommendation - highlighted
    if (primary) {
        html += `<div class="result-card primary-recommendation">
            <div class="result-card-header"><h4>&#11088; Primary Recommendation: ${escapeHtml(primary.model)}</h4>
            <span class="match-score">${primary.score}% match</span></div>
            <p>${escapeHtml(primary.description)}</p>
            <div class="model-details">
                <div class="model-detail"><strong>Methods:</strong> ${(primary.methods || []).map(m => `<span class="tag">${escapeHtml(m)}</span>`).join('')}</div>
                <div class="model-detail"><strong>Software:</strong> ${escapeHtml(primary.software || '')}</div>
                <div class="model-detail"><strong>Key Assumptions:</strong> ${(primary.assumptions || []).map(a => `<span class="tag tag-warn">${escapeHtml(a)}</span>`).join('')}</div>
            </div>
        </div>`;
    }

    // Other suggestions
    if (all.length > 1) {
        html += '<div class="result-card"><div class="result-card-header"><h4>&#128202; Alternative Models</h4></div>';
        all.slice(1).forEach(s => {
            html += `<div class="alt-model">
                <div class="alt-model-header">
                    <strong>${escapeHtml(s.model)}</strong>
                    <span class="match-score small">${s.score}% match</span>
                </div>
                <p style="font-size:0.9rem;margin:0.25rem 0;">${escapeHtml(s.description)}</p>
                <div style="font-size:0.85rem;color:#718096;">${escapeHtml(s.software || '')}</div>
            </div>`;
        });
        html += '</div>';
    }

    if (note) {
        html += `<div class="result-card"><div class="result-card-header"><h4>&#8505; Note</h4></div><p>${escapeHtml(note)}</p></div>`;
    }

    container.innerHTML = html || '<p class="placeholder-text">No suggestions available.</p>';
}

// ---- Code generation (existing, updated status IDs) ----
document.getElementById('generateAnalysisBtn').addEventListener('click', generateAnalysisCode);
document.getElementById('getRecommendationsBtn').addEventListener('click', getAnalysisRecommendations);
document.getElementById('copyAnalysisCodeBtn').addEventListener('click', copyAnalysisCode);

async function loadAnalysisMethods() {
    try {
        const resp = await apiFetch('/api/analysis/methods');
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();
        const select = document.getElementById('analysisMethod');
        if (data.methods && data.methods.length) {
            select.innerHTML = data.methods.map(m =>
                `<option value="${m.value || m.id || m}">${m.label || m.name || m}</option>`
            ).join('');
        }
    } catch (err) {
        showStatus('codegenStatus', `Failed to load methods: ${err.message}`, 'error');
    }
}

async function generateAnalysisCode() {
    const method = document.getElementById('analysisMethod').value;
    const language = document.getElementById('analysisLanguage').value;
    const dependent_var = document.getElementById('analysisDepVar').value.trim();
    const independent_vars = document.getElementById('analysisIndepVars').value.trim();
    const control_vars = document.getElementById('analysisControlVars').value.trim();
    const data_file = document.getElementById('analysisDataFile').value.trim();
    const entity_var = document.getElementById('analysisEntityVar').value.trim();
    const time_var = document.getElementById('analysisTimeVar').value.trim();
    const cluster_var = document.getElementById('analysisClusterVar').value.trim();
    const robust_se = document.getElementById('analysisRobustSE').checked;
    const instruments = document.getElementById('analysisInstruments').value.trim();

    if (!dependent_var || !independent_vars) {
        showStatus('codegenStatus', 'Please provide at least a dependent variable and independent variables.', 'error');
        return;
    }

    const body = {
        method,
        language,
        dependent_var,
        independent_vars: independent_vars.split(',').map(s => s.trim()).filter(Boolean),
        control_vars: control_vars ? control_vars.split(',').map(s => s.trim()).filter(Boolean) : [],
        data_file: data_file || null,
        entity_var: entity_var || null,
        time_var: time_var || null,
        cluster_var: cluster_var || null,
        robust_se,
        instruments: instruments ? instruments.split(',').map(s => s.trim()).filter(Boolean) : [],
    };

    const btn = document.getElementById('generateAnalysisBtn');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Generating...';
    showStatus('codegenStatus', `Generating ${method} code in ${language}...`, 'loading');

    try {
        const resp = await apiFetch('/api/analysis/generate', {
            method: 'POST',
            body: JSON.stringify(body),
        });
        if (!resp.ok) {
            const errData = await resp.json().catch(() => ({}));
            throw new Error(errData.detail || `HTTP ${resp.status}`);
        }
        const data = await resp.json();

        hideStatus('codegenStatus');
        showStatus('codegenStatus', 'Analysis code generated successfully.', 'success');

        const code = data.code || data.output || '';
        document.getElementById('analysisCodeOutput').textContent = code;
        document.getElementById('analysisCodeSection').style.display = 'block';
    } catch (err) {
        showStatus('codegenStatus', `Generation failed: ${err.message}`, 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '&#128202; Generate Analysis Code';
    }
}

function copyAnalysisCode() {
    const code = document.getElementById('analysisCodeOutput').textContent;
    if (!code) return;
    navigator.clipboard.writeText(code).then(() => {
        const btn = document.getElementById('copyAnalysisCodeBtn');
        const original = btn.innerHTML;
        btn.innerHTML = '&#10003; Copied!';
        setTimeout(() => { btn.innerHTML = original; }, 2000);
    }).catch(() => {
        showStatus('codegenStatus', 'Could not copy to clipboard. Please select and copy manually.', 'error');
    });
}

async function getAnalysisRecommendations() {
    const topic = document.getElementById('recommendTopic').value.trim();
    const data_type = document.getElementById('recommendDataType').value;

    if (!topic) {
        showStatus('codegenStatus', 'Please enter a research topic for recommendations.', 'error');
        return;
    }

    const btn = document.getElementById('getRecommendationsBtn');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Loading...';
    showStatus('codegenStatus', 'Getting recommendations...', 'loading');
    document.getElementById('analysisRecommendations').innerHTML = '';

    try {
        const resp = await apiFetch('/api/analysis/recommend', {
            method: 'POST',
            body: JSON.stringify({ topic, data_type }),
        });
        if (!resp.ok) {
            const errData = await resp.json().catch(() => ({}));
            throw new Error(errData.detail || `HTTP ${resp.status}`);
        }
        const data = await resp.json();
        hideStatus('codegenStatus');
        renderAnalysisRecommendations(data);
    } catch (err) {
        showStatus('codegenStatus', `Failed: ${err.message}`, 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Get Recommendations';
    }
}

function renderAnalysisRecommendations(data) {
    const container = document.getElementById('analysisRecommendations');
    const methods = data.recommended_methods || data.methods || [];
    const variables = data.recommended_variables || data.variables || [];
    const notes = data.notes || data.reasoning || '';

    const methodsHtml = methods.length ? `
        <div class="paper-card">
            <div class="paper-title">Recommended Methods</div>
            <ul style="margin-top:0.5rem;padding-left:1.25rem;">
                ${methods.map(m => `<li>${escapeHtml(typeof m === 'string' ? m : m.name + (m.reason ? ' — ' + m.reason : ''))}</li>`).join('')}
            </ul>
        </div>` : '';

    const variablesHtml = variables.length ? `
        <div class="paper-card">
            <div class="paper-title">Recommended Variables</div>
            <ul style="margin-top:0.5rem;padding-left:1.25rem;">
                ${variables.map(v => `<li>${escapeHtml(typeof v === 'string' ? v : v.name + (v.description ? ' — ' + v.description : ''))}</li>`).join('')}
            </ul>
        </div>` : '';

    const notesHtml = notes ? `<div class="paper-card"><div class="paper-title">Notes</div><p style="margin-top:0.5rem;">${escapeHtml(notes)}</p></div>` : '';

    container.innerHTML = methodsHtml + variablesHtml + notesHtml ||
        '<p class="placeholder-text">No recommendations returned. Try a different topic.</p>';
}

// ===========================================================================
// WRITING TOOLS
// ===========================================================================

document.getElementById('analyzeWritingBtn').addEventListener('click', analyzeWriting);
document.getElementById('checkJournalBtn').addEventListener('click', checkJournalReadiness);

// ---- Inline Enhancement (Grammarly/QuillBot/Paperpal style) ----

document.getElementById('enhanceAllBtn').addEventListener('click', () => enhanceText('all'));
document.getElementById('enhanceGrammarBtn').addEventListener('click', () => enhanceText('grammar'));
document.getElementById('enhanceParaphraseBtn').addEventListener('click', () => enhanceText('paraphrase'));
document.getElementById('enhanceAcademicBtn').addEventListener('click', () => enhanceText('academic'));
document.getElementById('enhanceClearBtn').addEventListener('click', () => {
    document.getElementById('enhanceTextInput').value = '';
    document.getElementById('enhanceResults').innerHTML = '';
    hideStatus('enhanceStatus');
    document.getElementById('enhanceTextInput').focus();
});

// Tool card click shortcuts
document.getElementById('toolGrammarly').addEventListener('click', () => enhanceText('grammar'));
document.getElementById('toolQuillbot').addEventListener('click', () => enhanceText('paraphrase'));
document.getElementById('toolPaperpal').addEventListener('click', () => enhanceText('academic'));

let _lastEnhancedText = '';

async function enhanceText(mode) {
    const text = document.getElementById('enhanceTextInput').value.trim();
    if (!text) {
        showStatus('enhanceStatus', 'Please paste some text first.', 'error');
        setTimeout(() => hideStatus('enhanceStatus'), 3000);
        return;
    }

    const endpoints = {
        grammar: '/api/writing/fix-grammar',
        paraphrase: '/api/writing/paraphrase',
        academic: '/api/writing/enhance-academic',
        all: '/api/writing/enhance-all',
    };

    const labels = {
        grammar: 'Fixing grammar...',
        paraphrase: 'Paraphrasing text...',
        academic: 'Enhancing academic tone...',
        all: 'Applying all enhancements...',
    };

    const url = endpoints[mode] || endpoints.all;

    // Disable all enhance buttons
    const btns = ['enhanceAllBtn', 'enhanceGrammarBtn', 'enhanceParaphraseBtn', 'enhanceAcademicBtn'];
    btns.forEach(id => {
        const b = document.getElementById(id);
        b.disabled = true;
        b.dataset.original = b.innerHTML;
        b.innerHTML = '<span class="spinner"></span> Working...';
    });

    // Highlight active tool
    document.querySelectorAll('.enhance-tool-btn').forEach(el => el.classList.remove('active'));
    if (mode === 'grammar') document.getElementById('toolGrammarly').classList.add('active');
    if (mode === 'paraphrase') document.getElementById('toolQuillbot').classList.add('active');
    if (mode === 'academic') document.getElementById('toolPaperpal').classList.add('active');
    if (mode === 'all') {
        document.getElementById('toolGrammarly').classList.add('active');
        document.getElementById('toolQuillbot').classList.add('active');
        document.getElementById('toolPaperpal').classList.add('active');
    }

    showStatus('enhanceStatus', labels[mode] || 'Working...', 'loading');
    document.getElementById('enhanceResults').innerHTML = '';

    try {
        const resp = await apiFetch(url, {
            method: 'POST',
            body: JSON.stringify({ text }),
        });
        if (!resp.ok) {
            const errData = await resp.json().catch(() => ({}));
            throw new Error(errData.detail || `HTTP ${resp.status}`);
        }
        const data = await resp.json();

        hideStatus('enhanceStatus');
        showStatus('enhanceStatus', data.summary || 'Enhancement complete.', 'success');
        setTimeout(() => hideStatus('enhanceStatus'), 5000);

        _lastEnhancedText = data.enhanced || text;
        renderEnhanceResults(data, mode);
    } catch (err) {
        showStatus('enhanceStatus', `Enhancement failed: ${err.message}`, 'error');
    } finally {
        btns.forEach(id => {
            const b = document.getElementById(id);
            b.disabled = false;
            if (b.dataset.original) b.innerHTML = b.dataset.original;
        });
    }
}

function renderEnhanceResults(data, mode) {
    const container = document.getElementById('enhanceResults');
    const enhanced = data.enhanced || '';
    const original = data.original || '';

    // Collect changes
    let changes = [];
    if (mode === 'all' && data.all_changes) {
        changes = data.all_changes;
    } else if (data.changes) {
        changes = data.changes;
    }

    // Count words
    const origWords = original.split(/\s+/).filter(w => w).length;
    const newWords = enhanced.split(/\s+/).filter(w => w).length;
    const wordDiff = newWords - origWords;

    // Build changes HTML
    let changesHtml = '';
    if (changes.length > 0) {
        changesHtml = `
            <div class="enhance-changes-list">
                <div class="enhance-changes-title">Changes Made (${changes.length})</div>
                ${changes.map(c => {
                    const cat = c.category || 'grammar';
                    const typeLabel = c.type ? c.type.replace(/_/g, ' ') : cat;
                    const origText = c.original ? escapeHtml(String(c.original).substring(0, 100)) : '';
                    const fixedText = c.fixed ? escapeHtml(String(c.fixed).substring(0, 100)) : '';
                    return `
                        <div class="enhance-change-item">
                            <span class="enhance-change-type ${cat}">${escapeHtml(typeLabel)}</span>
                            <span class="enhance-change-detail">
                                ${origText ? `<span class="original">${origText}</span>` : ''}
                                ${fixedText ? ` &rarr; <span class="fixed">${fixedText}</span>` : ''}
                            </span>
                        </div>
                    `;
                }).join('')}
            </div>
        `;
    } else {
        changesHtml = `
            <div class="enhance-changes-list">
                <p style="color:var(--success);font-weight:600;">&#9989; No changes needed. Your text is already in good shape for this tool.</p>
            </div>
        `;
    }

    container.innerHTML = `
        <div class="enhance-result-card">
            <div class="enhance-result-header">
                <span class="summary">${escapeHtml(data.summary || 'Enhancement complete.')}</span>
                ${aiModelBadge(data.model_used)}
                <div class="enhance-result-actions">
                    <button class="btn-copy" style="background:var(--primary);color:#fff;border:1px solid var(--primary);" onclick="copyGeneratedText(this, ${JSON.stringify(enhanced).replace(/'/g, "&#39;")})">
                        &#128203; Copy Enhanced Text
                    </button>
                    <button class="btn-primary btn-sm" onclick="applyEnhancedToEditor()">
                        &#10003; Apply to Editor
                    </button>
                </div>
            </div>
            <div class="enhance-result-text">${escapeHtml(enhanced)}</div>
            ${changesHtml}
            <div class="enhance-diff-banner">
                <span>&#128202; Word count: ${origWords} &rarr; ${newWords} (${wordDiff >= 0 ? '+' : ''}${wordDiff} words)</span>
            </div>
        </div>
    `;

    // Scroll to results
    setTimeout(() => {
        container.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 200);
}

function applyEnhancedToEditor() {
    if (_lastEnhancedText) {
        document.getElementById('enhanceTextInput').value = _lastEnhancedText;
        showStatus('enhanceStatus', 'Enhanced text applied to editor. You can run another tool or copy the text.', 'success');
        setTimeout(() => hideStatus('enhanceStatus'), 4000);
        document.getElementById('enhanceTextInput').focus();
    }
}

// ---- Humanize & Naturalize ----

let _lastHumanizedText = '';

document.getElementById('humanizeBtn').addEventListener('click', humanizeText);
document.getElementById('humanizeClearBtn').addEventListener('click', () => {
    document.getElementById('humanizeTextInput').value = '';
    document.getElementById('humanizeResults').innerHTML = '';
    hideStatus('humanizeStatus');
    document.getElementById('humanizeTextInput').focus();
});
document.getElementById('humanizeCopyBtn').addEventListener('click', () => {
    if (_lastHumanizedText) {
        navigator.clipboard.writeText(_lastHumanizedText).then(() => {
            showStatus('humanizeStatus', 'Humanized text copied to clipboard!', 'success');
            setTimeout(() => hideStatus('humanizeStatus'), 3000);
        }).catch(() => {
            showStatus('humanizeStatus', 'Copy failed. Please select and copy manually.', 'error');
            setTimeout(() => hideStatus('humanizeStatus'), 3000);
        });
    } else {
        showStatus('humanizeStatus', 'No humanized text to copy. Run the tool first.', 'error');
        setTimeout(() => hideStatus('humanizeStatus'), 3000);
    }
});

async function humanizeText() {
    const text = document.getElementById('humanizeTextInput').value.trim();
    if (!text) {
        showStatus('humanizeStatus', 'Please paste some text first.', 'error');
        setTimeout(() => hideStatus('humanizeStatus'), 3000);
        return;
    }

    const btn = document.getElementById('humanizeBtn');
    const origHtml = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Humanizing...';

    showStatus('humanizeStatus', 'Analyzing and naturalizing text...', 'loading');
    document.getElementById('humanizeResults').innerHTML = '';

    try {
        const resp = await apiFetch('/api/writing/humanize', {
            method: 'POST',
            body: JSON.stringify({ text }),
        });
        if (!resp.ok) {
            const errData = await resp.json().catch(() => ({}));
            throw new Error(errData.detail || `HTTP ${resp.status}`);
        }
        const data = await resp.json();

        hideStatus('humanizeStatus');
        showStatus('humanizeStatus', data.summary || 'Humanization complete.', 'success');
        setTimeout(() => hideStatus('humanizeStatus'), 6000);

        _lastHumanizedText = data.humanized || text;
        renderHumanizeResults(data);
    } catch (err) {
        showStatus('humanizeStatus', `Humanization failed: ${err.message}`, 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = origHtml;
    }
}

function renderHumanizeResults(data) {
    const container = document.getElementById('humanizeResults');
    const humanized = data.humanized || '';
    const original = data.original || '';
    const changes = data.changes || [];
    const patterns = data.patterns_detected || [];
    const score = data.naturalness_score || 0;

    // Score color
    let scoreColor = '#e53e3e';
    let scoreLabel = 'Needs Work';
    if (score >= 75) { scoreColor = '#38a169'; scoreLabel = 'Natural'; }
    else if (score >= 50) { scoreColor = '#319795'; scoreLabel = 'Moderate'; }
    else if (score >= 30) { scoreColor = '#dd6b20'; scoreLabel = 'AI Patterns Detected'; }

    // Patterns detected tags
    let patternsHtml = '';
    if (patterns.length > 0) {
        patternsHtml = `
            <div style="margin-bottom:1rem;">
                <h4 style="font-size:0.85rem;color:#718096;margin-bottom:0.5rem;">AI Patterns Detected (${patterns.length})</h4>
                <div class="humanize-patterns-list">
                    ${patterns.map(p => `<span class="humanize-pattern-tag">&#9888; ${escapeHtml(p)}</span>`).join('')}
                </div>
            </div>
        `;
    }

    // Changes list
    let changesHtml = '';
    if (changes.length > 0) {
        changesHtml = `
            <div style="margin-bottom:1rem;">
                <h4 style="font-size:0.85rem;color:#718096;margin-bottom:0.5rem;">Improvements Made (${changes.length})</h4>
                <ul class="humanize-changes-list">
                    ${changes.map(c => {
                        const typeLabel = c.type ? c.type.replace(/_/g, ' ') : 'change';
                        const origText = c.original ? escapeHtml(String(c.original).substring(0, 80)) : '';
                        const fixedText = c.fixed ? escapeHtml(String(c.fixed).substring(0, 80)) : '';
                        return `
                            <li class="humanize-change-item">
                                <span class="humanize-change-type">${escapeHtml(typeLabel)}</span>
                                <span class="humanize-change-detail">
                                    ${origText ? `<span class="original">${origText}</span>` : ''}
                                    ${fixedText ? ` &rarr; <span class="fixed">${fixedText}</span>` : ''}
                                </span>
                            </li>
                        `;
                    }).join('')}
                </ul>
            </div>
        `;
    } else {
        changesHtml = `
            <div style="margin-bottom:1rem;">
                <p style="color:var(--success);font-weight:600;">&#9989; Your text already reads naturally. No significant AI patterns detected.</p>
            </div>
        `;
    }

    // Before/After comparison
    const comparisonHtml = `
        <div class="humanize-comparison">
            <div class="humanize-comparison-col before">
                <h4>Before</h4>
                <div class="humanize-comparison-text">${escapeHtml(original)}</div>
            </div>
            <div class="humanize-comparison-col after">
                <h4>After</h4>
                <div class="humanize-comparison-text">${escapeHtml(humanized)}</div>
            </div>
        </div>
    `;

    // Word counts
    const origWords = original.split(/\s+/).filter(w => w).length;
    const newWords = humanized.split(/\s+/).filter(w => w).length;

    container.innerHTML = `
        <div class="humanize-result-card">
            <div class="humanize-score-banner" style="border:2px solid ${scoreColor};background:${scoreColor}11;">
                <div>
                    <div class="humanize-score-number" style="color:${scoreColor};">${score}</div>
                    <div class="humanize-score-label">Naturalness Score / 100 &mdash; ${scoreLabel}</div>
                </div>
                <div style="text-align:right;">
                    ${aiModelBadge(data.model_used)}
                    <div style="font-size:0.8rem;color:#718096;margin-top:0.3rem;">
                        ${origWords} &rarr; ${newWords} words
                    </div>
                </div>
            </div>

            ${patternsHtml}
            ${changesHtml}
            ${comparisonHtml}

            <div style="display:flex;gap:0.5rem;flex-wrap:wrap;margin-top:1rem;">
                <button class="btn-copy" style="background:var(--primary);color:#fff;border:1px solid var(--primary);" onclick="copyGeneratedText(this, ${JSON.stringify(humanized).replace(/'/g, "&#39;")})">
                    &#128203; Copy Humanized Text
                </button>
                <button class="btn-secondary btn-sm" onclick="applyHumanizedToEditor()">
                    &#10003; Apply to Editor
                </button>
                <button class="btn-secondary btn-sm" onclick="sendHumanizedToAnalysis()">
                    &#128270; Send to Writing Analysis
                </button>
            </div>
        </div>
    `;

    setTimeout(() => {
        container.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 200);
}

function applyHumanizedToEditor() {
    if (_lastHumanizedText) {
        document.getElementById('humanizeTextInput').value = _lastHumanizedText;
        showStatus('humanizeStatus', 'Humanized text applied to editor. You can run the tool again or copy the text.', 'success');
        setTimeout(() => hideStatus('humanizeStatus'), 4000);
        document.getElementById('humanizeTextInput').focus();
    }
}

function sendHumanizedToAnalysis() {
    if (_lastHumanizedText) {
        document.getElementById('writingTextInput').value = _lastHumanizedText;
        showStatus('humanizeStatus', 'Text sent to Writing Analysis. Scroll up to run analysis.', 'success');
        setTimeout(() => hideStatus('humanizeStatus'), 4000);
        document.getElementById('writingTextInput').scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
}

async function loadWritingTools() {
    try {
        const resp = await apiFetch('/api/writing/tools');
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();
        return data.tools || data;
    } catch (err) {
        showStatus('writingStatus', `Failed to load writing tools: ${err.message}`, 'error');
        return [];
    }
}

async function analyzeWriting() {
    const text = document.getElementById('writingTextInput').value.trim();
    if (!text) {
        showStatus('writingStatus', 'Please paste some text to analyze.', 'error');
        return;
    }

    const btn = document.getElementById('analyzeWritingBtn');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Analyzing...';
    showStatus('writingStatus', 'Analyzing your text...', 'loading');
    document.getElementById('writingAnalysisResults').innerHTML = '';

    try {
        const resp = await apiFetch('/api/writing/analyze', {
            method: 'POST',
            body: JSON.stringify({ text }),
        });
        if (!resp.ok) {
            const errData = await resp.json().catch(() => ({}));
            throw new Error(errData.detail || `HTTP ${resp.status}`);
        }
        const data = await resp.json();
        hideStatus('writingStatus');
        showStatus('writingStatus', 'Writing analysis complete.', 'success');
        renderWritingAnalysis(data);
    } catch (err) {
        showStatus('writingStatus', `Analysis failed: ${err.message}`, 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Analyze Writing';
    }
}

function renderWritingAnalysis(data) {
    const container = document.getElementById('writingAnalysisResults');

    const wordCount = data.word_count || 0;
    const sentenceCount = data.sentence_count || 0;
    const avgSentLen = data.avg_sentence_length || 'N/A';
    const readability = data.readability || {};
    const fleschScore = readability.flesch_reading_ease != null ? readability.flesch_reading_ease : 'N/A';
    const gradeLevel = readability.flesch_grade_level != null ? readability.flesch_grade_level : 'N/A';
    const gunningFog = readability.gunning_fog_index != null ? readability.gunning_fog_index : 'N/A';
    const readLabel = readability.label || 'N/A';
    const passiveCount = data.passive_voice_count || 0;
    const academicRatio = data.academic_ratio != null ? data.academic_ratio + '%' : 'N/A';
    const toneAssessment = data.tone_assessment || 'N/A';
    const transitionCount = data.transition_count || 0;
    const overallScore = data.overall_score != null ? data.overall_score : 'N/A';
    const suggestions = data.suggestions || [];

    const scoreColor = overallScore >= 80 ? 'var(--success)' : overallScore >= 60 ? 'var(--warning)' : 'var(--danger)';

    const suggestionsHtml = suggestions.length ? `
        <div class="paper-card" style="margin-top:1rem;">
            <div class="paper-title">Improvement Suggestions (${suggestions.length})</div>
            <ul style="margin-top:0.5rem;padding-left:1.25rem;">
                ${suggestions.map(s => {
                    const msg = typeof s === 'string' ? s : s.message || s.text || JSON.stringify(s);
                    const sev = (typeof s === 'object' && s.severity) ? s.severity : '';
                    const sevColor = sev === 'high' ? 'var(--danger)' : sev === 'medium' ? 'var(--warning)' : 'var(--text-light)';
                    return `<li style="margin-bottom:0.4rem;">${sev ? `<span style="color:${sevColor};font-weight:600;font-size:0.75rem;text-transform:uppercase;">${sev}</span> ` : ''}${escapeHtml(msg)}</li>`;
                }).join('')}
            </ul>
        </div>` : '<p style="color:var(--success);margin-top:1rem;">No issues found. Your writing looks good.</p>';

    container.innerHTML = `
        <div class="writing-score-banner" style="background:var(--surface);border-radius:var(--radius);padding:1.5rem;margin-bottom:1rem;text-align:center;border:2px solid ${scoreColor};">
            <div style="font-size:0.85rem;color:var(--text-light);margin-bottom:0.25rem;">Overall Writing Score</div>
            <div style="font-size:2.5rem;font-weight:700;color:${scoreColor};">${overallScore}<span style="font-size:1rem;color:var(--text-light);">/100</span></div>
            <div style="font-size:0.85rem;color:var(--text-light);margin-top:0.25rem;">Tone: ${escapeHtml(toneAssessment)}</div>
        </div>
        <div class="writing-stats-grid">
            <div class="stat-card">
                <span class="stat-label">Word Count</span>
                <span class="stat-value">${wordCount}</span>
            </div>
            <div class="stat-card">
                <span class="stat-label">Sentences</span>
                <span class="stat-value">${sentenceCount}</span>
            </div>
            <div class="stat-card">
                <span class="stat-label">Avg Sentence Length</span>
                <span class="stat-value">${avgSentLen}</span>
            </div>
            <div class="stat-card">
                <span class="stat-label">Flesch Reading Ease</span>
                <span class="stat-value">${fleschScore}</span>
            </div>
            <div class="stat-card">
                <span class="stat-label">Grade Level</span>
                <span class="stat-value">${gradeLevel}</span>
            </div>
            <div class="stat-card">
                <span class="stat-label">Gunning Fog</span>
                <span class="stat-value">${gunningFog}</span>
            </div>
            <div class="stat-card">
                <span class="stat-label">Readability</span>
                <span class="stat-value" style="font-size:1rem;">${escapeHtml(readLabel)}</span>
            </div>
            <div class="stat-card">
                <span class="stat-label">Passive Voice</span>
                <span class="stat-value">${passiveCount}</span>
            </div>
            <div class="stat-card">
                <span class="stat-label">Academic Ratio</span>
                <span class="stat-value">${academicRatio}</span>
            </div>
            <div class="stat-card">
                <span class="stat-label">Transition Words</span>
                <span class="stat-value">${transitionCount}</span>
            </div>
        </div>
        ${suggestionsHtml}
    `;
}

async function checkJournalReadiness() {
    const text = document.getElementById('writingTextInput').value.trim();
    const journal = document.getElementById('journalName').value.trim();

    if (!text) {
        showStatus('writingStatus', 'Please paste some text to check.', 'error');
        return;
    }
    if (!journal) {
        showStatus('writingStatus', 'Please enter a target journal name.', 'error');
        return;
    }

    const btn = document.getElementById('checkJournalBtn');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Checking...';
    showStatus('writingStatus', `Checking readiness for "${journal}"...`, 'loading');
    document.getElementById('journalReadinessResults').innerHTML = '';

    try {
        const resp = await apiFetch('/api/writing/journal-check', {
            method: 'POST',
            body: JSON.stringify({ text, journal }),
        });
        if (!resp.ok) {
            const errData = await resp.json().catch(() => ({}));
            throw new Error(errData.detail || `HTTP ${resp.status}`);
        }
        const data = await resp.json();
        hideStatus('writingStatus');
        showStatus('writingStatus', 'Journal readiness check complete.', 'success');
        renderJournalReadiness(data);
    } catch (err) {
        showStatus('writingStatus', `Check failed: ${err.message}`, 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Check Journal Readiness';
    }
}

function renderJournalReadiness(data) {
    const container = document.getElementById('journalReadinessResults');
    const score = data.readiness_score != null ? data.readiness_score : (data.score != null ? data.score : 'N/A');
    const checks = data.checks || data.criteria || [];

    const checksHtml = checks.length ? `
        <div class="paper-card" style="margin-top:1rem;">
            <div class="paper-title">Checks</div>
            <ul style="margin-top:0.5rem;padding-left:1.25rem;list-style:none;">
                ${checks.map(c => {
                    const passed = c.passed || c.status === 'pass' || c.status === 'passed';
                    const icon = passed ? '&#10003;' : '&#10007;';
                    const cls = passed ? 'check-passed' : 'check-failed';
                    return `<li class="${cls}">${icon} ${escapeHtml(c.name || c.check || c.message || '')}</li>`;
                }).join('')}
            </ul>
        </div>` : '';

    container.innerHTML = `
        <div class="readiness-score-card">
            <span class="stat-label">Journal Readiness Score</span>
            <span class="stat-value readiness-score">${score}${typeof score === 'number' ? '%' : ''}</span>
        </div>
        ${checksHtml}
    `;
}

// ===========================================================================
// REFERENCES
// ===========================================================================

document.getElementById('exportReferencesBtn').addEventListener('click', exportReferences);
document.getElementById('formatCitationsBtn').addEventListener('click', formatCitations);

async function loadReferenceManagers() {
    try {
        const resp = await apiFetch('/api/references/managers');
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();
        return data.managers || data;
    } catch (err) {
        showStatus('referencesStatus', `Failed to load reference managers: ${err.message}`, 'error');
        return [];
    }
}

async function exportReferences() {
    if (currentSearchResults.length === 0) {
        showStatus('referencesStatus', 'No search results to export. Run a search first.', 'error');
        return;
    }

    const format = document.getElementById('exportFormat').value;
    const btn = document.getElementById('exportReferencesBtn');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Exporting...';
    showStatus('referencesStatus', `Exporting ${currentSearchResults.length} references as ${format}...`, 'loading');

    try {
        const resp = await apiFetch('/api/references/export', {
            method: 'POST',
            body: JSON.stringify({ papers: currentSearchResults, format }),
        });
        if (!resp.ok) {
            const errData = await resp.json().catch(() => ({}));
            throw new Error(errData.detail || `HTTP ${resp.status}`);
        }

        // Determine content type and filename
        const extMap = {
            bibtex: 'bib', ris: 'ris', csl_json: 'json',
            endnote_xml: 'xml', apa: 'txt', mla: 'txt', chicago: 'txt', harvard: 'txt',
        };
        const ext = extMap[format] || 'txt';
        const contentType = resp.headers.get('content-type') || '';
        let content;
        if (contentType.includes('application/json')) {
            const data = await resp.json();
            content = data.content || data.output || JSON.stringify(data, null, 2);
        } else {
            content = await resp.text();
        }

        hideStatus('referencesStatus');
        showStatus('referencesStatus', `Exported ${currentSearchResults.length} references as ${format}.`, 'success');

        // Create downloadable file
        const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `theeye_references.${ext}`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        // Also show in output area
        document.getElementById('referencesOutput').innerHTML =
            `<div class="paper-card"><div class="paper-title">Exported Content (${format})</div>
             <pre class="code-output">${escapeHtml(content)}</pre></div>`;
    } catch (err) {
        showStatus('referencesStatus', `Export failed: ${err.message}`, 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Export References';
    }
}

async function formatCitations() {
    if (currentSearchResults.length === 0) {
        showStatus('referencesStatus', 'No search results to cite. Run a search first.', 'error');
        return;
    }

    const style = document.getElementById('citationFormat').value;
    const btn = document.getElementById('formatCitationsBtn');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Formatting...';
    showStatus('referencesStatus', `Formatting ${currentSearchResults.length} citations in ${style.toUpperCase()}...`, 'loading');
    document.getElementById('referencesOutput').innerHTML = '';

    try {
        const resp = await apiFetch('/api/references/cite', {
            method: 'POST',
            body: JSON.stringify({ papers: currentSearchResults, style }),
        });
        if (!resp.ok) {
            const errData = await resp.json().catch(() => ({}));
            throw new Error(errData.detail || `HTTP ${resp.status}`);
        }
        const data = await resp.json();
        hideStatus('referencesStatus');
        showStatus('referencesStatus', `Formatted ${currentSearchResults.length} citations in ${style.toUpperCase()}.`, 'success');

        const citations = data.citations || data.formatted || [];
        const container = document.getElementById('referencesOutput');
        if (citations.length) {
            container.innerHTML = `<div class="paper-card">
                <div class="paper-title">Formatted References (${style.toUpperCase()})</div>
                <ol style="margin-top:0.75rem;padding-left:1.5rem;">
                    ${citations.map(c => `<li style="margin-bottom:0.5rem;">${escapeHtml(typeof c === 'string' ? c : c.formatted || c.text || JSON.stringify(c))}</li>`).join('')}
                </ol>
            </div>`;
        } else if (data.content) {
            container.innerHTML = `<div class="paper-card">
                <div class="paper-title">Formatted References (${style.toUpperCase()})</div>
                <pre class="code-output">${escapeHtml(data.content)}</pre>
            </div>`;
        } else {
            container.innerHTML = '<p class="placeholder-text">No citations returned.</p>';
        }
    } catch (err) {
        showStatus('referencesStatus', `Formatting failed: ${err.message}`, 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Format Citations';
    }
}

// ---- Citation Verification ----

document.getElementById('verifyCitationsBtn').addEventListener('click', verifyCitations);
document.getElementById('clearVerifyBtn').addEventListener('click', () => {
    document.getElementById('verifyCiteText').value = '';
    document.getElementById('verifyCiteRefs').value = '';
    document.getElementById('verifyCiteResults').innerHTML = '';
    hideStatus('verifyCiteStatus');
    document.getElementById('verifyCiteText').focus();
});
document.getElementById('useSearchResultsBtn').addEventListener('click', populateRefsFromSearch);

function populateRefsFromSearch() {
    if (currentSearchResults.length === 0) {
        showStatus('verifyCiteStatus', 'No search results available. Run a search in Literature Discovery first.', 'error');
        setTimeout(() => hideStatus('verifyCiteStatus'), 4000);
        return;
    }

    const lines = currentSearchResults.map((p, i) => {
        const authors = p.authors && p.authors.length > 0
            ? p.authors.map(a => a.name).join(', ')
            : 'Unknown';
        const year = p.year || 'n.d.';
        const title = p.title || '';
        const journal = p.journal || '';
        const doi = p.doi ? ` DOI: ${p.doi}` : '';
        return `[${i + 1}] ${authors} (${year}). ${title}. ${journal}.${doi}`;
    });
    document.getElementById('verifyCiteRefs').value = lines.join('\n');
    document.getElementById('searchResultsCount').textContent = `(${currentSearchResults.length} references loaded)`;
    showStatus('verifyCiteStatus', `Loaded ${currentSearchResults.length} references from your latest search.`, 'success');
    setTimeout(() => hideStatus('verifyCiteStatus'), 3000);
}

async function verifyCitations() {
    const text = document.getElementById('verifyCiteText').value.trim();
    const refsText = document.getElementById('verifyCiteRefs').value.trim();

    if (!text) {
        showStatus('verifyCiteStatus', 'Please paste your cited text first.', 'error');
        setTimeout(() => hideStatus('verifyCiteStatus'), 3000);
        return;
    }

    // Parse references from the textarea
    let references = [];
    if (refsText) {
        references = parseReferenceList(refsText);
    }

    const btn = document.getElementById('verifyCitationsBtn');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Verifying...';
    showStatus('verifyCiteStatus', 'Checking citations against references...', 'loading');
    document.getElementById('verifyCiteResults').innerHTML = '';

    try {
        const resp = await apiFetch('/api/references/verify-citations', {
            method: 'POST',
            body: JSON.stringify({ text, references }),
        });
        if (!resp.ok) {
            const errData = await resp.json().catch(() => ({}));
            throw new Error(errData.detail || `HTTP ${resp.status}`);
        }
        const data = await resp.json();
        hideStatus('verifyCiteStatus');
        showStatus('verifyCiteStatus', data.summary, data.all_correct ? 'success' : (data.total_citations_found === 0 ? 'error' : 'loading'));
        if (data.all_correct) setTimeout(() => hideStatus('verifyCiteStatus'), 6000);
        renderVerifyResults(data);
    } catch (err) {
        showStatus('verifyCiteStatus', `Verification failed: ${err.message}`, 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '&#128270; Verify Citations';
    }
}

function parseReferenceList(text) {
    /** Parse a numbered reference list into structured dicts. */
    const lines = text.split('\n').filter(l => l.trim());
    const refs = [];
    for (const line of lines) {
        const match = line.match(/^\[(\d+)\]\s*(.+)/);
        if (match) {
            const refNum = parseInt(match[1]);
            const content = match[2].trim();
            // Try to extract year
            const yearMatch = content.match(/\((\d{4})\)/);
            const year = yearMatch ? yearMatch[1] : '';
            // Try to extract authors (text before first parenthesis or first period)
            let authors = '';
            if (yearMatch) {
                authors = content.substring(0, content.indexOf('(')).trim().replace(/\.$/, '');
            } else {
                const periodMatch = content.match(/^([^.]+)\./);
                authors = periodMatch ? periodMatch[1].trim() : content.substring(0, 50);
            }
            // Try to extract title (text after year parenthesis, before next period)
            let title = '';
            if (yearMatch) {
                const afterYear = content.substring(content.indexOf(')') + 1).trim();
                const titleMatch = afterYear.match(/^\.?\s*([^.]*)/);
                title = titleMatch ? titleMatch[1].trim() : '';
            }
            // Try to extract DOI
            const doiMatch = content.match(/DOI:\s*(\S+)/i);
            const doi = doiMatch ? doiMatch[1] : '';

            refs.push({
                ref_number: refNum,
                authors: authors,
                year: year,
                title: title,
                doi: doi,
                journal: '',
            });
        }
    }
    return refs;
}

function renderVerifyResults(data) {
    const container = document.getElementById('verifyCiteResults');

    if (data.total_citations_found === 0) {
        container.innerHTML = `
            <div class="verify-result-card">
                <div class="verify-result-header has-issues">
                    No citations detected in the text.
                </div>
                <div style="padding:1rem 1.25rem;font-size:0.85rem;color:var(--text-light);">
                    Make sure your text contains inline citations in one of these formats:
                    <ul style="margin-top:0.5rem;padding-left:1.5rem;">
                        <li><code>(Author, Year) [1]</code> &mdash; THEeye format</li>
                        <li><code>[1]</code> &mdash; numbered citation</li>
                        <li><code>(Smith et al., 2020)</code> &mdash; APA style</li>
                        <li><code>Smith (2020)</code> &mdash; narrative citation</li>
                    </ul>
                </div>
            </div>
        `;
        return;
    }

    // Build stats bar
    const statsHtml = `
        <div class="verify-result-stats">
            <div class="verify-stat matched"><span class="stat-num">${data.matched.length}</span> Matched</div>
            <div class="verify-stat orphan"><span class="stat-num">${data.orphan_citations.length}</span> Orphan Citation(s)</div>
            <div class="verify-stat uncited"><span class="stat-num">${data.uncited_references.length}</span> Uncited Reference(s)</div>
            <div class="verify-stat mismatch"><span class="stat-num">${data.mismatches.length}</span> Mismatch(es)</div>
        </div>
    `;

    // Build issues HTML
    let issuesHtml = '';

    // Orphan citations
    if (data.orphan_citations.length > 0) {
        issuesHtml += `<div class="verify-issues-list">
            <div class="verify-issues-list-title">&#9888; Orphan Citations (in text but not in references)</div>`;
        for (const oc of data.orphan_citations) {
            issuesHtml += `
                <div class="verify-issue-item orphan">
                    <span class="verify-issue-icon">&#10006;</span>
                    <div class="verify-issue-detail">
                        <span class="issue-label">Orphan Citation</span>
                        <div class="issue-desc">
                            <span class="citation-raw">${escapeHtml(oc.citation)}</span><br>
                            ${escapeHtml(oc.issue)}
                        </div>
                    </div>
                </div>
            `;
        }
        issuesHtml += `</div>`;
    }

    // Mismatches
    if (data.mismatches.length > 0) {
        issuesHtml += `<div class="verify-issues-list">
            <div class="verify-issues-list-title">&#9888; Citation Mismatches (details don't match reference)</div>`;
        for (const mm of data.mismatches) {
            issuesHtml += `
                <div class="verify-issue-item mismatch">
                    <span class="verify-issue-icon">&#9888;</span>
                    <div class="verify-issue-detail">
                        <span class="issue-label">Mismatch</span>
                        <div class="issue-desc">
                            <span class="citation-raw">${escapeHtml(mm.citation)}</span><br>
                            ${escapeHtml(mm.issue)}
                        </div>
                        ${mm.suggested_correction ? `<div class="suggested-fix">&#10003; Correct reference: ${escapeHtml(mm.suggested_correction)}</div>` : ''}
                    </div>
                </div>
            `;
        }
        issuesHtml += `</div>`;
    }

    // Uncited references
    if (data.uncited_references.length > 0) {
        issuesHtml += `<div class="verify-issues-list">
            <div class="verify-issues-list-title">&#9888; Uncited References (in list but never cited in text)</div>`;
        for (const ur of data.uncited_references) {
            issuesHtml += `
                <div class="verify-issue-item uncited">
                    <span class="verify-issue-icon">&#8505;</span>
                    <div class="verify-issue-detail">
                        <span class="issue-label">Uncited Reference [${ur.ref_num}]</span>
                        <div class="issue-desc">${escapeHtml(ur.issue)}</div>
                        <div class="issue-desc" style="margin-top:0.2rem;color:var(--text-light);">${escapeHtml(ur.reference)}</div>
                    </div>
                </div>
            `;
        }
        issuesHtml += `</div>`;
    }

    // Matched citations (collapsible)
    if (data.matched.length > 0) {
        issuesHtml += `<div class="verify-matched-list">
            <div class="verify-issues-list-title" style="color:var(--success);">&#9989; Correctly Matched Citations (${data.matched.length})</div>`;
        for (const m of data.matched) {
            issuesHtml += `
                <div class="verify-matched-item">
                    <span class="check-icon">&#10003;</span>
                    <span class="citation-raw">${escapeHtml(m.citation)}</span>
                    <span style="color:var(--text-light);">&rarr; ${escapeHtml(m.matched_reference || '')}</span>
                    ${m.note ? `<span style="color:var(--warning);font-size:0.75rem;">(${escapeHtml(m.note)})</span>` : ''}
                </div>
            `;
        }
        issuesHtml += `</div>`;
    }

    const headerClass = data.all_correct ? 'all-correct' : 'has-issues';
    const headerIcon = data.all_correct ? '&#9989;' : '&#9888;';

    container.innerHTML = `
        <div class="verify-result-card">
            <div class="verify-result-header ${headerClass}">
                ${headerIcon} ${escapeHtml(data.summary)}
            </div>
            ${statsHtml}
            ${issuesHtml}
        </div>
    `;

    // Scroll to results
    setTimeout(() => {
        container.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 200);
}

// ===========================================================================
// ADMIN PANEL
// ===========================================================================

document.getElementById('refreshAdminUsersBtn').addEventListener('click', loadAdminUsers);
document.getElementById('refreshAdminConfigBtn').addEventListener('click', loadAdminConfig);
document.getElementById('refreshAdminContentBtn').addEventListener('click', loadAdminContent);
document.getElementById('refreshAdminStatsBtn').addEventListener('click', loadAdminStats);
document.getElementById('refreshAdminDbSourcesBtn').addEventListener('click', loadDatabaseSources);
document.getElementById('refreshAdminToolsBtn').addEventListener('click', loadToolIntegrations);
document.getElementById('refreshAiConfigBtn').addEventListener('click', loadAiConfig);

function requireAdmin() {
    if (!(currentUser && currentUser.role === 'admin')) {
        showStatus('adminStatus', 'Admin access required.', 'error');
        return false;
    }
    return true;
}

async function loadAdminUsers() {
    if (!requireAdmin()) return;
    showStatus('adminStatus', 'Loading users...', 'loading');
    const container = document.getElementById('adminUsersTable');
    container.innerHTML = '';

    try {
        const resp = await apiFetch('/api/admin/users');
        if (!resp.ok) {
            const errData = await resp.json().catch(() => ({}));
            throw new Error(errData.detail || `HTTP ${resp.status}`);
        }
        const data = await resp.json();
        const users = data.users || data;
        hideStatus('adminStatus');

        if (!users.length) {
            container.innerHTML = '<p class="placeholder-text">No users found.</p>';
            return;
        }

        container.innerHTML = `
            <table class="admin-table">
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>Email</th>
                        <th>Role</th>
                        <th>Active</th>
                        <th>Institution</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    ${users.map(u => `
                        <tr>
                            <td>${escapeHtml(u.name || 'N/A')}</td>
                            <td>${escapeHtml(u.email || 'N/A')}</td>
                            <td>
                                <select onchange="toggleUserRole('${u.id}', this.value)" class="admin-select">
                                    <option value="user" ${u.role === 'user' ? 'selected' : ''}>user</option>
                                    <option value="admin" ${u.role === 'admin' ? 'selected' : ''}>admin</option>
                                </select>
                            </td>
                            <td>
                                <label class="toggle-switch">
                                    <input type="checkbox" ${u.is_active ? 'checked' : ''} onchange="toggleUserActive('${u.id}')">
                                    <span class="toggle-slider"></span>
                                </label>
                            </td>
                            <td>${escapeHtml(u.institution || 'N/A')}</td>
                            <td>
                                <button class="btn-secondary btn-danger-sm" onclick="deleteUser('${u.id}')">Delete</button>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
    } catch (err) {
        showStatus('adminStatus', `Failed to load users: ${err.message}`, 'error');
    }
}

async function toggleUserRole(userId, role) {
    if (!requireAdmin()) return;
    showStatus('adminStatus', `Updating role for user ${userId}...`, 'loading');
    try {
        const resp = await apiFetch(`/api/admin/users/${userId}/role`, {
            method: 'PUT',
            body: JSON.stringify({ role }),
        });
        if (!resp.ok) {
            const errData = await resp.json().catch(() => ({}));
            throw new Error(errData.detail || `HTTP ${resp.status}`);
        }
        hideStatus('adminStatus');
        showStatus('adminStatus', `User role updated to "${role}".`, 'success');
    } catch (err) {
        showStatus('adminStatus', `Failed: ${err.message}`, 'error');
        loadAdminUsers();
    }
}

async function toggleUserActive(userId) {
    if (!requireAdmin()) return;
    showStatus('adminStatus', `Toggling active status for user ${userId}...`, 'loading');
    try {
        const resp = await apiFetch(`/api/admin/users/${userId}/toggle-active`, {
            method: 'POST',
        });
        if (!resp.ok) {
            const errData = await resp.json().catch(() => ({}));
            throw new Error(errData.detail || `HTTP ${resp.status}`);
        }
        hideStatus('adminStatus');
        showStatus('adminStatus', 'User active status toggled.', 'success');
    } catch (err) {
        showStatus('adminStatus', `Failed: ${err.message}`, 'error');
        loadAdminUsers();
    }
}

async function deleteUser(userId) {
    if (!requireAdmin()) return;
    if (!confirm('Are you sure you want to delete this user? This cannot be undone.')) return;
    showStatus('adminStatus', `Deleting user ${userId}...`, 'loading');
    try {
        const resp = await apiFetch(`/api/admin/users/${userId}`, {
            method: 'DELETE',
        });
        if (!resp.ok) {
            const errData = await resp.json().catch(() => ({}));
            throw new Error(errData.detail || `HTTP ${resp.status}`);
        }
        hideStatus('adminStatus');
        showStatus('adminStatus', 'User deleted.', 'success');
        loadAdminUsers();
    } catch (err) {
        showStatus('adminStatus', `Failed: ${err.message}`, 'error');
    }
}

async function loadAdminConfig() {
    if (!requireAdmin()) return;
    showStatus('adminStatus', 'Loading configuration...', 'loading');
    const container = document.getElementById('adminConfigForm');
    container.innerHTML = '';

    try {
        const resp = await apiFetch('/api/admin/config');
        if (!resp.ok) {
            const errData = await resp.json().catch(() => ({}));
            throw new Error(errData.detail || `HTTP ${resp.status}`);
        }
        const data = await resp.json();
        const config = data.config || data;
        hideStatus('adminStatus');

        const entries = Object.entries(config);
        if (!entries.length) {
            container.innerHTML = '<p class="placeholder-text">No configuration entries.</p>';
            return;
        }

        container.innerHTML = `
            <div class="admin-form-inner">
                ${entries.map(([key, val]) => `
                    <label class="filter-input admin-config-field">
                        <span class="label-text">${escapeHtml(key)}:</span>
                        <input type="text" id="config_${escapeHtml(key)}" value="${escapeHtml(String(val))}" data-key="${escapeHtml(key)}">
                    </label>
                `).join('')}
                <button id="saveAdminConfigBtn" class="btn-primary">Save Configuration</button>
            </div>
        `;
        document.getElementById('saveAdminConfigBtn').addEventListener('click', updateAdminConfig);
    } catch (err) {
        showStatus('adminStatus', `Failed to load config: ${err.message}`, 'error');
    }
}

async function updateAdminConfig() {
    if (!requireAdmin()) return;
    const fields = document.querySelectorAll('.admin-config-field input[data-key]');
    const config = {};
    fields.forEach(f => { config[f.dataset.key] = f.value; });

    showStatus('adminStatus', 'Saving configuration...', 'loading');
    try {
        const resp = await apiFetch('/api/admin/config', {
            method: 'PUT',
            body: JSON.stringify(config),
        });
        if (!resp.ok) {
            const errData = await resp.json().catch(() => ({}));
            throw new Error(errData.detail || `HTTP ${resp.status}`);
        }
        hideStatus('adminStatus');
        showStatus('adminStatus', 'Configuration saved.', 'success');
    } catch (err) {
        showStatus('adminStatus', `Failed: ${err.message}`, 'error');
    }
}

async function loadAdminContent() {
    if (!requireAdmin()) return;
    showStatus('adminStatus', 'Loading content templates...', 'loading');
    const container = document.getElementById('adminContentForm');
    container.innerHTML = '';

    try {
        const resp = await apiFetch('/api/admin/content');
        if (!resp.ok) {
            const errData = await resp.json().catch(() => ({}));
            throw new Error(errData.detail || `HTTP ${resp.status}`);
        }
        const data = await resp.json();
        const content = data.content || data;
        hideStatus('adminStatus');

        const entries = Object.entries(content);
        if (!entries.length) {
            container.innerHTML = '<p class="placeholder-text">No content templates.</p>';
            return;
        }

        container.innerHTML = `
            <div class="admin-form-inner">
                ${entries.map(([key, val]) => `
                    <label class="admin-config-field">
                        <span class="label-text">${escapeHtml(key)}:</span>
                        <textarea id="content_${escapeHtml(key)}" data-key="${escapeHtml(key)}" rows="4" class="prompt-textarea" style="min-height:80px;">${escapeHtml(String(val))}</textarea>
                    </label>
                `).join('')}
                <button id="saveAdminContentBtn" class="btn-primary">Save Content</button>
            </div>
        `;
        document.getElementById('saveAdminContentBtn').addEventListener('click', updateAdminContent);
    } catch (err) {
        showStatus('adminStatus', `Failed to load content: ${err.message}`, 'error');
    }
}

async function updateAdminContent() {
    if (!requireAdmin()) return;
    const fields = document.querySelectorAll('#adminContentForm textarea[data-key]');
    const content = {};
    fields.forEach(f => { content[f.dataset.key] = f.value; });

    showStatus('adminStatus', 'Saving content templates...', 'loading');
    try {
        const resp = await apiFetch('/api/admin/content', {
            method: 'PUT',
            body: JSON.stringify(content),
        });
        if (!resp.ok) {
            const errData = await resp.json().catch(() => ({}));
            throw new Error(errData.detail || `HTTP ${resp.status}`);
        }
        hideStatus('adminStatus');
        showStatus('adminStatus', 'Content templates saved.', 'success');
    } catch (err) {
        showStatus('adminStatus', `Failed: ${err.message}`, 'error');
    }
}

async function loadAdminStats() {
    if (!requireAdmin()) return;
    showStatus('adminStatus', 'Loading platform statistics...', 'loading');
    const container = document.getElementById('adminStats');
    container.innerHTML = '';

    try {
        const resp = await apiFetch('/api/admin/stats');
        if (!resp.ok) {
            const errData = await resp.json().catch(() => ({}));
            throw new Error(errData.detail || `HTTP ${resp.status}`);
        }
        const data = await resp.json();
        const stats = data.stats || data;
        hideStatus('adminStatus');

        const entries = Object.entries(stats);
        if (!entries.length) {
            container.innerHTML = '<p class="placeholder-text">No statistics available.</p>';
            return;
        }

        container.innerHTML = `
            <div class="writing-stats-grid">
                ${entries.map(([key, val]) => `
                    <div class="stat-card">
                        <span class="stat-label">${escapeHtml(key.replace(/_/g, ' '))}</span>
                        <span class="stat-value">${escapeHtml(String(val))}</span>
                    </div>
                `).join('')}
            </div>
        `;
    } catch (err) {
        showStatus('adminStatus', `Failed to load stats: ${err.message}`, 'error');
    }
}

async function loadDatabaseSources() {
    if (!requireAdmin()) return;
    showStatus('adminStatus', 'Loading database sources...', 'loading');
    const container = document.getElementById('adminDbSources');
    container.innerHTML = '';

    try {
        const resp = await apiFetch('/api/admin/database-sources');
        if (!resp.ok) {
            const errData = await resp.json().catch(() => ({}));
            throw new Error(errData.detail || `HTTP ${resp.status}`);
        }
        const data = await resp.json();
        const sources = data.sources || data.database_sources || data;
        hideStatus('adminStatus');

        if (!sources.length) {
            container.innerHTML = '<p class="placeholder-text">No database sources configured.</p>';
            return;
        }

        container.innerHTML = sources.map(s => `
            <div class="admin-list-item">
                <div class="admin-list-info">
                    <span class="admin-list-name">${escapeHtml(s.name || s.id)}</span>
                    <span class="admin-list-status ${s.enabled || s.is_active ? 'enabled' : 'disabled'}">
                        ${s.enabled || s.is_active ? 'Enabled' : 'Disabled'}
                    </span>
                </div>
                <label class="toggle-switch">
                    <input type="checkbox" ${s.enabled || s.is_active ? 'checked' : ''} onchange="toggleDatabaseSource('${s.id}')">
                    <span class="toggle-slider"></span>
                </label>
            </div>
        `).join('');
    } catch (err) {
        showStatus('adminStatus', `Failed: ${err.message}`, 'error');
    }
}

async function toggleDatabaseSource(sourceId) {
    if (!requireAdmin()) return;
    showStatus('adminStatus', `Toggling database source ${sourceId}...`, 'loading');
    try {
        const resp = await apiFetch(`/api/admin/database-sources/${sourceId}/toggle`, {
            method: 'POST',
        });
        if (!resp.ok) {
            const errData = await resp.json().catch(() => ({}));
            throw new Error(errData.detail || `HTTP ${resp.status}`);
        }
        hideStatus('adminStatus');
        showStatus('adminStatus', 'Database source toggled.', 'success');
        loadDatabaseSources();
    } catch (err) {
        showStatus('adminStatus', `Failed: ${err.message}`, 'error');
        loadDatabaseSources();
    }
}

async function loadToolIntegrations() {
    if (!requireAdmin()) return;
    showStatus('adminStatus', 'Loading tool integrations...', 'loading');
    const container = document.getElementById('adminTools');
    container.innerHTML = '';

    try {
        const resp = await apiFetch('/api/admin/tools');
        if (!resp.ok) {
            const errData = await resp.json().catch(() => ({}));
            throw new Error(errData.detail || `HTTP ${resp.status}`);
        }
        const data = await resp.json();
        const tools = data.tools || data;
        hideStatus('adminStatus');

        if (!tools.length) {
            container.innerHTML = '<p class="placeholder-text">No tool integrations configured.</p>';
            return;
        }

        container.innerHTML = tools.map(t => `
            <div class="admin-list-item">
                <div class="admin-list-info">
                    <span class="admin-list-name">${escapeHtml(t.name || t.id)}</span>
                    <span class="admin-list-status ${t.enabled || t.is_active ? 'enabled' : 'disabled'}">
                        ${t.enabled || t.is_active ? 'Enabled' : 'Disabled'}
                    </span>
                </div>
                <label class="toggle-switch">
                    <input type="checkbox" ${t.enabled || t.is_active ? 'checked' : ''} onchange="toggleToolIntegration('${t.id}')">
                    <span class="toggle-slider"></span>
                </label>
            </div>
        `).join('');
    } catch (err) {
        showStatus('adminStatus', `Failed: ${err.message}`, 'error');
    }
}

async function toggleToolIntegration(toolId) {
    if (!requireAdmin()) return;
    showStatus('adminStatus', `Toggling tool integration ${toolId}...`, 'loading');
    try {
        const resp = await apiFetch(`/api/admin/tools/${toolId}/toggle`, {
            method: 'POST',
        });
        if (!resp.ok) {
            const errData = await resp.json().catch(() => ({}));
            throw new Error(errData.detail || `HTTP ${resp.status}`);
        }
        hideStatus('adminStatus');
        showStatus('adminStatus', 'Tool integration toggled.', 'success');
        loadToolIntegrations();
    } catch (err) {
        showStatus('adminStatus', `Failed: ${err.message}`, 'error');
        loadToolIntegrations();
    }
}

// ===========================================================================
// AI Model Configuration (Admin Panel)
// ===========================================================================

const AI_PROVIDER_LABELS = {
    gemini:    { name: 'Google Gemini',           link: 'https://aistudio.google.com/app/apikey',          tier: 'Free tier' },
    groq:      { name: 'Groq (Llama / Mixtral)',   link: 'https://console.groq.com/keys',                   tier: 'Free tier' },
    deepseek:  { name: 'DeepSeek',                 link: 'https://platform.deepseek.com/api_keys',          tier: 'Free tier' },
    mistral:   { name: 'Mistral AI',               link: 'https://console.mistral.ai/api-keys/',            tier: 'Free tier' },
    qwen:      { name: 'Qwen (Alibaba DashScope)', link: 'https://dashscope.console.aliyun.com/apiKey',     tier: 'Free tier' },
    openai:    { name: 'OpenAI (GPT-4o)',          link: 'https://platform.openai.com/api-keys',            tier: 'Paid' },
    anthropic: { name: 'Anthropic (Claude)',       link: 'https://console.anthropic.com/settings/keys',     tier: 'Paid' },
};

async function loadAiConfig() {
    if (!requireAdmin()) return;
    showStatus('aiConfigStatus', 'Loading AI model configuration...', 'loading');
    const summaryEl = document.getElementById('aiConfigSummary');
    const formEl = document.getElementById('aiConfigForm');
    summaryEl.innerHTML = '';
    formEl.innerHTML = '';

    try {
        const resp = await apiFetch('/api/admin/ai-config');
        if (!resp.ok) {
            const errData = await resp.json().catch(() => ({}));
            throw new Error(errData.detail || `HTTP ${resp.status}`);
        }
        const data = await resp.json();
        hideStatus('aiConfigStatus');

        const providers = data.providers || {};
        const providerEntries = Object.entries(providers);
        const available = data.available_count || 0;
        const total = data.total_count || providerEntries.length;

        // Render summary cards
        summaryEl.innerHTML = `
            <div class="ai-summary-card">
                <span class="stat-num">${available}</span>
                <span class="stat-desc">Providers Active</span>
            </div>
            <div class="ai-summary-card">
                <span class="stat-num">${total}</span>
                <span class="stat-desc">Total Providers</span>
            </div>
            <div class="ai-summary-card">
                <span class="stat-num">${available > 0 ? 'AI' : 'Template'}</span>
                <span class="stat-desc">Active Mode</span>
            </div>
        `;

        // Render provider cards
        formEl.innerHTML = providerEntries.map(([pid, info]) => {
            const label = AI_PROVIDER_LABELS[pid] || { name: pid, link: '#', tier: '' };
            const hasKey = info.has_key;
            const sourceLabel = info.key_source === 'admin' ? 'Admin Config'
                              : info.key_source === 'env' ? 'Env Variable'
                              : 'Not Set';
            const modelsText = (info.models || []).join(', ');
            const tierBadge = info.free_tier
                ? '<span style="color:#38a169;font-weight:600;">Free</span>'
                : '<span style="color:#d69e2e;font-weight:600;">Paid</span>';

            return `
                <div class="ai-provider-card ${hasKey ? 'has-key' : 'no-key'}" data-provider="${escapeHtml(pid)}">
                    <div class="ai-provider-header">
                        <div>
                            <span class="ai-provider-name">${escapeHtml(label.name)}</span>
                            <div class="ai-provider-meta">
                                Models: ${escapeHtml(modelsText)} &middot; ${tierBadge}
                                &middot; <a href="${escapeHtml(label.link)}" target="_blank" rel="noopener">Get API key &nearr;</a>
                            </div>
                        </div>
                        <span class="ai-key-status ${hasKey ? 'configured' : 'not-configured'}">
                            <span class="status-dot"></span>
                            ${hasKey ? 'Configured' : 'Not configured'} (${escapeHtml(sourceLabel)})
                        </span>
                    </div>
                    <div class="ai-key-input-row">
                        <input
                            type="password"
                            class="ai-key-input"
                            id="aikey_${escapeHtml(pid)}"
                            placeholder="${hasKey ? '•••••••• (enter new key to replace)' : 'Paste your API key here...'}"
                            data-provider="${escapeHtml(pid)}"
                        >
                    </div>
                    ${hasKey && info.key_preview ? `<div class="ai-key-preview">Current: ${escapeHtml(info.key_preview)}</div>` : ''}
                    <div class="ai-provider-actions" style="margin-top:0.6rem;">
                        <button class="ai-btn-test" onclick="testAiProvider('${escapeHtml(pid)}')">Test Connection</button>
                        <button class="ai-btn-clear" onclick="clearAiKey('${escapeHtml(pid)}')">Clear Key</button>
                    </div>
                    <div class="ai-test-result" id="aitest_${escapeHtml(pid)}"></div>
                </div>
            `;
        }).join('');

        // Add save button bar
        formEl.innerHTML += `
            <div class="ai-save-bar">
                <button id="saveAiKeysBtn" class="btn-primary" onclick="saveAiKeys()">Save All Keys</button>
                <span style="font-size:0.8rem;color:#718096;">Keys are stored in the platform config and override environment variables.</span>
            </div>
        `;

        // Add routing info
        const routing = data.task_routing || {};
        const routingEntries = Object.entries(routing);
        if (routingEntries.length) {
            formEl.innerHTML += `
                <div class="ai-routing-info">
                    <h4>Task Routing (priority order per task)</h4>
                    <div class="ai-routing-list">
                        ${routingEntries.map(([task, models]) => `
                            <div><span class="routing-task">${escapeHtml(task.replace(/_/g, ' '))}:</span> ${escapeHtml(models.join(' → '))}</div>
                        `).join('')}
                    </div>
                </div>
            `;
        }

    } catch (err) {
        showStatus('aiConfigStatus', `Failed to load AI config: ${err.message}`, 'error');
    }
}

async function saveAiKeys() {
    if (!requireAdmin()) return;
    const inputs = document.querySelectorAll('.ai-key-input[data-provider]');
    const updates = {};
    let hasChanges = false;

    inputs.forEach(inp => {
        const val = inp.value.trim();
        if (val) {
            updates[`${inp.dataset.provider}_api_key`] = val;
            hasChanges = true;
        }
    });

    if (!hasChanges) {
        showStatus('aiConfigStatus', 'No new keys entered. Enter a key in any field to save.', 'error');
        return;
    }

    showStatus('aiConfigStatus', 'Saving AI API keys...', 'loading');
    try {
        const resp = await apiFetch('/api/admin/config', {
            method: 'PUT',
            body: JSON.stringify(updates),
        });
        if (!resp.ok) {
            const errData = await resp.json().catch(() => ({}));
            throw new Error(errData.detail || `HTTP ${resp.status}`);
        }
        hideStatus('aiConfigStatus');
        showStatus('aiConfigStatus', 'AI API keys saved successfully. Provider status updated.', 'success');
        // Clear the input fields and reload to show updated status
        inputs.forEach(inp => { inp.value = ''; });
        setTimeout(() => loadAiConfig(), 800);
    } catch (err) {
        showStatus('aiConfigStatus', `Failed to save keys: ${err.message}`, 'error');
    }
}

async function testAiProvider(providerId) {
    if (!requireAdmin()) return;
    const resultEl = document.getElementById(`aitest_${providerId}`);
    if (!resultEl) return;

    // Check if there's a new key in the input field
    const inputEl = document.getElementById(`aikey_${providerId}`);
    const newKey = inputEl ? inputEl.value.trim() : '';

    resultEl.className = 'ai-test-result show testing';
    resultEl.textContent = 'Testing connection...';

    try {
        const resp = await apiFetch('/api/admin/ai-config/test', {
            method: 'POST',
            body: JSON.stringify({ provider: providerId, api_key: newKey || null }),
        });
        if (!resp.ok) {
            const errData = await resp.json().catch(() => ({}));
            throw new Error(errData.detail || `HTTP ${resp.status}`);
        }
        const data = await resp.json();

        if (data.success) {
            resultEl.className = 'ai-test-result show success';
            resultEl.innerHTML = `&#10003; ${escapeHtml(data.message)}`;
        } else {
            resultEl.className = 'ai-test-result show error';
            resultEl.innerHTML = `&#10007; ${escapeHtml(data.message)}`;
        }
    } catch (err) {
        resultEl.className = 'ai-test-result show error';
        resultEl.innerHTML = `&#10007; Error: ${escapeHtml(err.message)}`;
    }
}

async function clearAiKey(providerId) {
    if (!requireAdmin()) return;
    if (!confirm(`Clear the API key for ${providerId}? This sets it to empty in the platform config. (Environment variable keys, if set, will still be used as fallback.)`)) return;

    showStatus('aiConfigStatus', `Clearing key for ${providerId}...`, 'loading');
    try {
        const resp = await apiFetch('/api/admin/config', {
            method: 'PUT',
            body: JSON.stringify({ [`${providerId}_api_key`]: '' }),
        });
        if (!resp.ok) {
            const errData = await resp.json().catch(() => ({}));
            throw new Error(errData.detail || `HTTP ${resp.status}`);
        }
        hideStatus('aiConfigStatus');
        showStatus('aiConfigStatus', `Key for ${providerId} cleared.`, 'success');
        setTimeout(() => loadAiConfig(), 600);
    } catch (err) {
        showStatus('aiConfigStatus', `Failed: ${err.message}`, 'error');
    }
}

// Expose admin functions for inline onclick handlers
window.toggleUserRole = toggleUserRole;
window.toggleUserActive = toggleUserActive;
window.deleteUser = deleteUser;
window.toggleDatabaseSource = toggleDatabaseSource;
window.toggleToolIntegration = toggleToolIntegration;
window.testAiProvider = testAiProvider;
window.clearAiKey = clearAiKey;
window.saveAiKeys = saveAiKeys;


// ===========================================================================
// DRAFTING ASSISTANT — Document Roadmap, Research Topics, Open-Access Articles
// ===========================================================================

// ---- Document type format data (mirrors backend DOCUMENT_TYPES) ----
const DOC_TYPE_FORMATS = {
    research_article: {
        Q1: "Top-tier journal (Nature, Science, top field journals). Strict structure, high novelty, comprehensive methodology.",
        Q2: "High-quality journal. Standard IMRaD, solid contribution, robust methodology.",
        Q3: "Established journal. Standard structure, adequate contribution.",
        Q4: "Emerging/regional journal. Standard structure, contextual contribution.",
        general: "General research article format suitable for most journals.",
    },
    thesis: {
        undergraduate_usa: "Undergraduate Thesis (USA): Intro, Lit Review, Methodology, Results, Discussion, Conclusion. 40-60 pages.",
        undergraduate_uk: "Undergraduate Dissertation (UK): Intro, Lit Review, Methodology, Findings, Discussion, Conclusion. 10,000-15,000 words.",
        undergraduate_european: "Undergraduate Thesis (European): Intro, Theoretical Framework, Methodology, Empirical Analysis, Discussion, Conclusion. 30-50 pages.",
        undergraduate_chinese: "Undergraduate Thesis (Chinese): 摘要, 关键词, 引言, 文献综述, 研究方法, 研究结果, 讨论, 结论, 参考文献, 致谢. 8,000-15,000 characters.",
        undergraduate_african: "Undergraduate Project (African): Title Page, Declaration, Dedication, Acknowledgments, Abstract, TOC, Chapters 1-5, References, Appendices. 40-60 pages.",
        graduate_usa: "Master's Thesis (USA): Intro, Lit Review, Methodology, Results, Discussion, Conclusion, References, Appendices. 60-100 pages.",
        graduate_uk: "Master's Dissertation (UK): 15,000-20,000 words. Standard structure.",
        graduate_european: "Master's Thesis (European): Intro, Theoretical Framework, Lit Review, Methodology, Empirical Analysis, Discussion, Policy Implications, Conclusion. 60-80 pages.",
        graduate_chinese: "Master's Thesis (Chinese): 摘要, 绪论, 文献综述, 理论框架, 研究方法, 实证分析, 讨论, 结论与展望. 30,000-50,000 characters.",
        graduate_african: "Master's Dissertation (African): Title Page, Declaration, Certification, Chapters 1-6, References, Appendices. 80-120 pages.",
        phd_usa: "PhD Dissertation (USA): Intro, comprehensive Lit Review, Theoretical Framework, Methodology, multiple Results chapters, Discussion, Conclusion. 150-300 pages.",
        phd_uk: "PhD Thesis (UK): Intro, Lit Review, Methodology, Results, Discussion, Conclusion. 80,000-100,000 words.",
        phd_european: "PhD Thesis (European): Intro, Theoretical Framework, Lit Review, Methodology, multiple Empirical chapters, Discussion, Policy Implications, Conclusion. 150-250 pages.",
        phd_chinese: "PhD Dissertation (Chinese): 摘要, 绪论, 文献综述, 理论框架与研究假设, 研究设计与方法, 实证分析, 进一步分析, 结论与政策建议. 80,000-150,000 characters.",
        phd_african: "PhD Thesis (African): Title Page, Declaration, Certification, Chapters 1-7, References, Appendices. 200-350 pages.",
    },
    literature_review: {
        systematic: "Systematic Literature Review (PRISMA): Intro, Methods (search strategy, inclusion/exclusion), Results (PRISMA flow), Discussion, Conclusion.",
        narrative: "Narrative Literature Review: Intro, Thematic Sections, Discussion, Conclusion, References.",
        scoping: "Scoping Review: Intro, Methods (framework, search), Results (charting data), Discussion, Conclusion.",
        bibliometric: "Bibliometric Review: Intro, Data and Methods, Descriptive Results, Citation Analysis, Co-citation Analysis, Discussion, Conclusion.",
    },
    book_report: {
        analytical: "Analytical Book Report: Bibliographic Info, Intro, Summary (chapter-by-chapter), Critical Analysis, Themes, Strengths/Weaknesses, Conclusion.",
        comparative: "Comparative Book Report: Intro, Summary of Each Book, Comparative Analysis, Thematic Discussion, Conclusion.",
        academic_review: "Academic Book Review: Bibliographic Info, Brief Summary, Critical Evaluation, Contribution to Field, Recommendation.",
    },
    review_paper: {
        Q1: "Top-tier review paper: Abstract, Intro, Search Strategy, Thematic Analysis, Critical Synthesis, Research Agenda, Conclusion. 100+ references.",
        Q2: "Standard review paper: Abstract, Intro, Literature Search, Thematic Review, Discussion, Future Directions, Conclusion. 50-100 references.",
        Q3: "Review paper: Abstract, Intro, Literature Review, Discussion, Conclusion. 30-50 references.",
        narrative: "Narrative review: Abstract, Intro, Background, Review Sections, Discussion, Conclusion.",
    },
    conference_paper: {
        full: "Full Conference Paper: Abstract, Intro, Related Work, Methodology, Results, Discussion, Conclusion. 8-12 pages.",
        short: "Short Paper / Poster: Abstract, Intro, Approach, Preliminary Results, Conclusion. 4-6 pages.",
        workshop: "Workshop Paper: Abstract, Intro, Methodology, Results, Discussion. 6-8 pages.",
    },
    research_proposal: {
        grant: "Grant Proposal: Title, Abstract, Background, Specific Aims, Research Strategy, Timeline, Budget Justification, References.",
        academic: "Academic Research Proposal: Title, Intro, Lit Review, Research Questions, Methodology, Timeline, Expected Outcomes, References.",
        phd_proposal: "PhD Research Proposal: Title, Intro, Research Gap, Questions, Lit Review, Theoretical Framework, Methodology, Timeline. 3,000-5,000 words.",
    },
};


// ---- Format dropdown population ----
function updateRoadmapFormats() {
    const docType = document.getElementById('roadmapDocType').value;
    const formatSelect = document.getElementById('roadmapFormat');
    const formats = DOC_TYPE_FORMATS[docType] || {};
    formatSelect.innerHTML = '';
    for (const [key, desc] of Object.entries(formats)) {
        const opt = document.createElement('option');
        opt.value = key;
        // Truncate description for the dropdown label
        const shortDesc = desc.length > 80 ? desc.substring(0, 77) + '...' : desc;
        opt.textContent = key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()) + ' — ' + shortDesc;
        formatSelect.appendChild(opt);
    }
}


// ---- Drafting sub-tab switching ----
document.querySelectorAll('.drafting-subtab').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.drafting-subtab').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const target = btn.dataset.subtab;
        document.querySelectorAll('.drafting-subpanel').forEach(p => {
            p.classList.remove('active');
            p.style.display = 'none';
        });
        const panel = document.getElementById('drafting' + target);
        if (panel) { panel.classList.add('active'); panel.style.display = 'block'; }
    });
});


// ---- Initialize format dropdown on load ----
updateRoadmapFormats();


// ===========================================================================
// ROADMAP GENERATION
// ===========================================================================

document.getElementById('generateRoadmapBtn').addEventListener('click', async () => {
    const docType = document.getElementById('roadmapDocType').value;
    const format = document.getElementById('roadmapFormat').value;
    const topic = document.getElementById('roadmapTopic').value.trim();
    const field = document.getElementById('roadmapField').value.trim();

    if (!topic) {
        showStatus('roadmapStatus', 'Please enter a research topic or title.', 'error');
        return;
    }

    const btn = document.getElementById('generateRoadmapBtn');
    btn.disabled = true;
    btn.innerHTML = 'Generating...';
    showStatus('roadmapStatus', 'Generating document roadmap...', 'loading');
    document.getElementById('roadmapResults').innerHTML = '';

    try {
        const resp = await apiFetch('/api/drafting/roadmap', {
            method: 'POST',
            body: JSON.stringify({ document_type: docType, format, topic, field }),
        });
        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            throw new Error(err.detail || `HTTP ${resp.status}`);
        }
        const data = await resp.json();
        hideStatus('roadmapStatus');
        showStatus('roadmapStatus',
            `Roadmap generated: ${data.total_sections} sections, ~${data.total_estimated_words.toLocaleString()} estimated words.`,
            'success');
        renderRoadmap(data);
    } catch (err) {
        showStatus('roadmapStatus', `Failed: ${err.message}`, 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '\u{1F4CE} Generate Roadmap';
    }
});


function renderRoadmap(data) {
    const container = document.getElementById('roadmapResults');

    const sectionsHtml = data.sections.map((s, i) => `
        <div class="roadmap-section">
            <div class="roadmap-section-header">
                <h4>${escapeHtml(s.title)}</h4>
                <span class="roadmap-word-est">${s.est_words.toLocaleString()} words</span>
            </div>
            <p class="roadmap-purpose"><strong>Purpose:</strong> ${escapeHtml(s.purpose)}</p>
            <p class="roadmap-guidelines"><strong>Writing Guidelines:</strong> ${escapeHtml(s.guidelines)}</p>
        </div>
    `).join('');

    const aiRoadmap = data.ai_roadmap || '';
    const fullMarkdown = aiRoadmap || data.roadmap_markdown;
    const aiRoadmapBlock = aiRoadmap ? `
        <div class="ai-content-block">
            <div class="ai-content-header">
                <h4>AI-Generated Roadmap</h4>
                ${aiModelBadge(data.model_used)}
            </div>
            ${renderMarkdown(aiRoadmap)}
        </div>` : '';

    container.innerHTML = `
        <div class="roadmap-summary-bar">
            <div class="roadmap-meta">
                <span><strong>Type:</strong> ${escapeHtml(data.document_type_label)}</span>
                <span><strong>Format:</strong> ${escapeHtml(data.format)}</span>
                <span><strong>Field:</strong> ${escapeHtml(data.field || 'Not specified')}</span>
                <span><strong>Sections:</strong> ${data.total_sections}</span>
                <span><strong>Est. Words:</strong> ${data.total_estimated_words.toLocaleString()}</span>
            </div>
            <div class="roadmap-actions">
                <button class="btn-copy" onclick="copyGeneratedText(this, ${JSON.stringify(fullMarkdown).replace(/'/g, '&#39;')})">
                    &#128203; Copy Roadmap
                </button>
                <button class="btn-secondary btn-sm" onclick="downloadRoadmapMd(${JSON.stringify(fullMarkdown).replace(/'/g, '&#39;')}, ${JSON.stringify(data.topic).replace(/'/g, '&#39;')})">
                    &#128190; Download .md
                </button>
            </div>
        </div>
        ${aiRoadmapBlock}
        <div class="roadmap-format-desc">${escapeHtml(data.format_description)}</div>
        <div class="roadmap-sections-list">${sectionsHtml}</div>
        <div class="roadmap-disclaimer">${escapeHtml(data.disclaimer)}</div>
    `;
}


function downloadRoadmapMd(text, topic) {
    const blob = new Blob([text], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'THEeye_Roadmap_' + topic.replace(/[^a-zA-Z0-9]/g, '_').substring(0, 40) + '.md';
    a.click();
    URL.revokeObjectURL(url);
}


// ===========================================================================
// RESEARCH TOPIC SUGGESTION
// ===========================================================================

document.getElementById('suggestTopicsBtn').addEventListener('click', async () => {
    const field = document.getElementById('topicField').value;
    const keywords = document.getElementById('topicKeywords').value.trim();
    const focusNovelty = document.getElementById('topicNovelty').checked;
    const maxTopics = parseInt(document.getElementById('topicMax').value) || 10;

    const btn = document.getElementById('suggestTopicsBtn');
    btn.disabled = true;
    btn.innerHTML = 'Suggesting...';
    showStatus('topicsStatus', 'Generating novel research topic suggestions...', 'loading');
    document.getElementById('topicsResults').innerHTML = '';

    try {
        const resp = await apiFetch('/api/drafting/topics', {
            method: 'POST',
            body: JSON.stringify({ field, keywords, focus_novelty: focusNovelty, max_topics: maxTopics }),
        });
        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            throw new Error(err.detail || `HTTP ${resp.status}`);
        }
        const data = await resp.json();
        hideStatus('topicsStatus');
        showStatus('topicsStatus', `Found ${data.total} topic suggestions in ${data.field}.`, 'success');
        renderTopics(data);
    } catch (err) {
        showStatus('topicsStatus', `Failed: ${err.message}`, 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '\u{1F4A1} Suggest Topics';
    }
});


function renderTopics(data) {
    const container = document.getElementById('topicsResults');

    const topicsHtml = data.topics.map((t, i) => `
        <div class="topic-card">
            <div class="topic-card-header">
                <span class="topic-number">#${i + 1}</span>
                <h4>${escapeHtml(t.topic)}</h4>
                <span class="topic-difficulty difficulty-${t.estimated_difficulty.toLowerCase()}">${t.estimated_difficulty}</span>
            </div>
            <div class="topic-card-body">
                <p class="topic-gap"><strong>Research Gap:</strong> ${escapeHtml(t.research_gap)}</p>
                <div class="topic-novelty">
                    <strong>Novelty Factors:</strong>
                    <ul>${t.novelty_factors.map(f => `<li>${escapeHtml(f)}</li>`).join('')}</ul>
                </div>
                <div class="topic-methodology">
                    <strong>Suggested Methodology:</strong>
                    <ul>${t.suggested_methodology.map(m => `<li>${escapeHtml(m)}</li>`).join('')}</ul>
                </div>
                <div class="topic-journals">
                    <strong>Potential Journals:</strong>
                    ${t.potential_journals.map(j => `<span class="journal-tag">${escapeHtml(j)}</span>`).join('')}
                </div>
                <div class="topic-card-actions">
                    <button class="btn-secondary btn-sm" onclick="searchOATopics(${JSON.stringify(t.topic).replace(/'/g, '&#39;')})">
                        &#128196; Find Open-Access Articles
                    </button>
                    <button class="btn-copy btn-sm" onclick="copyGeneratedText(this, ${JSON.stringify(t.topic).replace(/'/g, '&#39;')})">
                        &#128203; Copy Topic
                    </button>
                </div>
            </div>
        </div>
    `).join('');

    const subAreasHtml = data.sub_areas.map(s => `<span class="sub-area-tag">${escapeHtml(s)}</span>`).join('');

    const aiTopicsBlock = data.ai_topics ? `
        <div class="ai-content-block">
            <div class="ai-content-header">
                <h4>AI-Generated Topic Suggestions</h4>
                ${aiModelBadge(data.model_used)}
            </div>
            ${renderMarkdown(data.ai_topics)}
        </div>` : '';

    container.innerHTML = `
        <div class="topics-summary">
            <p><strong>Field:</strong> ${escapeHtml(data.field)}</p>
            <div class="sub-areas"><strong>Sub-areas:</strong> ${subAreasHtml}</div>
            <p class="topics-note">${escapeHtml(data.note)}</p>
        </div>
        ${aiTopicsBlock}
        <div class="topics-list">${topicsHtml}</div>
    `;
}


// ===========================================================================
// OPEN-ACCESS ARTICLE FINDER
// ===========================================================================

document.getElementById('findArticlesBtn').addEventListener('click', async () => {
    const topic = document.getElementById('oaTopic').value.trim();
    const maxResults = parseInt(document.getElementById('oaMax').value) || 15;

    if (!topic) {
        showStatus('articlesStatus', 'Please enter a research topic.', 'error');
        return;
    }

    const btn = document.getElementById('findArticlesBtn');
    btn.disabled = true;
    btn.innerHTML = 'Searching...';
    showStatus('articlesStatus', 'Searching 7 platforms (OpenAlex, Semantic Scholar, CORE, Crossref, DOAJ, arXiv, Academia.edu) for open-access articles with PDFs across 300M+ papers...', 'loading');
    document.getElementById('articlesResults').innerHTML = '';

    try {
        const resp = await apiFetch('/api/drafting/open-access-articles', {
            method: 'POST',
            body: JSON.stringify({ topic, max_results: maxResults }),
        });
        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            throw new Error(err.detail || `HTTP ${resp.status}`);
        }
        const data = await resp.json();
        hideStatus('articlesStatus');
        if (data.total_found === 0) {
            showStatus('articlesStatus', 'No open-access articles found across any of the 7 platforms. Try broader keywords or a different topic.', 'error');
        } else {
            const sources = data.sources_succeeded ? data.sources_succeeded.join(', ') : 'multiple sources';
            showStatus('articlesStatus', `Found ${data.total_found} open-access articles from: ${sources}. Download PDFs directly or click "Open in Browser" to access the source.`, 'success');
        }
        renderOAArticles(data);
    } catch (err) {
        showStatus('articlesStatus', `Failed: ${err.message}`, 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '\u{1F4C4} Find Articles';
    }
});


function renderOAArticles(data) {
    const container = document.getElementById('articlesResults');

    if (!data.articles || data.articles.length === 0) {
        container.innerHTML = '<p class="placeholder-text">No articles found. Try a different topic or broader keywords.</p>';
        return;
    }

    // Source-specific CSS classes for badges
    const sourceClass = (src) => {
        const map = {
            'OpenAlex': 'src-openalex',
            'Semantic Scholar': 'src-s2',
            'CORE': 'src-core',
            'Crossref': 'src-crossref',
            'DOAJ': 'src-doaj',
            'arXiv': 'src-arxiv',
            'Academia.edu': 'src-academia',
        };
        return map[src] || 'src-default';
    };

    const articlesHtml = data.articles.map((a, i) => {
        const authors = a.authors && a.authors.length > 0
            ? a.authors.join(', ') + (a.authors.length > 5 ? ' et al.' : '')
            : 'Unknown';
        const abstract = a.abstract
            ? (a.abstract.length > 300 ? escapeHtml(a.abstract.substring(0, 297)) + '...' : escapeHtml(a.abstract))
            : '<em>No abstract available</em>';
        const yearStr = a.year ? `(${a.year})` : '';
        const journalStr = a.journal ? `<em>${escapeHtml(a.journal)}</em>` : '';
        const doiLink = a.doi
            ? `<a href="https://doi.org/${escapeHtml(a.doi)}" target="_blank" class="doi-link">${escapeHtml(a.doi)}</a>`
            : '';
        const srcCls = sourceClass(a.source);
        const sourceTag = a.source ? `<span class="source-tag ${srcCls}">${escapeHtml(a.source)}</span>` : '';

        return `
            <div class="oa-article-card">
                <div class="oa-article-header">
                    <span class="oa-article-number">#${i + 1}</span>
                    <h4>${escapeHtml(a.title)}</h4>
                    ${a.cited_by_count > 0 ? `<span class="citation-count">&#128279; ${a.cited_by_count} citations</span>` : ''}
                </div>
                <div class="oa-article-meta">
                    <span class="oa-authors">${escapeHtml(authors)} ${yearStr}</span>
                    ${journalStr ? '<span class="oa-journal">' + journalStr + '</span>' : ''}
                    ${doiLink}
                    ${sourceTag}
                    ${a.license ? `<span class="license-tag">${escapeHtml(a.license)}</span>` : ''}
                </div>
                <div class="oa-article-abstract">${abstract}</div>
                <div class="oa-article-actions">
                    ${a.pdf_url
                        ? `<button class="btn-primary btn-sm" onclick="downloadArticlePdf(this, ${JSON.stringify(a.pdf_url).replace(/'/g, '&#39;')})">
                            &#128190; Download PDF
                           </button>`
                        : `<button class="btn-secondary btn-sm" disabled title="No direct PDF link available for this article">
                            &#128190; PDF Unavailable
                           </button>`
                    }
                    ${a.oa_url || a.pdf_url
                        ? `<a href="${escapeHtml(a.oa_url || a.pdf_url)}" target="_blank" class="btn-secondary btn-sm">
                            &#128279; Open in Browser
                           </a>`
                        : ''
                    }
                    <button class="btn-copy btn-sm" onclick="copyGeneratedText(this, ${JSON.stringify(a.title + ' | ' + authors + ' ' + yearStr + ' | ' + (a.doi || a.pdf_url)).replace(/'/g, '&#39;')})">
                        &#128203; Copy Citation
                    </button>
                </div>
            </div>
        `;
    }).join('');

    container.innerHTML = `<div class="oa-articles-list">${articlesHtml}</div>`;
}


async function downloadArticlePdf(btn, url) {
    if (!url) {
        showOaToast('No PDF link is available for this article. Try "Open in Browser" instead.', 'error');
        return;
    }

    // ---- Capture original button state for restore ----
    const originalHtml = btn ? btn.innerHTML : '';
    const originalDisabled = btn ? btn.disabled : false;

    // ---- Quick check: does the URL look like a direct PDF? ----
    // If not, skip the backend attempt (which would waste 15-20 seconds failing)
    // and open directly in the user's browser instead.
    const urlPath = url.toLowerCase().split('?')[0].split('#')[0];
    const looksLikePdf = urlPath.endsWith('.pdf')
        || urlPath.includes('/pdf/')
        || urlPath.endsWith('/pdf')
        || urlPath.includes('/download/')
        || urlPath.includes('/fulltext/')
        || urlPath.includes('/ftpdf/');

    // Known landing-page patterns that are NOT direct PDFs
    const isLandingPage = urlPath.includes('doi.org/')
        || urlPath.includes('/science/article')
        || urlPath.includes('/article/')
        || urlPath.includes('/abs/')
        || urlPath.includes('/abstract')
        || urlPath.includes('/landingpage');

    if (!looksLikePdf || isLandingPage) {
        // ---- Not a direct PDF link — open in browser right away ----
        showOaToast('This article does not have a direct PDF link. Opening the source page in a new tab — you can download the PDF from there.', 'info');
        window.open(url, '_blank', 'noopener,noreferrer');
        if (btn) {
            btn.innerHTML = '&#128279; Opened';
            setTimeout(() => {
                btn.innerHTML = originalHtml;
                btn.disabled = originalDisabled;
            }, 2500);
        }
        return;
    }

    // ---- Show loading state on button ----
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner"></span> Downloading...';
    }

    // ---- Strategy: Try backend download first (15s timeout), then auto-fallback to browser ----
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 15000);

    try {
        const resp = await apiFetch('/api/drafting/download-pdf', {
            method: 'POST',
            body: JSON.stringify({ url }),
            signal: controller.signal,
        });
        clearTimeout(timeoutId);

        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            throw new Error(err.detail || `Server returned HTTP ${resp.status}`);
        }

        // ---- Verify the blob is actually a PDF ----
        const blob = await resp.blob();

        if (blob.size < 1000) {
            throw new Error('File too small to be a valid PDF.');
        }

        if (blob.type && blob.type.includes('text/html')) {
            throw new Error('Source returned HTML instead of PDF.');
        }

        // ---- Trigger the download ----
        const downloadUrl = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = downloadUrl;

        const cd = resp.headers.get('Content-Disposition') || '';
        const match = cd.match(/filename\*?=["']?(?:UTF-8'')?([^"';\s]+)/i);
        a.download = match ? decodeURIComponent(match[1]) : 'THEeye_article.pdf';

        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(downloadUrl);

        // ---- Success feedback ----
        showOaToast('PDF downloaded successfully!', 'success');
        if (btn) {
            btn.innerHTML = '&#9989; Downloaded';
            setTimeout(() => {
                btn.innerHTML = originalHtml;
                btn.disabled = originalDisabled;
            }, 2500);
        }

    } catch (err) {
        clearTimeout(timeoutId);
        console.error('[downloadArticlePdf] Backend download failed:', err);

        // ---- AUTOMATIC FALLBACK: Open the PDF URL directly in the browser ----
        // The user's browser has a residential IP, cookies, and JS — it can access
        // PDFs that the cloud server cannot.
        showOaToast('Opening PDF in a new tab... If it doesn\'t load, use "Open in Browser" or try again.', 'info');

        try {
            // Try to open the PDF directly in a new tab
            const newTab = window.open(url, '_blank');

            // If popup was blocked, try creating a link and clicking it
            if (!newTab || newTab.closed || typeof newTab.closed === 'undefined') {
                const fallbackLink = document.createElement('a');
                fallbackLink.href = url;
                fallbackLink.target = '_blank';
                fallbackLink.rel = 'noopener noreferrer';
                document.body.appendChild(fallbackLink);
                fallbackLink.click();
                document.body.removeChild(fallbackLink);
            }
        } catch (openErr) {
            console.error('[downloadArticlePdf] Failed to open URL:', openErr);
        }

        // ---- Restore button with a "Retry" option ----
        if (btn) {
            btn.innerHTML = '&#128279; Open PDF';
            btn.disabled = false;
            btn.onclick = () => window.open(url, '_blank');
            setTimeout(() => {
                btn.innerHTML = originalHtml;
                btn.disabled = originalDisabled;
                // Restore original onclick after 10 seconds
                setTimeout(() => { btn.onclick = null; }, 100);
            }, 10000);
        }
    }
}


/**
 * Show a toast notification for Open-Access articles tab.
 * @param {string} message - The message to display
 * @param {string} type - 'success', 'error', or 'info'
 * @param {function} [actionCallback] - Optional callback for an action button
 */
function showOaToast(message, type, actionCallback) {
    // Remove any existing toast
    const existing = document.getElementById('oa-toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.id = 'oa-toast';
    toast.className = `oa-toast oa-toast-${type}`;

    const colors = {
        success: { bg: '#f0fff4', border: '#38a169', text: '#22543d', icon: '&#9989;' },
        error:   { bg: '#fff5f5', border: '#e53e3e', text: '#742a2a', icon: '&#9888;' },
        info:    { bg: '#ebf8ff', border: '#3182ce', text: '#2a4365', icon: '&#8505;' },
    };
    const c = colors[type] || colors.info;

    toast.style.cssText = `
        position: fixed; bottom: 24px; right: 24px; z-index: 10000;
        background: ${c.bg}; border: 1px solid ${c.border}; border-left: 4px solid ${c.border};
        color: ${c.text}; padding: 14px 18px; border-radius: 8px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.1); max-width: 420px;
        font-size: 0.875rem; line-height: 1.5; display: flex; gap: 10px;
        align-items: flex-start; animation: oaToastIn 0.3s ease;
    `;

    toast.innerHTML = `
        <span style="font-size: 1.1rem; flex-shrink: 0;">${c.icon}</span>
        <div style="flex: 1;">
            <div>${escapeHtml(message)}</div>
            ${actionCallback ? '<button class="oa-toast-action" style="margin-top: 8px; padding: 4px 12px; background: ' + c.border + '; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 0.8rem;">Open in Browser</button>' : ''}
        </div>
        <button class="oa-toast-close" style="background: none; border: none; cursor: pointer; font-size: 1.2rem; color: ${c.text}; opacity: 0.5; padding: 0; line-height: 1;">&times;</button>
    `;

    document.body.appendChild(toast);

    // Inject keyframe animation if not already present
    if (!document.getElementById('oa-toast-style')) {
        const style = document.createElement('style');
        style.id = 'oa-toast-style';
        style.textContent = '@keyframes oaToastIn { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }';
        document.head.appendChild(style);
    }

    // Wire up buttons
    toast.querySelector('.oa-toast-close').onclick = () => toast.remove();
    if (actionCallback) {
        toast.querySelector('.oa-toast-action').onclick = () => {
            toast.remove();
            actionCallback();
        };
    }

    // Auto-dismiss after 8 seconds (errors stay a bit longer)
    setTimeout(() => {
        if (toast.parentNode) {
            toast.style.transition = 'opacity 0.3s ease';
            toast.style.opacity = '0';
            setTimeout(() => toast.remove(), 300);
        }
    }, type === 'error' ? 10000 : 5000);
}


// ---- Cross-tab: search OA articles from a topic suggestion ----
function searchOATopics(topic) {
    // Switch to the Articles sub-tab
    document.querySelectorAll('.drafting-subtab').forEach(b => b.classList.remove('active'));
    document.querySelector('.drafting-subtab[data-subtab="Articles"]').classList.add('active');
    document.querySelectorAll('.drafting-subpanel').forEach(p => {
        p.classList.remove('active');
        p.style.display = 'none';
    });
    const panel = document.getElementById('draftingArticles');
    panel.classList.add('active');
    panel.style.display = 'block';

    // Fill the topic and trigger search
    document.getElementById('oaTopic').value = topic;
    document.getElementById('findArticlesBtn').click();
}


// ---- Expose global functions for inline onclick handlers ----
window.updateRoadmapFormats = updateRoadmapFormats;
window.downloadArticlePdf = downloadArticlePdf;
window.searchOATopics = searchOATopics;
window.downloadRoadmapMd = downloadRoadmapMd;
