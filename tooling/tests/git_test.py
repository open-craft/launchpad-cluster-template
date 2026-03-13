"""
Unit tests for launchpad.git helpers.
"""

from unittest.mock import Mock, patch

import pytest

from launchpad.git import (
    get_git_repo_branch,
    get_git_repo_url,
    parse_repo_name,
    parse_repo_owner,
)


class TestGitUrlDetection:
    @patch("subprocess.run")
    def test_https_to_ssh_conversion(self, mrun):
        mrun.return_value = Mock(stdout="https://github.com/open-craft/repo.git\n")
        url = get_git_repo_url()
        assert url == "git@github.com:open-craft/repo.git"

    @patch("subprocess.run")
    def test_ssh_preserved(self, mrun):
        mrun.return_value = Mock(stdout="git@github.com:open-craft/repo.git\n")
        url = get_git_repo_url()
        assert url == "git@github.com:open-craft/repo.git"

    @patch("subprocess.run", side_effect=FileNotFoundError())
    def test_missing_url_returns_empty(self, _mrun):
        assert get_git_repo_url() == ""


class TestGitBranchDetection:
    @patch("subprocess.run")
    def test_branch_detected(self, mrun):
        mrun.return_value = Mock(stdout="feature-branch\n")
        assert get_git_repo_branch() == "feature-branch"

    @patch("subprocess.run", side_effect=FileNotFoundError())
    def test_branch_fallback_main(self, _mrun):
        assert get_git_repo_branch() == "main"


class TestParsing:
    @pytest.mark.parametrize(
        "url,owner",
        [
            ("git@github.com:open-craft/repo.git", "open-craft"),
            ("https://github.com/open-craft/repo.git", "open-craft"),
            ("", ""),
        ],
    )
    def test_parse_repo_owner(self, url, owner):
        assert parse_repo_owner(url) == owner

    @pytest.mark.parametrize(
        "url,name",
        [
            ("git@github.com:open-craft/repo.git", "repo"),
            ("https://github.com/open-craft/repo.git", "repo"),
            ("https://github.com/open-craft/repo", "repo"),
            ("", ""),
        ],
    )
    def test_parse_repo_name(self, url, name):
        assert parse_repo_name(url) == name
