/**
 * VEXORA — V2 Extension JavaScript Module
 * Phase A: Visual Evidence Overlay Modal & Tracing System
 */

(function () {
  'use strict';

  let currentZoom = 1.0;

  // Initialize modal structure once DOM is ready
  function ensureEvidenceModal() {
    if (document.getElementById('v2EvidenceModal')) {
      return;
    }

    const modalHtml = `
      <div id="v2EvidenceModal" class="v2-modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="v2ModalTitle">
        <div class="v2-modal-window">
          <div class="v2-modal-header">
            <div class="v2-modal-title-group">
              <span id="v2ModalRulePill" class="pill-tag pill-high">RULE</span>
              <h3 id="v2ModalTitle" class="v2-modal-title">Visual Evidence Overlay</h3>
            </div>
            <button id="v2ModalCloseBtn" class="v2-modal-close-btn" type="button" aria-label="Close modal">&times;</button>
          </div>
          <div class="v2-modal-body">
            <div class="v2-evidence-meta-bar">
              <span class="v2-evidence-meta-item">Document: <strong id="v2ModalDocName">—</strong></span>
              <span class="v2-evidence-meta-item">Class: <strong id="v2ModalClass">—</strong></span>
              <span class="v2-evidence-meta-item">Location: <strong id="v2ModalLocation">—</strong></span>
              <span class="v2-evidence-meta-item">Severity: <strong id="v2ModalSeverity">—</strong></span>
            </div>

            <div id="v2VisualCanvasContainer" class="v2-evidence-canvas-wrap">
              <div id="v2EvidenceLoading" style="color:var(--text-muted); font-size:0.85rem; padding:40px; text-align:center;">
                <div style="font-size:1.4rem; margin-bottom:8px;">🔍</div>
                Rendering visual forensic evidence overlay from document primitives...
              </div>
              <img id="v2EvidenceImg" class="v2-evidence-img" src="" alt="Forensic Evidence Overlay" style="display:none;" />
              <div id="v2CanvasToolbar" class="v2-evidence-toolbar" style="display:none;">
                <button type="button" id="v2ZoomOutBtn" class="v2-tool-btn" title="Zoom Out">−</button>
                <button type="button" id="v2ZoomResetBtn" class="v2-tool-btn" title="Reset Zoom">100%</button>
                <button type="button" id="v2ZoomInBtn" class="v2-tool-btn" title="Zoom In">+</button>
                <a id="v2OpenTabBtn" href="#" target="_blank" class="v2-tool-btn" style="text-decoration:none;" title="Open full resolution in new tab">↗ Open</a>
              </div>
            </div>

            <div id="v2NoCoordsAlert" class="v2-no-coords-card" style="display:none;">
              <div class="v2-no-coords-title">
                <span>ℹ️</span> Contextual / Non-Visual Forensic Finding
              </div>
              <p style="margin:0; font-size:0.85rem; color:var(--text-secondary); line-height:1.5;">
                This observation was produced by an automated contextual or relational forensic heuristic
                (such as contradictory dates, missing statutory fields, or cross-document discrepancies).
                No physical 2D bounding box applies to this finding.
              </p>
            </div>

            <div class="v2-finding-details-box">
              <p id="v2ModalDescription" class="v2-finding-desc"></p>
              <div id="v2ModalEvidenceContainer" style="display:none;">
                <span class="v2-finding-evidence-text" id="v2ModalEvidence"></span>
              </div>
            </div>
          </div>
          <div class="v2-modal-footer">
            <button id="v2ModalDismissBtn" type="button" class="btn btn-secondary" style="padding:6px 14px; font-size:0.85rem;">Close Preview</button>
          </div>
        </div>
      </div>
    `;

    const wrapper = document.createElement('div');
    wrapper.innerHTML = modalHtml;
    document.body.appendChild(wrapper.firstElementChild);

    // Event Listeners for Closing Modal
    const modalEl = document.getElementById('v2EvidenceModal');
    const closeBtn = document.getElementById('v2ModalCloseBtn');
    const dismissBtn = document.getElementById('v2ModalDismissBtn');

    function closeModal() {
      if (modalEl) {
        modalEl.classList.remove('active');
      }
    }

    if (closeBtn) closeBtn.addEventListener('click', closeModal);
    if (dismissBtn) dismissBtn.addEventListener('click', closeModal);

    if (modalEl) {
      modalEl.addEventListener('click', (e) => {
        if (e.target === modalEl) {
          closeModal();
        }
      });
    }

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && modalEl && modalEl.classList.contains('active')) {
        closeModal();
      }
    });

    // Zoom Controls
    const zoomInBtn = document.getElementById('v2ZoomInBtn');
    const zoomOutBtn = document.getElementById('v2ZoomOutBtn');
    const zoomResetBtn = document.getElementById('v2ZoomResetBtn');
    const imgEl = document.getElementById('v2EvidenceImg');

    function applyZoom() {
      if (imgEl) {
        imgEl.style.transform = `scale(${currentZoom})`;
      }
      if (zoomResetBtn) {
        zoomResetBtn.textContent = `${Math.round(currentZoom * 100)}%`;
      }
    }

    if (zoomInBtn) {
      zoomInBtn.addEventListener('click', () => {
        currentZoom = Math.min(currentZoom + 0.25, 3.0);
        applyZoom();
      });
    }
    if (zoomOutBtn) {
      zoomOutBtn.addEventListener('click', () => {
        currentZoom = Math.max(currentZoom - 0.25, 0.5);
        applyZoom();
      });
    }
    if (zoomResetBtn) {
      zoomResetBtn.addEventListener('click', () => {
        currentZoom = 1.0;
        applyZoom();
      });
    }
  }

  /**
   * Opens Evidence Overlay Modal for a specific finding record
   */
  window.v2OpenEvidenceModal = function (finding) {
    if (!finding) return;
    ensureEvidenceModal();

    const modalEl = document.getElementById('v2EvidenceModal');
    const rulePill = document.getElementById('v2ModalRulePill');
    const titleEl = document.getElementById('v2ModalTitle');
    const docNameEl = document.getElementById('v2ModalDocName');
    const locEl = document.getElementById('v2ModalLocation');
    const sevEl = document.getElementById('v2ModalSeverity');
    const descEl = document.getElementById('v2ModalDescription');
    const evContainer = document.getElementById('v2ModalEvidenceContainer');
    const evText = document.getElementById('v2ModalEvidence');
    const canvasWrap = document.getElementById('v2VisualCanvasContainer');
    const noCoordsAlert = document.getElementById('v2NoCoordsAlert');
    const loadingEl = document.getElementById('v2EvidenceLoading');
    const imgEl = document.getElementById('v2EvidenceImg');
    const toolbarEl = document.getElementById('v2CanvasToolbar');
    const openTabBtn = document.getElementById('v2OpenTabBtn');

    currentZoom = 1.0;
    if (imgEl) imgEl.style.transform = 'scale(1.0)';
    const zoomResetBtn = document.getElementById('v2ZoomResetBtn');
    if (zoomResetBtn) zoomResetBtn.textContent = '100%';

    // Populate Headers & Metadata
    const ruleId = finding.rule_id || 'RULE';
    const title = finding.title || 'Forensic Finding';
    const severity = finding.severity || 'Medium';
    const pageNum = finding.page_number || 1;
    const coords = finding.coordinates;

    if (rulePill) {
      rulePill.textContent = ruleId;
      const sevLower = severity.toLowerCase();
      rulePill.className = 'pill-tag ' + (sevLower === 'critical' || sevLower === 'high' ? 'pill-high' : sevLower === 'medium' ? 'pill-medium' : 'pill-low');
    }

    const classEl = document.getElementById('v2ModalClass');
    if (classEl) classEl.textContent = finding.evidence_class || 'Observation';
    if (titleEl) titleEl.textContent = title;
    if (docNameEl) docNameEl.textContent = finding.document_filename || finding.document_id || 'Document';
    if (sevEl) sevEl.textContent = severity;
    if (locEl) {
      locEl.textContent = coords ? `Page ${pageNum} • Box [${String(coords)}]` : `Page ${pageNum} • Contextual Check`;
    }

    if (descEl) descEl.textContent = finding.description || 'No detailed forensic explanation provided.';

    if (finding.evidence) {
      if (evContainer) evContainer.style.display = 'block';
      if (evText) evText.textContent = `Evidence Trace: ${finding.evidence}`;
    } else {
      if (evContainer) evContainer.style.display = 'none';
    }

    // Determine if visual coordinates exist
    let hasCoords = false;
    if (coords) {
      try {
        const parsed = typeof coords === 'string' ? JSON.parse(coords) : coords;
        if (Array.isArray(parsed) && parsed.length >= 4) {
          hasCoords = true;
        }
      } catch (e) {
        if (typeof coords === 'string' && coords.includes(',')) {
          hasCoords = true;
        }
      }
    }

    if (hasCoords && finding.id) {
      // Visual finding with coordinates
      if (canvasWrap) canvasWrap.style.display = 'flex';
      if (noCoordsAlert) noCoordsAlert.style.display = 'none';
      if (loadingEl) loadingEl.style.display = 'block';
      if (imgEl) imgEl.style.display = 'none';
      if (toolbarEl) toolbarEl.style.display = 'none';

      const imageUrl = `/api/findings/${encodeURIComponent(finding.id)}/evidence-image?t=${Date.now()}`;
      if (openTabBtn) openTabBtn.href = imageUrl;

      // Load image
      const tempImg = new Image();
      tempImg.onload = function () {
        if (loadingEl) loadingEl.style.display = 'none';
        if (imgEl) {
          imgEl.src = imageUrl;
          imgEl.style.display = 'block';
        }
        if (toolbarEl) toolbarEl.style.display = 'flex';
      };
      tempImg.onerror = function () {
        if (loadingEl) {
          loadingEl.innerHTML = `
            <div style="color:var(--status-danger); font-size:1.2rem; margin-bottom:6px;">⚠️</div>
            Failed to render evidence overlay image from server.
          `;
          loadingEl.style.display = 'block';
        }
      };
      tempImg.src = imageUrl;

    } else {
      // Contextual check with no coordinates
      if (canvasWrap) canvasWrap.style.display = 'none';
      if (noCoordsAlert) noCoordsAlert.style.display = 'block';
    }

    // Show modal
    if (modalEl) {
      modalEl.classList.add('active');
    }
  };

  /**
   * V2 Phase A UI Hook: Injects "View Evidence" button into finding card
   */
  window.v2RenderFindingEvidenceButton = function (cardElement, finding) {
    if (!cardElement || !finding) return;

    // Avoid duplicate buttons if re-rendered
    if (cardElement.querySelector('.v2-btn-evidence')) return;

    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'v2-btn-evidence';
    btn.title = 'View highlighted visual evidence overlay on document page';
    btn.innerHTML = '🔍 View Evidence';

    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      window.v2OpenEvidenceModal(finding);
    });

    cardElement.appendChild(btn);
  };

  // Pre-initialize on load
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', ensureEvidenceModal);
  } else {
    ensureEvidenceModal();
  }

})();
