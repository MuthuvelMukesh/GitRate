# GitRate 

GitRate is a Streamlit-based GitHub repository analyzer. Paste any **public GitHub repo URL**, and GitRate will:

- Fetch repository telemetry (stars, forks, issues, commits, branches, PRs, license, contributors)
- Inspect structure (folders, tests, config/quality files, README presence)
- Compute a **0–100 score** with a transparent breakdown
- Use **Gemini AI** (optional) to generate a concise summary and a 3-step improvement roadmap
- Let you **download a Markdown report** of the assessment

---

## Features

- **URL parsing & validation**
  - Accepts typical GitHub URLs (HTTPS or `git@github.com:` formats)
  - Validates that the URL looks like `https://github.com/owner/repo`

- **Repository telemetry (via GitHub API)**
  - Basic metadata: name, description, stars, forks, open issues
  - Structure: root folders/files, detects `tests/` / `test/` and common source folders
  - Languages used
  - Commits: total count and last commit date
  - Branches and pull requests: counts for basic workflow health
  - License and contributor count
  - README presence and a snippet of its content

- **Score engine (0–100)**
  The score is composed of several dimensions, each with a clear contribution:

  - Documentation (README presence)
  - Testing (tests folder)
  - Activity & consistency (commit count)
  - Structure & organization (`src/`, `app/`, or `lib/` folders)
  - Tech stack & quality indicators (languages + config/quality files)
  - Best practices / workflow (branches and PRs)
  - Recency of activity (recent commits)
  - License presence

  The app also exposes a **score breakdown** so it’s clear where points are gained or lost.

- **AI insights (optional)**
  - If a valid `GEMINI_API_KEY` is set, GitRate calls Gemini to:
    - Summarize the repository’s health
    - Propose a short, actionable 3-step roadmap
  - If no key is set, a sensible local fallback summary and roadmap are used instead.

- **Modern UI/UX**
  - Built with Streamlit and a custom Space Grotesk theme
  - Light-mode dashboard with glassy cards and clear typography
  - Mission score card with a visual score bar
  - Sidebar setup & status for tokens
  - One-click **Markdown report download**

---

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/MuthuvelMukesh/GitRate.git
cd GitRate
```

### 2. Create and activate a virtual environment (Windows)

```cmd
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables (recommended)

GitRate works best with a GitHub token (for higher rate limits) and a Gemini API key (for AI insights). These are **not** stored in the code; they are read from environment variables.

In **cmd** on Windows:

```cmd
set GITHUB_TOKEN=your_github_personal_access_token
set GEMINI_API_KEY=your_gemini_api_key
```

In **PowerShell** on Windows:

```powershell
$env:GITHUB_TOKEN = "your_github_personal_access_token"
$env:GEMINI_API_KEY = "your_gemini_api_key"
```

> You can run GitRate without these variables:
> - Without `GITHUB_TOKEN`, GitHub API calls run anonymously (lower rate limits).
> - Without `GEMINI_API_KEY`, the app uses a local fallback summary and roadmap.

### 5. Run the app

```bash
streamlit run app.py
```

Streamlit will print a **Local URL** (e.g. `http://localhost:8501`). Open it in your browser.

---

## Using GitRate

1. Open the Streamlit app in your browser.
2. Paste a **public GitHub repository URL**, for example:
   - `https://github.com/streamlit/streamlit`
   - `https://github.com/owner/repo`
3. Click **“Analyze Repository”**.
4. After a short scan, you’ll see:
   - **Mission Score** (0–100) with a score bar and core repo metrics
   - **AI Summary** of the repo’s health (if Gemini is configured)
   - **Score Breakdown** (expandable) explaining how the score was calculated
   - **Personalized Roadmap** of improvement steps
   - A button to **download the report as Markdown**

---

## Security Notes

- API keys are **not** hard-coded in the repository.
- GitHub and Gemini tokens are read only from environment variables (`GITHUB_TOKEN`, `GEMINI_API_KEY`).
- If you ever accidentally commit a secret, **revoke/rotate it immediately** in the provider’s console.

---

## Tech Stack

- Python
- Streamlit
- PyGithub
- Google Generative AI (Gemini)

---

## License

This project is for hackathon/demo use. You may adapt or extend it for your own GitHub analysis tools as needed.
