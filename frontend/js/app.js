/**
 * VEXORA — Document Forensics & Contextual Intelligence
 * Frontend Application Logic (Phase 1: Project Setup & UI Foundation)
 */

document.addEventListener('DOMContentLoaded', () => {
  // Initialize all interactive modules
  initThemeManager();
  initSidebar();
  initNavigation();
  initLiveClock();
  initSearchFilter();
  initCaseModal();
  initToastSystem();
  initKeyboardShortcuts();

  showToast('Welcome to VEXORA — Forensic Intelligence System ready.', 'info');
});

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
 * 2. Navigation Item Click and Active State Handler
 */
function initNavigation() {
  const navItems = document.querySelectorAll('.nav-item');
  const breadcrumbActive = document.getElementById('breadcrumbActive');

  navItems.forEach((item) => {
    item.addEventListener('click', (e) => {
      // In Phase 1, we prevent default navigation and toggle active indicator
      e.preventDefault();
      navItems.forEach((n) => n.classList.remove('active'));
      item.classList.add('active');

      const label = item.querySelector('.nav-label');
      if (label && breadcrumbActive) {
        breadcrumbActive.textContent = label.textContent.trim();
        showToast(`Navigated to ${label.textContent.trim()} view.`, 'info');
      }
    });
  });
}

/**
 * 3. Header Live Clock
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
 * 4. Live Table Search Filter
 */
function initSearchFilter() {
  const searchInput = document.getElementById('globalSearchInput');
  const casesTable = document.getElementById('recentCasesTable');

  if (!searchInput || !casesTable) return;

  searchInput.addEventListener('input', (e) => {
    const query = e.target.value.toLowerCase().trim();
    const rows = casesTable.querySelectorAll('tbody tr');

    rows.forEach((row) => {
      const text = row.textContent.toLowerCase();
      if (text.includes(query)) {
        row.style.display = '';
      } else {
        row.style.display = 'none';
      }
    });
  });
}

/**
 * 5. Case Modal Logic (Create New Investigation)
 */
function initCaseModal() {
  const modal = document.getElementById('newCaseModal');
  const openButtons = document.querySelectorAll('[data-action="open-new-case"]');
  const closeBtn = document.getElementById('closeCaseModalBtn');
  const cancelBtn = document.getElementById('cancelCaseModalBtn');
  const caseForm = document.getElementById('newCaseForm');
  const tableBody = document.querySelector('#recentCasesTable tbody');

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
  if (caseForm && tableBody) {
    caseForm.addEventListener('submit', (e) => {
      e.preventDefault();

      const titleInput = document.getElementById('caseTitleInput');
      const priorityInput = document.getElementById('casePriorityInput');
      const investigatorInput = document.getElementById('caseInvestigatorInput');

      const title = titleInput.value.trim();
      const priority = priorityInput.value;
      const investigator = investigatorInput.value.trim() || 'Misari Vadalia';

      if (!title) {
        showToast('Please provide a valid case title.', 'warning');
        return;
      }

      // Generate random case reference number
      const randomId = 'VX-' + Math.floor(1000 + Math.random() * 9000);

      // Create new row
      const newRow = document.createElement('tr');
      const priorityClass =
        priority === 'High' ? 'pill-high' : priority === 'Medium' ? 'pill-medium' : 'pill-low';

      newRow.innerHTML = `
        <td class="case-id-cell">${randomId}</td>
        <td>
          <span class="case-title-cell">${escapeHtml(title)}</span>
          <span class="case-subtitle">Lead: ${escapeHtml(investigator)} • Created just now</span>
        </td>
        <td>0 docs</td>
        <td><span class="pill-tag ${priorityClass}">${priority}</span></td>
        <td><span class="pill-tag pill-status">Active</span></td>
        <td>Just now</td>
        <td>
          <div class="action-btn-group">
            <button class="table-action-btn" onclick="showToast('Opened case ${randomId}', 'info')">Inspect</button>
            <button class="table-action-btn" onclick="showToast('Upload triggered for ${randomId}', 'info')">Upload</button>
          </div>
        </td>
      `;

      // Insert at the top of the table
      tableBody.insertBefore(newRow, tableBody.firstChild);

      // Update Active Cases Counter
      const activeCasesCounter = document.getElementById('activeCasesCount');
      if (activeCasesCounter) {
        let count = parseInt(activeCasesCounter.textContent) || 0;
        activeCasesCounter.textContent = count + 1;
      }

      closeModal();
      showToast(`Case ${randomId} successfully created and registered!`, 'success');
    });
  }
}

/**
 * 6. Toast Notification Manager
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
 * 7. Keyboard Shortcuts (Ctrl+K, ESC)
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
 * 0. Theme Manager (High-Contrast Crisp Light Default + Dark Mode Toggle)
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
      showToast(`Switched to ${newTheme.toUpperCase()} theme mode`, 'info');
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
 * Helper to prevent XSS in client-side text injection
 */
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

