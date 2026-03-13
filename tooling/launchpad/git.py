"""
Git helper utilities for detecting repository metadata.

These helpers are used by the instance creation workflow to detect the
current cluster repository information and pass it to cookiecutter as
context, avoiding reliance on Jinja extensions that run in temporary
directories.
"""

import subprocess


def _run_git_command(args: list[str]) -> str | None:
    """
    Run a git command and return its standard output.

    Args:
        args: Arguments to pass to the `git` executable (e.g., ["rev-parse", "HEAD"]).

    Returns:
        The command's stdout with trailing whitespace stripped, or None if the
        command fails or git is not available.
    """

    try:
        result = subprocess.run(
            ["git", *args], capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def get_git_repo_url() -> str:
    """
    Get the repository remote.origin.url as an SSH URL when possible.

    Converts HTTPS GitHub URLs (https://github.com/owner/repo.git) to SSH form
    (git@github.com:owner/repo.git). If the URL cannot be determined, an empty
    string is returned.

    Returns:
        Repository URL (SSH preferred) or an empty string when unavailable.
    """

    url = _run_git_command(["config", "--get", "remote.origin.url"]) or ""

    if not url:
        return ""

    if url.startswith("https://github.com/"):
        return url.replace("https://github.com/", "git@github.com:")

    return url


def get_git_repo_branch() -> str:
    """
    Get the current git branch name.

    Returns:
        The current branch name. Falls back to "main" when detection fails.
    """

    branch = _run_git_command(["rev-parse", "--abbrev-ref", "HEAD"]) or ""
    return branch if branch else "main"


def parse_repo_owner(repo_url: str) -> str:
    """
    Extract the repository owner/organization from a GitHub URL.

    Supports SSH (git@github.com:owner/repo.git) and HTTPS
    (https://github.com/owner/repo.git) formats.

    Args:
        repo_url: Repository URL in SSH or HTTPS form.

    Returns:
        Repository owner/organization, or an empty string if it cannot be parsed.
    """

    if not repo_url:
        return ""

    path = repo_url
    if repo_url.startswith("git@github.com:"):
        path = repo_url.split(":", 1)[1]
    elif repo_url.startswith("https://github.com/"):
        path = repo_url.split("github.com/", 1)[1]

    segments = [s for s in path.split("/") if s]
    if len(segments) < 2:
        return ""
    return segments[0]


def parse_repo_name(repo_url: str) -> str:
    """
    Extract the repository name from a GitHub URL.

    Args:
        repo_url: Repository URL in SSH or HTTPS form.

    Returns:
        Repository name without the trailing ".git" suffix, or an empty string
        if it cannot be parsed.
    """

    if not repo_url:
        return ""

    path = repo_url
    if repo_url.startswith("git@github.com:"):
        path = repo_url.split(":", 1)[1]
    elif repo_url.startswith("https://github.com/"):
        path = repo_url.split("github.com/", 1)[1]

    segments = [s for s in path.split("/") if s]
    if not segments:
        return ""

    repo = segments[-1]
    if repo.endswith(".git"):
        repo = repo[:-4]
    return repo
