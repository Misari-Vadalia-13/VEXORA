"""
VEXORA — Forensic Evidence Classification Layer (Phase B)
Classifies forensic findings into three standardized, objective categories:
1. "Observation": A measured fact or structural property (e.g., multiple fonts present)
2. "Inconsistency": Two contradictory facts or conflicting attributes
3. "Potential Manipulation": An anomaly pattern commonly seen after document alteration

Complies with hackathon integrity guidelines: never asserts "confirmed fraud".
"""

# Official Rule ID to Evidence Classification Mapping
RULE_EVIDENCE_CLASS_MAP = {
    # Baseline Visual Rules
    'RULE-VIS-001': 'Observation',            # Discrepant Font Family Detected (two fonts present)
    'RULE-VIS-002': 'Potential Manipulation', # Overlapping Text Elements Detected (overwritten numbers)
    'RULE-VIS-003': 'Observation',            # Out-of-Bounds Text Placement
    'RULE-VIS-004': 'Observation',            # Irregular Line Spacing Disparity
    'RULE-VIS-005': 'Observation',            # Degraded Resolution or Compression Artifact

    # Baseline Contextual Rules
    'RULE-CTX-001': 'Inconsistency',          # Missing Mandatory Document Field
    'RULE-CTX-002': 'Inconsistency',          # Multiple Conflicting Document Identifiers
    'RULE-CTX-003': 'Inconsistency',          # Chronological Sequence Inconsistency
    'RULE-CTX-004': 'Inconsistency',          # Conflicting Monetary Values or Currencies
    'RULE-CTX-005': 'Inconsistency',          # Metadata Timestamp Mismatch

    # Phase B: Deeper PDF Forensic Rules
    'PDF-001': 'Potential Manipulation',      # Text Hidden Under Opaque / White Filled Shape
    'PDF-002': 'Observation',                 # Incremental Updates / Multiple Revisions
    'PDF-003': 'Inconsistency',               # Metadata Revision Desynchronization
    'PDF-004': 'Potential Manipulation',      # Embedded Image Placed Over Text / Resolution Disparity
    'PDF-005': 'Potential Manipulation',      # Invisible or Fully Off-Page Text

    # Fallback Generic Rules
    'RULE-GEN-001': 'Observation'
}

DEFAULT_EVIDENCE_CLASS = 'Observation'
VALID_EVIDENCE_CLASSES = {'Observation', 'Inconsistency', 'Potential Manipulation'}


def get_evidence_class(rule_id, existing_class=None):
    """
    Returns the objective evidence classification for a given rule ID.
    If an existing valid class is provided, preserves it.
    Falls back to the mapping table, or DEFAULT_EVIDENCE_CLASS ('Observation').
    """
    if existing_class and isinstance(existing_class, str) and existing_class.strip() in VALID_EVIDENCE_CLASSES:
        return existing_class.strip()

    if not rule_id or not isinstance(rule_id, str):
        return DEFAULT_EVIDENCE_CLASS

    clean_id = rule_id.strip()
    return RULE_EVIDENCE_CLASS_MAP.get(clean_id, DEFAULT_EVIDENCE_CLASS)


def classify_finding(finding):
    """
    Annotates a finding dictionary with its official evidence_class label.
    Safe for both existing finding objects and new findings.
    """
    if not isinstance(finding, dict):
        return finding

    rule_id = finding.get('rule_id')
    current_class = finding.get('evidence_class')
    finding['evidence_class'] = get_evidence_class(rule_id, current_class)
    return finding
