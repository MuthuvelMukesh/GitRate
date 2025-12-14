import streamlit as st
from github import Github
import google.generativeai as genai
import json
import datetime

GITHUB_TOKEN = "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"
GEMINI_API_KEY = "AIzaSyBuMqhJmGwAweLacXREt-5_fzQYIWSDKuY"

st.set_page_config(layout="wide")


def parse_repo_url(url: str):
    if url is None:
        return None, None, "Please paste a GitHub repository URL."

    raw = url.strip()
    if not raw:
        return None, None, "Please paste a GitHub repository URL."

    u = raw
    if "?" in u:
        u = u.split("?", 1)[0]
    if "#" in u:
        u = u.split("#", 1)[0]

    u = u.strip()
    if not u:
        return None, None, "Please paste a GitHub repository URL."

    if u.startswith("git@github.com:"):
        u = u[len("git@github.com:") :]
        if u.endswith(".git"):
            u = u[: -len(".git")]
        parts = [p for p in u.split("/") if p]
        if len(parts) < 2:
            return None, None, "That doesn't look like a valid GitHub repository URL."
        owner = parts[0].strip()
        repo_name = parts[1].strip()
        if not owner or not repo_name:
            return None, None, "That doesn't look like a valid GitHub repository URL."
        return owner, repo_name, None

    lower = u.lower()
    if "github.com" not in lower:
        return None, None, "Please provide a GitHub repository URL (github.com)."

    for prefix in ["https://", "http://"]:
        if lower.startswith(prefix):
            u = u[len(prefix) :]
            lower = lower[len(prefix) :]
            break

    if lower.startswith("www."):
        u = u[4:]
        lower = lower[4:]

    idx = lower.find("github.com")
    if idx == -1:
        return None, None, "Please provide a GitHub repository URL (github.com)."

    after = u[idx + len("github.com") :]
    if after.startswith("/"):
        after = after[1:]

    if not after:
        return None, None, "That URL is missing the owner/repo path."

    parts = [p for p in after.split("/") if p]
    if len(parts) < 2:
        return None, None, "That URL is missing the owner/repo path."

    owner = parts[0].strip()
    repo_name = parts[1].strip()

    if repo_name.endswith(".git"):
        repo_name = repo_name[: -len(".git")]

    invalid_segments = {"issues", "pull", "pulls", "wiki", "actions", "settings", "security", "projects"}
    if repo_name.lower() in invalid_segments:
        return None, None, "Please paste the repository root URL like https://github.com/owner/repo"

    if not owner or not repo_name:
        return None, None, "That doesn't look like a valid GitHub repository URL."

    return owner, repo_name, None


@st.cache_data(show_spinner=False, ttl=900)
def fetch_repo_data(owner: str, repo_name: str):
    token = (GITHUB_TOKEN or "").strip()
    if not token or token == "YOUR_GITHUB_TOKEN":
        gh = Github()
    else:
        gh = Github(token)

    full_name = f"{owner}/{repo_name}"
    repo = gh.get_repo(full_name)

    contents = []
    folder_names = set()
    file_names = set()

    try:
        root_items = repo.get_contents("")
        for item in root_items:
            name = (item.name or "").strip()
            item_type = (item.type or "").strip()
            contents.append({"name": name, "type": item_type})
            if item_type == "dir":
                folder_names.add(name.lower())
            elif item_type == "file":
                file_names.add(name.lower())
    except Exception:
        root_items = []

    readme_exists = False
    for fn in file_names:
        if fn.startswith("readme"):
            readme_exists = True
            break

    if not readme_exists:
        try:
            _ = repo.get_readme()
            readme_exists = True
        except Exception:
            readme_exists = False

    try:
        languages = repo.get_languages() or {}
    except Exception:
        languages = {}

    commit_count = 0
    last_commit_date = None
    try:
        commits = repo.get_commits()
        commit_count = int(getattr(commits, "totalCount", 0) or 0)
        if commit_count > 0:
            try:
                c0 = commits[0]
                if c0 and getattr(c0, "commit", None) is not None:
                    author = getattr(c0.commit, "author", None)
                    committer = getattr(c0.commit, "committer", None)
                    if author is not None and getattr(author, "date", None) is not None:
                        last_commit_date = author.date
                    elif committer is not None and getattr(committer, "date", None) is not None:
                        last_commit_date = committer.date
            except Exception:
                last_commit_date = None
    except Exception:
        commit_count = 0
        last_commit_date = None

    repo_info = {
        "full_name": getattr(repo, "full_name", full_name),
        "name": getattr(repo, "name", repo_name),
        "description": getattr(repo, "description", "") or "",
        "html_url": getattr(repo, "html_url", "") or "",
        "stargazers_count": int(getattr(repo, "stargazers_count", 0) or 0),
        "forks_count": int(getattr(repo, "forks_count", 0) or 0),
        "open_issues_count": int(getattr(repo, "open_issues_count", 0) or 0),
        "default_branch": getattr(repo, "default_branch", "") or "",
        "readme_exists": bool(readme_exists),
    }

    commits_info = {
        "count": int(commit_count),
        "last_date": last_commit_date,
    }

    return {
        "repo": repo_info,
        "contents": contents,
        "languages": languages,
        "commits": commits_info,
        "folders": sorted(list(folder_names)),
        "files": sorted(list(file_names)),
    }


def calculate_score(repo, contents, languages, commits):
    score = 0

    readme_exists = False
    try:
        if isinstance(repo, dict) and bool(repo.get("readme_exists")):
            readme_exists = True
    except Exception:
        readme_exists = False

    if not readme_exists:
        try:
            for item in contents or []:
                name = (item.get("name", "") or "").lower()
                typ = (item.get("type", "") or "").lower()
                if typ == "file" and name.startswith("readme"):
                    readme_exists = True
                    break
        except Exception:
            readme_exists = False

    if readme_exists:
        score += 20

    folder_set = set()
    try:
        for item in contents or []:
            name = (item.get("name", "") or "").strip().lower()
            typ = (item.get("type", "") or "").strip().lower()
            if typ == "dir" and name:
                folder_set.add(name)
    except Exception:
        folder_set = set()

    if ("test" in folder_set) or ("tests" in folder_set):
        score += 20

    commit_count = 0
    try:
        commit_count = int((commits or {}).get("count", 0) or 0)
    except Exception:
        commit_count = 0

    if commit_count > 10:
        score += 15

    if ("src" in folder_set) or ("app" in folder_set) or ("lib" in folder_set):
        score += 15

    try:
        if isinstance(languages, dict) and len(languages.keys()) > 0:
            score += 10
    except Exception:
        pass

    last_commit_date = None
    try:
        last_commit_date = (commits or {}).get("last_date")
    except Exception:
        last_commit_date = None

    if last_commit_date is not None:
        try:
            now = datetime.datetime.now(datetime.timezone.utc)
            if getattr(last_commit_date, "tzinfo", None) is None:
                last_dt = last_commit_date.replace(tzinfo=datetime.timezone.utc)
            else:
                last_dt = last_commit_date
            if now - last_dt <= datetime.timedelta(days=90):
                score += 20
        except Exception:
            pass

    if score > 100:
        score = 100

    if score < 0:
        score = 0

    return int(score)


def generate_ai_insights(repo_info, contents, languages, commits, score):
    fallback_summary = "AI summary unavailable. Showing a quick metadata-based overview."
    fallback_roadmap = []

    try:
        readme_exists = bool((repo_info or {}).get("readme_exists"))
    except Exception:
        readme_exists = False

    folder_set = set()
    try:
        for item in contents or []:
            if (item.get("type", "") or "").lower() == "dir":
                folder_set.add((item.get("name", "") or "").lower())
    except Exception:
        folder_set = set()

    commit_count = 0
    last_commit_date = None
    try:
        commit_count = int((commits or {}).get("count", 0) or 0)
        last_commit_date = (commits or {}).get("last_date")
    except Exception:
        commit_count = 0
        last_commit_date = None

    langs_list = []
    try:
        if isinstance(languages, dict):
            langs_list = sorted([k for k in languages.keys() if k])
    except Exception:
        langs_list = []

    try:
        last_commit_str = "unknown"
        if last_commit_date is not None:
            try:
                last_commit_str = last_commit_date.isoformat()
            except Exception:
                last_commit_str = "unknown"

        fallback_summary = (
            f"Repository '{(repo_info or {}).get('full_name', '')}' looks "
            f"{'active' if commit_count > 10 else 'lightly maintained'} with "
            f"{commit_count} commits and languages detected: "
            f"{', '.join(langs_list) if langs_list else 'none'}. "
            f"Last commit: {last_commit_str}. Score: {score}/100."
        )
    except Exception:
        fallback_summary = "AI summary unavailable. Showing a quick metadata-based overview."

    if not readme_exists:
        fallback_roadmap.append("Add or improve the README with setup, usage, and contribution details.")
    if ("test" not in folder_set) and ("tests" not in folder_set):
        fallback_roadmap.append("Add a basic test suite (and a tests/ folder) to protect core behavior.")
    if ("src" not in folder_set) and ("app" not in folder_set) and ("lib" not in folder_set):
        fallback_roadmap.append("Organize the code into a clear source folder such as src/ to improve maintainability.")
    if not langs_list:
        fallback_roadmap.append("Ensure the repository contains source files so languages are detected on GitHub.")

    while len(fallback_roadmap) < 3:
        fallback_roadmap.append("Add lightweight documentation and usage examples for quicker onboarding.")

    fallback_roadmap = fallback_roadmap[:6]

    api_key = (GEMINI_API_KEY or "").strip()
    if not api_key or api_key == "YOUR_GEMINI_API_KEY":
        return {"summary": fallback_summary, "roadmap": fallback_roadmap[:3]}

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-pro")

        contents_preview = []
        try:
            for item in (contents or [])[:40]:
                nm = item.get("name", "")
                tp = item.get("type", "")
                if nm:
                    contents_preview.append(f"{tp}:{nm}")
        except Exception:
            contents_preview = []

        prompt = (
            "You are an expert software engineer analyzing a public GitHub repository.\n"
            "Return STRICT JSON ONLY (no markdown, no code fences, no extra keys).\n"
            "Schema:\n"
            "{\"summary\": \"string\", \"roadmap\": [\"step 1\", \"step 2\", \"step 3\"]}\n\n"
            "Repository metadata:\n"
            f"- full_name: {(repo_info or {}).get('full_name', '')}\n"
            f"- description: {(repo_info or {}).get('description', '')}\n"
            f"- stars: {(repo_info or {}).get('stargazers_count', 0)}\n"
            f"- forks: {(repo_info or {}).get('forks_count', 0)}\n"
            f"- open_issues: {(repo_info or {}).get('open_issues_count', 0)}\n"
            f"- default_branch: {(repo_info or {}).get('default_branch', '')}\n"
            f"- readme_exists: {bool((repo_info or {}).get('readme_exists'))}\n"
            f"- languages: {', '.join(langs_list) if langs_list else 'none'}\n"
            f"- commit_count: {commit_count}\n"
            f"- last_commit_iso: {last_commit_date.isoformat() if last_commit_date is not None and hasattr(last_commit_date, 'isoformat') else 'unknown'}\n"
            f"- score: {score}/100\n"
            f"- root_contents_preview: {', '.join(contents_preview) if contents_preview else 'none'}\n\n"
            "Constraints:\n"
            "- Keep summary short (1-3 sentences).\n"
            "- Roadmap must be 3 actionable steps personalized to the repository.\n"
            "- Output must be valid JSON that can be parsed with json.loads.\n"
        )

        resp = model.generate_content(prompt)
        text = ""
        try:
            text = (resp.text or "").strip()
        except Exception:
            text = ""

        if not text:
            return {"summary": fallback_summary, "roadmap": fallback_roadmap[:3]}

        parsed = None
        try:
            parsed = json.loads(text)
        except Exception:
            try:
                start = text.find("{")
                end = text.rfind("}")
                if start != -1 and end != -1 and end > start:
                    parsed = json.loads(text[start : end + 1])
            except Exception:
                parsed = None

        if not isinstance(parsed, dict):
            return {"summary": fallback_summary, "roadmap": fallback_roadmap[:3]}

        summary = parsed.get("summary")
        roadmap = parsed.get("roadmap")

        if not isinstance(summary, str) or not summary.strip():
            summary = fallback_summary

        if not isinstance(roadmap, list) or len(roadmap) == 0:
            roadmap = fallback_roadmap[:3]

        cleaned = []
        for step in roadmap:
            if isinstance(step, str) and step.strip():
                cleaned.append(step.strip())
        if len(cleaned) < 3:
            for step in fallback_roadmap:
                if len(cleaned) >= 3:
                    break
                if step not in cleaned:
                    cleaned.append(step)

        return {"summary": summary.strip(), "roadmap": cleaned[:3]}

    except Exception:
        return {"summary": fallback_summary, "roadmap": fallback_roadmap[:3]}

st.markdown(
    """
<style>
:root {
  --bg: #0e1117;
  --accent: #00ffff;
  --card: rgba(255, 255, 255, 0.08);
  --card-border: rgba(0, 255, 255, 0.22);
  --text: rgba(255, 255, 255, 0.92);
  --muted: rgba(255, 255, 255, 0.72);
}

.stApp {
  background: radial-gradient(1200px 600px at 20% 10%, rgba(0, 255, 255, 0.10), transparent 55%),
              radial-gradient(900px 500px at 85% 15%, rgba(0, 255, 255, 0.07), transparent 55%),
              var(--bg);
  color: var(--text);
}

h1, h2, h3 {
  color: var(--text);
}

.space-card {
  background: var(--card);
  border: 1px solid var(--card-border);
  border-radius: 18px;
  padding: 18px 18px;
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  box-shadow: 0 0 0 1px rgba(0,255,255,0.08) inset;
}

.neon-title {
  font-weight: 700;
  letter-spacing: 0.6px;
}

.neon-accent {
  color: var(--accent);
}

.kpi {
  font-size: 44px;
  font-weight: 800;
  line-height: 1.0;
  margin: 0;
}

.kpi-sub {
  margin-top: 6px;
  color: var(--muted);
}

.meta {
  margin-top: 12px;
  color: var(--muted);
  font-size: 14px;
  line-height: 1.45;
}

hr.space {
  border: none;
  border-top: 1px solid rgba(0,255,255,0.18);
  margin: 14px 0;
}

@keyframes float {
  0%   { transform: translateY(0px); }
  50%  { transform: translateY(-8px); }
  100% { transform: translateY(0px); }
}

.float {
  animation: float 5.5s ease-in-out infinite;
}

input[type="text"] {
  border-radius: 12px !important;
}
</style>
""",
    unsafe_allow_html=True,
)

st.title("🚀 GitHub Repository Analyzer")

repo_url = st.text_input("Paste a public GitHub repository URL", value="", placeholder="https://github.com/owner/repo")

analyze_clicked = st.button("Analyze Repository")

if analyze_clicked:
    owner, repo_name, err = parse_repo_url(repo_url)
    if err:
        st.error(err)
    else:
        with st.spinner("Scanning repository telemetry..."):
            try:
                data = fetch_repo_data(owner, repo_name)
            except Exception as e:
                msg = "Could not fetch repository data. "
                msg += "If this is a valid public repo, try again in a moment."
                st.error(msg)
                data = None

        if data is not None:
            repo_info = data.get("repo") or {}
            contents = data.get("contents") or []
            languages = data.get("languages") or {}
            commits = data.get("commits") or {}

            score = calculate_score(repo_info, contents, languages, commits)

            with st.spinner("Generating AI mission briefing..."):
                insights = generate_ai_insights(repo_info, contents, languages, commits, score)

            summary = (insights or {}).get("summary", "") or ""
            roadmap = (insights or {}).get("roadmap", []) or []

            lang_list = []
            try:
                if isinstance(languages, dict):
                    lang_list = sorted([k for k in languages.keys() if k])
            except Exception:
                lang_list = []

            commit_count = 0
            last_commit_date = None
            try:
                commit_count = int((commits or {}).get("count", 0) or 0)
                last_commit_date = (commits or {}).get("last_date")
            except Exception:
                commit_count = 0
                last_commit_date = None

            last_commit_display = "Unknown"
            if last_commit_date is not None:
                try:
                    last_commit_display = last_commit_date.strftime("%Y-%m-%d")
                except Exception:
                    try:
                        last_commit_display = str(last_commit_date)
                    except Exception:
                        last_commit_display = "Unknown"

            left, right = st.columns(2)

            with left:
                st.markdown(
                    f"""
<div class="space-card float">
  <div class="neon-title">Mission Score</div>
  <hr class="space"/>
  <p class="kpi"><span class="neon-accent">{score}</span><span style="font-size:18px; color: rgba(255,255,255,0.70);">/100</span></p>
  <div class="meta">
    <div><span class="neon-accent">Repo:</span> {(repo_info.get('full_name') or '').strip()}</div>
    <div><span class="neon-accent">Languages:</span> {(', '.join(lang_list) if lang_list else 'None detected')}</div>
    <div><span class="neon-accent">Commits:</span> {commit_count}</div>
    <div><span class="neon-accent">Last Commit:</span> {last_commit_display}</div>
  </div>
</div>
""",
                    unsafe_allow_html=True,
                )

            with right:
                st.markdown(
                    f"""
<div class="space-card float">
  <div class="neon-title">AI Summary</div>
  <hr class="space"/>
  <div style="color: rgba(255,255,255,0.88); line-height: 1.6;">{summary}</div>
</div>
""",
                    unsafe_allow_html=True,
                )

            st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

            st.markdown(
                """
<div class="space-card">
  <div class="neon-title">Personalized Roadmap</div>
  <hr class="space"/>
</div>
""",
                unsafe_allow_html=True,
            )

            if isinstance(roadmap, list) and len(roadmap) > 0:
                for step in roadmap:
                    if isinstance(step, str) and step.strip():
                        st.markdown(f"- {step.strip()}")
            else:
                st.markdown("- Add documentation, tests, and a clear project structure.")
