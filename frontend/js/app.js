/**
 * VEXORA — Document Forensics & Contextual Intelligence
 * Frontend Application Logic (Phase 2: Core Pages & User Interface)
 */

document.addEventListener('DOMContentLoaded', () => {
  // Initialize all core subsystems
  initThemeManager();
  initSidebar();
  initNavigation();
  initLiveClock();
  initSearchFilter();
  initCaseModal();
  initCaseFilters();
  initDocLibraryFilters();
  initUploadSimulator();
  initToastSystem();
  initKeyboardShortcuts();
  initBackendSync();

  // Handle direct URL hash navigation (e.g. #cases, #upload, #forensics)
  handleInitialRoute();

  showToast('VEXORA Forensic Intelligence System Initialized.', 'info');
});

/**
 * 0. Theme Manager (High-Contrast Crisp Light Default + View Transitions API)
 */
function initThemeManager() {
  const themeToggleBtn = document.getElementById('themeToggleBtn');
  const themeIcon = document.getElementById('themeToggleIcon');
  const themeText = document.getElementById('themeToggleText');

  // Default to high-contrast crisp light theme
  const savedTheme = localStorage.getItem('vexora-theme') || 'light';
  applyTheme(savedTheme);

  if (themeToggleBtn) {
    themeToggleBtn.addEventListener('click', () => {
      // Trigger icon spring rotation animation
      themeToggleBtn.classList.add('animating');
      setTimeout(() => themeToggleBtn.classList.remove('animating'), 500);

      const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
      const newTheme = currentTheme === 'light' ? 'dark' : 'light';

      // Use native View Transitions API if supported for zero-glitch GPU cross-fade
      if (document.startViewTransition) {
        document.startViewTransition(() => {
          applyTheme(newTheme);
        });
      } else {
        // Fallback: apply temporary transition class
        document.documentElement.classList.add('theme-transitioning');
        applyTheme(newTheme);
        setTimeout(() => {
          document.documentElement.classList.remove('theme-transitioning');
        }, 400);
      }

      localStorage.setItem('vexora-theme', newTheme);
      showToast(`Switched to ${newTheme.toUpperCase()} mode`, 'info');
    });
  }

  function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    if (themeIcon && themeText) {
      if (theme === 'dark') {
        themeIcon.textContent = '🌙';
        themeText.textContent = 'Dark';
      } else {
        themeIcon.textContent = '☀️';
        themeText.textContent = 'Light';
      }
    }
  }
}

/**
 * 1. Sidebar Collapse and Mobile Toggle
 */
function initSidebar() {
  const sidebar = document.getElementById('vexoraSidebar');
  const sidebarToggle = document.getElementById('sidebarToggleBtn');
  const mobileToggle = document.getElementById('mobileNavToggle');

  if (sidebarToggle && sidebar) {
    sidebarToggle.addEventListener('click', () => {
      sidebar.classList.toggle('collapsed');
      const isCollapsed = sidebar.classList.contains('collapsed');
      sidebarToggle.setAttribute('aria-expanded', !isCollapsed);
    });
  }

  if (mobileToggle && sidebar) {
    mobileToggle.addEventListener('click', () => {
      sidebar.classList.toggle('mobile-open');
    });

    // Close sidebar when clicking outside on mobile
    document.addEventListener('click', (e) => {
      if (
        sidebar.classList.contains('mobile-open') &&
        !sidebar.contains(e.target) &&
        !mobileToggle.contains(e.target)
      ) {
        sidebar.classList.remove('mobile-open');
      }
    });
  }
}

/**
 * 2. Multi-View Navigation Router (Phase 2 Core Feature)
 */
function navigateToView(viewName) {
  const targetId = 'view-' + viewName;
  const targetSection = document.getElementById(targetId);
  const breadcrumbActive = document.getElementById('breadcrumbActive');
  const allSections = document.querySelectorAll('.view-section');
  const navItems = document.querySelectorAll('.nav-item');

  if (!targetSection) {
    console.warn(`View section "${targetId}" not found. Falling back to dashboard.`);
    return navigateToView('dashboard');
  }

  // Hide all view sections, activate target section
  allSections.forEach((sec) => sec.classList.remove('active'));
  targetSection.classList.add('active');

  // Update active sidebar nav link
  navItems.forEach((nav) => {
    if (nav.getAttribute('data-view') === viewName) {
      nav.classList.add('active');
    } else {
      nav.classList.remove('active');
    }
  });

  // Update breadcrumb text
  const title = targetSection.getAttribute('data-view-title') || viewName.toUpperCase();
  if (breadcrumbActive) {
    breadcrumbActive.textContent = title;
  }

  // Update browser URL hash without jump
  if (window.location.hash !== '#' + viewName) {
    history.pushState(null, '', '#' + viewName);
  }

  // Smooth scroll to top of content
  window.scrollTo({ top: 0, behavior: 'smooth' });

  // Close mobile sidebar if open
  const sidebar = document.getElementById('vexoraSidebar');
  if (sidebar) sidebar.classList.remove('mobile-open');

  // Phase 1: Repopulate all selectors & views on view switch
  if (typeof window.refreshAll === 'function') {
    window.refreshAll();
  }
}

// Make navigateToView globally accessible for inline onclick handlers
window.navigateToView = navigateToView;

function initNavigation() {
  const navItems = document.querySelectorAll('.nav-item');

  navItems.forEach((item) => {
    item.addEventListener('click', (e) => {
      e.preventDefault();
      const viewKey = item.getAttribute('data-view');
      if (viewKey) {
        navigateToView(viewKey);
      }
    });
  });

  // Listen to popstate / browser back/forward buttons
  window.addEventListener('popstate', handleInitialRoute);
}

function handleInitialRoute() {
  const hash = window.location.hash.replace('#', '').trim();
  if (hash) {
    navigateToView(hash);
  } else {
    navigateToView('dashboard');
  }
}

/**
 * 3. Case Management Filter Toolbar
 */
function initCaseFilters() {
  const filterPills = document.querySelectorAll('[data-filter]');
  const caseCards = document.querySelectorAll('#caseManagementGrid .case-card');

  filterPills.forEach((pill) => {
    pill.addEventListener('click', () => {
      filterPills.forEach((p) => p.classList.remove('active'));
      pill.classList.add('active');

      const filterVal = pill.getAttribute('data-filter');

      caseCards.forEach((card) => {
        const priority = card.getAttribute('data-priority');
        if (filterVal === 'all' || priority === filterVal) {
          card.style.display = '';
        } else {
          card.style.display = 'none';
        }
      });
    });
  });
}

/**
 * 4. Document Library Filter Toolbar
 */
function initDocLibraryFilters() {
  const docFilterPills = document.querySelectorAll('[data-doc-filter]');
  const docCards = document.querySelectorAll('#docLibraryGrid .doc-card');

  docFilterPills.forEach((pill) => {
    pill.addEventListener('click', () => {
      docFilterPills.forEach((p) => p.classList.remove('active'));
      pill.classList.add('active');

      const category = pill.getAttribute('data-doc-filter');

      docCards.forEach((card) => {
        const cardCat = card.getAttribute('data-category');
        if (category === 'all' || cardCat === category) {
          card.style.display = '';
        } else {
          card.style.display = 'none';
        }
      });
    });
  });
}

/**
 * 5. Drag & Drop File Upload & Forensic Ingestion Pipeline
 */
let stagedFilesList = [];

function initUploadSimulator() {
  const dropzone = document.getElementById('documentDropzone');
  const fileInput = document.getElementById('fileUploadInput');
  const queue = document.getElementById('stagedQueueContainer');
  const processBtn = document.getElementById('processQueueBtn');
  const targetCaseSelect = document.getElementById('targetCaseSelect');

  if (!dropzone || !fileInput) return;

  // Drag over styling
  ['dragenter', 'dragover'].forEach((eventName) => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      dropzone.classList.add('drag-active');
    });
  });

  ['dragleave', 'drop'].forEach((eventName) => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      dropzone.classList.remove('drag-active');
    });
  });

  // Handle dropped files
  dropzone.addEventListener('drop', (e) => {
    const files = e.dataTransfer.files;
    handleFiles(files);
  });

  // Handle file input selection
  fileInput.addEventListener('change', (e) => {
    const files = e.target.files;
    handleFiles(files);
  });

  function handleFiles(files) {
    if (!files || files.length === 0) return;

    const allowedExtensions = ['pdf', 'png', 'jpg', 'jpeg', 'tiff', 'bmp'];
    let addedCount = 0;

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const ext = file.name.split('.').pop().toLowerCase();

      if (!allowedExtensions.includes(ext)) {
        showToast(`Skipped '${file.name}': Unsupported format. Use PDF, PNG, or JPG.`, 'warning');
        continue;
      }

      if (file.size > 16 * 1024 * 1024) {
        showToast(`Skipped '${file.name}': Exceeds 16 MB limit.`, 'warning');
        continue;
      }

      stagedFilesList.push(file);
      addedCount++;

      const sizeMb = (file.size / (1024 * 1024)).toFixed(1) + ' MB';
      const icon = ext === 'pdf' ? '📄' : '🖼️';

      const item = document.createElement('div');
      item.className = 'staged-item';
      item.innerHTML = `
        <div class="staged-item-top">
          <span class="staged-name">${icon} ${escapeHtml(file.name)}</span>
          <span class="staged-size">${sizeMb}</span>
        </div>
        <div class="progress-bar-wrap">
          <div class="progress-bar-fill" style="width: 100%;"></div>
        </div>
        <div style="display:flex; justify-content:space-between; align-items:center; font-size:0.72rem; color:var(--text-muted);">
          <span>Format: ${ext.toUpperCase()} • Ready for Hash & Ingest</span>
          <span style="color:var(--status-verified); font-weight:700;">✓ Staged</span>
        </div>
      `;

      if (queue) {
        queue.prepend(item);
      }
    }

    if (addedCount > 0) {
      showToast(`${addedCount} document(s) staged for forensic ingestion.`, 'info');
    }
  }

  if (processBtn) {
    processBtn.addEventListener('click', async () => {
      if (stagedFilesList.length === 0) {
        showToast('No files staged for ingestion. Drag & drop or select documents first.', 'warning');
        return;
      }

      const caseId = targetCaseSelect ? targetCaseSelect.value : '';
      const apiBase = getApiBase();

      processBtn.disabled = true;
      const originalText = processBtn.textContent;
      processBtn.textContent = '⏳ Ingesting...';

      try {
        const formData = new FormData();
        if (caseId) {
          formData.append('case_id', caseId);
        }

        for (const file of stagedFilesList) {
          formData.append('files', file);
        }

        const res = await fetch(`${apiBase}/documents/upload`, {
          method: 'POST',
          body: formData
        });

        const resData = await res.json();

        if (res.ok && resData.success) {
          const uploadedDocs = resData.data || [];
          const count = resData.count || uploadedDocs.length;
          showToast(`Ingested ${count} document(s) successfully! Cryptographic SHA-256 generated.`, 'success');
          stagedFilesList = [];
          if (queue) queue.innerHTML = '';

          // Auto-select uploaded document and target case
          if (uploadedDocs.length > 0) {
            const lastDoc = uploadedDocs[uploadedDocs.length - 1];
            if (lastDoc.id) {
              localStorage.setItem('vexora_selected_doc_id', lastDoc.id);
            }
            if (lastDoc.case_id) {
              localStorage.setItem('vexora_selected_case_id', lastDoc.case_id);
            }
          } else if (resData.id) {
            localStorage.setItem('vexora_selected_doc_id', resData.id);
            if (resData.case_id) {
              localStorage.setItem('vexora_selected_case_id', resData.case_id);
            }
          }

          // Refresh live library and stats
          if (typeof window.refreshAll === 'function') {
            await window.refreshAll();
          } else {
            initBackendSync();
          }

          setTimeout(() => {
            navigateToView('library');
          }, 800);
        } else {
          showToast(`Ingestion error: ${resData.error || 'Server rejected files.'}`, 'danger');
        }
      } catch (err) {
        console.warn('[VEXORA Upload] Live upload failed:', err);
        showToast('Upload failed: cannot reach the VEXORA backend. Start it with python -m backend.app and open http://127.0.0.1:5000', 'danger');
        // Do not clear staged files or navigate away so the user can retry
      } finally {
        processBtn.disabled = false;
        processBtn.textContent = originalText;
      }
    });
  }
}

/**
 * 6. Header Live Clock
 */
function initLiveClock() {
  const clockElement = document.getElementById('headerClock');
  if (!clockElement) return;

  function updateClock() {
    const now = new Date();
    const options = {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: true,
    };
    clockElement.textContent = now.toLocaleTimeString([], options);
  }

  updateClock();
  setInterval(updateClock, 1000);
}

/**
 * 7. Live Table & Global Search Filter
 */
function initSearchFilter() {
  const searchInput = document.getElementById('globalSearchInput');
  const casesTable = document.getElementById('recentCasesTable');

  if (!searchInput) return;

  searchInput.addEventListener('input', (e) => {
    const query = e.target.value.toLowerCase().trim();

    // Filter table rows
    if (casesTable) {
      const rows = casesTable.querySelectorAll('tbody tr');
      rows.forEach((row) => {
        const text = row.textContent.toLowerCase();
        row.style.display = text.includes(query) ? '' : 'none';
      });
    }

    // Filter case cards
    const caseCards = document.querySelectorAll('#caseManagementGrid .case-card');
    caseCards.forEach((card) => {
      const text = card.textContent.toLowerCase();
      card.style.display = text.includes(query) ? '' : 'none';
    });
  });
}

/**
 * 8. Case Modal Logic (Create New Investigation Case)
 */
function initCaseModal() {
  const modal = document.getElementById('newCaseModal');
  const openButtons = document.querySelectorAll('[data-action="open-new-case"]');
  const closeBtn = document.getElementById('closeCaseModalBtn');
  const cancelBtn = document.getElementById('cancelCaseModalBtn');
  const caseForm = document.getElementById('newCaseForm');
  const tableBody = document.querySelector('#recentCasesTable tbody');
  const casesGrid = document.getElementById('caseManagementGrid');

  if (!modal) return;

  function openModal() {
    modal.classList.add('active');
    const firstInput = modal.querySelector('input');
    if (firstInput) firstInput.focus();
  }

  function closeModal() {
    modal.classList.remove('active');
    if (caseForm) caseForm.reset();
  }

  openButtons.forEach((btn) => btn.addEventListener('click', openModal));
  if (closeBtn) closeBtn.addEventListener('click', closeModal);
  if (cancelBtn) cancelBtn.addEventListener('click', closeModal);

  // Close when clicking modal backdrop
  modal.addEventListener('click', (e) => {
    if (e.target === modal) closeModal();
  });

  // Handle Form Submission
  if (caseForm) {
    caseForm.addEventListener('submit', async (e) => {
      e.preventDefault();

      const titleInput = document.getElementById('caseTitleInput');
      const priorityInput = document.getElementById('casePriorityInput');
      const investigatorInput = document.getElementById('caseInvestigatorInput');
      const notesInput = document.getElementById('caseNotesInput');

      const title = titleInput.value.trim();
      const priority = priorityInput.value;
      const investigator = investigatorInput.value.trim() || 'Misari Vadalia';
      const notes = notesInput ? notesInput.value.trim() : 'Preliminary inquiry';

      if (!title) {
        showToast('Please provide a valid case title.', 'warning');
        return;
      }

      let caseId = 'VX-' + Math.floor(2100 + Math.random() * 8000);
      let isLiveSaved = false;

      // Attempt to save to backend SQLite database
      try {
        const apiBase = getApiBase();
        const response = await fetch(`${apiBase}/cases`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            title: title,
            type: 'Financial Fraud',
            priority: priority,
            status: 'Active',
            investigator: investigator,
            description: notes
          })
        });

        if (response.ok) {
          const resData = await response.json();
          if (resData.success && resData.data) {
            caseId = resData.data.id;
            isLiveSaved = true;
            localStorage.setItem('vexora_selected_case_id', caseId);
          }
        } else {
          const errData = await response.json().catch(() => ({}));
          showToast(`Failed to create case: ${errData.error || 'Server error'}`, 'danger');
          return;
        }
      } catch (err) {
        console.warn('[VEXORA API] Backend not reachable for case creation, using optimistic local state.', err);
      }

      const priorityClass =
        priority === 'High' ? 'pill-high' : priority === 'Critical' ? 'pill-high' : priority === 'Medium' ? 'pill-medium' : 'pill-low';
      const priorityDataAttr = priority.toLowerCase();

      // 1. Insert row in Dashboard table if present
      if (tableBody) {
        const newRow = document.createElement('tr');
        newRow.innerHTML = `
          <td class="case-id-cell">${caseId}</td>
          <td>
            <span class="case-title-cell">${escapeHtml(title)}</span>
            <span class="case-subtitle">Lead: ${escapeHtml(investigator)} • Created just now</span>
          </td>
          <td>0 docs</td>
          <td><span class="pill-tag ${priorityClass}">${priority}</span></td>
          <td><span class="pill-tag pill-status">Active</span></td>
          <td>
            <div class="action-btn-group">
              <button class="table-action-btn" onclick="navigateToView('forensics')">Inspect</button>
              <button class="table-action-btn" onclick="navigateToView('upload')">Upload</button>
            </div>
          </td>
        `;
        tableBody.insertBefore(newRow, tableBody.firstChild);
      }

      // 2. Insert card in Case Management grid if present
      if (casesGrid) {
        const newCard = document.createElement('div');
        newCard.className = 'case-card';
        newCard.setAttribute('data-priority', priorityDataAttr);
        newCard.innerHTML = `
          <div class="case-card-header">
            <span class="case-card-id">${caseId}</span>
            <span class="pill-tag ${priorityClass}">${priority}</span>
          </div>
          <h3 class="case-card-title">${escapeHtml(title)}</h3>
          <p class="case-card-desc">${escapeHtml(notes || 'Newly created investigation case ready for artifact ingestion.')}</p>
          <div class="case-card-metrics">
            <div class="case-metric-item">
              <span class="case-metric-val">0</span>
              <span class="case-metric-lbl">Documents</span>
            </div>
            <div class="case-metric-item">
              <span class="case-metric-val" style="color:var(--status-verified);">0</span>
              <span class="case-metric-lbl">Anomalies</span>
            </div>
            <div class="case-metric-item">
              <span class="case-metric-val" style="color:var(--primary-accent);">Active</span>
              <span class="case-metric-lbl">Status</span>
            </div>
          </div>
          <div class="case-card-footer">
            <span class="case-author-note">Lead: ${escapeHtml(investigator)}</span>
            <div class="action-btn-group">
              <button class="table-action-btn" onclick="navigateToView('upload')">Upload</button>
              <button class="table-action-btn" onclick="navigateToView('dossier')">Dossier</button>
            </div>
          </div>
        `;
        casesGrid.prepend(newCard);
      }

      // 3. Update Active Cases Counter & Sidebar Badge
      const activeCasesCounter = document.getElementById('activeCasesCount');
      if (activeCasesCounter) {
        let count = parseInt(activeCasesCounter.textContent) || 0;
        activeCasesCounter.textContent = count + 1;
      }

      const sidebarCaseBadge = document.getElementById('sidebarCaseBadge');
      if (sidebarCaseBadge) {
        let badgeCount = parseInt(sidebarCaseBadge.textContent) || 0;
        sidebarCaseBadge.textContent = badgeCount + 1;
      }

      closeModal();
      if (isLiveSaved) {
        showToast(`Case ${caseId} created and saved in SQLite database!`, 'success');
      } else {
        showToast(`Case ${caseId} registered in active inventory!`, 'success');
      }
      if (typeof window.refreshAll === 'function') {
        await window.refreshAll();
      }
    });
  }
}

/**
 * 9. Toast Notification Manager
 */
function initToastSystem() {
  let container = document.getElementById('toastContainer');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toastContainer';
    container.className = 'toast-container';
    document.body.appendChild(container);
  }
}

function showToast(message, type = 'info') {
  const container = document.getElementById('toastContainer');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;

  const icon =
    type === 'success' ? '✓' : type === 'warning' ? '⚠' : type === 'danger' ? '✕' : 'ℹ';

  toast.innerHTML = `
    <span class="toast-icon">${icon}</span>
    <span class="toast-message">${escapeHtml(message)}</span>
  `;

  container.appendChild(toast);

  // Auto remove after 3.5 seconds
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

/**
 * 10. Keyboard Shortcuts (Ctrl+K, ESC, Ctrl+P)
 */
function initKeyboardShortcuts() {
  document.addEventListener('keydown', (e) => {
    // Focus search on Ctrl + K or Cmd + K
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
      e.preventDefault();
      const search = document.getElementById('globalSearchInput');
      if (search) search.focus();
    }

    // Close modal on Escape
    if (e.key === 'Escape') {
      const modal = document.getElementById('newCaseModal');
      if (modal && modal.classList.contains('active')) {
        modal.classList.remove('active');
      }
    }
  });
}

/**
 * Helper to prevent XSS in client-side text injection
 */
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

/**
 * 11. Backend API Synchronizer & Live Database Integration
 */
let __vexoraApiBase = null;
const __vexoraApiTried = [];

window.getApiBase = getApiBase;
function getApiBase() {
  if (__vexoraApiBase) return __vexoraApiBase;
  let override = window.VEXORA_API_BASE || null;
  try { override = override || localStorage.getItem('vexora_api_base'); } catch (e) {}
  if (override) return String(override).replace(/\/+$/, '');
  if (window.location.port === '5000') return '/api';
  if (window.location.protocol === 'file:' || window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    return 'http://127.0.0.1:5000/api';
  }
  return '/api';
}

async function resolveApiBase() {
  const cands = [];
  let override = window.VEXORA_API_BASE || null;
  try { override = override || localStorage.getItem('vexora_api_base'); } catch (e) {}
  if (override) cands.push(String(override).replace(/\/+$/, ''));
  if (window.location.protocol.startsWith('http')) cands.push('/api');
  ['http://127.0.0.1:5000/api', 'http://localhost:5000/api', 'http://127.0.0.1:5001/api', 'http://127.0.0.1:8000/api']
    .forEach(c => { if (!cands.includes(c)) cands.push(c); });
  __vexoraApiTried.length = 0;
  for (const base of cands) {
    __vexoraApiTried.push(base);
    try {
      const ctrl = new AbortController();
      const timer = setTimeout(() => ctrl.abort(), 2500);
      const res = await fetch(base + '/health', { signal: ctrl.signal });
      clearTimeout(timer);
      const ct = res.headers.get('content-type') || '';
      if (!res.ok || !ct.includes('json')) continue;
      const j = await res.json();
      if (j && j.status === 'healthy') { __vexoraApiBase = base; return base; }
    } catch (e) { /* try next candidate */ }
  }
  __vexoraApiBase = null;
  return null;
}
window.vexoraApiReady = resolveApiBase();

window.vexoraFetch = async function(path, opts) {
  await window.vexoraApiReady;
  if (!__vexoraApiBase) throw new Error('BACKEND_UNREACHABLE');
  let res;
  try { res = await fetch(__vexoraApiBase + path, opts); }
  catch (e) { throw new Error('BACKEND_UNREACHABLE'); }
  const ct = res.headers.get('content-type') || '';
  if (!ct.includes('json')) throw new Error('BACKEND_UNREACHABLE');
  return res;
};

function showBackendOfflineBanner() {
  if (document.getElementById('vexoraOfflineBanner')) return;
  const el = document.createElement('div');
  el.id = 'vexoraOfflineBanner';
  el.style.cssText = 'position:fixed;left:0;right:0;bottom:0;z-index:99999;background:#b91c1c;color:#fff;padding:10px 16px;font-size:0.85rem;display:flex;gap:12px;align-items:center;justify-content:center;flex-wrap:wrap;font-weight:600;box-shadow:0 -2px 10px rgba(0,0,0,0.5);';
  el.innerHTML = '<span>⚠️ Backend offline - showing no live data. (Tried: ' + __vexoraApiTried.join(', ') + '). Start server with <code>python -m backend.app</code> at <strong>http://127.0.0.1:5000</strong></span>' +
    '<button id="vexoraRetryBtn" style="background:#fff;color:#b91c1c;border:0;border-radius:6px;padding:4px 12px;font-weight:700;cursor:pointer;">Retry</button>';
  document.body.appendChild(el);
  document.getElementById('vexoraRetryBtn').onclick = async () => {
    el.remove();
    window.vexoraApiReady = resolveApiBase();
    initBackendSync();
  };
}

/**
 * Phase 1: Unified Data Refresh and Selector Synchronization
 * Fetches /api/stats, /api/cases, /api/documents and repopulates every selector independently.
 */
window.updateAiReasoningBadge = function(isAiOn, modelName) {
  const badge = document.getElementById('aiReasoningBadge');
  if (!badge) return;
  if (isAiOn) {
    badge.className = 'pill-tag pill-verified';
    badge.style.background = 'rgba(16, 185, 129, 0.15)';
    badge.style.color = '#10b981';
    badge.style.borderColor = 'rgba(16, 185, 129, 0.3)';
    let mLabel = modelName || 'Gemini 2.5 Flash';
    if (mLabel.toLowerCase().includes('gemini-2.5-flash')) mLabel = 'Gemini 2.5 Flash';
    else if (mLabel.toLowerCase().includes('gpt-4o-mini')) mLabel = 'GPT-4o Mini';
    badge.innerHTML = `🤖 AI reasoning: ON (${escapeHtml(mLabel)})`;
  } else {
    badge.className = 'pill-tag pill-status';
    badge.style.background = 'rgba(148, 163, 184, 0.15)';
    badge.style.color = 'var(--text-muted, #94a3b8)';
    badge.style.borderColor = 'rgba(148, 163, 184, 0.3)';
    badge.innerHTML = '🤖 AI reasoning: OFF (deterministic mode)';
  }
};

window.loadDemoCaseAction = async function() {
  if (!confirm('This will ERASE all cases, documents and findings and load the demo case. Continue?')) {
    return;
  }
  const btn = document.getElementById('loadDemoCaseBtn');
  const originalText = btn ? btn.innerHTML : '⚡ Reset & Load Demo';
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '⏳ Loading Demo...';
  }

  showToast('Resetting database and loading benchmark showcase case (Apex Global Due Diligence)...', 'info');
  try {
    const apiBase = getApiBase();
    const res = await fetch(`${apiBase}/demo/reset`, { method: 'POST' });
    const data = await res.json();
    if (res.ok && data.success) {
      showToast('Showcase case loaded successfully! 3 genuine docs, 1 tampered doc, and cross-document discrepancy matrix initialized.', 'success');
      if (typeof window.refreshAll === 'function') {
        await window.refreshAll();
      }
    } else {
      showToast(`Failed to load demo case: ${data.error || 'Server error'}`, 'danger');
    }
  } catch (err) {
    showToast('Failed to connect to backend to reset demo case.', 'danger');
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = originalText;
    }
  }
};

window.addDemoCaseAction = async function() {
  const btn = document.getElementById('addDemoCaseBtn');
  const originalText = btn ? btn.innerHTML : '📁 Add Demo Case';
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '⏳ Adding Demo...';
  }

  showToast('Adding showcase demo case (Apex Global Due Diligence) while keeping your existing data...', 'info');
  try {
    const apiBase = getApiBase();
    const res = await fetch(`${apiBase}/demo/add`, { method: 'POST' });
    const data = await res.json();
    if (res.ok && data.success) {
      showToast(data.message || 'Demo case added successfully! Existing cases and documents were preserved.', 'success');
      if (typeof window.refreshAll === 'function') {
        await window.refreshAll();
      }
    } else {
      showToast(`Failed to add demo case: ${data.error || 'Server error'}`, 'danger');
    }
  } catch (err) {
    showToast('Failed to connect to backend to add demo case.', 'danger');
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = originalText;
    }
  }
};

window.deleteDocumentRecord = async function(docId) {
  if (!confirm(`Are you sure you want to delete document ${docId}?`)) return;
  const apiBase = getApiBase();
  try {
    const res = await fetch(`${apiBase}/documents/${encodeURIComponent(docId)}`, { method: 'DELETE' });
    if (res.ok) {
      showToast(`Document ${docId} deleted successfully.`, 'info');
      if (typeof window.refreshAll === 'function') {
        await window.refreshAll();
      }
    } else {
      const err = await res.json().catch(() => ({}));
      showToast(`Failed to delete document: ${err.error || 'Server error'}`, 'danger');
    }
  } catch (err) {
    showToast('Failed to connect to backend to delete document.', 'danger');
  }
};

window.deleteCaseRecord = async function(caseId) {
  if (!confirm(`Are you sure you want to delete case ${caseId} and all associated documents?`)) return;
  const apiBase = getApiBase();
  try {
    const res = await fetch(`${apiBase}/cases/${encodeURIComponent(caseId)}`, { method: 'DELETE' });
    const data = await res.json().catch(() => ({}));
    if (res.ok && data.success) {
      showToast(`Case ${caseId} deleted successfully.`, 'info');
      if (typeof window.refreshAll === 'function') {
        await window.refreshAll();
      }
    } else {
      showToast(`Failed to delete case: ${data.error || 'Server error'}`, 'danger');
    }
  } catch (err) {
    showToast('Failed to connect to backend to delete case.', 'danger');
  }
};

window.refreshAll = async function refreshAll() {
  await window.vexoraApiReady;
  if (!__vexoraApiBase) {
    showBackendOfflineBanner();
    return;
  }
  const offline = document.getElementById('vexoraOfflineBanner');
  if (offline) offline.remove();

  const apiBase = getApiBase();

  // 1. Fetch live data endpoints
  let statsData = null;
  let casesList = [];
  let docsList = [];

  try {
    const statsRes = await fetch(`${apiBase}/stats`);
    if (statsRes.ok) {
      const statsJson = await statsRes.json();
      if (statsJson.success && statsJson.data) statsData = statsJson.data;
    }
  } catch (e) {
    console.warn('[refreshAll] /api/stats failed:', e);
  }

  try {
    const casesRes = await fetch(`${apiBase}/cases`);
    if (casesRes.ok) {
      const casesJson = await casesRes.json();
      if (casesJson.success && Array.isArray(casesJson.data)) casesList = casesJson.data;
    } else {
      const err = await casesRes.json().catch(() => ({}));
      showToast(`Failed to load cases: ${err.error || casesRes.statusText}`, 'danger');
    }
  } catch (e) {
    console.warn('[refreshAll] /api/cases failed:', e);
    showToast('Failed to connect to backend for cases list.', 'danger');
  }

  try {
    const docsRes = await fetch(`${apiBase}/documents`);
    if (docsRes.ok) {
      const docsJson = await docsRes.json();
      if (docsJson.success && Array.isArray(docsJson.data)) {
        docsList = docsJson.data;
        window.__vexoraDocs = docsList;
      }
    } else {
      const err = await docsRes.json().catch(() => ({}));
      showToast(`Failed to load documents: ${err.error || docsRes.statusText}`, 'danger');
    }
  } catch (e) {
    console.warn('[refreshAll] /api/documents failed:', e);
    showToast('Failed to connect to backend for documents list.', 'danger');
  }

  // 2. Update Stats Counter Cards & Sidebar Badges
  try {
    const activeCounter = document.getElementById('activeCasesCount');
    if (activeCounter) activeCounter.textContent = statsData?.active_cases !== undefined ? statsData.active_cases : casesList.length;

    const docsCounter = document.getElementById('totalDocsCount');
    if (docsCounter) docsCounter.textContent = statsData?.total_documents !== undefined ? statsData.total_documents : docsList.length;

    const flagsCounter = document.getElementById('flaggedAnomaliesCount');
    if (flagsCounter && statsData?.critical_findings !== undefined) flagsCounter.textContent = statsData.critical_findings;

    const evidenceCounter = document.getElementById('evidenceNodesCount');
    if (evidenceCounter && statsData?.total_findings !== undefined) evidenceCounter.textContent = statsData.total_findings;

    const persistStats = document.getElementById('localPersistenceStats');
    if (persistStats) {
      const cCount = casesList.length;
      const dCount = docsList.length;
      persistStats.textContent = `${cCount} cases • ${dCount} documents`;
    }

    const sidebarCaseBadge = document.getElementById('sidebarCaseBadge');
    if (sidebarCaseBadge) sidebarCaseBadge.textContent = casesList.length;

    const sidebarDocBadge = document.getElementById('sidebarDocBadge');
    if (sidebarDocBadge) sidebarDocBadge.textContent = docsList.length;

    if (statsData?.ai_reasoning_active) {
      window.updateAiReasoningBadge(true, statsData.ai_model || 'Gemini 2.5 Flash');
    } else {
      window.updateAiReasoningBadge(false);
    }
  } catch (e) {
    console.warn('[refreshAll] Stats and badges update failed:', e);
  }

  // 3. Upload Ingestion Guard: Disable if zero cases
  try {
    const browseBtn = document.getElementById('browseFilesBtn');
    const dropzone = document.getElementById('documentDropzone');
    let noCaseAlert = document.getElementById('noCasesUploadAlert');

    if (casesList.length === 0) {
      if (browseBtn) browseBtn.disabled = true;
      if (dropzone) {
        dropzone.style.opacity = '0.6';
        dropzone.style.pointerEvents = 'none';
      }
      if (!noCaseAlert && dropzone && dropzone.parentNode) {
        noCaseAlert = document.createElement('div');
        noCaseAlert.id = 'noCasesUploadAlert';
        noCaseAlert.style.cssText = 'margin-bottom:16px; padding:12px 16px; background:rgba(239,68,68,0.12); border:1px solid rgba(239,68,68,0.3); border-radius:6px; display:flex; align-items:center; justify-content:space-between; gap:12px;';
        noCaseAlert.innerHTML = `
          <span style="color:var(--status-danger); font-weight:600; font-size:0.9rem;">⚠️ Create a case first before uploading documents.</span>
          <button type="button" class="btn-primary" style="font-size:0.8rem; padding:6px 12px;" onclick="navigateToView('cases')">Go to Case Management</button>
        `;
        dropzone.parentNode.insertBefore(noCaseAlert, dropzone);
      }
    } else {
      if (browseBtn) browseBtn.disabled = false;
      if (dropzone) {
        dropzone.style.opacity = '1';
        dropzone.style.pointerEvents = 'auto';
      }
      if (noCaseAlert) noCaseAlert.remove();
    }
  } catch (e) {
    console.warn('[refreshAll] Upload guard failed:', e);
  }

  // 4. Populate targetCaseSelect (Upload Page Case Selector)
  try {
    const targetCaseSelect = document.getElementById('targetCaseSelect');
    if (targetCaseSelect) {
      const prevVal = targetCaseSelect.value;
      targetCaseSelect.innerHTML = '';
      if (casesList.length === 0) {
        const opt = document.createElement('option');
        opt.value = '';
        opt.disabled = true;
        opt.selected = true;
        opt.textContent = 'No cases yet - create one';
        targetCaseSelect.appendChild(opt);
      } else {
        casesList.forEach((c) => {
          const opt = document.createElement('option');
          opt.value = c.id;
          opt.textContent = `${c.id}: ${c.title}`;
          targetCaseSelect.appendChild(opt);
        });
        const savedCaseId = localStorage.getItem('vexora_selected_case_id');
        if (prevVal && [...targetCaseSelect.options].some((o) => o.value === prevVal)) {
          targetCaseSelect.value = prevVal;
        } else if (savedCaseId && [...targetCaseSelect.options].some((o) => o.value === savedCaseId)) {
          targetCaseSelect.value = savedCaseId;
        }
        targetCaseSelect.onchange = (e) => {
          if (e.target.value) localStorage.setItem('vexora_selected_case_id', e.target.value);
        };
      }
    }
  } catch (e) {
    console.warn('[refreshAll] targetCaseSelect update failed:', e);
  }

  // 5. Populate dossierCaseSelector (Dossier Report Case Selector)
  try {
    const dossierCaseSelect = document.getElementById('dossierCaseSelector');
    if (dossierCaseSelect) {
      const prevVal = dossierCaseSelect.value;
      dossierCaseSelect.innerHTML = '<option value="">Select Investigation Case...</option>';
      if (casesList.length === 0) {
        const opt = document.createElement('option');
        opt.value = '';
        opt.disabled = true;
        opt.selected = true;
        opt.textContent = 'No cases yet - create one';
        dossierCaseSelect.appendChild(opt);
      } else {
        casesList.forEach((c) => {
          const opt = document.createElement('option');
          opt.value = c.id;
          opt.textContent = `${c.id}: ${c.title}`;
          dossierCaseSelect.appendChild(opt);
        });
        const savedCaseId = localStorage.getItem('vexora_selected_case_id');
        if (prevVal && [...dossierCaseSelect.options].some((o) => o.value === prevVal)) {
          dossierCaseSelect.value = prevVal;
        } else if (savedCaseId && [...dossierCaseSelect.options].some((o) => o.value === savedCaseId)) {
          dossierCaseSelect.value = savedCaseId;
        } else if (casesList.length > 0 && !dossierCaseSelect.value) {
          dossierCaseSelect.selectedIndex = 1;
        }
        dossierCaseSelect.onchange = (e) => {
          if (e.target.value) {
            localStorage.setItem('vexora_selected_case_id', e.target.value);
            if (typeof window.loadCaseDossierPreview === 'function') {
              window.loadCaseDossierPreview(e.target.value);
            }
          }
        };
        if (dossierCaseSelect.value && typeof window.loadCaseDossierPreview === 'function') {
          window.loadCaseDossierPreview(dossierCaseSelect.value);
        }
      }
    }
  } catch (e) {
    console.warn('[refreshAll] dossierCaseSelector update failed:', e);
  }

  // 6. Populate relGraphCaseSelect (Cross-Document Relationship Graph Case Selector)
  try {
    const relGraphSelect = document.getElementById('relGraphCaseSelect');
    if (relGraphSelect) {
      const prevVal = relGraphSelect.value;
      relGraphSelect.innerHTML = '';
      if (casesList.length === 0) {
        const opt = document.createElement('option');
        opt.value = '';
        opt.disabled = true;
        opt.selected = true;
        opt.textContent = 'No cases yet - create one';
        relGraphSelect.appendChild(opt);
      } else {
        casesList.forEach((c) => {
          const opt = document.createElement('option');
          opt.value = c.id;
          opt.textContent = `${c.id} (${c.title})`;
          relGraphSelect.appendChild(opt);
        });
        const savedCaseId = localStorage.getItem('vexora_selected_case_id');
        if (prevVal && [...relGraphSelect.options].some((o) => o.value === prevVal)) {
          relGraphSelect.value = prevVal;
        } else if (savedCaseId && [...relGraphSelect.options].some((o) => o.value === savedCaseId)) {
          relGraphSelect.value = savedCaseId;
        }
        relGraphSelect.onchange = (e) => {
          if (e.target.value) {
            localStorage.setItem('vexora_selected_case_id', e.target.value);
            if (typeof window.v2LoadRelationshipGraph === 'function') {
              window.v2LoadRelationshipGraph(e.target.value);
            }
            if (typeof window.v2LoadCaseTimeline === 'function') {
              window.v2LoadCaseTimeline(e.target.value);
            }
          }
        };
        if (relGraphSelect.value) {
          if (typeof window.v2LoadRelationshipGraph === 'function') {
            window.v2LoadRelationshipGraph(relGraphSelect.value);
          }
          if (typeof window.v2LoadCaseTimeline === 'function') {
            window.v2LoadCaseTimeline(relGraphSelect.value);
          }
        }
      }
    }
  } catch (e) {
    console.warn('[refreshAll] relGraphCaseSelect update failed:', e);
  }

  // 7. Populate forensicDocSelector (Forensic Inspector Document Selector)
  try {
    const forensicDocSelector = document.getElementById('forensicDocSelector');
    if (forensicDocSelector) {
      const prevVal = forensicDocSelector.value;
      forensicDocSelector.innerHTML = '';
      if (docsList.length === 0) {
        const opt = document.createElement('option');
        opt.value = '';
        opt.disabled = true;
        opt.selected = true;
        opt.textContent = 'No documents yet - upload one';
        forensicDocSelector.appendChild(opt);
      } else {
        docsList.forEach((doc) => {
          const opt = document.createElement('option');
          opt.value = doc.id;
          opt.textContent = `${doc.filename} (${doc.id})`;
          forensicDocSelector.appendChild(opt);
        });
        const savedDocId = localStorage.getItem('vexora_selected_doc_id');
        if (prevVal && [...forensicDocSelector.options].some((o) => o.value === prevVal)) {
          forensicDocSelector.value = prevVal;
        } else if (savedDocId && [...forensicDocSelector.options].some((o) => o.value === savedDocId)) {
          forensicDocSelector.value = savedDocId;
        } else if (docsList.length > 0) {
          forensicDocSelector.selectedIndex = 0;
        }
        forensicDocSelector.onchange = (e) => {
          if (e.target.value) {
            localStorage.setItem('vexora_selected_doc_id', e.target.value);
            if (typeof window.loadDocumentFindings === 'function') {
              window.loadDocumentFindings(e.target.value);
            }
          }
        };
        if (forensicDocSelector.value && typeof window.loadDocumentFindings === 'function') {
          window.loadDocumentFindings(forensicDocSelector.value);
        }
      }
    }
  } catch (e) {
    console.warn('[refreshAll] forensicDocSelector update failed:', e);
  }

  // 8. Populate compareDocA and compareDocB (Cross-Document Comparison Selectors)
  try {
    const compareDocA = document.getElementById('compareDocA');
    const compareDocB = document.getElementById('compareDocB');
    if (compareDocA && compareDocB) {
      const prevA = compareDocA.value;
      const prevB = compareDocB.value;
      compareDocA.innerHTML = '';
      compareDocB.innerHTML = '';

      if (docsList.length === 0) {
        const optA = document.createElement('option');
        optA.value = '';
        optA.disabled = true;
        optA.selected = true;
        optA.textContent = 'No documents yet - upload one';
        compareDocA.appendChild(optA);

        const optB = document.createElement('option');
        optB.value = '';
        optB.disabled = true;
        optB.selected = true;
        optB.textContent = 'No documents yet - upload one';
        compareDocB.appendChild(optB);
      } else {
        docsList.forEach((doc) => {
          const optA = document.createElement('option');
          optA.value = doc.id;
          optA.textContent = `${doc.filename} (${doc.id})`;
          compareDocA.appendChild(optA);

          const optB = document.createElement('option');
          optB.value = doc.id;
          optB.textContent = `${doc.filename} (${doc.id})`;
          compareDocB.appendChild(optB);
        });

        const savedDocId = localStorage.getItem('vexora_selected_doc_id');
        if (prevA && [...compareDocA.options].some((o) => o.value === prevA)) {
          compareDocA.value = prevA;
        } else if (savedDocId && [...compareDocA.options].some((o) => o.value === savedDocId)) {
          compareDocA.value = savedDocId;
        }

        if (prevB && [...compareDocB.options].some((o) => o.value === prevB)) {
          compareDocB.value = prevB;
        } else if (docsList.length > 1) {
          const targetIdx = compareDocA.selectedIndex === 0 ? 1 : 0;
          compareDocB.selectedIndex = targetIdx;
        }
      }
    }
  } catch (e) {
    console.warn('[refreshAll] comparison selectors update failed:', e);
  }

  // 9. Repopulate Dashboard Recent Cases Table
  try {
    const tableBody = document.querySelector('#recentCasesTable tbody');
    if (tableBody) {
      tableBody.innerHTML = '';
      if (casesList.length === 0) {
        tableBody.innerHTML = `
          <tr>
            <td colspan="6" style="text-align:center; padding:24px; color:var(--text-muted);">
              No active cases found. Click <strong>+ Add Case</strong> to create an investigation case.
            </td>
          </tr>
        `;
      } else {
        casesList.forEach((c) => {
          const docCount = docsList.filter((d) => d.case_id === c.id).length;
          const priority = c.priority || 'Medium';
          const priorityClass =
            priority === 'High' || priority === 'Critical' ? 'pill-high' : priority === 'Medium' ? 'pill-medium' : 'pill-low';
          const status = c.status || 'Active';
          const investigator = c.investigator || 'Unassigned';

          const row = document.createElement('tr');
          row.innerHTML = `
            <td class="case-id-cell">${escapeHtml(c.id)}</td>
            <td>
              <span class="case-title-cell">${escapeHtml(c.title)}</span>
              <span class="case-subtitle">Lead: ${escapeHtml(investigator)}${c.description ? ` • ${escapeHtml(c.description)}` : ''}</span>
            </td>
            <td>${docCount} doc${docCount === 1 ? '' : 's'}</td>
            <td><span class="pill-tag ${priorityClass}">${escapeHtml(priority)}</span></td>
            <td><span class="pill-tag pill-status">${escapeHtml(status)}</span></td>
            <td>
              <div class="action-btn-group">
                <button class="table-action-btn" onclick="localStorage.setItem('vexora_selected_case_id','${escapeHtml(c.id)}'); navigateToView('upload')">Upload</button>
                <button class="table-action-btn" onclick="localStorage.setItem('vexora_selected_case_id','${escapeHtml(c.id)}'); navigateToView('dossier')">Dossier</button>
              </div>
            </td>
          `;
          tableBody.appendChild(row);
        });
      }
    }
  } catch (e) {
    console.warn('[refreshAll] recentCasesTable update failed:', e);
  }

  // 10. Repopulate Case Management Grid
  try {
    const casesGrid = document.getElementById('caseManagementGrid');
    if (casesGrid) {
      casesGrid.innerHTML = '';
      if (casesList.length === 0) {
        casesGrid.innerHTML = `
          <div style="grid-column: 1 / -1; padding: 40px; text-align: center; color: var(--text-muted);">
            <div style="font-size: 2rem; margin-bottom: 8px;">📁</div>
            <p>No investigation cases created yet. Click <strong>+ New Investigation Case</strong> above to create one.</p>
          </div>
        `;
      } else {
        casesList.forEach((c) => {
          const docCount = docsList.filter((d) => d.case_id === c.id).length;
          const priority = c.priority || 'Medium';
          const priorityClass =
            priority === 'High' || priority === 'Critical' ? 'pill-high' : priority === 'Medium' ? 'pill-medium' : 'pill-low';
          const priorityDataAttr = priority.toLowerCase();
          const status = c.status || 'Active';
          const investigator = c.investigator || 'Unassigned';

          const card = document.createElement('div');
          card.className = 'case-card';
          card.setAttribute('data-priority', priorityDataAttr);
          card.innerHTML = `
            <div class="case-card-header">
              <span class="case-card-id">${escapeHtml(c.id)}</span>
              <span class="pill-tag ${priorityClass}">${escapeHtml(priority)}</span>
            </div>
            <h3 class="case-card-title">${escapeHtml(c.title)}</h3>
            <p class="case-card-desc">${escapeHtml(c.description || 'Investigation case ready for artifact ingestion and cross-checking.')}</p>
            <div class="case-card-metrics">
              <div class="case-metric-item">
                <span class="case-metric-val">${docCount}</span>
                <span class="case-metric-lbl">Documents</span>
              </div>
              <div class="case-metric-item">
                <span class="case-metric-val" style="color:var(--status-verified);">${escapeHtml(c.type || 'General')}</span>
                <span class="case-metric-lbl">Type</span>
              </div>
              <div class="case-metric-item">
                <span class="case-metric-val" style="color:var(--primary-accent);">${escapeHtml(status)}</span>
                <span class="case-metric-lbl">Status</span>
              </div>
            </div>
            <div class="case-card-footer">
              <span class="case-author-note">Lead: ${escapeHtml(investigator)}</span>
              <div class="action-btn-group">
                <button class="table-action-btn" onclick="localStorage.setItem('vexora_selected_case_id','${escapeHtml(c.id)}'); navigateToView('upload')">Upload</button>
                <button class="table-action-btn" onclick="localStorage.setItem('vexora_selected_case_id','${escapeHtml(c.id)}'); navigateToView('dossier')">Dossier</button>
                <button class="table-action-btn" onclick="deleteCaseRecord('${escapeHtml(c.id)}')" title="Delete Case" style="color:var(--status-danger);">🗑️ Delete</button>
              </div>
            </div>
          `;
          casesGrid.appendChild(card);
        });
      }
    }
  } catch (e) {
    console.warn('[refreshAll] caseManagementGrid update failed:', e);
  }

  // 11. Populate Document Library Grid Cards
  try {
    const docLibraryGrid = document.getElementById('docLibraryGrid');
    if (docLibraryGrid) {
      docLibraryGrid.innerHTML = '';
      if (docsList.length === 0) {
        docLibraryGrid.innerHTML = `
          <div style="grid-column: 1 / -1; padding: 40px; text-align: center; color: var(--text-muted);">
            <div style="font-size: 2rem; margin-bottom: 8px;">📂</div>
            <p>No documents uploaded yet. Go to <a href="#upload" onclick="navigateToView('upload')">Upload</a> to stage and ingest files.</p>
          </div>
        `;
      } else {
        docsList.forEach((doc) => {
          const sizeMb = (doc.file_size / (1024 * 1024)).toFixed(1) + ' MB';
          const icon = doc.file_type === 'pdf' ? '📄' : '🖼️';
          const catLower = (doc.category || 'general').toLowerCase();
          const filterCat = catLower.includes('invoice') || catLower.includes('financial') || catLower.includes('bank')
            ? 'financial'
            : catLower.includes('id') || catLower.includes('identity') || catLower.includes('passport')
            ? 'identity'
            : catLower.includes('tax') || catLower.includes('return')
            ? 'tax'
            : catLower.includes('contract') || catLower.includes('agreement')
            ? 'legal'
            : 'all';

          const card = document.createElement('div');
          card.className = 'doc-card';
          card.setAttribute('data-category', filterCat);
          card.innerHTML = `
            <div class="doc-card-top">
              <div class="doc-badge-icon">${icon}</div>
              <span class="pill-tag pill-status">${escapeHtml(doc.category || 'Document')}</span>
            </div>
            <h3 class="doc-card-title" title="${escapeHtml(doc.filename)}">${escapeHtml(doc.filename)}</h3>
            <div class="doc-card-meta">
              <span>${escapeHtml((doc.file_type || 'PDF').toUpperCase())}</span> • <span>${sizeMb}</span> • <span style="color:var(--status-verified);">${doc.classification_confidence || 95}% Conf</span>
            </div>
            <div style="font-size:0.75rem; color:var(--text-muted); margin-top:4px;">
              Case: <strong>${escapeHtml(doc.case_id || 'General Vault')}</strong>
            </div>
            ${doc.extraction_mode === 'simulated_fallback' ? `
              <div style="margin-top:6px;">
                <span class="pill-tag pill-medium" style="font-size:0.7rem; background:rgba(245,158,11,0.15); color:#f59e0b; border:1px solid rgba(245,158,11,0.3);">
                  ⚠️ OCR unavailable - fallback mode
                </span>
              </div>` : ''}
            <div class="doc-card-footer">
              <button class="table-action-btn" onclick="triggerDocumentExtraction('${doc.id}')" title="Run OCR & Entity Extraction">⚡ Extract</button>
              <button class="table-action-btn" onclick="analyzeDocumentAndInspect('${doc.id}')" title="Run Forensic & Contextual Analysis">🔬 Analyze</button>
              <button class="table-action-btn" onclick="deleteDocumentRecord('${doc.id}')" title="Delete Document" style="color:var(--status-danger);">🗑️ Delete</button>
              <a href="${apiBase}/documents/${doc.id}/download" target="_blank" class="table-action-btn" style="text-decoration:none; display:inline-flex; align-items:center;">Download</a>
            </div>
          `;
          docLibraryGrid.appendChild(card);
        });
      }
    }
  } catch (e) {
    console.warn('[refreshAll] docLibraryGrid update failed:', e);
  }

  // 12. Auxiliary report, audit trail, and graph loading
  try {
    if (typeof loadGeneratedReportsList === 'function') loadGeneratedReportsList();
    if (typeof loadAuditTrailLogs === 'function') loadAuditTrailLogs();
    if (typeof loadEvidenceProvenanceGraph === 'function') loadEvidenceProvenanceGraph();
  } catch (e) {
    console.warn('[refreshAll] Auxiliary sync failed:', e);
  }

  // 13. Dispatch data ready event to eliminate race condition
  window.__vexoraDataReady = true;
  document.dispatchEvent(new CustomEvent('vexora:data-ready', { detail: { cases: casesList, docs: docsList } }));
};

async function initBackendSync() {
  await window.vexoraApiReady;
  if (!__vexoraApiBase) {
    showBackendOfflineBanner();
    return;
  }
  const offline = document.getElementById('vexoraOfflineBanner');
  if (offline) offline.remove();
  const apiBase = getApiBase();

  try {
    const healthRes = await fetch(`${apiBase}/health`, { method: 'GET' });
    if (!healthRes.ok) return;
    const healthData = await healthRes.json();

    if (healthData.status === 'healthy') {
      console.log('[VEXORA API] Connected to Flask backend & SQLite database.');
      const bannerPill = document.querySelector('.banner-pill');
      if (bannerPill) {
        bannerPill.textContent = '⚡ VEXORA Intelligence Engine • Phase 6 Active (Forensic & Contextual Analysis)';
      }
      await window.refreshAll();
    }
  } catch (e) {
    console.warn('[initBackendSync] Connection check failed:', e);
  }
}

/**
 * Trigger Forensic OCR & Information Extraction for a specific document
 */
window.triggerDocumentExtraction = async function(docId) {
  const apiBase = getApiBase();
  showToast('Initiating forensic text & entity extraction...', 'info');
  try {
    const res = await fetch(`${apiBase}/documents/${docId}/extract`, { method: 'POST' });
    const data = await res.json();
    if (res.ok && data.success) {
      const ext = data.data;
      const entities = ext.entities || {};
      const entityCount = (entities.dates?.length || 0) +
        (entities.monetary_values?.length || 0) +
        (entities.organizations?.length || 0) +
        (entities.persons?.length || 0) +
        (entities.identifiers?.length || 0) +
        (entities.emails?.length || 0);

      showToast(`Extraction Complete! Found ${entityCount} entities across ${ext.page_count} page(s) (${ext.total_words} words).`, 'success');
      console.log('[VEXORA Extraction Details]', ext);
      if (typeof window.refreshAll === 'function') {
        window.refreshAll();
      }
    } else {
      showToast(`Extraction failed: ${data.error || 'Server error'}`, 'danger');
    }
  } catch (err) {
    console.error('[VEXORA Extraction Error]', err);
    showToast('Failed to connect to extraction engine.', 'danger');
  }
};

/**
 * Phase 6: Trigger Forensic & Contextual Analysis, then navigate to Forensic Inspector
 */
window.analyzeDocumentAndInspect = async function(docId) {
  const apiBase = getApiBase();
  showToast('Executing visual typography & contextual anomaly evaluation...', 'info');
  try {
    const res = await fetch(`${apiBase}/documents/${docId}/analyze`, { method: 'POST' });
    const data = await res.json();
    if (res.ok && data.success) {
      showToast(`Analysis Complete! Risk Level: ${data.risk_level} (${data.findings_count} anomalies detected).`, data.risk_level.includes('Critical') ? 'danger' : 'warning');
      console.log('[VEXORA Forensic Report]', data);

      // Render findings in the Forensic Inspector view
      renderForensicFindings(data.findings);

      // Update selector in inspector if present
      const selector = document.getElementById('forensicDocSelector');
      if (selector) {
        selector.value = docId;
      }
      localStorage.setItem('vexora_selected_doc_id', docId);

      if (typeof window.refreshAll === 'function') {
        window.refreshAll();
      }

      // Switch view to Forensic Inspector
      setTimeout(() => {
        navigateToView('forensics');
      }, 500);
    } else {
      showToast(`Forensic analysis failed: ${data.error || 'Unknown error'}`, 'danger');
    }
  } catch (err) {
    console.error('[VEXORA Analysis Error]', err);
    showToast('Failed to connect to forensic intelligence service.', 'danger');
  }
};

/**
 * Phase 6 & Additive Forensic Polish: Fetch and load findings & evidence integrity for a selected document
 */
window.loadDocumentFindings = async function(docId) {
  window.__currentForensicDocId = docId;
  const apiBase = getApiBase();

  // Initialize and populate Evidence Integrity & Chain of Custody panel
  try {
    const doc = (window.__vexoraDocs || []).find(d => String(d.id) === String(docId));
    const hashDisplay = document.getElementById('evidenceHashDisplay');
    const badge = document.getElementById('integrityResultBadge');
    const eventCount = document.getElementById('custodyEventCount');
    const feed = document.getElementById('custodyTimelineFeed');
    const details = document.getElementById('custodyTimelineDetails');

    if (details) details.open = false;
    if (feed) feed.innerHTML = '<div style="color:var(--text-muted); font-size:0.75rem;">Click to expand chain of custody timeline...</div>';

    if (doc && doc.file_hash) {
      window.__currentEvidenceHash = doc.file_hash;
      if (hashDisplay) {
        const h = doc.file_hash;
        hashDisplay.textContent = h.length > 20 ? (h.substring(0, 14) + '...' + h.substring(h.length - 8)) : h;
        hashDisplay.title = h;
      }
    } else {
      window.__currentEvidenceHash = '';
      if (hashDisplay) {
        hashDisplay.textContent = 'Fetching hash...';
        hashDisplay.title = '';
      }
    }

    if (badge) {
      badge.innerHTML = '<span class="pill-tag" style="background:rgba(100,116,139,0.15); color:var(--text-muted); font-size:0.72rem;">Unverified</span>';
    }
    if (eventCount) {
      eventCount.textContent = '...';
    }

    // Always fetch custody count and stored hash to ensure fresh metadata
    fetch(`${apiBase}/documents/${encodeURIComponent(docId)}/custody`)
      .then(res => res.json())
      .then(custodyData => {
        if (custodyData && custodyData.success) {
          if (custodyData.stored_hash) {
            window.__currentEvidenceHash = custodyData.stored_hash;
            if (hashDisplay) {
              const h = custodyData.stored_hash;
              hashDisplay.textContent = h.length > 20 ? (h.substring(0, 14) + '...' + h.substring(h.length - 8)) : h;
              hashDisplay.title = h;
            }
          }
          if (eventCount) eventCount.textContent = custodyData.count !== undefined ? custodyData.count : (custodyData.events ? custodyData.events.length : 0);
        }
      })
      .catch(() => {});
  } catch (err) {
    console.warn('[Evidence Integrity Init Error]', err);
  }

  try {
    const res = await fetch(`${apiBase}/documents/${docId}/findings`);
    const data = await res.json();
    if (res.ok && data.success) {
      renderForensicFindings(data.data);
      showToast(`Loaded ${data.count} observation(s) for document ${docId}.`, 'info');
    }
  } catch (err) {
    console.warn('[VEXORA Load Findings Error]', err);
  }

  // Trigger dynamic live page viewer overlay & extraction mode badge
  if (typeof window.v2RenderDynamicForensicViewer === 'function') {
    window.v2RenderDynamicForensicViewer(docId);
  }
};

/**
 * Verify evidence integrity by recomputing SHA-256 on the backend
 */
window.verifyCurrentDocIntegrity = async function() {
  const docId = window.__currentForensicDocId || document.getElementById('forensicDocSelector')?.value;
  if (!docId) {
    showToast('Please select a document first.', 'warning');
    return;
  }
  const apiBase = getApiBase();
  const btn = document.getElementById('verifyIntegrityBtn');
  const badge = document.getElementById('integrityResultBadge');
  const origBtnText = btn ? btn.innerHTML : '🔍 Verify Integrity';
  if (btn) btn.innerHTML = '⏳ Verifying...';

  try {
    const res = await fetch(`${apiBase}/documents/${encodeURIComponent(docId)}/integrity`);
    const data = await res.json();
    if (res.ok && data.success) {
      if (data.match) {
        if (badge) {
          badge.innerHTML = '<span class="pill-tag" style="background:rgba(16,185,129,0.15); color:#10b981; font-weight:700; font-size:0.72rem; border:1px solid rgba(16,185,129,0.3);">✓ Hash matches</span>';
        }
        showToast('Evidence integrity verified: SHA-256 matches ingest hash.', 'success');
      } else {
        if (badge) {
          badge.innerHTML = '<span class="pill-tag" style="background:rgba(239,68,68,0.15); color:#ef4444; font-weight:700; font-size:0.72rem; border:1px solid rgba(239,68,68,0.3);">✕ Hash mismatch - file changed since ingest</span>';
        }
        showToast('Integrity Alert: File hash mismatch or modified on disk!', 'danger');
      }
      // If custody details are open, refresh timeline to show the new integrity check event
      const details = document.getElementById('custodyTimelineDetails');
      if (details && details.open) {
        window.loadCurrentDocCustody();
      }
    } else {
      if (badge) {
        badge.innerHTML = `<span class="pill-tag" style="background:rgba(239,68,68,0.15); color:#ef4444; font-weight:700; font-size:0.72rem;">✕ ${escapeHtml(data.error || 'Verification Failed')}</span>`;
      }
      showToast(data.error || 'Failed to verify evidence integrity.', 'danger');
    }
  } catch (err) {
    console.error('[Verify Integrity Error]', err);
    showToast('Failed to connect to integrity verification service.', 'danger');
  } finally {
    if (btn) btn.innerHTML = origBtnText;
  }
};

/**
 * Copy full SHA-256 hash to clipboard
 */
window.copyEvidenceHash = function() {
  const hash = window.__currentEvidenceHash;
  if (!hash) {
    showToast('No hash available to copy. Select an ingested document.', 'warning');
    return;
  }
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(hash).then(() => {
      showToast('Full SHA-256 copied to clipboard.', 'info');
    }).catch(() => {
      prompt('Evidence SHA-256 Hash:', hash);
    });
  } else {
    prompt('Evidence SHA-256 Hash:', hash);
  }
};

/**
 * Fetch and render chronological Chain of Custody events for current document
 */
window.loadCurrentDocCustody = async function() {
  const docId = window.__currentForensicDocId || document.getElementById('forensicDocSelector')?.value;
  if (!docId) return;
  const apiBase = getApiBase();
  const eventCount = document.getElementById('custodyEventCount');
  const feed = document.getElementById('custodyTimelineFeed');
  if (feed) feed.innerHTML = '<div style="color:var(--text-muted); font-size:0.75rem;">Loading custody audit trail...</div>';

  try {
    const res = await fetch(`${apiBase}/documents/${encodeURIComponent(docId)}/custody`);
    const data = await res.json();
    if (res.ok && data.success) {
      if (eventCount) eventCount.textContent = data.count !== undefined ? data.count : (data.events ? data.events.length : 0);
      if (!feed) return;
      if (!data.events || data.events.length === 0) {
        feed.innerHTML = '<div style="color:var(--text-muted); font-size:0.75rem;">No audit events recorded for this document yet.</div>';
        return;
      }
      feed.innerHTML = data.events.map((ev) => {
        const timeStr = ev.timestamp ? ev.timestamp.replace('T', ' ').substring(0, 19) : 'Unknown';
        const actor = ev.actor || 'system';
        const action = ev.action || 'EVENT';
        return `
          <div style="display:flex; align-items:flex-start; gap:8px; padding:6px 0; border-bottom:1px solid rgba(255,255,255,0.04); font-size:0.75rem;">
            <div style="font-family:var(--font-mono); color:var(--text-muted); min-width:115px; font-size:0.7rem;">${timeStr}</div>
            <div style="display:flex; flex-direction:column; gap:2px; flex:1;">
              <div style="display:flex; align-items:center; gap:6px;">
                <span class="pill-tag" style="background:rgba(59,130,246,0.15); color:var(--primary-accent); font-size:0.68rem; padding:1px 5px; font-weight:700;">${escapeHtml(action)}</span>
                <span style="color:var(--text-muted); font-size:0.7rem;">by <strong>${escapeHtml(actor)}</strong></span>
              </div>
              <div style="color:var(--text-secondary); word-break:break-word; font-size:0.72rem;">${escapeHtml(ev.details || '')}</div>
            </div>
          </div>
        `;
      }).join('');
    } else {
      if (feed) feed.innerHTML = '<div style="color:var(--status-critical); font-size:0.75rem;">Failed to load chain of custody.</div>';
    }
  } catch (err) {
    console.error('[Custody Trail Error]', err);
    if (feed) feed.innerHTML = '<div style="color:var(--status-critical); font-size:0.75rem;">Connection error loading custody trail.</div>';
  }
};

/**
 * Phase 6: Render findings dynamically into #forensicFindingsFeed
 */
function renderForensicFindings(findings) {
  const feed = document.getElementById('forensicFindingsFeed');
  if (!feed) return;

  if (!findings || findings.length === 0) {
    feed.innerHTML = `
      <div class="finding-detail-card" style="border-left-color:var(--status-verified);">
        <div class="finding-card-head">
          <span class="finding-title">✓ Verified Document Profile</span>
          <span class="finding-loc">All Evaluated Pages</span>
        </div>
        <p class="finding-reason">
          No typographic inconsistencies, conflicting identifiers, or chronological flow anomalies detected across evaluated forensic rules.
        </p>
        <div class="finding-recommendation" style="color:var(--status-verified); background:var(--status-verified-dim); border-color:var(--status-verified-border);">
          Document verified against active forensic heuristics.
        </div>
      </div>
    `;
    return;
  }

  feed.innerHTML = '';
  findings.forEach((f) => {
    const sev = (f.severity || 'Medium').toLowerCase();
    const cardClass = sev === 'critical' ? 'critical' : sev === 'high' ? 'critical' : '';
    const locText = f.coordinates
      ? `Page ${f.page_number || 1} • Box [${escapeHtml(String(f.coordinates))}]`
      : `Page ${f.page_number || 1} • Contextual Check`;

    const evClass = f.evidence_class || 'Observation';
    const evClassPill = evClass === 'Potential Manipulation' ? 'pill-high' : evClass === 'Inconsistency' ? 'pill-medium' : 'pill-low';

    const card = document.createElement('div');
    card.className = `finding-detail-card ${cardClass}`;
    card.style.cursor = 'pointer';
    card.title = 'Click to inspect visual evidence & bounding box';
    card.onclick = (e) => {
      if (e.target.tagName === 'BUTTON' || e.target.closest('button')) return;
      if (typeof window.v2OpenEvidenceModal === 'function') {
        window.v2OpenEvidenceModal(f);
      }
    };
    card.innerHTML = `
      <div class="finding-card-head">
        <span class="finding-title">[${escapeHtml(f.rule_id || 'RULE')}] ${escapeHtml(f.title)}</span>
        <div>
          <span class="pill-tag ${evClassPill}" style="margin-right:6px; font-size:0.7rem;">${escapeHtml(evClass)}</span>
          ${f.confidence !== undefined && f.confidence !== null ? `<span style="font-size:0.75rem; color:var(--text-muted); margin-right:6px;">Rule Weight: <strong>${escapeHtml(String(f.confidence))}</strong></span>` : ''}
          <span class="finding-loc">${escapeHtml(locText)}</span>
        </div>
      </div>
      <p class="finding-reason">${escapeHtml(f.description)}</p>
      ${f.evidence ? `<div class="finding-recommendation">🔍 Evidence: <strong>${escapeHtml(f.evidence)}</strong></div>` : ''}
    `;
    feed.appendChild(card);

    // V2 Phase A Hook: Attach Visual Evidence Overlay trigger
    try {
      if (window.v2RenderFindingEvidenceButton) {
        window.v2RenderFindingEvidenceButton(card, f);
      }
    } catch (v2Err) {
      console.warn('[V2 Phase A Hook Error]', v2Err);
    }
  });
}

/**
 * ============================================================================
 * Phase 7: Cross-Document Comparison & Discrepancy Matrix
 * ============================================================================
 */
window.triggerAiCaseCrosscheck = async function() {
  const btn = document.getElementById('runAiCrosscheckBtn');
  const originalText = btn ? btn.innerHTML : '🤖 AI Cross-Check';
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '⏳ AI Checking...';
  }

  const relSelect = document.getElementById('relGraphCaseSelect');
  const targetSelect = document.getElementById('targetCaseSelect');
  const dossierSelect = document.getElementById('dossierCaseSelector');
  const caseId = (relSelect && relSelect.value) || (targetSelect && targetSelect.value) || (dossierSelect && dossierSelect.value);

  if (!caseId) {
    showToast('Please select or create an investigation case first.', 'warning');
    if (btn) { btn.disabled = false; btn.innerHTML = originalText; }
    return;
  }

  showToast(`Running AI contextual cross-check on Case ${caseId}...`, 'info');
  try {
    const apiBase = getApiBase();
    const res = await fetch(`${apiBase}/cases/${encodeURIComponent(caseId)}/ai-crosscheck`, { method: 'POST' });
    const data = await res.json();
    if (res.ok && data.success) {
      const count = data.count || (data.findings ? data.findings.length : 0);
      if (count > 0) {
        showToast(`AI cross-check flagged ${count} contextual inconsistency item(s) (AI-assessed, requires human review).`, 'warning');
        if (typeof window.v2LoadRelationshipGraph === 'function') {
          window.v2LoadRelationshipGraph(caseId);
        }
      } else {
        showToast('AI cross-check complete: No contextual inconsistencies found across case documents.', 'success');
      }
    } else {
      showToast(data.message || data.error || 'AI reasoning unavailable: set VEXORA_LLM_API_KEY in .env. Falling back to deterministic rules.', 'warning');
    }
  } catch (err) {
    showToast('AI cross-check unavailable. Falling back to deterministic rules.', 'warning');
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = originalText;
    }
  }
};

window.triggerCrossDocumentComparison = async function() {
  const compBtn = document.getElementById('runComparisonBtn');
  const originalBtnText = compBtn ? compBtn.innerHTML : 'Run Cross-Check';
  if (compBtn) {
    compBtn.disabled = true;
    compBtn.innerHTML = '⏳ Comparing...';
  }

  const docASelect = document.getElementById('compareDocA');
  const docBSelect = document.getElementById('compareDocB');
  const docAId = docASelect ? docASelect.value : null;
  const docBId = docBSelect ? docBSelect.value : null;

  if (!docAId || !docBId) {
    showToast('Please select two documents to compare.', 'warning');
    if (compBtn) { compBtn.disabled = false; compBtn.innerHTML = originalBtnText; }
    return;
  }
  if (docAId === docBId) {
    showToast('Please select two distinct documents for cross-comparison.', 'warning');
    if (compBtn) { compBtn.disabled = false; compBtn.innerHTML = originalBtnText; }
    return;
  }

  const apiBase = getApiBase();
  showToast('Executing cross-document entity alignment & discrepancy analysis...', 'info');

  try {
    const res = await fetch(`${apiBase}/documents/compare`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ doc_a_id: docAId, doc_b_id: docBId })
    });
    const data = await res.json();
    if (res.ok && data.success) {
      const compResult = data.data || data;
      renderComparisonMatrix(compResult);
      const discCount = compResult.discrepancies_count !== undefined
        ? compResult.discrepancies_count
        : ((compResult.conflicts_count || 0) + (compResult.mismatches_count || 0));

      if (discCount > 0) {
        showToast(`Comparison complete: Flagged ${discCount} cross-document discrepanc${discCount === 1 ? 'y' : 'ies'}.`, 'warning');
      } else {
        showToast('Comparison complete: Full factual alignment verified across both documents.', 'success');
      }
    } else {
      showToast(`Comparison failed: ${data.error || 'Server error'}`, 'danger');
    }
  } catch (err) {
    console.error('[VEXORA Comparison Error]', err);
    showToast('Failed to connect to comparison engine.', 'danger');
  } finally {
    if (compBtn) {
      compBtn.disabled = false;
      compBtn.innerHTML = originalBtnText;
    }
  }
};

/**
 * Phase 7: Render dynamic comparison findings into #comparisonMatrixBody
 */
function renderComparisonMatrix(result) {
  const matrixBody = document.getElementById('comparisonMatrixBody');
  if (!matrixBody) return;

  matrixBody.innerHTML = '';
  const docA = result.doc_a || result.document_a || {};
  const docB = result.doc_b || result.document_b || {};
  const items = result.alignment_matrix || result.discrepancies || [];

  if (items.length === 0) {
    const row = document.createElement('tr');
    row.innerHTML = `
      <td style="font-weight:700;">Overall Alignment</td>
      <td>${escapeHtml(docA.filename || 'Doc A')}</td>
      <td>${escapeHtml(docB.filename || 'Doc B')}</td>
      <td><span class="pill-tag pill-low">✓ Exact Match</span></td>
      <td>Identical identifiers, aligned monetary figures, and consistent counterparty entities verified across both records.</td>
    `;
    matrixBody.appendChild(row);
    return;
  }

  items.forEach((m) => {
    const row = document.createElement('tr');
    const attr = m.attribute || m.field || m.type || 'Field';
    const valA = m.val_a ?? m.doc_a_value ?? '—';
    const valB = m.val_b ?? m.doc_b_value ?? '—';
    const status = m.status || '';
    const sev = String(m.severity || '').toLowerCase();

    const isConflict = status === 'Conflict' || status === 'Duplicate' || sev === 'critical' || sev === 'high';
    const isMismatch = status === 'Mismatch' || sev === 'medium' || sev === 'warning';

    const bgStyle = isConflict ? 'background:var(--status-danger-dim);' : isMismatch ? 'background:var(--status-anomaly-dim);' : '';
    const pillClass = isConflict ? 'pill-high' : isMismatch ? 'pill-medium' : 'pill-low';
    const verdict = m.verdict || (isConflict ? '⚠️ CONFLICT' : isMismatch ? '⚠️ VARIANCE' : '✓ Verified');
    const explanation = m.explanation || m.message || '';

    if (bgStyle) row.style = bgStyle;
    row.innerHTML = `
      <td style="font-weight:700; color:${isConflict ? 'var(--status-danger)' : isMismatch ? 'var(--status-anomaly)' : 'inherit'};">
        ${escapeHtml(attr)}
      </td>
      <td style="font-family:var(--font-mono); font-size:0.85rem;">
        ${escapeHtml(String(valA))}
      </td>
      <td style="font-family:var(--font-mono); font-size:0.85rem;">
        ${escapeHtml(String(valB))}
      </td>
      <td><span class="pill-tag ${pillClass}">${escapeHtml(verdict)}</span></td>
      <td>
        <strong>${escapeHtml(explanation)}</strong>
        ${m.variance ? `<br><small style="color:var(--text-muted);">Variance: ${escapeHtml(String(m.variance))}</small>` : ''}
      </td>
    `;
    matrixBody.appendChild(row);
  });
}

/**
 * ============================================================================
 * Phase 7: Evidence Provenance Graph Sync
 * ============================================================================
 */
window.loadEvidenceProvenanceGraph = async function() {
  const container = document.getElementById('evidenceProvenanceContainer');
  if (!container) return;

  const apiBase = getApiBase();
  try {
    const res = await fetch(`${apiBase}/evidence-graph`);
    if (!res.ok) return;
    const data = await res.json();
    const nodes = data.data || data.nodes || [];
    if (nodes && nodes.length > 0) {
      container.innerHTML = '';
      nodes.forEach((n) => {
        const card = document.createElement('div');
        card.className = 'case-card';
        const sev = (n.severity || 'Medium').toLowerCase();
        const pillClass = sev === 'critical' || sev === 'high' ? 'pill-high' : sev === 'medium' ? 'pill-medium' : 'pill-low';
        const coordText = n.coordinates ? ` • BBox: [${n.coordinates}]` : '';

        card.innerHTML = `
          <span class="case-card-id">${escapeHtml(n.id)}</span>
          <h4 style="font-size:0.95rem; font-weight:700; color:var(--text-primary); margin:6px 0;">
            ${escapeHtml(n.title)}
          </h4>
          <p style="font-size:0.8rem; color:var(--text-secondary); margin-bottom:8px;">
            Source: <code>${escapeHtml(n.document_name || n.document_id || 'Unknown')}</code> • Page ${n.page_number || 1}${escapeHtml(coordText)}
          </p>
          <p style="font-size:0.75rem; color:var(--text-muted); margin-bottom:8px;">
            ${escapeHtml(n.evidence || '')}
          </p>
          <div class="pill-tag ${pillClass}">
            ${n.case_id ? `Linked to Case ${escapeHtml(n.case_id)}` : 'General Repository Finding'}
          </div>
        `;
        container.appendChild(card);
      });
    }
  } catch (err) {
    console.warn('[VEXORA Evidence Graph Sync Failed]', err);
  }
};

/**
 * ============================================================================
 * Phase 8: Investigation Dossier & Report Generation
 * ============================================================================
 */

/**
 * Loads dynamic dossier preview for a selected case
 */
window.loadCaseDossierPreview = async function(caseId) {
  if (!caseId) return;

  const apiBase = getApiBase();
  try {
    const res = await fetch(`${apiBase}/cases/${caseId}/dossier`);
    if (!res.ok) {
      showToast(`Could not load dossier data for case ${caseId}.`, 'warning');
      return;
    }

    const data = await res.json();
    if (!data.success || !data.data) return;

    const d = data.data;
    const c = d.case || {};
    const sum = d.executive_summary || {};

    // Header & Meta
    const refEl = document.getElementById('dossierCaseRef');
    const titleEl = document.getElementById('dossierCaseTitle');
    const metaEl = document.getElementById('dossierCaseMeta');
    const badgeEl = document.getElementById('dossierRiskBadge');
    const narrativeEl = document.getElementById('dossierNarrative');
    const verifyEl = document.getElementById('dossierVerificationCode');
    const signoffUser = document.getElementById('dossierSignoffUser');

    if (refEl) refEl.textContent = `VEXORA OFFICIAL FORENSIC DOSSIER • CASE ${c.id}`;
    if (titleEl) titleEl.textContent = `${c.title} Audit Report`;
    if (metaEl) metaEl.textContent = `Lead Investigator: ${c.investigator || 'Misari Vadalia'} • Priority: ${c.priority} • Status: ${c.status}`;
    if (signoffUser) signoffUser.textContent = c.investigator || 'Misari Vadalia';
    if (verifyEl) verifyEl.textContent = sum.dossier_verification_code || `VX-${c.id}-SEC-OK`;

    if (badgeEl) {
      badgeEl.textContent = sum.risk_level || 'Assessment Pending';
      badgeEl.className = 'pill-tag ' + (sum.risk_score >= 50 ? 'pill-high' : sum.risk_score >= 20 ? 'pill-medium' : 'pill-low');
    }

    if (narrativeEl) {
      narrativeEl.textContent = sum.narrative || 'No summary narrative available.';
    }

    // Evidence Inventory
    const invEl = document.getElementById('dossierEvidenceInventory');
    if (invEl) {
      invEl.innerHTML = '';
      if (!d.documents || d.documents.length === 0) {
        invEl.innerHTML = '<li><em>No documents uploaded to this case yet.</em></li>';
      } else {
        d.documents.forEach((doc) => {
          const li = document.createElement('li');
          li.innerHTML = `<code>${escapeHtml(doc.filename)}</code> (${escapeHtml(doc.file_type)}) — SHA-256: <code>${escapeHtml(doc.file_hash.substring(0, 16))}...</code> • <strong>${escapeHtml(doc.file_size_formatted)}</strong> • Status: <span style="font-weight:700;">${escapeHtml(doc.status)}</span>`;
          invEl.appendChild(li);
        });
      }
    }

    // Findings List
    const findingsEl = document.getElementById('dossierFindingsList');
    if (findingsEl) {
      findingsEl.innerHTML = '';
      if (!d.findings || d.findings.length === 0) {
        findingsEl.innerHTML = `
          <div class="finding-detail-card" style="border-left-color:var(--status-verified);">
            <strong>✓ Verified Baseline — No Anomalies Documented</strong>
            <p style="font-size:0.8rem; margin:0; color:var(--text-secondary);">No typographic overwrites, baseline breaks, or chronology discrepancies recorded for this case.</p>
          </div>
        `;
      } else {
        d.findings.forEach((f) => {
          const sev = (f.severity || 'Medium').toLowerCase();
          const card = document.createElement('div');
          card.className = `finding-detail-card ${sev === 'critical' || sev === 'high' ? 'critical' : ''}`;
          card.style.cursor = 'pointer';
          card.title = 'Click to inspect visual evidence & bounding box';
          card.onclick = (e) => {
            if (e.target.tagName === 'BUTTON' || e.target.closest('button')) return;
            if (typeof window.v2OpenEvidenceModal === 'function') {
              window.v2OpenEvidenceModal(f);
            }
          };
          const coordText = f.coordinates ? ` • Box [${escapeHtml(f.coordinates)}]` : '';

          const evClass = f.evidence_class || 'Observation';
          const evClassPill = evClass === 'Potential Manipulation' ? 'pill-high' : evClass === 'Inconsistency' ? 'pill-medium' : 'pill-low';

          card.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:center;">
              <strong>[${escapeHtml(f.rule_id || 'RULE')}] ${escapeHtml(f.title)}</strong>
              <div>
                <span class="pill-tag ${evClassPill}" style="margin-right:6px; font-size:0.7rem;">${escapeHtml(evClass)}</span>
                <span style="font-size:0.75rem; color:var(--text-muted); font-weight:600;">(${escapeHtml(f.severity)})</span>
              </div>
            </div>
            <p style="font-size:0.8rem; margin:3px 0 0 0; color:var(--text-secondary);">
              Page ${f.page_number || 1}${coordText}: ${escapeHtml(f.description)}
            </p>
            ${f.evidence ? `<small style="color:var(--text-muted);">Evidence: ${escapeHtml(f.evidence)}</small>` : ''}
          `;
          findingsEl.appendChild(card);

          // V2 Phase A Hook: Attach Visual Evidence Overlay trigger
          try {
            if (window.v2RenderFindingEvidenceButton) {
              window.v2RenderFindingEvidenceButton(card, f);
            }
          } catch (v2Err) {
            console.warn('[V2 Phase A Hook Error]', v2Err);
          }
        });
      }
    }

    // Discrepancy Matrix
    const discEl = document.getElementById('dossierDiscrepancyList');
    if (discEl) {
      discEl.innerHTML = '';
      const discrepancies = d.cross_document_comparison?.discrepancies || [];
      if (discrepancies.length === 0) {
        discEl.innerHTML = `<p style="font-size:0.85rem; color:var(--status-verified); margin:0;">✓ Full cross-document factual alignment verified across all assigned case files.</p>`;
      } else {
        discrepancies.forEach((disc) => {
          const card = document.createElement('div');
          card.style = 'background:var(--status-danger-dim); border:1px solid var(--status-danger-border); border-radius:4px; padding:10px 14px;';
          card.innerHTML = `
            <strong style="color:var(--status-danger);">⚠️ ${escapeHtml(disc.field || 'Discrepancy')}</strong>
            <p style="font-size:0.85rem; color:var(--text-primary); margin:4px 0 0 0;">${escapeHtml(disc.message || '')}</p>
          `;
          discEl.appendChild(card);
        });
      }
    }

  } catch (err) {
    console.error('[VEXORA Dossier Preview Error]', err);
  }
};

/**
 * Triggers export of a publication-ready PDF or HTML dossier for current selected case
 */
window.exportCurrentCaseDossier = async function(format) {
  const caseSelect = document.getElementById('dossierCaseSelector');
  const caseId = caseSelect ? caseSelect.value : null;

  if (!caseId) {
    showToast('Please select an investigation case to generate a dossier report.', 'warning');
    return;
  }

  const apiBase = getApiBase();
  showToast(`Generating audit-ready ${format.toUpperCase()} dossier for case ${caseId}...`, 'info');

  try {
    const res = await fetch(`${apiBase}/cases/${caseId}/report`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ format: format })
    });

    const data = await res.json();
    if (res.ok && data.success) {
      showToast(`Dossier Generated! File size: ${data.file_size_formatted}. Opening file...`, 'success');

      // Refresh reports history table
      loadGeneratedReportsList();

      // Open download / preview in new tab
      if (data.view_url) {
        window.open(data.view_url, '_blank');
      } else if (data.download_url) {
        window.open(data.download_url, '_blank');
      }
    } else {
      showToast(`Dossier export failed: ${data.error || 'Server error'}`, 'danger');
    }
  } catch (err) {
    console.error('[VEXORA Dossier Export Error]', err);
    showToast('Failed to connect to report generation service.', 'danger');
  }
};

/**
 * Loads the history of generated reports from backend repository into table
 */
window.loadGeneratedReportsList = async function() {
  const tableBody = document.getElementById('generatedReportsTableBody');
  if (!tableBody) return;

  const apiBase = getApiBase();
  try {
    const res = await fetch(`${apiBase}/reports`);
    if (!res.ok) return;

    const data = await res.json();
    if (data.success && data.data && data.data.length > 0) {
      tableBody.innerHTML = '';
      data.data.forEach((r) => {
        const sizeFormatted = (r.file_size / 1024).toFixed(1) + ' KB';
        const isPdf = (r.file_format || '').toLowerCase() === 'pdf';
        const formatBadge = isPdf
          ? '<span class="pill-tag pill-high">PDF</span>'
          : '<span class="pill-tag pill-medium">HTML</span>';

        const row = document.createElement('tr');
        row.innerHTML = `
          <td><code style="font-size:0.8rem;">${escapeHtml(r.id)}</code></td>
          <td><strong>${escapeHtml(r.case_id)}</strong></td>
          <td>${escapeHtml(r.title)}</td>
          <td>${formatBadge}</td>
          <td>${escapeHtml(sizeFormatted)}</td>
          <td><small style="color:var(--text-muted);">${escapeHtml(r.created_at || '')}</small></td>
          <td>
            <a href="${apiBase}/reports/${r.id}/view" target="_blank" class="table-action-btn" style="text-decoration:none; display:inline-flex; align-items:center;">👁️ View</a>
            <a href="${apiBase}/reports/${r.id}/download" target="_blank" class="table-action-btn" style="text-decoration:none; display:inline-flex; align-items:center;">⬇️ Download</a>
          </td>
        `;
        tableBody.appendChild(row);
      });
    } else {
      tableBody.innerHTML = `
        <tr>
          <td colspan="7" style="text-align:center; color:var(--text-muted); padding:16px;">
            No reports generated yet. Click "Export PDF Dossier" or "Export HTML" above to generate your first audit dossier.
          </td>
        </tr>
      `;
    }
  } catch (err) {
    console.warn('[VEXORA Reports History Sync Failed]', err);
  }
};

/**
 * ============================================================================
 * Phase 9: Audit Trail, Diagnostics & System Finalization
 * ============================================================================
 */

/**
 * Loads chronological audit trail logs into #auditTrailTableBody
 */
window.loadAuditTrailLogs = async function(filters = {}) {
  const tableBody = document.getElementById('auditTrailTableBody');
  if (!tableBody) return;

  const apiBase = getApiBase();
  try {
    let url = `${apiBase}/audit-logs?limit=50`;
    if (filters.action) url += `&action=${encodeURIComponent(filters.action)}`;
    if (filters.entity_type) url += `&entity_type=${encodeURIComponent(filters.entity_type)}`;
    if (filters.user) url += `&user=${encodeURIComponent(filters.user)}`;

    const res = await fetch(url);
    if (!res.ok) return;

    const data = await res.json();
    if (data.success && data.data && data.data.length > 0) {
      tableBody.innerHTML = '';
      data.data.forEach((log) => {
        const actionStr = log.action || 'ACTIVITY';
        const isAuth = actionStr.includes('LOGIN') || actionStr.includes('AUTH');
        const isAlert = actionStr.includes('FLAG') || actionStr.includes('CONFLICT') || actionStr.includes('DISCREPANCY');
        const isReport = actionStr.includes('REPORT') || actionStr.includes('DOSSIER');

        const pillClass = isAlert ? 'pill-high' : isReport ? 'pill-medium' : isAuth ? 'pill-status' : 'pill-low';

        const row = document.createElement('tr');
        row.innerHTML = `
          <td><code style="font-size:0.75rem;">#${log.id}</code></td>
          <td><small style="color:var(--text-muted); font-family:var(--font-mono);">${escapeHtml(log.timestamp || '')}</small></td>
          <td><span class="pill-tag ${pillClass}">${escapeHtml(actionStr)}</span></td>
          <td><code>${escapeHtml(log.entity_type || 'system')}</code></td>
          <td><code style="font-size:0.8rem;">${escapeHtml(log.entity_id || '—')}</code></td>
          <td><strong>${escapeHtml(log.user || 'System')}</strong></td>
          <td style="font-size:0.8rem; color:var(--text-secondary); max-width:300px;">
            ${escapeHtml(log.details || '')}
          </td>
        `;
        tableBody.appendChild(row);
      });
    } else {
      tableBody.innerHTML = `
        <tr>
          <td colspan="7" style="text-align:center; color:var(--text-muted); padding:16px;">
            No audit records matching query parameters.
          </td>
        </tr>
      `;
    }
  } catch (err) {
    console.warn('[VEXORA Audit Trail Sync Failed]', err);
  }
};

/**
 * Triggers direct browser download of the entire investigation audit trail
 */
window.exportAuditLogs = function(format = 'csv') {
  const apiBase = getApiBase();
  showToast(`Exporting complete investigation audit trail (${format.toUpperCase()})...`, 'info');
  window.open(`${apiBase}/audit-logs/export?format=${format}`, '_blank');
};

/**
 * Executes system-wide health and diagnostics self-test
 */
window.runSystemDiagnostics = async function() {
  const apiBase = getApiBase();
  showToast('Executing system-wide diagnostic health check...', 'info');

  try {
    const res = await fetch(`${apiBase}/system/diagnostics`);
    if (!res.ok) {
      showToast('System diagnostics returned error status.', 'danger');
      return;
    }

    const data = await res.json();
    if (data.success) {
      const db = data.database || {};
      const counts = db.table_counts || {};
      const storage = data.storage || {};

      const summaryEl = document.getElementById('settingsDiagnosticsSummary');
      if (summaryEl) {
        summaryEl.innerHTML = `
          • Engine Status: <strong style="color:var(--status-verified);">${data.status.toUpperCase()}</strong><br>
          • Engine Version: <strong>${escapeHtml(data.engine_version)}</strong><br>
          • Python Runtime: <strong>${escapeHtml(data.python_version)}</strong> • PyMuPDF: <strong>${escapeHtml(data.pymupdf_version)}</strong><br>
          • Relational Database: <strong>${escapeHtml(db.engine)} (${escapeHtml(db.status)})</strong><br>
          • Repository Metrics: <strong>${counts.cases || 0} Cases, ${counts.documents || 0} Docs, ${counts.findings || 0} Findings, ${counts.reports || 0} Reports</strong><br>
          • Storage Vault: <code>${escapeHtml(storage.upload_folder)}</code> (${storage.upload_folder_writable ? 'Writable ✓' : 'ReadOnly ⚠'})<br>
          • Reports Storage: <code>${escapeHtml(storage.reports_folder)}</code> (${storage.reports_folder_writable ? 'Writable ✓' : 'ReadOnly ⚠'})
        `;
      }

      showToast(`Diagnostics Completed! Node Status: ${data.status.toUpperCase()} (${counts.cases || 0} Cases, ${counts.documents || 0} Docs, ${counts.reports || 0} Reports).`, 'success');
    }
  } catch (err) {
    console.error('[VEXORA Diagnostics Error]', err);
    showToast('Failed to reach diagnostics service.', 'danger');
  }
};




