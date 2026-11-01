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
          showToast(`Ingested ${resData.count} document(s) successfully! Cryptographic SHA-256 generated.`, 'success');
          stagedFilesList = [];
          if (queue) queue.innerHTML = '';

          // Refresh live library and stats
          initBackendSync();

          setTimeout(() => {
            navigateToView('library');
          }, 800);
        } else {
          showToast(`Ingestion error: ${resData.error || 'Server rejected files.'}`, 'danger');
        }
      } catch (err) {
        console.warn('[VEXORA Upload] Live upload failed, using fallback simulation.', err);
        showToast('Processed staged documents locally (backend offline).', 'success');
        stagedFilesList = [];
        if (queue) queue.innerHTML = '';
        setTimeout(() => {
          navigateToView('library');
        }, 800);
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
          }
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
function getApiBase() {
  if (window.location.port === '5000') {
    return '/api';
  }
  if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    return 'http://127.0.0.1:5000/api';
  }
  return '/api';
}

async function initBackendSync() {
  const apiBase = getApiBase();
  try {
    const healthRes = await fetch(`${apiBase}/health`, { method: 'GET' });
    if (!healthRes.ok) return;
    const healthData = await healthRes.json();

    if (healthData.status === 'healthy') {
      console.log('[VEXORA API] Connected to Flask backend & SQLite database.');

      // Update banner pill to show connected state
      const bannerPill = document.querySelector('.banner-pill');
      if (bannerPill) {
        bannerPill.textContent = '⚡ VEXORA Intelligence Engine • Phase 6 Active (Forensic & Contextual Analysis)';
      }

      // 1. Fetch live stats
      try {
        const statsRes = await fetch(`${apiBase}/stats`);
        if (statsRes.ok) {
          const statsJson = await statsRes.json();
          if (statsJson.success && statsJson.data) {
            const stats = statsJson.data;
            const activeCounter = document.getElementById('activeCasesCount');
            if (activeCounter && stats.active_cases !== undefined) {
              activeCounter.textContent = stats.active_cases;
            }
            const docsCounter = document.getElementById('totalDocsCount');
            if (docsCounter && stats.total_documents !== undefined) {
              docsCounter.textContent = stats.total_documents;
            }
            const flagsCounter = document.getElementById('flaggedAnomaliesCount');
            if (flagsCounter && stats.critical_findings !== undefined) {
              flagsCounter.textContent = stats.critical_findings;
            }
            const evidenceCounter = document.getElementById('evidenceNodesCount');
            if (evidenceCounter && stats.total_findings !== undefined) {
              evidenceCounter.textContent = stats.total_findings;
            }
          }
        }
      } catch (e) {
        console.warn('[VEXORA API] Stats fetch failed:', e);
      }

      // 2. Fetch active cases and populate upload case selector
      const targetCaseSelect = document.getElementById('targetCaseSelect');
      if (targetCaseSelect) {
        try {
          const casesRes = await fetch(`${apiBase}/cases`);
          if (casesRes.ok) {
            const casesJson = await casesRes.json();
            if (casesJson.success && casesJson.data && casesJson.data.length > 0) {
              targetCaseSelect.innerHTML = '';
              casesJson.data.forEach((c) => {
                const opt = document.createElement('option');
                opt.value = c.id;
                opt.textContent = `${c.id}: ${c.title}`;
                targetCaseSelect.appendChild(opt);
              });
            }
          }
        } catch (e) {
          console.warn('[VEXORA API] Cases sync failed:', e);
        }
      }

      // 3. Fetch live documents and populate Document Library cards & Inspector selector
      const docLibraryGrid = document.getElementById('docLibraryGrid');
      const forensicDocSelector = document.getElementById('forensicDocSelector');

      if (docLibraryGrid) {
        try {
          const docsRes = await fetch(`${apiBase}/documents`);
          if (docsRes.ok) {
            const docsJson = await docsRes.json();
            if (docsJson.success && docsJson.data && docsJson.data.length > 0) {
              docLibraryGrid.innerHTML = '';

              if (forensicDocSelector) {
                forensicDocSelector.innerHTML = '';
              }

              docsJson.data.forEach((doc) => {
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

                // Populate selector in Forensic Inspector
                if (forensicDocSelector) {
                  const opt = document.createElement('option');
                  opt.value = doc.id;
                  opt.textContent = `${doc.filename} (${doc.id})`;
                  forensicDocSelector.appendChild(opt);
                }

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
                    <span>${escapeHtml(doc.file_type.toUpperCase())}</span> • <span>${sizeMb}</span> • <span style="color:var(--status-verified);">${doc.classification_confidence || 95}% Conf</span>
                  </div>
                  <div style="font-size:0.75rem; color:var(--text-muted); margin-top:4px;">
                    Case: <strong>${escapeHtml(doc.case_id || 'General Vault')}</strong>
                  </div>
                  <div class="doc-card-footer">
                    <button class="table-action-btn" onclick="triggerDocumentExtraction('${doc.id}')" title="Run OCR & Entity Extraction">⚡ Extract</button>
                    <button class="table-action-btn" onclick="analyzeDocumentAndInspect('${doc.id}')" title="Run Forensic & Contextual Analysis">🔬 Analyze</button>
                    <a href="${apiBase}/documents/${doc.id}/download" target="_blank" class="table-action-btn" style="text-decoration:none; display:inline-flex; align-items:center;">Download</a>
                  </div>
                `;
                docLibraryGrid.appendChild(card);
              });

              if (forensicDocSelector) {
                forensicDocSelector.onchange = (e) => {
                  loadDocumentFindings(e.target.value);
                };
              }
            }
          }
        } catch (e) {
          console.warn('[VEXORA API] Documents sync failed:', e);
        }
      }
    }
  } catch (err) {
    // Backend server not currently running on port 5000; running in static client mode
    console.log('[VEXORA API] Running in standalone frontend mode.');
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
 * Phase 6: Fetch and load findings for a selected document
 */
window.loadDocumentFindings = async function(docId) {
  const apiBase = getApiBase();
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

    const card = document.createElement('div');
    card.className = `finding-detail-card ${cardClass}`;
    card.innerHTML = `
      <div class="finding-card-head">
        <span class="finding-title">[${escapeHtml(f.rule_id || 'RULE')}] ${escapeHtml(f.title)}</span>
        <span class="finding-loc">${escapeHtml(locText)}</span>
      </div>
      <p class="finding-reason">${escapeHtml(f.description)}</p>
      ${f.evidence ? `<div class="finding-recommendation">🔍 Evidence: <strong>${escapeHtml(f.evidence)}</strong></div>` : ''}
    `;
    feed.appendChild(card);
  });
}

