"""Sandbox's Docker path built its command via shell=True string
concatenation of caller-supplied image/command/memory_limit/cpu_limit —
shell metacharacters in any of those fields executed on the HOST shell
before docker even started, defeating the container isolation the endpoint
exists to provide. Its local (non-Docker) path also returned no signal
that no container isolation was used, so a caller (e.g. pr_readiness)
could not tell a real docker-isolated pass from an unsandboxed one.
"""

from __future__ import annotations

from unittest.mock import Mock, patch

from app.domains.workspace.sandbox import SandboxDockerRequest, _run_docker_sandbox, _run_local_sandbox, pr_readiness


class TestDockerSandboxNotShellInjectable:
    def test_builds_argv_list_not_a_shell_string(self):
        fake_result = Mock(returncode=0, stdout="ok", stderr="")
        with patch("app.domains.workspace.sandbox.shutil.which", return_value="/usr/bin/docker"), \
             patch("app.domains.workspace.sandbox.subprocess.run", return_value=fake_result) as mock_run:
            _run_docker_sandbox(SandboxDockerRequest(image="python:3.11-slim", command="python main.py"))

        args, kwargs = mock_run.call_args
        assert isinstance(args[0], list), "command must be an argv list, not a shell string"
        assert kwargs.get("shell") is False

    def test_malicious_command_field_never_reaches_a_host_shell(self):
        """A `; ` or backtick in image/command used to break out of the
        container BEFORE docker even ran, since the whole thing was one
        shell=True string. With shell=False + an argv list, the malicious
        text is just one inert argv element — it can only ever run inside
        the container's own /bin/sh, not the host's."""
        fake_result = Mock(returncode=0, stdout="", stderr="")
        with patch("app.domains.workspace.sandbox.shutil.which", return_value="/usr/bin/docker"), \
             patch("app.domains.workspace.sandbox.subprocess.run", return_value=fake_result) as mock_run:
            _run_docker_sandbox(
                SandboxDockerRequest(image="python:3.11-slim", command="echo hi; rm -rf /tmp/whatever")
            )

        args, kwargs = mock_run.call_args
        assert kwargs.get("shell") is False
        # The dangerous text is a single argv element, not concatenated into
        # anything the host shell parses.
        assert "echo hi; rm -rf /tmp/whatever" in args[0]

    def test_falls_back_cleanly_when_docker_missing(self):
        with patch("app.domains.workspace.sandbox.shutil.which", return_value=None):
            result = _run_docker_sandbox(SandboxDockerRequest())

        assert result["success"] is False
        assert result["mode"] == "docker_unavailable"


class TestLocalSandboxSurfacesUnsandboxedMode:
    def test_success_result_flags_unsandboxed_mode(self):
        result = _run_local_sandbox("print('hi')", "python", 10, "", None)
        assert result["mode"] == "local_unsandboxed"


class TestPrReadinessSurfacesIsolationMode:
    def test_reports_docker_isolated_false_for_local_fallback(self):
        from app.domains.workspace.sandbox import PRReadinessRequest

        with patch("app.domains.workspace.sandbox.shutil.which", return_value=None):
            out = pr_readiness(PRReadinessRequest(code="print(1)", language="python", prefer_docker=True))

        assert out["docker_isolated"] is False
        assert out["sandbox"]["mode"] == "local_unsandboxed"

    def test_reports_docker_isolated_true_when_docker_actually_used(self):
        from app.domains.workspace.sandbox import PRReadinessRequest

        with patch("app.domains.workspace.sandbox.shutil.which", return_value="/usr/bin/docker"), \
             patch(
                 "app.domains.workspace.sandbox._run_docker_sandbox",
                 return_value={"success": True, "mode": "docker"},
             ):
            out = pr_readiness(PRReadinessRequest(code="print(1)", language="python", prefer_docker=True))

        assert out["docker_isolated"] is True
