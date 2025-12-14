import streamlit as st
from github import Github
import google.generativeai as genai
import json
import datetime
import os
from typing import Any, Dict, List, Optional, Set, Tuple, cast

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

st.set_page_config(layout="wide")


def parse_repo_url(url: Optional[str]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
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
def fetch_repo_data(owner: str, repo_name: str) -> Dict[str, Any]:
    token = (GITHUB_TOKEN or "").strip()

    # Prefer authenticated client if a token is configured, but gracefully
    # fall back to anonymous access for public repositories.
    if token:
        gh = Github(token)
    else:
        gh = Github()

    full_name = f"{owner}/{repo_name}"

    try:
        repo = gh.get_repo(full_name)
    except Exception:
        # Retry without a token in case the configured token is invalid or
        # missing scopes but the repo is public.
        try:
            repo = Github().get_repo(full_name)
        except Exception as exc:
            # Let the caller surface a clear error message.
            raise RuntimeError(f"GitHub API error while fetching {full_name}: {exc}")

    contents: List[Dict[str, str]] = []
    folder_names: Set[str] = set()
    file_names: Set[str] = set()

    try:
        root = repo.get_contents("")
        if isinstance(root, list):
            root_items = root
        else:
            root_items = [root]

        for item in root_items:
            name = (getattr(item, "name", "") or "").strip()
            item_type = (getattr(item, "type", "") or "").strip()
            contents.append({"name": name, "type": item_type})
            lower_name = name.lower()
            if item_type == "dir":
                folder_names.add(lower_name)
            elif item_type == "file":
                file_names.add(lower_name)
    except Exception:
        # If anything fails, fall back to empty collections
        contents = []
        folder_names = set()
        file_names = set()

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

    # --- NEW: Fetch Branch & PR Data (Best Practices) ---
    branch_count = 1
    try:
        # Getting total count might be slow on huge repos, so we just check if > 1
        branches = repo.get_branches()
        branch_count = branches.totalCount
    except Exception:
        branch_count = 1

    pr_count = 0
    try:
        # Just checking recent PRs to see if they use them
        pulls = repo.get_pulls(state='all')
        pr_count = pulls.totalCount
    except Exception:
        pr_count = 0

    # --- NEW: Fetch README Content (Documentation Quality) ---
    readme_content = ""
    if readme_exists:
        try:
            readme_obj = repo.get_readme()
            readme_content = readme_obj.decoded_content.decode("utf-8")[:1500] # First 1500 chars
        except Exception:
            readme_content = ""

    # --- NEW: Check for Config/Quality Files ---
    quality_files: List[str] = []
    known_configs: Set[str] = {".gitignore", ".editorconfig", ".eslintrc", ".prettierrc", "pyproject.toml", "package.json", "requirements.txt", "pom.xml", "dockerfile"}
    for fn in file_names:
        for config in known_configs:
            if config in fn or fn.endswith(config):
                quality_files.append(fn)
    
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

    # --- NEW: Fetch License & Contributors ---
    license_name = "None"
    try:
        lic = repo.get_license()
        license_name = lic.license.name
    except Exception:
        license_name = "None"

    contributors_count = 0
    try:
        # Getting total count might be slow on huge repos, so we just check first page size or similar
        # For speed, we might just get the first few
        contributors = repo.get_contributors()
        contributors_count = contributors.totalCount
    except Exception:
        contributors_count = 0

    repo_info: Dict[str, Any] = {
        "full_name": getattr(repo, "full_name", full_name),
        "name": getattr(repo, "name", repo_name),
        "description": getattr(repo, "description", "") or "",
        "html_url": getattr(repo, "html_url", "") or "",
        "stargazers_count": int(getattr(repo, "stargazers_count", 0) or 0),
        "forks_count": int(getattr(repo, "forks_count", 0) or 0),
        "open_issues_count": int(getattr(repo, "open_issues_count", 0) or 0),
        "default_branch": getattr(repo, "default_branch", "") or "",
        "readme_exists": bool(readme_exists),
        "branch_count": int(branch_count),
        "pr_count": int(pr_count),
        "license_name": license_name,
        "contributors_count": int(contributors_count),
    }

    commits_info: Dict[str, Any] = {
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
        "readme_content": readme_content,
        "quality_files": sorted(list(set(quality_files))),
    }


def calculate_score(repo: Dict[str, Any], contents: List[Dict[str, str]], languages: Dict[str, int], commits: Dict[str, Any], quality_files: List[str]) -> Dict[str, Any]:
    score: int = 0
    breakdown: List[str] = []

    # 1. Documentation (20 pts)
    readme_exists = False
    try:
        readme_exists = bool(repo.get("readme_exists"))
    except Exception:
        readme_exists = False
    if readme_exists:
        score += 20
        breakdown.append("✅ README exists (+20)")
    else:
        breakdown.append("❌ Missing README (0/20)")

    # 2. Testing (20 pts)
    folder_set: Set[str] = set()
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
        breakdown.append("✅ Tests folder detected (+20)")
    else:
        breakdown.append("❌ No tests folder found (0/20)")

    # 3. Activity & Consistency (15 pts)
    commit_count = 0
    try:
        commit_count = int((commits or {}).get("count", 0) or 0)
    except Exception:
        commit_count = 0

    if commit_count > 10:
        score += 15
        breakdown.append("✅ Active commit history (>10 commits) (+15)")
    else:
        breakdown.append(f"⚠️ Low commit count ({commit_count}) (0/15)")

    # 4. Structure & Organization (10 pts)
    if ("src" in folder_set) or ("app" in folder_set) or ("lib" in folder_set):
        score += 10
        breakdown.append("✅ Standard folder structure (src/app/lib) (+10)")
    else:
        breakdown.append("⚠️ Non-standard root structure (0/10)")

    # 5. Tech Stack & Quality Indicators (15 pts)
    # Has languages?
    has_langs = False
    try:
        has_langs = len(languages.keys()) > 0
    except Exception:
        has_langs = False
    
    # Has config files? (e.g. .gitignore)
    has_config = len(quality_files) > 0
    
    if has_langs:
        score += 5
        breakdown.append("✅ Languages detected (+5)")
    if has_config:
        score += 10
        breakdown.append("✅ Config/Quality files present (+10)")
    else:
        breakdown.append("⚠️ No config/quality files found (0/10)")

    # 6. Best Practices / Workflow (10 pts)
    # Branches > 1 or PRs > 0
    branch_count = int(repo.get("branch_count", 1))
    pr_count = int(repo.get("pr_count", 0))
    
    if branch_count > 1 or pr_count > 0:
        score += 10
        breakdown.append("✅ Uses Branches/PRs (+10)")
    else:
        breakdown.append("⚠️ Single branch / No PRs detected (0/10)")

    # 7. Recency (5 pts)
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
                score += 5
                breakdown.append("✅ Recent activity (<90 days) (+5)")
            else:
                breakdown.append("⚠️ No recent activity (0/5)")
        except Exception:
            pass
    
    # 8. License (5 pts)
    license_name = str(repo.get("license_name", "None"))
    if license_name and license_name != "None":
        score += 5
        breakdown.append("✅ License found (+5)")
    else:
        breakdown.append("⚠️ No License found (0/5)")

    if score > 100:
        score = 100

    if score < 0:
        score = 0

    return {"score": int(score), "breakdown": breakdown}


def generate_ai_insights(repo_info: Dict[str, Any], contents: List[Dict[str, str]], languages: Dict[str, int], commits: Dict[str, Any], score_data: Dict[str, Any], readme_content: str, quality_files: List[str]) -> Dict[str, Any]:
    score: int = int(score_data.get("score", 0))
    breakdown: List[str] = cast(List[str], score_data.get("breakdown", []) or [])

    fallback_summary: str = "AI summary unavailable. Showing a quick metadata-based overview."
    fallback_roadmap: List[str] = []

    try:
        readme_exists = bool((repo_info or {}).get("readme_exists"))
    except Exception:
        readme_exists = False

    folder_set: Set[str] = set()
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

    langs_list: List[str] = []
    try:
        langs_list = sorted([k for k in languages.keys() if k])
    except Exception:
        langs_list = []

    try:
        fallback_summary = (
            f"Repository '{(repo_info or {}).get('full_name', '')}' looks "
            f"{'active' if commit_count > 10 else 'lightly maintained'} with "
            f"{commit_count} commits. "
            f"Score: {score}/100."
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
        genai_any = cast(Any, genai)
        genai_any.configure(api_key=api_key)
        model = genai_any.GenerativeModel("gemini-pro")

        contents_preview: List[str] = []
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
            f"- readme_exists: {bool((repo_info or {}).get('readme_exists'))}\n"
            f"- languages: {', '.join(langs_list) if langs_list else 'none'}\n"
            f"- commit_count: {commit_count}\n"
            f"- branch_count: {(repo_info or {}).get('branch_count', 1)}\n"
            f"- pr_count: {(repo_info or {}).get('pr_count', 0)}\n"
            f"- license: {(repo_info or {}).get('license_name', 'None')}\n"
            f"- contributors: {(repo_info or {}).get('contributors_count', 0)}\n"
            f"- config_files_detected: {', '.join(quality_files) if quality_files else 'none'}\n"
            f"- last_commit_iso: {last_commit_date.isoformat() if last_commit_date is not None and hasattr(last_commit_date, 'isoformat') else 'unknown'}\n"
            f"- score: {score}/100\n"
            f"- score_breakdown: {', '.join(breakdown)}\n"
            f"- root_contents_preview: {', '.join(contents_preview) if contents_preview else 'none'}\n"
            f"- readme_snippet_start: {readme_content[:500] if readme_content else 'N/A'}\n\n"
            "Constraints:\n"
            "- Summary: Evaluate code quality, documentation, and best practices based on the data provided. Be honest.\n"
            "- Roadmap: 3 specific, actionable steps. If score is low, focus on basics (README, .gitignore). If high, focus on CI/CD or tests.\n"
            "- Output must be valid JSON.\n"
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

        parsed_dict: Dict[str, Any] = cast(Dict[str, Any], parsed)
        raw_summary = parsed_dict.get("summary")
        raw_roadmap = parsed_dict.get("roadmap")

        if isinstance(raw_summary, str) and raw_summary.strip():
            summary = raw_summary
        else:
            summary = fallback_summary

        roadmap_list: List[str] = []
        if isinstance(raw_roadmap, list):
            for step in cast(List[Any], raw_roadmap):
                if isinstance(step, str) and step.strip():
                    roadmap_list.append(step.strip())
        if not roadmap_list:
            roadmap_list = fallback_roadmap[:3]

        cleaned: List[str] = []
        for step in roadmap_list:
            cleaned.append(step)
        if len(cleaned) < 3:
            for step in fallback_roadmap:
                if len(cleaned) >= 3:
                    break
                if step not in cleaned:
                    cleaned.append(step)

        return {"summary": summary.strip(), "roadmap": cleaned[:3]}

    except Exception:
        return {"summary": fallback_summary, "roadmap": fallback_roadmap[:3]}

st.sidebar.title("⚙️ Setup & Status")

st.sidebar.markdown(
    "- **GitHub Token**: " + ("✅ set" if GITHUB_TOKEN else "⚠️ not set (using anonymous access)")
)
st.sidebar.markdown(
    "- **Gemini Key**: " + ("✅ set" if GEMINI_API_KEY else "⚠️ not set (using fallback summary)")
)

st.sidebar.markdown(
    """---
**How to set keys (cmd)**

```cmd
set GITHUB_TOKEN=your_pat
set GEMINI_API_KEY=your_gemini_key
```
Then run:

```cmd
M:\\GitRate\\.venv\\Scripts\\python.exe -m streamlit run app.py
```
"""
)

bg = "#f5f5f7"
accent = "#2563eb"
card = "rgba(255, 255, 255, 0.96)"
card_border = "rgba(15, 23, 42, 0.06)"
text = "rgba(15, 23, 42, 0.94)"
muted = "rgba(15, 23, 42, 0.65)"
bg_grad_1 = "rgba(37, 99, 235, 0.20)"
bg_grad_2 = "rgba(56, 189, 248, 0.18)"

style_css = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&display=swap');

:root {{
    --bg: {bg};
    --accent: {accent};
    --card: {card};
    --card-border: {card_border};
    --text: {text};
    --muted: {muted};
}}

html, body, [data-testid="stAppViewContainer"], .stApp {{
    font-family: 'Space Grotesk', system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    color: var(--text);
}}

.stApp {{
    background:
        radial-gradient(1200px 600px at 20% 10%, {bg_grad_1}, transparent 55%),
        radial-gradient(900px 500px at 85% 15%, {bg_grad_2}, transparent 55%),
        var(--bg);
}}

.block-container {{
    padding-top: 2.5rem;
    padding-bottom: 3rem;
    max-width: 1100px;
}}

h1, h2, h3 {{
    color: var(--text);
}}

.space-card {{
    background: var(--card);
    border: 1px solid var(--card-border);
    border-radius: 16px;
    padding: 16px 18px;
    backdrop-filter: blur(14px);
    -webkit-backdrop-filter: blur(14px);
    box-shadow: 0 18px 45px rgba(15, 23, 42, 0.32);
}}

.neon-title {{
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    font-size: 12px;
    color: var(--muted);
}}

.neon-accent {{
    color: var(--accent);
}}

.kpi {{
    font-size: 42px;
    font-weight: 700;
    line-height: 1.0;
    margin: 0;
}}

.kpi-sub {{
    margin-top: 4px;
    color: var(--muted);
}}

.meta {{
    margin-top: 10px;
    color: var(--muted);
    font-size: 13px;
    line-height: 1.5;
}}

hr.space {{
    border: none;
    border-top: 1px solid rgba(15, 23, 42, 0.08);
    margin: 12px 0;
}}

@keyframes float {{
    0%   {{ transform: translateY(0px); }}
    50%  {{ transform: translateY(-6px); }}
    100% {{ transform: translateY(0px); }}
}}

.float {{
    animation: float 5.5s ease-in-out infinite;
}}

input[type="text"] {{
    border-radius: 10px !important;
}}
</style>
"""

st.markdown(style_css, unsafe_allow_html=True)

st.title("🚀 GitHub Repository Analyzer")

repo_url = st.text_input("Paste a public GitHub repository URL", value="", placeholder="https://github.com/owner/repo")

analyze_clicked = st.button("Analyze Repository")

if analyze_clicked:
    owner, repo_name, err = parse_repo_url(repo_url)
    if err or owner is None or repo_name is None:
        st.error(err or "Please paste a GitHub repository URL.")
    else:
        with st.spinner("Scanning repository telemetry..."):
            try:
                data = fetch_repo_data(owner, repo_name)
            except Exception as e:
                st.error(
                    "Could not fetch repository data. "
                    "Details: " + str(e)
                )
                data = None

        if data is not None:
            repo_info: Dict[str, Any] = data.get("repo") or {}
            contents: List[Dict[str, str]] = data.get("contents") or []
            languages: Dict[str, int] = data.get("languages") or {}
            commits: Dict[str, Any] = data.get("commits") or {}

            quality_files: List[str] = cast(List[str], data.get("quality_files") or [])
            readme_content: str = str(data.get("readme_content") or "")

            score_data = calculate_score(repo_info, contents, languages, commits, quality_files)
            score_val: int = int(score_data.get("score", 0))
            breakdown: List[str] = cast(List[str], score_data.get("breakdown", []) or [])

            with st.spinner("Generating AI mission briefing..."):
                insights = generate_ai_insights(repo_info, contents, languages, commits, score_data, readme_content, quality_files)

            summary = (insights or {}).get("summary", "") or ""
            roadmap: List[str] = cast(List[str], (insights or {}).get("roadmap", []) or [])

            lang_list: List[str] = []
            try:
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
  <p class="kpi"><span class="neon-accent">{score_val}</span><span style="font-size:18px; color: rgba(15,23,42,0.75);">/100</span></p>
  <div class="meta">
        <div style="margin-bottom: 6px;">
            <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em; color: rgba(15,23,42,0.7); margin-bottom: 2px;">Score health</div>
            <div style="width: 100%; height: 6px; border-radius: 999px; background: rgba(15,23,42,0.06); overflow: hidden;">
                <div style="width: {score_val}%; height: 100%; background: linear-gradient(90deg, #2563eb, #22c55e);"></div>
            </div>
        </div>
    <div><span class="neon-accent">Repo:</span> {(repo_info.get('full_name') or '').strip()}</div>
    <div><span class="neon-accent">Languages:</span> {(', '.join(lang_list) if lang_list else 'None detected')}</div>
    <div><span class="neon-accent">Commits:</span> {commit_count}</div>
    <div><span class="neon-accent">Last Commit:</span> {last_commit_display}</div>
    <div><span class="neon-accent">PRs:</span> {repo_info.get('pr_count', 0)} | <span class="neon-accent">Branches:</span> {repo_info.get('branch_count', 1)}</div>
    <div><span class="neon-accent">License:</span> {repo_info.get('license_name', 'None')}</div>
    <div><span class="neon-accent">Contributors:</span> {repo_info.get('contributors_count', 0)}</div>
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
    <div style="color: rgba(15,23,42,0.9); line-height: 1.6;">{summary}</div>
</div>
""",
                    unsafe_allow_html=True,
                )

            st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

            with st.expander("View Score Breakdown"):
                if breakdown:
                    for item in breakdown:
                        st.write(f"- {item}")
                else:
                    st.write("No breakdown available.")

            # Simple Markdown export of the assessment
            report_lines: List[str] = []
            report_lines.append(f"# GitRate Report for {(repo_info.get('full_name') or '').strip()}")
            report_lines.append("")
            report_lines.append(f"**Score:** {score_val}/100")
            report_lines.append("")
            if summary:
                report_lines.append("## AI Summary")
                report_lines.append("")
                report_lines.append(summary)
                report_lines.append("")
            if breakdown:
                report_lines.append("## Score Breakdown")
                report_lines.append("")
                for item in breakdown:
                    report_lines.append(f"- {item}")
                report_lines.append("")
            if roadmap:
                report_lines.append("## Personalized Roadmap")
                report_lines.append("")
                for step in roadmap:
                    report_lines.append(f"- {step}")

            report_md = "\n".join(report_lines)

            st.markdown(
                """
<div class="space-card">
  <div class="neon-title">Personalized Roadmap</div>
  <hr class="space"/>
</div>
""",
                unsafe_allow_html=True,
            )

            if roadmap:
                for step in roadmap:
                    st.markdown(f"- {step.strip()}")
            else:
                st.markdown("- Add documentation, tests, and a clear project structure.")

            st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

            st.download_button(
                label="⬇️ Download report as Markdown",
                data=report_md,
                file_name="gitrate-report.md",
                mime="text/markdown",
            )
