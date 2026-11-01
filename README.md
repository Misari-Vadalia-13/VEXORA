# VEXORA
### AI-Powered Document Forensics & Contextual Intelligence System

**Analyze. Investigate. Connect. Discover.**

VEXORA is an AI-powered document analysis and forensic investigation platform designed to help users examine digital documents, extract meaningful information, identify potential inconsistencies, and connect findings across multiple documents.

The system aims to combine document processing, OCR, entity extraction, contextual analysis, and evidence mapping into one centralized investigation workspace.

---

## 🎯 Project Overview

Investigating multiple documents manually can be time-consuming, especially when information is scattered across different files.

VEXORA aims to simplify this process by providing a structured environment where users can upload documents, extract information, examine potential anomalies, compare records, and generate investigation reports.

The platform focuses on making document analysis more organized, explainable, and traceable.

## ✨ Key Features

The following features represent the planned project scope. Their implementation status will be updated as development progresses.

| Feature | Description | Status |
|---|---|---|
| Investigation Dashboard | Centralized overview of investigation activities. | Completed (UI) |
| Case Management | Create and manage investigation cases. | Completed (UI) |
| Document Upload | Upload PDF, JPG and PNG documents. | Completed (UI) |
| Document Library | Organize and access uploaded documents. | Completed (UI) |
| OCR Processing | Extract text from scanned documents and images. | Planned (Phase 5) |
| Information Extraction | Identify names, dates and organizations. | Planned (Phase 5) |
| Document Analysis | Examine unusual formatting and contextual inconsistencies. | Completed (UI) |
| Cross-Document Comparison | Compare information across multiple documents. | Completed (UI) |
| Evidence Mapping | Connect findings to their original documents and pages. | Completed (UI) |
| Investigation Dossier | Generate structured investigation reports. | Completed (UI) |
| Audit Trail | Maintain records of important investigation activities. | Completed (UI) |

## ⚙️ Technology Stack

VEXORA uses a beginner-friendly technology stack.

### Frontend
- **HTML5** – Structures the application pages.
- **CSS3** – Handles styling, layouts and responsiveness.
- **JavaScript** – Provides interactive functionality.

### Backend
- **Python** – Implements document processing and analysis.
- **Flask** – Connects frontend requests with backend functionality.
- **SQLite** – Stores investigation records and application data.

### Document Processing & Analysis
- **PyMuPDF** – Extracts text and page information from PDF documents.
- **Tesseract OCR** – Recognizes text from scanned documents.
- **spaCy** – Identifies entities such as names, dates and organizations.

### Development Tools
- **Visual Studio Code / Antigravity** – Development environment.
- **Git & GitHub** – Version control and project management.

## 🔍 How VEXORA Works

The planned investigation workflow:

1. **Create an Investigation:** Start a new case and organize its details.
2. **Upload Documents:** Add PDF files and supported images.
3. **Extract Information:** Process documents using text extraction and OCR.
4. **Identify Entities:** Extract relevant names, dates and organizations.
5. **Analyze Documents:** Examine potential formatting and contextual inconsistencies.
6. **Compare Documents:** Identify matching, repeated and conflicting information.
7. **Map Evidence:** Connect findings with their original document pages.
8. **Generate Reports:** Create an investigation dossier containing findings and supporting evidence.

## 🗺️ Development Roadmap

VEXORA is being developed through nine structured phases.

| Phase | Development Area | Status |
|---|---|---|
| 01 | Project Setup & UI Foundation | **Completed** |
| 02 | Core Pages & User Interface | **Completed** |
| 03 | Backend & Database Integration | Not Started |
| 04 | Document Upload & Classification | Not Started |
| 05 | OCR & Information Extraction | Not Started |
| 06 | Forensic & Contextual Analysis | Not Started |
| 07 | Cross-Document Comparison & Evidence Mapping | Not Started |
| 08 | Investigation Dossier & Report Generation | Not Started |
| 09 | Audit Trail, Testing & Finalization | Not Started |

Each phase includes implementation, testing, documentation and a beginner-friendly learning report.

See [`VEXORA_DEVELOPMENT_ROADMAP.md`](VEXORA_DEVELOPMENT_ROADMAP.md) for the complete development instructions.

See [`VEXORA_DEVELOPMENT_LOG.md`](VEXORA_DEVELOPMENT_LOG.md) for phase progress and implementation records.

## 📁 Planned Project Structure

```text
VEXORA/
│
├── frontend/
│   ├── index.html
│   ├── pages/
│   ├── css/
│   ├── js/
│   └── assets/
│
├── backend/
│   ├── app.py
│   ├── routes/
│   ├── database/
│   ├── processing/
│   └── analysis/
│
├── uploads/
│
├── reports/
│
├── tests/
│
├── requirements.txt
├── README.md
├── VEXORA_DEVELOPMENT_ROADMAP.md
└── VEXORA_DEVELOPMENT_LOG.md
```

*Note: This is the proposed structure. The actual structure may evolve during implementation.*

## 🚀 Getting Started

VEXORA is currently in the development planning/setup stage. Installation and execution instructions will be added and verified as the corresponding phases are completed.

### Prerequisites

The planned development environment includes:

- Python 3
- Visual Studio Code or Antigravity
- Git
- A modern web browser

### Running Phase 1 (Frontend Foundation)

To run the application locally:

```bash
# Using Python built-in HTTP server:
py -m http.server 8080

# Then open in any web browser:
http://localhost:8080
```

### Future Setup (Phases 3-9)
Once the backend and dependencies are implemented, setup instructions will be provided here, including:
- Virtual environment creation.
- Dependency installation (`pip install -r requirements.txt`).
- Database initialization.
- Flask server execution.

## 🧪 Testing

Testing will cover:

- Frontend navigation and responsiveness.
- Backend routes and database operations.
- Document uploads and validation.
- PDF text extraction and OCR.
- Entity extraction.
- Contextual analysis.
- Cross-document comparison.
- Evidence traceability.
- PDF report generation.

Actual testing results will be documented as development progresses.

## ⚠️ Important Disclaimer

VEXORA is intended as a document analysis and investigation-support prototype.

Automated findings indicate potential anomalies or inconsistencies and must not be treated as definitive proof of document manipulation, fraud, or wrongdoing.

All findings require appropriate human verification and interpretation.

## 🎓 Project Objectives

- Explore practical applications of AI-assisted document analysis.
- Understand PDF processing and OCR technologies.
- Apply Python programming to real-world problems.
- Learn frontend and backend integration.
- Develop contextual comparison and evidence-mapping logic.
- Build a complete, demonstrable software application.
- Gain practical experience with software development and GitHub.

## 🔮 Future Improvements

Potential future enhancements include:

- Advanced document similarity analysis.
- Improved visual anomaly detection.
- More sophisticated entity relationship mapping.
- Additional document formats.
- Advanced investigation analytics.
- Enhanced evidence visualization.

## 👩‍💻 Development

VEXORA is being developed as a learning-focused software project with an emphasis on understanding the technologies, implementation logic, and complete application workflow.

**Development Philosophy:** Build it. Understand it. Test it. Improve it.

---

<p align="center">
  <b>VEXORA</b><br>
  Analyze. Investigate. Connect. Discover.
</p>
