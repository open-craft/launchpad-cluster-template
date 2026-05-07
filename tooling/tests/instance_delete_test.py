"""
Tests for instance deletion helpers.
"""

import subprocess
from unittest import mock

import pytest

from launchpad.cli import instance_delete
from launchpad.exceptions import KubernetesError


class TestCreateDeprovisionWorkflows:
    """Tests for _create_deprovision_workflows."""

    @mock.patch("launchpad.cli.instance_delete.wait_for_workflow_completion")
    @mock.patch("launchpad.cli.instance_delete.run_command_with_logging")
    def test_raises_when_any_workflow_fails(self, _mock_rcl, mock_wait):
        mock_wait.side_effect = [True, False, True]

        with pytest.raises(KubernetesError, match="MongoDB"):
            instance_delete._create_deprovision_workflows(
                mock.Mock(),
                "test-instance",
                "https://example.com/manifests",
                {},
            )

        assert mock_wait.call_count == 3

    @mock.patch("launchpad.cli.instance_delete.log_success")
    @mock.patch("launchpad.cli.instance_delete.subprocess.run")
    @mock.patch("launchpad.cli.instance_delete.wait_for_workflow_completion")
    @mock.patch("launchpad.cli.instance_delete.run_command_with_logging")
    def test_succeeds_and_cleans_workflows_when_all_complete(
        self, _mock_rcl, mock_wait, mock_subprocess_run, mock_log_success
    ):
        mock_wait.return_value = True

        instance_delete._create_deprovision_workflows(
            mock.Mock(),
            "test-instance",
            "https://example.com/manifests",
            {},
        )

        mock_log_success.assert_called_once()
        delete_calls = [
            c
            for c in mock_subprocess_run.call_args_list
            if c[0][0][:3] == ["kubectl", "delete", "workflow"]
        ]
        assert len(delete_calls) == 3


class TestWaitForNamespaceAbsent:
    """Tests for _wait_for_namespace_absent."""

    @mock.patch("launchpad.cli.instance_delete.time.sleep")
    @mock.patch("launchpad.cli.instance_delete.subprocess.run")
    @mock.patch("launchpad.cli.instance_delete.time.monotonic")
    def test_returns_immediately_when_namespace_missing(
        self, mock_mono, mock_run, _mock_sleep
    ):
        mock_mono.side_effect = [0.0, 1.0]
        mock_run.return_value = subprocess.CompletedProcess(
            ["kubectl", "get", "namespace", "ns-a"],
            returncode=1,
            stdout="",
            stderr='Error from server (NotFound): namespaces "ns-a" not found',
        )

        instance_delete._wait_for_namespace_absent(
            "ns-a", timeout_s=30, poll_interval_s=1.0
        )

        mock_run.assert_called_once()
        assert mock_run.call_args[0][0][:4] == ["kubectl", "get", "namespace", "ns-a"]

    @mock.patch("launchpad.cli.instance_delete.time.sleep")
    @mock.patch("launchpad.cli.instance_delete.subprocess.run")
    @mock.patch("launchpad.cli.instance_delete.time.monotonic")
    def test_succeeds_after_namespace_disappears(
        self, mock_mono, mock_run, _mock_sleep
    ):
        mock_mono.side_effect = [0.0, 2.0, 4.0, 6.0]
        mock_run.side_effect = [
            subprocess.CompletedProcess(
                ["kubectl", "get", "namespace", "ns-b"],
                returncode=0,
                stdout="ns-b   Active\n",
                stderr="",
            ),
            subprocess.CompletedProcess(
                ["kubectl", "get", "namespace", "ns-b"],
                returncode=0,
                stdout="ns-b   Terminating\n",
                stderr="",
            ),
            subprocess.CompletedProcess(
                ["kubectl", "get", "namespace", "ns-b"],
                returncode=1,
                stdout="",
                stderr="not found",
            ),
        ]

        instance_delete._wait_for_namespace_absent(
            "ns-b", timeout_s=30, poll_interval_s=1.0
        )

        assert mock_run.call_count == 3

    @mock.patch("launchpad.cli.instance_delete.time.sleep")
    @mock.patch("launchpad.cli.instance_delete.subprocess.run")
    @mock.patch("launchpad.cli.instance_delete.time.monotonic")
    def test_times_out_when_namespace_remains(self, mock_mono, mock_run, _mock_sleep):
        mock_mono.side_effect = [0.0, 2.0, 4.0, 11.0]
        mock_run.return_value = subprocess.CompletedProcess(
            ["kubectl", "get", "namespace", "ns-c"],
            returncode=0,
            stdout="ns-c   Terminating\n",
            stderr="",
        )

        with pytest.raises(KubernetesError, match="Timed out after 10s"):
            instance_delete._wait_for_namespace_absent(
                "ns-c", timeout_s=10, poll_interval_s=1.0
            )

        assert mock_run.call_count >= 2


class TestDeleteNamespaceWithRetry:
    """Tests for _delete_namespace_with_retry."""

    @mock.patch("launchpad.cli.instance_delete._wait_for_namespace_absent")
    @mock.patch("launchpad.cli.instance_delete.subprocess.run")
    def test_succeeds_on_second_round(self, mock_run, mock_wait):
        ok = subprocess.CompletedProcess(
            ["kubectl", "delete", "namespace", "ns-d"],
            returncode=0,
            stdout='namespace "ns-d" deleted\n',
            stderr="",
        )
        mock_run.return_value = ok
        mock_wait.side_effect = [
            KubernetesError("timed out round 1"),
            None,
        ]

        instance_delete._delete_namespace_with_retry("ns-d")

        assert mock_wait.call_count == 2
        delete_calls = [
            c
            for c in mock_run.call_args_list
            if c[0][0][:3] == ["kubectl", "delete", "namespace"]
        ]
        assert len(delete_calls) == 2

    @mock.patch("launchpad.cli.instance_delete._wait_for_namespace_absent")
    @mock.patch("launchpad.cli.instance_delete.subprocess.run")
    def test_raises_after_all_rounds_exhausted(self, mock_run, mock_wait):
        mock_run.return_value = subprocess.CompletedProcess(
            ["kubectl", "delete", "namespace", "ns-e"],
            returncode=0,
            stdout="",
            stderr="",
        )
        mock_wait.side_effect = KubernetesError("still there")

        with pytest.raises(KubernetesError, match="Failed to delete namespace 'ns-e'"):
            instance_delete._delete_namespace_with_retry("ns-e")

        assert mock_wait.call_count == instance_delete.NAMESPACE_DELETE_RETRY
