# Clinical Trial Intelligence Platform - Enterprise Edition 🚀

> **Note**: This is an enterprise-grade prototype designed to revolutionize how clinical trials are monitored and analyzed using Agentic AI.

![Role-Based Dashboard](https://raw.githubusercontent.com/sagar-grv/clinical-trial-intelligence-nest2.0/main/screenshot_placeholder.png)
*(Note: Replace with actual screenshot URL after deployment)*

## 📖 Project Overview

The **Clinical Trial Intelligence Platform** is a sophisticated system that ingests raw clinical trial data (Excel), runs advanced analytics to detect specific risks, and uses **Agentic AI** to propose actionable solutions (emails, visit recommendations).

It solves the problem of "Data Overload" in clinical trials by providing a **Trust Layer** (explainable AI) and **Role-Based Views** (CTT, CRA, Site).

## 🌟 Key Features

### 1. 🛡️ Trust & Explainability (The "Proof Layer")

We don't just flag "High Risk." We prove it.

- **Rule-BASED Evidence**: Every issue links to a specific deterministic rule (e.g., `MISSING_LAB_DATA`).
- **Data Proof**: Shows `Actual Value` vs `Threshold` (e.g., "12% missing > 5% limit").
- **Confidence Badges**: ✅ Rule-Verified (100% Code) vs ⚠️ AI-Explained (Generative).

### 2. ⚡ Performance Architecture (Async + Cache) 🆕

Built for enterprise scale:

- **Asynchronous Analysis**: Heavy computations happen in the background (`AnalysisWorker`).
- **Instant Caching**: Results are stored in the DB (`Study.cached_analytics`), making dashboard loads instant (O(1)).
- **Pagination**: Server-side pagination handles thousands of issues without UI lag.

### 3. 🤖 Agentic AI (Human-in-the-Loop)

- **Email Drafter**: Auto-writes polite, context-aware emails to sites about specific queries.
- **Visit Recommender**: Analyzes issue density to suggest specific monitoring visits.
- **Safety First**: AI *proposes*, Human *approves*. No unseen actions.

### 4. 👥 Role-Based Dashboards

- **CTT (Study Lead)**: Strategic risk overview & trends.
- **CRA (Monitor)**: Site-specific action items & query backlog.
- **Site User**: Compliance tracking & simplified task list.

---

## 💻 Tech Stack

- **Frontend**: Streamlit (Python) + Custom CSS Themes.
- **Backend**: Python, SQLite, SQLAlchemy.
- **Processing**: Pandas, OpenPyXL, Threading.
- **AI Engine**: Google Gemini Pro (via `GeminiClient`).
- **Visualization**: Plotly Interactive Charts.

## 📚 Documentation & Reports

Detailed documentation is available in the `docs/` folder:

- [📥 Project Walkthrough](./docs/walkthrough.md): Comprehensive guide to all features, roles, and workflows.
- [📊 Project Analysis](./docs/project_analysis.md): In-depth architectural review and improvement roadmap.
- [🚀 Deployment Guide](./docs/deployment_guide.md): Step-by-step instructions for GitHub and Streamlit Cloud.

---

## 🚀 How to Run Locally

1. **Clone the Repository**:

    ```bash
    git clone https://github.com/sagar-grv/clinical-trial-intelligence-nest2.0.git
    cd clinical-trial-intelligence-nest2.0
    ```

2. **Install Dependencies**:

    ```bash
    pip install -r requirements.txt
    ```

3. **Run the App**:

    ```bash
    streamlit run app.py
    ```

4. **Access the Dashboard**:
    Open `http://localhost:8501` in your browser.

---

## 🔮 Future Enhancements Roadmap

Based on the [Project Analysis](./brain/project_analysis.md), here is the roadmap for moving to production:

### Phase 1: Hardening (Immediate)

- [ ] **Unit Tests**: Implement `pytest` suite for core logic validation.
- [ ] **External Rules**: Move hardcoded thresholds (`pipeline.py`) to a config file (`rules.yaml`).
- [ ] **PostgreSQL**: Migrate from SQLite to PostgreSQL for concurrency.

### Phase 2: Enterprise Scale

- [ ] **Task Queue**: Replace Python `threading` with **Celery/Redis** for horizontal scaling.
- [ ] **Audit Logging**: Track *user actions* (approvals/rejections), not just data extraction.
- [ ] **Cost Tracking**: Dashboard to monitor Gemini API token usage.

### Phase 3: Advanced Intelligence

- [ ] **RAG Integration**: Query across *all* historical studies ("Has this site failed before?").
- [ ] **Feedback Loop**: Use user rejection data to fine-tune AI prompts automatically.

---

## 📄 License

MIT License. See [LICENSE](LICENSE) for details.
