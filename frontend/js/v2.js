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
        fetch(`/api/findings/${encodeURIComponent(finding.id)}/explain`, {
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

    fetch(`/api/cases/${encodeURIComponent(caseId)}/relationships`)
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
              Failed to load relationship graph: ${escapeHtml(err.message || 'Unknown network error')}
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

  // Pre-initialize on load
  function initAllV2() {
    ensureEvidenceModal();
    const select = document.getElementById('relGraphCaseSelect');
    if (select) {
      window.v2LoadRelationshipGraph(select.value || 'CAS-2026-0891');
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAllV2);
  } else {
    initAllV2();
  }

})();
