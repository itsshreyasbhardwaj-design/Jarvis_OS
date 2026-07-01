"""
JARVIS OS — Command Line Interface
Provides developer commands for managing JARVIS.

Stack (v2): typer replaces click (drop-in, type-hint native, 18.3k ⭐)
"""

from __future__ import annotations

import asyncio

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(
    name="jarvis",
    help="JARVIS OS — AI Personal Desktop Assistant",
    pretty_exceptions_enable=False,
)
console = Console()


@app.command()
def start() -> None:
    """Start JARVIS OS in the foreground."""
    from jarvis.core.application import JarvisOS
    jarvis = JarvisOS()
    console.print("[bold green]Starting JARVIS OS...[/bold green]")
    jarvis.run()


@app.command()
def health() -> None:
    """Check the health of all JARVIS modules."""
    from jarvis.core.application import JarvisOS

    async def _check() -> None:
        jarvis = JarvisOS()
        await jarvis.start()
        statuses = await jarvis.health()

        table = Table(title="JARVIS OS Health Check")
        table.add_column("Module", style="cyan")
        table.add_column("Status")
        table.add_column("Message")

        for s in statuses:
            status = "[green]✓ Healthy[/green]" if s["healthy"] else "[red]✗ Unhealthy[/red]"
            table.add_row(s["module"], status, s.get("message", ""))

        console.print(table)
        await jarvis.stop()

    asyncio.run(_check())


@app.command()
def config() -> None:
    """Show current configuration (redacts secrets)."""
    from jarvis.config.settings import Settings
    settings = Settings()

    table = Table(title="JARVIS OS Configuration")
    table.add_column("Key", style="cyan")
    table.add_column("Value")

    for key, value in settings.model_dump().items():
        display = "***" if "key" in key.lower() or "secret" in key.lower() else str(value)
        table.add_row(key, display)

    console.print(table)


@app.command()
def install_plugin(plugin_name: str = typer.Argument(..., help="Plugin name to install")) -> None:
    """Install a JARVIS plugin."""
    console.print(f"Installing plugin: [cyan]{plugin_name}[/cyan]...")
    console.print("[yellow]Plugin system will be available in Phase 2.[/yellow]")


@app.command()
def chat() -> None:
    """Have a typed conversation with JARVIS (memory + LLM + web search)."""
    from dotenv import load_dotenv

    from jarvis.ai.agent import JarvisAgent
    from jarvis.ai.conversation import ConversationEngine
    from jarvis.ai.llm_router import LLMRouter
    from jarvis.ai.tools import build_tool_executor
    from jarvis.config.settings import Settings
    from jarvis.desktop.permissions import PermissionManager
    from jarvis.integrations.web_search import WebSearch
    from jarvis.memory.memory_manager import MemoryManager

    load_dotenv()  # let an ANTHROPIC_API_KEY in .env reach the LLM

    async def _run() -> None:
        settings = Settings()
        memory = MemoryManager(settings)
        await memory.initialize(title="CLI chat")
        router = LLMRouter(settings)
        engine = ConversationEngine(router, memory)
        tools = build_tool_executor(
            web_search=WebSearch(),
            permissions=PermissionManager(require_confirmation=False, safe_mode=False),
        )
        agent = JarvisAgent(engine, tools=tools)

        console.print("[bold cyan]JARVIS[/bold cyan] — type 'exit' or Ctrl-D to quit.")
        console.print("[dim]Try: \"search for the tallest mountain\"[/dim]")
        if not router.is_live():
            console.print(
                "[yellow]Offline mode — set ANTHROPIC_API_KEY and "
                "`uv pip install litellm` for full intelligence.[/yellow]"
            )
        try:
            while True:
                try:
                    user = console.input("[bold green]you >[/bold green] ")
                except (EOFError, KeyboardInterrupt):
                    break
                if user.strip().lower() in {"exit", "quit", ":q"}:
                    break
                if not user.strip():
                    continue
                reply = await agent.handle(user)
                console.print(f"[bold cyan]jarvis >[/bold cyan] {reply}")
        finally:
            await memory.close()
            console.print("\n[dim]Session saved. Goodbye.[/dim]")

    asyncio.run(_run())


@app.command(name="console")
def web_console(port: int = 8765) -> None:
    """Launch the JARVIS web console (voice + high-tech UI) in your browser."""
    import threading
    import webbrowser

    import uvicorn
    from dotenv import load_dotenv

    load_dotenv()
    url = f"http://127.0.0.1:{port}"
    console.print(f"[bold cyan]JARVIS Console[/bold cyan]  ->  {url}")
    console.print("[dim]Allow the microphone when prompted. Press Ctrl-C to stop.[/dim]")
    threading.Timer(1.6, lambda: webbrowser.open(url)).start()
    uvicorn.run("jarvis.web.server:app", host="127.0.0.1", port=port, log_level="warning")


# Entry point for `jarvis-cli` console script
def cli() -> None:
    app()


if __name__ == "__main__":
    app()
