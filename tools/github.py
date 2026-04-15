import re
import sys
from pathlib import Path
from typing import Optional

# Running `python tools/github.py` puts `tools/` on sys.path first, which shadows
# the PyGithub package name `github`. Strip it before importing PyGithub.
if __name__ == "__main__":
    _tools_dir = str(Path(__file__).resolve().parent)
    if _tools_dir in sys.path:
        sys.path.remove(_tools_dir)

from github import Auth, Github
from github.GithubException import BadCredentialsException, GithubException

_EMPTY_TOKEN = (
    "Please connect your GitHub account first. Enter your GitHub token in the sidebar."
)
_INVALID_TOKEN = "Your GitHub token is invalid. Please check it and try again."
_FAILURE = "Sorry I could not connect to GitHub right now."

_REPO_QUERY_PATTERNS = (
    re.compile(r"(?i)tell me about\s+(.+)"),
    re.compile(r"(?i)what is\s+(.+)"),
    re.compile(r"(?i)show\s+(.+)"),
)


def _strip_repo_name(raw: str) -> str:
    return raw.strip().strip("\"'").rstrip("?.!")


def _extract_repo_query(message: str) -> Optional[str]:
    for pat in _REPO_QUERY_PATTERNS:
        m = pat.search(message)
        if not m:
            continue
        name = _strip_repo_name(m.group(1))
        if not name:
            continue
        low = name.lower()
        if low in ("my profile", "my repos", "my repositories"):
            continue
        return name
    return None


def _github_client(token: str) -> Github:
    return Github(auth=Auth.Token(token.strip()))


def run_github(message: str, token: str) -> str:
    if token is None or not str(token).strip():
        return _EMPTY_TOKEN

    token = str(token).strip()

    try:
        g = _github_client(token)
        user = g.get_user()
    except BadCredentialsException:
        return _INVALID_TOKEN
    except GithubException:
        return _FAILURE
    except OSError:
        return _FAILURE

    low = message.lower()

    try:
        if "my repos" in low or "my repositories" in low:
            repos = []
            for repo in user.get_repos(sort="updated", direction="desc"):
                repos.append(repo)
                if len(repos) >= 5:
                    break
            if not repos:
                return "You have no repositories yet."
            lines = ["Here are your top 5 repositories (most recently updated):", ""]
            for i, repo in enumerate(repos, start=1):
                desc = (repo.description or "").strip() or "No description"
                lines.append(f"{i}. {repo.name}")
                lines.append(f"   Description: {desc}")
                if i < len(repos):
                    lines.append("")
            return "\n".join(lines)

        if "my profile" in low or re.search(r"(?i)who\s+am\s+i\??", message):
            bio = (user.bio or "").strip() or "No bio"
            lines = [
                "Your GitHub profile:",
                "",
                f"Username: {user.login}",
                f"Bio: {bio}",
                f"Followers: {user.followers}",
                f"Public repositories: {user.public_repos}",
            ]
            return "\n".join(lines)

        repo_query = _extract_repo_query(message)
        if repo_query:
            try:
                repo = user.get_repo(repo_query)
            except GithubException:
                return _FAILURE
            desc = (repo.description or "").strip() or "No description"
            lang = repo.language or "Not specified"
            updated = repo.updated_at
            updated_s = (
                updated.strftime("%Y-%m-%d %H:%M UTC") if updated else "Unknown"
            )
            lines = [
                f"Repository: {repo.name}",
                f"Description: {desc}",
                f"Stars: {repo.stargazers_count}",
                f"Language: {lang}",
                f"Last updated: {updated_s}",
            ]
            return "\n".join(lines)

    except GithubException:
        return _FAILURE
    except OSError:
        return _FAILURE

    return _FAILURE


if __name__ == "__main__":
    print(run_github("my repos", ""))
    print(
        "To test with real token run: run_github(your message, your token)",
    )
