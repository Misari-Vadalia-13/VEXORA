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
              <span class="v2-evidence-meta-item">Rule Weight: <strong id="v2ModalRuleWeight">—</strong></span>
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

            <!-- Phase C: AI Contextual Reasoning Box -->
            <div id="v2AiExplanationBox" class="v2-ai-explanation-box" style="display:none;">
              <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                <strong style="color:#38bdf8; font-size:0.85rem;">🤖 AI Contextual Reasoning</strong>
                <span style="font-size:0.75rem; color:#94a3b8; font-style:italic;">AI-assessed, requires human review</span>
              </div>
              <p id="v2AiExplanationText" style="font-size:0.85rem; color:var(--text-secondary, #cbd5e1); margin:0 0 8px 0; line-height:1.5;"></p>
              <div id="v2AiInnocentHypotheses" style="font-size:0.8rem; color:#38bdf8; background:rgba(2,132,199,0.12); border:1px solid rgba(2,132,199,0.25); padding:6px 10px; border-radius:4px; margin-bottom:6px; display:none;"></div>
              <div id="v2AiNextStep" style="font-size:0.8rem; color:#34d399; background:rgba(16,185,129,0.12); border:1px solid rgba(16,185,129,0.25); padding:6px 10px; border-radius:4px; display:none;"></div>
            </div>
          </div>
          <div class="v2-modal-footer">
            <button id="v2ExplainWithAiBtn" type="button" class="v2-btn-ai" style="margin-right:auto;">🤖 Explain with AI</button>
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
    const weightEl = document.getElementById('v2ModalRuleWeight');
    if (weightEl) {
      weightEl.textContent = (finding.confidence !== undefined && finding.confidence !== null) ? String(finding.confidence) : '—';
    }
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

    // Phase C: Reset and wire AI explanation trigger
    const aiBox = document.getElementById('v2AiExplanationBox');
    const aiText = document.getElementById('v2AiExplanationText');
    const aiHypotheses = document.getElementById('v2AiInnocentHypotheses');
    const aiNextStep = document.getElementById('v2AiNextStep');
    const explainBtn = document.getElementById('v2ExplainWithAiBtn');

    if (aiBox) aiBox.style.display = 'none';
    if (aiText) aiText.textContent = '';
    if (aiHypotheses) aiHypotheses.style.display = 'none';
    if (aiNextStep) aiNextStep.style.display = 'none';
    if (explainBtn) {
      explainBtn.disabled = false;
      explainBtn.innerHTML = '🤖 Explain with AI';
      explainBtn.onclick = function () {
        explainBtn.disabled = true;
        explainBtn.innerHTML = '⏳ Analyzing...';
        vexoraFetch(`/findings/${encodeURIComponent(finding.id)}/explain`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' }
        })
          .then(res => res.json())
          .then(data => {
            if (data.success && data.explanation) {
              if (aiText) aiText.textContent = data.explanation;
              if (data.innocent_hypotheses && data.innocent_hypotheses.length > 0 && aiHypotheses) {
                aiHypotheses.innerHTML = '<strong>Plausible Alternative:</strong> ' + data.innocent_hypotheses.join('; ');
                aiHypotheses.style.display = 'block';
              }
              if (data.next_verification_step && aiNextStep) {
                aiNextStep.innerHTML = '<strong>Next Verification Step:</strong> ' + data.next_verification_step;
                aiNextStep.style.display = 'block';
              }
              if (aiBox) aiBox.style.display = 'block';
              explainBtn.innerHTML = '✓ Explained';
            } else {
              if (aiText) aiText.textContent = data.message || 'AI reasoning is currently unavailable or disabled on this server.';
              if (aiBox) aiBox.style.display = 'block';
              explainBtn.innerHTML = '🤖 Explain with AI';
              explainBtn.disabled = false;
            }
          })
          .catch(err => {
            if (aiText) aiText.textContent = 'Failed to connect to AI reasoning endpoint.';
            if (aiBox) aiBox.style.display = 'block';
            explainBtn.innerHTML = '🤖 Explain with AI';
            explainBtn.disabled = false;
          });
      };
    }

    // Determine if visual coordinates or visual artifacts exist
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
    const hasEvidenceUrl = Boolean(finding.evidence_url || (finding.evidence && String(finding.evidence).includes('saved: ')));
    const hasVisualEvidence = (hasCoords || hasEvidenceUrl) && (finding.id || hasEvidenceUrl);

    if (hasVisualEvidence) {
      // Visual finding with coordinates or evidence artifact
      if (canvasWrap) canvasWrap.style.display = 'flex';
      if (noCoordsAlert) noCoordsAlert.style.display = 'none';
      if (loadingEl) loadingEl.style.display = 'block';
      if (imgEl) imgEl.style.display = 'none';
      if (toolbarEl) toolbarEl.style.display = 'none';

      const _apiBase = (typeof getApiBase === "function") ? getApiBase() : ((typeof window.getApiBase === "function") ? window.getApiBase() : "/api");
      let imageUrl = "";
      if (finding.evidence_url) {
        imageUrl = finding.evidence_url.startsWith('http') || finding.evidence_url.startsWith('/')
          ? finding.evidence_url
          : `${_apiBase}/${finding.evidence_url}`;
      } else {
        imageUrl = `${_apiBase}/findings/${encodeURIComponent(finding.id)}/evidence-image?t=${Date.now()}`;
      }
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

    // Check if finding has spatial coordinates or visual evidence file
    const hasVisual = finding.coordinates || finding.evidence_url || (finding.evidence && String(finding.evidence).includes('saved: '));
    if (!hasVisual) return;

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

  // =========================================================================
  // Phase F: Cross-Document Relationship Graph SVG Visualization
  // =========================================================================

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  window.v2LoadRelationshipGraph = function (caseId) {
    const container = document.getElementById('relationshipGraphContainer');
    if (!container) return;

    if (!caseId) {
      const select = document.getElementById('relGraphCaseSelect');
      caseId = select ? select.value : 'CAS-2026-0891';
    }

    container.innerHTML = `
      <div style="color:var(--text-muted); font-size:0.85rem; padding:40px; text-align:center;">
        <div style="font-size:1.4rem; margin-bottom:8px;">🔄</div>
        Loading cross-document relationship graph for ${escapeHtml(caseId)}...
      </div>
    `;

    vexoraFetch(`/cases/${encodeURIComponent(caseId)}/relationships`)
      .then(res => {
        if (res.status === 403) {
          throw new Error('CORRELATOR_DISABLED');
        }
        return res.json();
      })
      .then(data => {
        const graphData = data.data || data;
        window.v2RenderRelationshipGraph(graphData, 'relationshipGraphContainer');
      })
      .catch(err => {
        if (err.message === 'CORRELATOR_DISABLED') {
          container.innerHTML = `
            <div style="padding:32px; text-align:center; color:var(--text-secondary); max-width:480px; margin:0 auto;">
              <div style="font-size:1.5rem; margin-bottom:8px;">🔒</div>
              <strong style="color:var(--status-anomaly, #f59e0b);">Cross-Document Correlator Offline</strong>
              <p style="margin:8px 0 0 0; font-size:0.85rem; line-height:1.5;">
                The cross-document correlation engine is protected by feature flag. Enable with <code>ENABLE_CORRELATOR=true</code> in your environment to visualize entity relationships and chronological conflict edges.
              </p>
            </div>
          `;
        } else {
          container.innerHTML = `
            <div style="padding:32px; text-align:center; color:var(--status-danger);">
              <div style="font-size:1.5rem; margin-bottom:8px;">⚠️</div>
              ${err.message === 'BACKEND_UNREACHABLE' ? 'VEXORA backend not reachable. Start <code>python -m backend.app</code> and open http://127.0.0.1:5000, then click Refresh.' : 'Failed to load relationship graph: ' + escapeHtml(err.message || 'Unknown network error')}
            </div>
          `;
        }
      });
  };

  window.v2ReloadCurrentRelationshipGraph = function () {
    const select = document.getElementById('relGraphCaseSelect');
    const caseId = select ? select.value : 'CAS-2026-0891';
    window.v2LoadRelationshipGraph(caseId);
  };

  window.v2RenderRelationshipGraph = function (graph, containerId) {
    const container = document.getElementById(containerId || 'relationshipGraphContainer');
    if (!container) return;

    const nodes = (graph && graph.nodes) || [];
    const edges = (graph && graph.edges) || [];

    if (nodes.length === 0) {
      container.innerHTML = `
        <div style="padding:40px; text-align:center; color:var(--text-muted); font-size:0.85rem;">
          <div style="font-size:1.5rem; margin-bottom:8px;">📂</div>
          No documents or correlated entities found for this case. Upload and analyze documents to populate the relationship graph.
        </div>
      `;
      return;
    }

    const svgWidth = 840;
    const svgHeight = 440;
    const centerX = svgWidth / 2;
    const centerY = svgHeight / 2;

    const docNodes = nodes.filter(n => n.type === 'document');
    const entNodes = nodes.filter(n => n.type === 'entity');

    const nodePositions = {};

    // Layout document nodes on outer ellipse
    const docCount = docNodes.length;
    const rDocX = 300;
    const rDocY = 160;
    docNodes.forEach((node, idx) => {
      const angle = (idx / Math.max(docCount, 1)) * 2 * Math.PI - Math.PI / 2;
      nodePositions[node.id] = {
        x: centerX + rDocX * Math.cos(angle),
        y: centerY + rDocY * Math.sin(angle),
        node: node
      };
    });

    // Layout entity nodes on inner ellipse
    const entCount = entNodes.length;
    const rEntX = 170;
    const rEntY = 90;
    entNodes.forEach((node, idx) => {
      const angle = (idx / Math.max(entCount, 1)) * 2 * Math.PI + (docCount > 0 ? (Math.PI / docCount) : 0);
      nodePositions[node.id] = {
        x: centerX + rEntX * Math.cos(angle),
        y: centerY + rEntY * Math.sin(angle),
        node: node
      };
    });

    // Edge colors and styles
    function getEdgeStyle(relation) {
      switch (relation) {
        case 'shared_invoice_id':
          return { color: '#10b981', dash: '', label: 'Invoice #' };
        case 'shared_amount':
          return { color: '#f59e0b', dash: '', label: 'Amount Match' };
        case 'shared_party':
          return { color: '#8b5cf6', dash: '', label: 'Party Match' };
        case 'date_conflict':
          return { color: '#ef4444', dash: '5,5', label: 'Date Conflict' };
        case 'bank_payment_match':
          return { color: '#06b6d4', dash: '', label: 'Bank Payment' };
        default:
          return { color: '#64748b', dash: '', label: relation };
      }
    }

    // Build SVG markup
    let svgHtml = `
      <svg viewBox="0 0 ${svgWidth} ${svgHeight}" style="width:100%; height:100%; min-height:440px; display:block; user-select:none;" id="v2RelationshipSvg">
        <defs>
          <filter id="glow-filter" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
        </defs>
        <g id="v2GraphEdges">
    `;

    // Render Edges
    edges.forEach((edge, idx) => {
      const p1 = nodePositions[edge.source];
      const p2 = nodePositions[edge.target];
      if (!p1 || !p2) return;

      const style = getEdgeStyle(edge.relation);
      const midX = (p1.x + p2.x) / 2;
      const midY = (p1.y + p2.y) / 2;

      svgHtml += `
        <g class="v2-edge-group" data-edge-index="${idx}" style="cursor:pointer;">
          <line x1="${p1.x}" y1="${p1.y}" x2="${p2.x}" y2="${p2.y}"
            stroke="${style.color}" stroke-width="2" stroke-dasharray="${style.dash}" opacity="0.75" />
          <rect x="${midX - 35}" y="${midY - 9}" width="70" height="18" rx="4" fill="#0f172a" stroke="${style.color}" stroke-width="1" opacity="0.9" />
          <text x="${midX}" y="${midY + 3}" fill="${style.color}" font-size="9" text-anchor="middle" font-weight="600">${style.label}</text>
        </g>
      `;
    });

    svgHtml += `</g><g id="v2GraphNodes">`;

    // Render Nodes
    Object.values(nodePositions).forEach(pos => {
      const node = pos.node;
      const isDoc = node.type === 'document';

      if (isDoc) {
        const docLabel = (node.label || 'Document').length > 18 ? (node.label.substring(0, 16) + '…') : node.label;
        svgHtml += `
          <g class="v2-node-group" data-node-id="${node.id}" style="cursor:pointer;">
            <circle cx="${pos.x}" cy="${pos.y}" r="26" fill="#0c4a6e" stroke="#38bdf8" stroke-width="2.5" />
            <text x="${pos.x}" y="${pos.y + 4}" fill="#ffffff" font-size="14" text-anchor="middle">📄</text>
            <text x="${pos.x}" y="${pos.y + 40}" fill="#e2e8f0" font-size="10" text-anchor="middle" font-weight="600">${escapeHtml(docLabel)}</text>
            <text x="${pos.x}" y="${pos.y + 51}" fill="#94a3b8" font-size="8.5" text-anchor="middle">${escapeHtml(node.category || '')}</text>
          </g>
        `;
      } else {
        let entColor = '#10b981';
        let entIcon = '#';
        if (node.entity_type === 'monetary_value') {
          entColor = '#f59e0b';
          entIcon = '$';
        } else if (node.entity_type === 'organization') {
          entColor = '#8b5cf6';
          entIcon = '🏢';
        }

        const entLabel = (node.label || 'Entity').length > 18 ? (node.label.substring(0, 16) + '…') : node.label;
        svgHtml += `
          <g class="v2-node-group" data-node-id="${node.id}" style="cursor:pointer;">
            <circle cx="${pos.x}" cy="${pos.y}" r="18" fill="#1e293b" stroke="${entColor}" stroke-width="2" />
            <text x="${pos.x}" y="${pos.y + 4}" fill="${entColor}" font-size="11" text-anchor="middle" font-weight="bold">${entIcon}</text>
            <text x="${pos.x}" y="${pos.y + 30}" fill="#cbd5e1" font-size="9" text-anchor="middle" font-weight="500">${escapeHtml(entLabel)}</text>
          </g>
        `;
      }
    });

    svgHtml += `</g></svg>`;

    container.innerHTML = svgHtml;

    // Attach click handlers to nodes & edges
    const detailsCard = document.getElementById('relGraphDetailsCard');
    const detailsTitle = document.getElementById('relGraphDetailsTitle');
    const detailsContent = document.getElementById('relGraphDetailsContent');

    container.querySelectorAll('.v2-node-group').forEach(el => {
      el.addEventListener('click', () => {
        const nodeId = el.getAttribute('data-node-id');
        const pos = nodePositions[nodeId];
        if (!pos) return;
        const n = pos.node;

        if (detailsCard && detailsTitle && detailsContent) {
          detailsCard.style.display = 'block';
          if (n.type === 'document') {
            detailsTitle.textContent = `Document: ${n.label}`;
            const relatedEdges = edges.filter(e => e.source === n.id || e.target === n.id);
            detailsContent.innerHTML = `
              <div><strong>Category:</strong> ${escapeHtml(n.category || 'General Document')} | <strong>Status:</strong> ${escapeHtml(n.status || 'Pending')}</div>
              <div style="margin-top:6px;"><strong>Active Correlations (${relatedEdges.length}):</strong></div>
              <ul style="margin:4px 0 0 16px; padding:0;">
                ${relatedEdges.map(e => `<li><strong style="color:var(--accent-primary);">${escapeHtml(e.relation)}</strong>: ${escapeHtml(e.evidence)}</li>`).join('')}
              </ul>
            `;
          } else {
            detailsTitle.textContent = `Entity: ${n.label}`;
            const relatedEdges = edges.filter(e => e.source === n.id || e.target === n.id);
            detailsContent.innerHTML = `
              <div><strong>Entity Type:</strong> ${escapeHtml(n.entity_type || 'Unknown')}</div>
              <div style="margin-top:6px;"><strong>Cross-Document Links (${relatedEdges.length}):</strong></div>
              <ul style="margin:4px 0 0 16px; padding:0;">
                ${relatedEdges.map(e => `<li><strong style="color:var(--accent-primary);">${escapeHtml(e.relation)}</strong>: ${escapeHtml(e.evidence)}</li>`).join('')}
              </ul>
            `;
          }
        }
      });
    });

    container.querySelectorAll('.v2-edge-group').forEach(el => {
      el.addEventListener('click', () => {
        const idx = parseInt(el.getAttribute('data-edge-index'), 10);
        const edge = edges[idx];
        if (!edge) return;

        if (detailsCard && detailsTitle && detailsContent) {
          detailsCard.style.display = 'block';
          detailsTitle.textContent = `Relationship: ${edge.relation}`;
          detailsContent.innerHTML = `
            <div><strong>Verbatim Evidence:</strong> "${escapeHtml(edge.evidence)}"</div>
            <div style="margin-top:4px;"><strong>Location / Page:</strong> Page ${edge.page || 1} | <strong>Correlation Confidence:</strong> ${Math.round((edge.confidence || 1.0) * 100)}%</div>
          `;
        }
      });
    });
  };

  // =========================================================================
  // Phase I: LLM Integration — AI Test Connection & Extracted Fields UI
  // =========================================================================

  /**
   * Injects "Test AI Connection" button into System Settings diagnostics panel
   */
  window.v2SetupAiTestButton = function () {
    const summaryEl = document.getElementById('settingsDiagnosticsSummary');
    if (!summaryEl) return;
    if (document.getElementById('v2AiTestBtn')) return;

    const btnWrap = document.createElement('div');
    btnWrap.style.marginTop = '12px';

    const aiBtn = document.createElement('button');
    aiBtn.id = 'v2AiTestBtn';
    aiBtn.type = 'button';
    aiBtn.className = 'btn-secondary';
    aiBtn.style.fontSize = '0.82rem';
    aiBtn.style.padding = '6px 14px';
    aiBtn.innerHTML = '🤖 Test AI Connection';

    const statusSpan = document.createElement('span');
    statusSpan.id = 'v2AiTestStatus';
    statusSpan.style.marginLeft = '10px';
    statusSpan.style.fontSize = '0.8rem';
    statusSpan.style.color = 'var(--text-muted)';

    btnWrap.appendChild(aiBtn);
    btnWrap.appendChild(statusSpan);

    if (summaryEl.parentElement) {
      summaryEl.parentElement.appendChild(btnWrap);
    }

    aiBtn.addEventListener('click', async () => {
      aiBtn.disabled = true;
      aiBtn.innerHTML = '⏳ Testing AI...';
      statusSpan.textContent = 'Contacting configured provider...';
      try {
        const res = await vexoraFetch('/system/ai-test', { method: 'POST' });
        const data = await res.json();
        if (data.ok) {
          statusSpan.style.color = 'var(--status-verified, #10b981)';
          statusSpan.textContent = `✓ Connected (${data.provider} / ${data.model}) — ${data.latency_ms}ms`;
          if (typeof window.updateAiReasoningBadge === 'function') {
            window.updateAiReasoningBadge(true, data.model);
          }
          if (typeof window.showToast === 'function') {
            window.showToast(`AI Connection OK (${data.provider} / ${data.model}) - Latency: ${data.latency_ms}ms`, 'success');
          }
        } else {
          statusSpan.style.color = 'var(--status-danger, #ef4444)';
          statusSpan.textContent = `⚠️ Failed: ${data.error || 'Unavailable'}`;
          if (typeof window.updateAiReasoningBadge === 'function') {
            window.updateAiReasoningBadge(false);
          }
          if (typeof window.showToast === 'function') {
            window.showToast(`AI Test: ${data.error || 'Check configuration'}`, 'danger');
          }
        }
      } catch (err) {
        statusSpan.style.color = 'var(--status-danger, #ef4444)';
        statusSpan.textContent = '⚠️ Backend unreachable calling /api/system/ai-test';
        if (typeof window.updateAiReasoningBadge === 'function') {
          window.updateAiReasoningBadge(false);
        }
      } finally {
        setTimeout(() => {
          aiBtn.disabled = false;
          aiBtn.innerHTML = '🤖 Test AI Connection';
        }, 3500);
      }
    });
  };

  /**
   * Renders AI-extracted structured fields table in Forensic Document Inspector
   */
  window.v2RenderAiExtractedFields = async function (docId) {
    if (!docId) {
      const selector = document.getElementById('forensicDocSelector');
      docId = selector ? selector.value : null;
    }
    if (!docId) return;

    const pane = document.querySelector('.document-inspection-pane');
    if (!pane) return;

    let container = document.getElementById('v2AiExtractedFieldsSection');
    if (!container) {
      container = document.createElement('div');
      container.id = 'v2AiExtractedFieldsSection';
      container.className = 'card-panel';
      container.style.marginTop = '16px';
      container.style.padding = '14px 18px';
      pane.appendChild(container);
    }

    container.innerHTML = `
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
        <div style="display:flex; align-items:center; gap:8px;">
          <strong style="font-size:0.9rem; color:var(--text-primary);">🤖 AI-Extracted Fields</strong>
          <span class="pill-tag pill-low" style="font-size:0.68rem;">Verified Grounding</span>
        </div>
        <span style="font-size:0.75rem; color:#94a3b8; font-style:italic;">AI-assessed, requires human review</span>
      </div>
      <div id="v2AiFieldsContent" style="font-size:0.82rem; color:var(--text-muted); padding:8px 0;">
        Loading AI insights for ${escapeHtml(docId)}...
      </div>
    `;

    try {
      const res = await vexoraFetch(`/documents/${encodeURIComponent(docId)}/ai-insights`);
      const resData = await res.json();
      const contentEl = document.getElementById('v2AiFieldsContent');
      if (!contentEl) return;

      const insights = (resData && resData.data) || [];
      const fieldInsight = insights.find(i => i.insight_type === 'field_extraction');

      if (!fieldInsight || !fieldInsight.data || Object.keys(fieldInsight.data).length === 0) {
        contentEl.innerHTML = `
          <div style="display:flex; align-items:center; justify-content:space-between; gap:12px; padding:6px 0;">
            <span>No structured AI fields extracted yet for this document.</span>
            <button id="v2TriggerAiExtractBtn" type="button" class="btn-secondary" style="font-size:0.78rem; padding:4px 10px;">
              ⚡ Extract with AI
            </button>
          </div>
        `;
        const extractBtn = document.getElementById('v2TriggerAiExtractBtn');
        if (extractBtn) {
          extractBtn.onclick = async () => {
            extractBtn.disabled = true;
            extractBtn.innerHTML = '⏳ Extracting...';
            try {
              const extRes = await vexoraFetch(`/documents/${encodeURIComponent(docId)}/ai-extract`, { method: 'POST' });
              const extData = await extRes.json();
              if (extData.success) {
                if (typeof window.showToast === 'function') {
                  window.showToast('AI field extraction completed and verified.', 'success');
                }
                window.v2RenderAiExtractedFields(docId);
              } else {
                if (typeof window.showToast === 'function') {
                  window.showToast(extData.message || 'AI extraction failed', 'warning');
                }
                const hint = document.getElementById('v2AiFieldsContent');
                if (hint && !hint.querySelector('.v2-llm-hint')) {
                  hint.insertAdjacentHTML('beforeend', '<div class="v2-llm-hint" style="margin-top:6px;font-size:0.75rem;color:#f59e0b;">' + escapeHtml(extData.message || extData.error || 'AI extraction failed') + ' (Set ENABLE_LLM=true and VEXORA_LLM_API_KEY in .env, then restart the backend.)</div>');
                }
                extractBtn.disabled = false;
                extractBtn.innerHTML = '⚡ Extract with AI';
              }
            } catch (e) {
              extractBtn.disabled = false;
              extractBtn.innerHTML = '⚡ Extract with AI';
            }
          };
        }
        return;
      }

      const rawFields = typeof fieldInsight.data === 'string' ? JSON.parse(fieldInsight.data) : fieldInsight.data;
      const rows = [];

      // Scalar fields
      if (rawFields.vendor) {
        rows.push({
          field: 'Vendor / Issuer',
          val: rawFields.vendor.value || '—',
          conf: rawFields.vendor.confidence !== undefined ? Math.round(rawFields.vendor.confidence * 100) + '%' : '—',
          quote: rawFields.vendor.source_quote || '—'
        });
      }
      if (rawFields.invoice_number) {
        rows.push({
          field: 'Invoice / Ref Number',
          val: rawFields.invoice_number.value || '—',
          conf: rawFields.invoice_number.confidence !== undefined ? Math.round(rawFields.invoice_number.confidence * 100) + '%' : '—',
          quote: rawFields.invoice_number.source_quote || '—'
        });
      }
      if (rawFields.subtotal) {
        rows.push({
          field: 'Subtotal Amount',
          val: rawFields.subtotal.value || '—',
          conf: rawFields.subtotal.confidence !== undefined ? Math.round(rawFields.subtotal.confidence * 100) + '%' : '—',
          quote: rawFields.subtotal.source_quote || '—'
        });
      }
      if (rawFields.tax) {
        rows.push({
          field: 'Tax / VAT Amount',
          val: rawFields.tax.value || '—',
          conf: rawFields.tax.confidence !== undefined ? Math.round(rawFields.tax.confidence * 100) + '%' : '—',
          quote: rawFields.tax.source_quote || '—'
        });
      }
      if (rawFields.total) {
        rows.push({
          field: 'Total Amount Due',
          val: rawFields.total.value || '—',
          conf: rawFields.total.confidence !== undefined ? Math.round(rawFields.total.confidence * 100) + '%' : '—',
          quote: rawFields.total.source_quote || '—'
        });
      }

      // Dates list
      if (Array.isArray(rawFields.dates)) {
        rawFields.dates.forEach(d => {
          rows.push({
            field: `Date (${escapeHtml(d.field || 'Transaction')})`,
            val: d.value || '—',
            conf: d.confidence !== undefined ? Math.round(d.confidence * 100) + '%' : '—',
            quote: d.source_quote || '—'
          });
        });
      }

      // Line items
      if (Array.isArray(rawFields.line_items)) {
        rawFields.line_items.forEach((item, idx) => {
          rows.push({
            field: `Line Item ${idx + 1}`,
            val: `${item.description || 'Item'} (Qty: ${item.quantity || 1}, Total: ${item.total || '—'})`,
            conf: item.confidence !== undefined ? Math.round(item.confidence * 100) + '%' : '—',
            quote: item.source_quote || '—'
          });
        });
      }

      // Parties
      if (Array.isArray(rawFields.parties)) {
        rawFields.parties.forEach(p => {
          rows.push({
            field: `Party (${escapeHtml(p.role || 'Entity')})`,
            val: p.name || '—',
            conf: p.confidence !== undefined ? Math.round(p.confidence * 100) + '%' : '—',
            quote: p.source_quote || '—'
          });
        });
      }

      if (rows.length === 0) {
        contentEl.innerHTML = '<span style="color:var(--text-muted);">No verified fields stored for this document.</span>';
        return;
      }

      let tableHtml = `
        <table style="width:100%; border-collapse:collapse; font-size:0.8rem; margin-top:6px;">
          <thead>
            <tr style="border-bottom:1px solid rgba(255,255,255,0.08); text-align:left; color:var(--text-secondary);">
              <th style="padding:6px 8px; width:22%;">Field</th>
              <th style="padding:6px 8px; width:30%;">Extracted Value</th>
              <th style="padding:6px 8px; width:12%;">Confidence</th>
              <th style="padding:6px 8px; width:36%;">Verified Source Quote</th>
            </tr>
          </thead>
          <tbody>
      `;

      rows.forEach(r => {
        tableHtml += `
          <tr style="border-bottom:1px solid rgba(255,255,255,0.04);">
            <td style="padding:6px 8px; font-weight:600; color:var(--text-primary);">${escapeHtml(r.field)}</td>
            <td style="padding:6px 8px; color:var(--accent-primary, #38bdf8);">${escapeHtml(r.val)}</td>
            <td style="padding:6px 8px; color:var(--text-muted);">${escapeHtml(r.conf)}</td>
            <td style="padding:6px 8px; font-family:var(--font-mono, monospace); font-size:0.75rem; color:#94a3b8;">"${escapeHtml(r.quote)}"</td>
          </tr>
        `;
      });

      tableHtml += `</tbody></table>`;
      contentEl.innerHTML = tableHtml;

    } catch (err) {
      console.warn('[V2 AI Insights Fetch Error]', err);
      const errEl = document.getElementById('v2AiFieldsContent');
      if (errEl) {
        errEl.textContent = (err && err.message === 'BACKEND_UNREACHABLE')
          ? '⚠ Backend not reachable — AI insights unavailable. Start the Flask server and click Retry in the red banner.'
          : 'Could not load AI insights for this document.';
      }
    }
  };

  // =========================================================================
  // Phase J: Dynamic Forensic Document Viewer & Extraction Mode
  // =========================================================================
  let _viewerCurrentDocId = null;
  let _viewerCurrentPage = 1;
  let _viewerTotalPages = 1;
  let _viewerZoom = 1.0;
  let _viewerShowText = false;
  let _viewerCachedDoc = null;

  window.v2RenderDynamicForensicViewer = async function(docId) {
    if (!docId) {
      const sel = document.getElementById('forensicDocSelector');
      docId = sel ? sel.value : null;
    }
    if (!docId) return;

    _viewerCurrentDocId = docId;
    _viewerCurrentPage = 1;
    _viewerZoom = 1.0;
    _viewerShowText = false;

    const titleHeader = document.getElementById('forensicDocTitleHeader');
    const modeBadge = document.getElementById('forensicExtractionModeBadge');
    const countBadge = document.getElementById('forensicFindingsCountBadge');
    const downloadBtn = document.getElementById('forensicDownloadBtn');
    const loadingEl = document.getElementById('forensicViewerLoading');
    const imgEl = document.getElementById('forensicPageOverlayImg');
    const textWrap = document.getElementById('forensicTextTranscriptWrap');

    if (loadingEl) {
      loadingEl.style.display = 'block';
      loadingEl.innerHTML = '<div style="font-size:1.6rem; margin-bottom:8px;">⏳</div> Loading document overlay...';
    }
    if (imgEl) imgEl.style.display = 'none';
    if (textWrap) textWrap.style.display = 'none';

    try {
      const res = await vexoraFetch(`/documents/${encodeURIComponent(docId)}`);
      const resData = await res.json();
      if (!res.ok || !resData.success) {
        if (loadingEl) {
          loadingEl.innerHTML = `<div style="color:var(--status-danger);">⚠️ ${escapeHtml(resData.error || 'Failed to load document')}</div>`;
        }
        return;
      }

      const doc = resData.data;
      _viewerCachedDoc = doc;
      _viewerTotalPages = Math.max(1, doc.page_count || 1);

      if (titleHeader) {
        titleHeader.textContent = `📄 ${doc.filename || doc.id}`;
      }

      // Extraction Mode Badge
      let modeText = '📄 Native Digital';
      let modeClass = 'pill-low';
      const extMode = (doc.extraction_mode || '').toLowerCase();
      const fileType = (doc.file_type || '').toLowerCase();

      if (extMode === 'hybrid_pdf' || extMode.includes('hybrid')) {
        modeText = '⚡ Hybrid OCR (Native + Scanned)';
        modeClass = 'pill-medium';
      } else if (extMode === 'ocr_fallback' || extMode.includes('ocr') || extMode === 'scanned_image') {
        modeText = '📷 Scanned OCR (Tesseract Engine)';
        modeClass = 'pill-medium';
      } else if (fileType === 'pdf') {
        modeText = '📄 Native Digital (Vector Text)';
        modeClass = 'pill-low';
      } else if (['png', 'jpg', 'jpeg', 'tif', 'tiff', 'bmp'].includes(fileType)) {
        modeText = '🖼️ Raster Image Analysis';
        modeClass = 'pill-low';
      }

      if (modeBadge) {
        modeBadge.textContent = modeText;
        modeBadge.className = `pill-tag ${modeClass}`;
      }

      if (countBadge) {
        const count = (doc.findings || []).length;
        countBadge.textContent = `${count} Anomal${count === 1 ? 'y' : 'ies'}`;
        countBadge.className = 'pill-tag ' + (count > 0 ? 'pill-high' : 'pill-low');
      }

      if (downloadBtn) {
        const _apiBase = (typeof getApiBase === "function") ? getApiBase() : ((typeof window.getApiBase === "function") ? window.getApiBase() : "/api");
        downloadBtn.href = `${_apiBase}/documents/${encodeURIComponent(docId)}/download`;
      }

      _setupViewerControls();
      _updateViewerPage();

    } catch (err) {
      console.warn('[Viewer Load Error]', err);
      if (loadingEl) {
        loadingEl.innerHTML = `<div style="color:var(--status-danger);">⚠️ Failed to connect to document service.</div>`;
      }
    }
  };

  function _setupViewerControls() {
    const prevBtn = document.getElementById('forensicPrevPageBtn');
    const nextBtn = document.getElementById('forensicNextPageBtn');
    const zoomInBtn = document.getElementById('forensicZoomInBtn');
    const zoomOutBtn = document.getElementById('forensicZoomOutBtn');
    const toggleTextBtn = document.getElementById('forensicToggleTextBtn');

    if (prevBtn) {
      prevBtn.onclick = () => {
        if (_viewerCurrentPage > 1) {
          _viewerCurrentPage--;
          _updateViewerPage();
        }
      };
    }
    if (nextBtn) {
      nextBtn.onclick = () => {
        if (_viewerCurrentPage < _viewerTotalPages) {
          _viewerCurrentPage++;
          _updateViewerPage();
        }
      };
    }
    if (zoomInBtn) {
      zoomInBtn.onclick = () => {
        _viewerZoom = Math.min(_viewerZoom + 0.25, 3.0);
        _applyViewerZoom();
      };
    }
    if (zoomOutBtn) {
      zoomOutBtn.onclick = () => {
        _viewerZoom = Math.max(_viewerZoom - 0.25, 0.5);
        _applyViewerZoom();
      };
    }
    if (toggleTextBtn) {
      toggleTextBtn.onclick = () => {
        _viewerShowText = !_viewerShowText;
        toggleTextBtn.textContent = _viewerShowText ? '🖼️ Visual' : '🔤 Text';
        _updateViewerPage();
      };
    }
  }

  function _applyViewerZoom() {
    const imgEl = document.getElementById('forensicPageOverlayImg');
    const zoomText = document.getElementById('forensicZoomText');
    if (imgEl) {
      imgEl.style.transform = `scale(${_viewerZoom})`;
    }
    if (zoomText) {
      zoomText.textContent = `${Math.round(_viewerZoom * 100)}%`;
    }
  }

  function _updateViewerPage() {
    const pageIndicator = document.getElementById('forensicPageIndicator');
    const loadingEl = document.getElementById('forensicViewerLoading');
    const imgEl = document.getElementById('forensicPageOverlayImg');
    const textWrap = document.getElementById('forensicTextTranscriptWrap');

    if (pageIndicator) {
      pageIndicator.textContent = `Page ${_viewerCurrentPage} of ${_viewerTotalPages}`;
    }

    if (_viewerShowText) {
      if (imgEl) imgEl.style.display = 'none';
      if (loadingEl) loadingEl.style.display = 'none';
      if (textWrap) {
        textWrap.style.display = 'block';
        const txt = (_viewerCachedDoc && (_viewerCachedDoc.extracted_text || 'No text extracted for this document.')) || '';
        textWrap.textContent = txt;
      }
      return;
    }

    if (textWrap) textWrap.style.display = 'none';
    if (loadingEl) {
      loadingEl.style.display = 'block';
      loadingEl.innerHTML = '<div style="font-size:1.4rem; margin-bottom:6px;">🔍</div> Rendering page overlay...';
    }
    if (imgEl) imgEl.style.display = 'none';

    const _apiBase = (typeof getApiBase === "function") ? getApiBase() : ((typeof window.getApiBase === "function") ? window.getApiBase() : "/api");
    const overlayUrl = `${_apiBase}/documents/${encodeURIComponent(_viewerCurrentDocId)}/pages/${_viewerCurrentPage}/overlay?zoom=2.0&t=${Date.now()}`;

    const tempImg = new Image();
    tempImg.onload = function() {
      if (loadingEl) loadingEl.style.display = 'none';
      if (imgEl) {
        imgEl.src = overlayUrl;
        imgEl.style.display = 'block';
        _applyViewerZoom();
      }
    };
    tempImg.onerror = function() {
      if (loadingEl) {
        loadingEl.innerHTML = `
          <div style="color:var(--text-muted); padding:20px; font-size:0.85rem;">
            <div style="font-size:1.5rem; margin-bottom:6px;">📄</div>
            Document page preview unavailable for this format.
          </div>
        `;
        loadingEl.style.display = 'block';
      }
    };
    tempImg.src = overlayUrl;
  }

  // =========================================================================
  // Phase K: Cross-Document Chronological Timeline & Sequence Anomalies
  // =========================================================================
  window.v2ReloadCaseTimeline = function() {
    const sel = document.getElementById('relGraphCaseSelect');
    const caseId = sel ? sel.value : null;
    window.v2LoadCaseTimeline(caseId);
  };

  window.v2LoadCaseTimeline = async function(caseId) {
    if (!caseId) {
      const sel = document.getElementById('relGraphCaseSelect');
      caseId = sel ? sel.value : null;
    }
    if (!caseId) return;

    const statsBadge = document.getElementById('timelineStatsBadge');
    const bannerEl = document.getElementById('timelineAnomalyBanner');
    const feedEl = document.getElementById('caseTimelineFeed');

    if (feedEl) {
      feedEl.innerHTML = '<div style="text-align:center; padding:30px; color:var(--text-muted); font-size:0.85rem;"><div style="font-size:1.5rem; margin-bottom:8px;">⏳</div> Synthesizing cross-document chronological event timeline...</div>';
    }
    if (bannerEl) bannerEl.style.display = 'none';

    try {
      const res = await vexoraFetch(`/cases/${encodeURIComponent(caseId)}/timeline`);
      const data = await res.json();
      if (!res.ok || !data.success) {
        if (feedEl) feedEl.innerHTML = `<div style="text-align:center; padding:20px; color:var(--status-danger); font-size:0.85rem;">⚠️ ${escapeHtml(data.error || 'Failed to load timeline')}</div>`;
        return;
      }

      const events = data.events || [];
      const anomalies = data.anomalies || [];

      if (statsBadge) {
        statsBadge.textContent = `${events.length} Event${events.length === 1 ? '' : 's'} Synthesized`;
        statsBadge.className = 'pill-tag ' + (anomalies.length > 0 ? 'pill-high' : 'pill-low');
      }

      // Render Temporal Sequence Anomalies Banner
      if (anomalies.length > 0 && bannerEl) {
        let anomalyHtml = `
          <div class="v2-anomaly-summary-banner">
            <div style="display:flex; align-items:center; gap:8px; margin-bottom:6px;">
              <span style="font-size:1.1rem;">⚠️</span>
              <strong style="color:#ef4444; font-size:0.9rem;">Temporal Sequence Anomalies Detected (${anomalies.length})</strong>
              <span class="pill-tag pill-high" style="font-size:0.7rem;">Chronological Conflict</span>
            </div>
            <p style="margin:0 0 10px 0; font-size:0.82rem; color:var(--text-secondary); line-height:1.45;">
              Automated business workflow correlation detected out-of-order document issuance or settlements that contradict standard commercial sequencing:
            </p>
        `;
        anomalies.forEach((a) => {
          anomalyHtml += `
            <div style="background:rgba(239,68,68,0.1); border-left:3px solid #ef4444; padding:8px 12px; border-radius:4px; margin-bottom:6px; font-size:0.8rem;">
              <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                <strong style="color:#fca5a5;">[${escapeHtml(a.rule_id || 'RULE-TIME')}] ${escapeHtml(a.type || 'Temporal Conflict')}</strong>
                <span class="pill-tag pill-high" style="font-size:0.68rem;">${escapeHtml(a.severity || 'Critical')}</span>
              </div>
              <div style="color:var(--text-primary); margin-bottom:4px;">${escapeHtml(a.description)}</div>
              <div style="font-size:0.75rem; color:#94a3b8; font-style:italic;">
                ℹ️ Recommendation: Verify bank clearing logs and formal contract authorization before confirming intentional alteration.
              </div>
            </div>
          `;
        });
        anomalyHtml += `</div>`;
        bannerEl.innerHTML = anomalyHtml;
        bannerEl.style.display = 'block';
      } else if (bannerEl) {
        bannerEl.style.display = 'none';
      }

      // Render Chronological Timeline Feed
      if (events.length === 0) {
        if (feedEl) {
          feedEl.innerHTML = `
            <div style="text-align:center; padding:30px; color:var(--text-muted); font-size:0.85rem;">
              <div style="font-size:1.6rem; margin-bottom:8px;">📅</div>
              No dated events extracted from documents in this case. Ingest invoices, purchase orders, or bank statements with transaction dates.
            </div>
          `;
        }
        return;
      }

      const anomalyDocNames = new Set();
      anomalies.forEach(a => {
        if (a.event_earlier && a.event_earlier.document_filename) anomalyDocNames.add(a.event_earlier.document_filename);
        if (a.event_later && a.event_later.document_filename) anomalyDocNames.add(a.event_later.document_filename);
      });

      let feedHtml = '';
      events.forEach((ev) => {
        const isAnomaly = anomalyDocNames.has(ev.document_filename);
        const itemClass = isAnomaly ? 'v2-timeline-item has-anomaly' : 'v2-timeline-item';

        let typeIcon = '📄';
        const docType = (ev.doc_type || '').toLowerCase();
        if (docType.includes('po') || docType.includes('order')) typeIcon = '🛒';
        else if (docType.includes('invoice')) typeIcon = '🧾';
        else if (docType.includes('bank') || docType.includes('payment')) typeIcon = '🏦';
        else if (docType.includes('contract')) typeIcon = '📜';
        else if (docType.includes('ship') || docType.includes('delivery')) typeIcon = '🚚';

        feedHtml += `
          <div class="${itemClass}">
            <div class="v2-timeline-header">
              <div style="display:flex; align-items:center; gap:8px;">
                <span class="v2-timeline-date">${escapeHtml(ev.date || 'Undated')}</span>
                <span class="v2-timeline-type" style="color:var(--text-muted);">${typeIcon} ${escapeHtml(ev.doc_type || 'Event')}</span>
              </div>
              <div>
                ${isAnomaly ? '<span class="pill-tag pill-high" style="font-size:0.68rem; margin-right:6px;">Sequence Conflict</span>' : ''}
                <span style="font-family:var(--font-mono); font-size:0.75rem; color:var(--text-muted);">${escapeHtml(ev.document_filename || ev.document_id || '')}</span>
              </div>
            </div>
            <div class="v2-timeline-body">
              <strong>${escapeHtml(ev.description || 'Transaction recorded')}</strong>
            </div>
            <div class="v2-timeline-meta">
              ${ev.amount ? `<span>Amount: <strong>${escapeHtml(String(ev.amount))}</strong></span>` : ''}
              ${ev.counterparty ? `<span>Counterparty: <strong>${escapeHtml(ev.counterparty)}</strong></span>` : ''}
            </div>
          </div>
        `;
      });

      if (feedEl) feedEl.innerHTML = feedHtml;

    } catch (err) {
      console.warn('[Timeline Load Error]', err);
      if (feedEl) {
        feedEl.innerHTML = `<div style="text-align:center; padding:20px; color:var(--status-danger); font-size:0.85rem;">⚠️ Error connecting to timeline synthesis endpoint.</div>`;
      }
    }
  };

  // Pre-initialize on load
  function setupGraphAndForensicSelectors() {
    const select = document.getElementById('relGraphCaseSelect');
    if (select && select.value) {
      window.v2LoadRelationshipGraph(select.value);
      if (typeof window.v2LoadCaseTimeline === 'function') {
        window.v2LoadCaseTimeline(select.value);
      }
    }
    const forensicSelect = document.getElementById('forensicDocSelector');
    if (forensicSelect) {
      forensicSelect.addEventListener('change', (e) => {
        if (e.target.value) {
          window.v2RenderAiExtractedFields(e.target.value);
          if (typeof window.v2RenderDynamicForensicViewer === 'function') {
            window.v2RenderDynamicForensicViewer(e.target.value);
          }
        }
      });
      if (forensicSelect.value) {
        window.v2RenderAiExtractedFields(forensicSelect.value);
        if (typeof window.v2RenderDynamicForensicViewer === 'function') {
          window.v2RenderDynamicForensicViewer(forensicSelect.value);
        }
      }
    }
  }

  function initAllV2() {
    ensureEvidenceModal();
    window.v2SetupAiTestButton();

    if (window.__vexoraDataReady) {
      setupGraphAndForensicSelectors();
    } else {
      document.addEventListener('vexora:data-ready', () => {
        setupGraphAndForensicSelectors();
      }, { once: true });
    }

    const navSettings = document.getElementById('navSettings');
    if (navSettings) {
      navSettings.addEventListener('click', () => {
        setTimeout(window.v2SetupAiTestButton, 150);
      });
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAllV2);
  } else {
    initAllV2();
  }

})();
