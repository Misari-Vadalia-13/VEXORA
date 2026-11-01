# VEXORA — Complete Development Roadmap

**Project:** VEXORA – AI-Powered Document Forensics and Contextual Intelligence System  
**Development Approach:** Beginner-friendly, phase-by-phase development  
**Developer:** B.Tech CSE Student  
**Primary Goal:** Build a functional project while understanding its implementation.

----

# 1. Project Development Instructions

You are developing VEXORA with me. Act as both a software developer and a technical mentor.

I am a beginner in several technologies used in this project. Therefore, your responsibility is not just to generate code but also to help me understand how the application works.

## Mandatory Development Rules

1. Work on only ONE development phase at a time.
2. Never start the next phase without completing the current phase report.
3. Inspect existing project files before making changes.
4. Preserve existing functionality and project structure wherever possible.
5. Do not introduce unnecessary advanced technologies.
6. Explain important code, functions, classes, routes and database operations.
7. Clearly distinguish implemented features from simulated or placeholder features.
8. Never claim that a feature works unless it has been tested.
9. Never invent testing results, evidence or accuracy measurements.
10. Keep the implementation beginner-friendly and maintainable.
11. Update `VEXORA_DEVELOPMENT_LOG.md` after every phase.
12. Wait for my explicit approval before moving to the next phase.

## Standard Development Cycle

For every phase, follow this sequence:

1. Understand the requirements.
2. Inspect the existing project.
3. Explain the planned implementation.
4. Implement the required functionality.
5. Test the implementation.
6. Fix errors.
7. Generate the mandatory Phase Completion Report.
8. Update the development log.
9. Suggest a GitHub commit message.
10. Wait for my approval.

---

# 2. Technology Stack

Use this beginner-friendly technology stack.

| Technology | Purpose |
|---|---|
| HTML5 | Creates webpage structure. |
| CSS3 | Controls appearance, layout and responsiveness. |
| JavaScript | Adds interactive functionality. |
| Python | Handles document processing and analysis. |
| Flask | Connects the frontend with Python backend logic. |
| SQLite | Stores users, cases, documents and findings. |
| PyMuPDF | Extracts text and information from PDFs. |
| Tesseract OCR | Recognizes text from scanned documents and images. |
| spaCy | Identifies entities such as names, dates and organizations. |
| Git & GitHub | Tracks and manages project development. |

Do not add React, Node.js, MongoDB, Docker or other advanced technologies unless a genuine requirement arises and I approve the change.

---

# 3. Complete Development Roadmap

## PHASE 1 — Project Setup & UI Foundation

**Area:** Frontend Foundation

**Objective:** Establish the project structure and create the basic application interface.

### Work Involved

- Set up the VEXORA project and folder structure.
- Establish the color palette, typography and design system.
- Develop the sidebar and navigation.
- Create the main dashboard layout.
- Make the interface responsive.
- Add reusable CSS styles and basic JavaScript interactions.

**Technologies:** HTML5, CSS3, JavaScript.

**Expected Outcome:** A complete, navigable frontend with a consistent design.

### Phase Verification

- Check the project structure.
- Run the application.
- Test navigation.
- Check responsive layouts.
- Check browser-console errors.

---

## PHASE 2 — Core Pages & User Interface

**Area:** Frontend Development

**Objective:** Build all essential screens users will interact with.

### Work Involved

- Dashboard and overview.
- Investigation case management.
- Document upload interface.
- Document library.
- Analysis results page.
- Evidence and findings page.
- Investigation report page.
- User settings.

Connect the pages through navigation and implement appropriate buttons, forms and interactive elements.

**Technologies:** HTML5, CSS3, JavaScript.

**Expected Outcome:** All major screens designed and connected through navigation.

### Phase Verification

- Visit every page.
- Test buttons and navigation.
- Check form interactions.
- Verify responsive layouts.
- Identify any placeholder functionality.

---

## PHASE 3 — Backend & Database Integration

**Area:** Backend Development

**Objective:** Make VEXORA function beyond its visual interface.

### Work Involved

- Set up Python and Flask.
- Connect frontend pages with backend routes.
- Create the SQLite database.
- Create tables for users, cases, documents and findings.
- Implement basic authentication if included in the approved scope.
- Store and retrieve investigation records.
- Implement basic input validation.

**Technologies:** Python, Flask, SQLite.

**Expected Outcome:** A working application that can store and retrieve information.

### Phase Verification

- Start the Flask application.
- Test backend routes.
- Test database operations.
- Verify that information persists after restarting the application.
- Check error handling.

---

## PHASE 4 — Document Upload & Classification

**Area:** Document Ingestion

**Objective:** Allow users to submit documents for investigation.

### Work Involved

- Upload PDF, JPG and PNG files.
- Support multiple documents within one investigation.
- Validate file types and sizes.
- Assign unique document IDs.
- Store original documents.
- Implement basic document categorization.
- Maintain document source information.
- Associate documents with their investigation cases.

**Technologies:** Python, Flask, SQLite.

**Expected Outcome:** Users can upload and manage multiple investigation documents.

### Phase Verification

- Upload different supported file types.
- Test multiple uploads.
- Test unsupported file types.
- Test oversized files.
- Verify file storage and database records.
- Check duplicate filenames and upload errors.

---

## PHASE 5 — OCR & Information Extraction

**Area:** Document Processing

**Objective:** Extract useful information from uploaded documents.

### Work Involved

- Extract existing text from digital PDFs.
- Apply OCR to scanned PDFs and images.
- Identify names, dates and organizations.
- Extract page-wise information.
- Organize extracted information into structured formats.
- Preserve references to original document pages.
- Handle extraction failures.

**Technologies:** Python, PyMuPDF, Tesseract OCR, spaCy.

**Expected Outcome:** Extracted document information displayed in an organized format.

### Phase Verification

- Test a digital PDF.
- Test a scanned PDF.
- Test an image.
- Compare extracted text with the original.
- Verify page references.
- Test unreadable documents.

---

## PHASE 6 — Forensic & Contextual Analysis

**Area:** Core Intelligence Module

**Objective:** Identify suspicious characteristics and inconsistencies that require investigation.

### A. Visual and Structural Analysis

- Examine available font information.
- Identify unusual font differences.
- Examine spacing and alignment.
- Detect potentially unusual text placement.
- Record relevant pages and observations.

### B. Contextual Verification

- Identify missing information.
- Detect duplicated information.
- Check inconsistent dates and values.
- Compare related information within documents.
- Explain which rules triggered each observation.

**Technologies:** Python, PyMuPDF, spaCy.

**Expected Outcome:** A list of potential anomalies with explanations and supporting observations.

### Important Requirements

- A formatting difference does not prove document alteration.
- Metadata is not guaranteed to be reliable.
- Not every inconsistency represents fraud.
- Do not claim advanced image tampering detection unless implemented and tested.
- Use labels such as Potential Anomaly and Needs Review.
- Never automatically declare a document fraudulent.

### Phase Verification

- Test documents with known formatting differences.
- Test deliberately inconsistent information.
- Verify explanations for each finding.
- Check source document and page references.
- Identify false positives and limitations.

---

## PHASE 7 — Cross-Document Comparison & Evidence Mapping

**Area:** Investigation Intelligence

**Objective:** Compare multiple documents and connect identified findings with their original evidence.

### Work Involved

- Compare information across uploaded documents.
- Identify mismatched names, dates and values.
- Find conflicting and duplicate records.
- Connect findings to their respective documents.
- Display relevant source pages.
- Highlight suspicious text or regions when reliable coordinates are available.
- Provide explanations for identified discrepancies.

**Technologies:** Python, spaCy, PyMuPDF, JavaScript.

**Expected Outcome:** An investigation view showing discrepancies and their supporting document evidence.

### Phase Verification

- Compare two or more documents.
- Test matching information.
- Test conflicting information.
- Verify document IDs and page references.
- Verify text highlighting.
- Check that comparison results are understandable.

---

## PHASE 8 — Investigation Dossier & Report Generation

**Area:** Report Generation

**Objective:** Generate a structured investigation report from the analysis.

### Work Involved

- Generate document overview.
- Include extracted information.
- Display contextual inconsistencies.
- Include visual forensic observations.
- Add cross-document discrepancies.
- Include supporting evidence and page references.
- Display explanations for findings.
- Represent confidence only when a defined scoring method exists.
- Allow report export as PDF.
- Include a human-review disclaimer.

**Technologies:** Python, Flask, HTML, CSS, JavaScript and an appropriate PDF-generation library.

**Expected Outcome:** A downloadable investigation dossier.

### Phase Verification

- Generate a report for an investigation.
- Verify all included findings.
- Check document and page references.
- Open and inspect the PDF.
- Test empty investigations.
- Test report-generation errors.

---

## PHASE 9 — Audit Trail, Testing & Finalization

**Area:** Quality Assurance

**Objective:** Ensure the system works correctly and records investigation activities.

### Work Involved

- Maintain document upload history.
- Record processing activities.
- Store analysis findings and associated evidence.
- Record important investigation activities.
- Test all major functionalities.
- Fix frontend and backend errors.
- Test multiple document uploads.
- Check database accuracy.
- Review upload and authentication security.
- Prepare the final demonstration.
- Complete GitHub documentation.

**Technologies:** Python, Flask, SQLite, HTML, CSS, JavaScript, Git and GitHub.

**Expected Outcome:** A tested and demonstrable VEXORA prototype.

### Phase Verification

- Run the application from a clean setup.
- Test the complete investigation workflow.
- Verify database consistency.
- Test invalid inputs.
- Verify activity history.
- Document remaining limitations.
- Prepare a final demonstration.

---

# 4. Mandatory Phase Completion Report

After completing EVERY phase, you MUST generate a report using the following structure.

Do not start another phase until I have reviewed and approved the report.

## VEXORA — Phase Completion Report

**Phase Number:**  
**Phase Title:**  
**Completion Date:**  
**Overall Status:** Completed / Partially Completed / Blocked

### 1. What Was Done?

- List all features implemented.
- Explain what was successfully completed.
- Mention incomplete functionality.

### 2. How Was It Done?

- Explain the implementation process in simple language.
- Describe the working logic.
- Explain how the frontend, backend and database interact.
- Provide simple examples wherever useful.

### 3. Why Was It Done?

- Explain the purpose of each feature.
- Explain why the selected technology was used.
- Describe how the feature contributes to VEXORA.

### 4. Technologies Explained

For every technology, library or framework introduced, explain:

- What it is.
- What it does.
- Why we selected it.
- Where it is used in VEXORA.

### 5. Files and Code Changes

List the files created, modified or deleted.

For important files, explain:

- File name and location.
- Its responsibility.
- Important functions, classes and routes.
- How it connects to other files.

### 6. Testing and Verification

- Explain how to run the features.
- List tests actually performed.
- Provide actual test results.
- Identify errors and limitations.
- Never claim a test passed if it was not performed.

### 7. Learning Summary

Provide:

- Five important concepts learned.
- Important technical terms with simple definitions.
- Three possible viva questions with answers.
- Common mistakes to avoid.

### 8. Phase Status

Classify every planned feature as:

- Completed
- Partially Completed
- Not Completed
- Not Implemented

### 9. GitHub Commit Suggestion

Suggest a meaningful Git commit message describing the actual completed work.

### 10. Approval Gate

End the report by asking me to review and approve the phase.

**Never automatically proceed to the next phase.**

---

# 5. Mandatory Development Log

Maintain a file named:

`VEXORA_DEVELOPMENT_LOG.md`

Create it in the root directory if it does not exist.

Update it after every phase.

Use this structure:

## Project Overview

VEXORA — AI-Powered Document Forensics and Contextual Intelligence System.

## Phase Tracker

| Phase | Title | Status |
|---|---|---|
| 1 | Project Setup & UI Foundation | Not Started |
| 2 | Core Pages & User Interface | Not Started |
| 3 | Backend & Database Integration | Not Started |
| 4 | Document Upload & Classification | Not Started |
| 5 | OCR & Information Extraction | Not Started |
| 6 | Forensic & Contextual Analysis | Not Started |
| 7 | Cross-Document Comparison & Evidence Mapping | Not Started |
| 8 | Investigation Dossier & Report Generation | Not Started |
| 9 | Audit Trail, Testing & Finalization | Not Started |

For every phase, record:

- Completion date.
- Features implemented.
- Technologies introduced.
- Important technical decisions.
- Files created or modified.
- Actual testing results.
- Known limitations.
- Concepts learned.
- Suggested Git commit message.
- Approval status.

Never mark a phase complete until its required functionality has been implemented and verified.

---

# 6. Project-Wide Quality Requirements

## Beginner-Friendly Code

- Use understandable variable and function names.
- Keep functions focused.
- Avoid unnecessary complexity.
- Add comments where logic is difficult.
- Explain unfamiliar syntax.
- Organize files logically.

## Reliability and Security

- Validate inputs on the backend.
- Validate uploaded files.
- Use safe file-storage paths.
- Do not expose passwords or secret keys.
- Handle errors clearly.
- Protect existing investigation data.

## Evidence Traceability

- Preserve original uploaded documents.
- Maintain unique document identifiers.
- Preserve page references.
- Associate extracted text with its source.
- Explain why each anomaly was identified.
- Never invent evidence or source references.
- Treat automated findings as observations requiring human review.

## GitHub Documentation

Maintain an accurate README containing:

- Project overview.
- Implemented features.
- Technology stack.
- Folder structure.
- Installation instructions.
- Run instructions.
- Actual screenshots.
- Testing instructions.
- Known limitations.
- Future improvements.

---

# 7. Initial Instruction — Start Phase 1

When this document is read for the first time, follow these instructions:

### Step 1 — Inspect

Inspect the existing VEXORA repository.

Report:

1. Existing files and folders.
2. Existing implementation, if any.
3. Missing files or components.
4. Changes required for Phase 1.
5. Any risk of affecting existing functionality.

### Step 2 — Plan

Explain the Phase 1 implementation plan in beginner-friendly language.

### Step 3 — Implement

Implement Phase 1 only.

Do not start Phase 2.

### Step 4 — Test

Run the application and test the implemented functionality.

### Step 5 — Report

Generate the complete mandatory Phase Completion Report.

### Step 6 — Update Log

Create or update `VEXORA_DEVELOPMENT_LOG.md`.

### Step 7 — Wait

Stop and wait for my approval.

---

# 8. Final Project Goal

My goal is not simply to generate VEXORA using AI.

I want to understand how the complete application works so I can independently explain, demonstrate and defend it during my project evaluation and viva.

For example, when someone asks:

**"How does VEXORA identify inconsistencies between two documents?"**

I should be able to explain:

1. How documents are uploaded.
2. How Python processes the documents.
3. How PyMuPDF extracts PDF text.
4. How OCR works on scanned documents.
5. How spaCy identifies entities.
6. How the comparison logic works.
7. How discrepancies are identified.
8. How findings are linked to original evidence.
9. How the results are displayed.
10. How the investigation report is generated.

**Build the application with me, explain it to me, verify it honestly, and move forward one approved phase at a time.**

**START WITH PHASE 1 ONLY.**
