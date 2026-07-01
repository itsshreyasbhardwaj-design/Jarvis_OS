"""
Terminal Plugin (Example)
==========================
Executes shell commands with explicit user confirmation.
HIGH risk: always requires user approval.
"""

from __future__ import annotations

import asyncio
import subprocess

from jarvis.plugins.base import JarvisPlugin, PluginContext, PluginMetadata


class TerminalPlugin(JarvisPlugin):
    """
    Terminal/shell command execution plugin.

    SAFETY: All command executions are HIGH risk.
    They will always ask for user confirmation regardless of safe_mode.
    """

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="terminal",
            version="0.1.0",
            description="Execute shell commands with user confirmation",
            author="JARVIS OS",
            required_permissions=["high"],
            tags=["terminal", "shell", "developer"],
        )

    async def start(self, context: PluginContext) -> None:
        context.tool_executor.register(
            name="run_command",
            description=(
                "Execute a shell command and return its output. "
                "REQUIRES USER CONFIRMATION before running."
            ),
            parameters={
                "command": {
                    "type": "string",
                    "description": "The shell command to execute",
                },
                "working_dir": {
                    "type": "string",
                    "description": "Working directory (optional)",
                },
                "timeout_seconds": {
                    "type": "integer",
                    "description": "Max execution time in seconds (default: 30)",
                },
            },
            required=["command"],
            requires_confirmation=True,
            risk_level="high",
            timeout_seconds=60.0,
        )(self.run_command)

    async def run_command(
        self,
        command: str,
        working_dir: str | None = None,
        timeout_seconds: int = 30,
    ) -> str:
        """Execute a shell command and return stdout + stderr."""
        try:
            result = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: subprocess.run(
                        command,
                        shell=True,
                        capture_output=True,
                        text=True,
                        cwd=working_dir,
                    ),
                ),
                timeout=float(timeout_seconds),
            )
            output = result.stdout + result.stderr
            return_code = result.returncode
            return (
                f"Exit code: {return_code}\n"
                f"Output:\n{output[:5000] if output else '(no output)'}"
            )
        except TimeoutError:
            return f"Command timed out after {timeout_seconds}s"
        except Exception as e:
            return f"Command failed: {e}"

    async def stop(self) -> None:
        pass
