"""Main CLI entry point using Typer."""

import json
import os
from pathlib import Path
from typing import Annotated

import typer
import uvicorn
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from mcp_canon import __version__
from mcp_canon.ingestion import (
    DatabaseWriter,
    chunk_content,
    discover_guides,
    resolve_content,
    validate_frontmatter,
)
from mcp_canon.ingestion.writer import compute_content_hash
from mcp_canon.schemas.database import EMBEDDING_MODEL_NAME
from mcp_canon.server.mcp import mcp as mcp_server
from mcp_canon.server.search import SearchEngine

# Default database path: src/mcp_canon/bundled_db (relative to this file)
DEFAULT_DB_PATH = Path(__file__).parent.parent / "bundled_db"

app = typer.Typer(
    name="canon",
    help="MCP server for architectural patterns and best practices.",
    add_completion=False,
)


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        typer.echo(f"mcp-canon v{__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool | None,
        typer.Option(
            "--version",
            "-V",
            help="Show version and exit.",
            callback=version_callback,
            is_eager=True,
        ),
    ] = None,
) -> None:
    """Canon - Architectural Consultant for LLM Agents."""
    pass


@app.command()
def index(
    library: Annotated[
        Path,
        typer.Option(
            "--library",
            "-l",
            help="Path to the library directory with guides.",
            exists=True,
            file_okay=False,
            dir_okay=True,
        ),
    ] = Path("./library"),
    db: Annotated[
        Path,
        typer.Option(
            "--db",
            help="Path to the LanceDB database.",
        ),
    ] = DEFAULT_DB_PATH,
    incremental: Annotated[
        bool,
        typer.Option(
            "--incremental",
            "-i",
            help="Only index changed files.",
        ),
    ] = False,
    append: Annotated[
        bool,
        typer.Option(
            "--append",
            "-a",
            help="Add guides to existing database without removing old data.",
        ),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            "-v",
            help="Verbose output.",
        ),
    ] = False,
) -> None:
    """Index the library into LanceDB."""

    console = Console()

    console.print(f"\n📚 [bold]Canon Indexer v{__version__}[/bold]")
    console.print("━" * 40)
    console.print(f"📁 Library: [cyan]{library}[/cyan]")
    console.print(f"🗄️  Database: [cyan]{db}[/cyan]")
    console.print(f"🧠 Model: [cyan]{EMBEDDING_MODEL_NAME}[/cyan]")
    console.print()

    # Discover guides
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task("🔍 Scanning library...", total=None)
        discovered = discover_guides(library)

    local_count = sum(1 for g in discovered if g.guide_path is not None)
    link_count = len(discovered) - local_count
    console.print(
        f"   Found [green]{len(discovered)}[/green] guides ([cyan]{local_count}[/cyan] local, [blue]{link_count}[/blue] links)"
    )

    if not discovered:
        console.print("\n[yellow]⚠️  No guides found. Add guides to your library.[/yellow]")
        raise typer.Exit(0)

    # Initialize database writer
    writer = DatabaseWriter(db)
    writer.initialize_database(str(library), preserve_existing=append)

    # Get existing guides for incremental/append indexing
    existing_guides = writer.get_existing_guides() if (incremental or append) else {}

    # Track changes
    new_count = 0
    modified_count = 0
    skipped_count = 0
    error_count = 0

    with Progress(console=console) as progress:
        task = progress.add_task("⚙️  Indexing...", total=len(discovered))

        for guide in discovered:
            progress.update(task, advance=1, description=f"⚙️  Indexing {guide.id}...")

            # Validate frontmatter
            result = validate_frontmatter(guide.index_path, guide.guide_name)
            if not result.success:
                console.print(
                    f"   [red]❌[/red] {guide.id}: {result.error_code} - {result.error_message}"
                )
                error_count += 1
                continue

            frontmatter = result.frontmatter
            if frontmatter is None:
                continue

            try:
                # Resolve content
                resolved = resolve_content(frontmatter, guide.index_path.parent)
                content = resolved.content

                # Check for changes (incremental mode)
                if incremental and guide.id in existing_guides:
                    content_hash = compute_content_hash(content)
                    if existing_guides[guide.id] == content_hash:
                        skipped_count += 1
                        if verbose:
                            console.print(f"   [dim]⏭️  Skipped {guide.id} (unchanged)[/dim]")
                        continue
                    modified_count += 1
                else:
                    new_count += 1

                # Chunk content
                chunks = chunk_content(content, guide.id)

                # Delete existing guide if updating
                if guide.id in existing_guides:
                    writer.delete_guide(guide.id)

                # Write to database
                writer.write_guide(
                    guide_id=guide.id,
                    namespace=guide.namespace,
                    frontmatter=frontmatter,
                    content=content,
                    file_path=str(guide.index_path),
                    chunks=chunks,
                )

                if verbose:
                    status = "✨" if guide.id not in existing_guides else "📝"
                    console.print(f"   {status} {guide.id} ({len(chunks)} chunks)")

            except Exception as e:
                console.print(f"   [red]❌[/red] {guide.id}: {e}")
                error_count += 1

    # Update metadata
    writer.update_last_indexed()

    # Create FTS indexes for hybrid search
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task("🔍 Building FTS indexes...", total=None)
        writer.create_fts_indexes()

    # Summary
    console.print()
    console.print("📊 [bold]Changes:[/bold]")
    console.print(f"   ✨ New:      [green]{new_count}[/green] guides")
    console.print(f"   📝 Modified: [yellow]{modified_count}[/yellow] guides")
    if incremental:
        console.print(f"   ⏭️  Skipped:  [dim]{skipped_count}[/dim] guides")
    if error_count:
        console.print(f"   ❌ Errors:   [red]{error_count}[/red] guides")

    console.print()
    console.print("✅ [bold green]Done![/bold green]")
    console.print(f"   📄 Guides: [green]{writer.get_guide_count()}[/green]")
    console.print(f"   📦 Chunks: [green]{writer.get_chunk_count()}[/green]")
    console.print("   🔍 FTS indexes: [green]enabled[/green]")


@app.command()
def serve(
    host: Annotated[
        str,
        typer.Option(
            "--host",
            "-h",
            help="Host to bind to.",
        ),
    ] = "127.0.0.1",
    port: Annotated[
        int,
        typer.Option(
            "--port",
            "-p",
            help="Port to listen on.",
        ),
    ] = 8080,
    db: Annotated[
        Path,
        typer.Option(
            "--db",
            help="Path to the LanceDB database.",
        ),
    ] = DEFAULT_DB_PATH,
) -> None:
    """Start the HTTP MCP server."""
    os.environ["CANON_DB_PATH"] = str(db)

    typer.echo(f"🚀 Starting Canon MCP server on http://{host}:{port}/mcp")
    app_instance = mcp_server.streamable_http_app()
    uvicorn.run(app_instance, host=host, port=port)


@app.command("list")
def list_guides(
    db: Annotated[
        Path,
        typer.Option(
            "--db",
            help="Path to the LanceDB database.",
        ),
    ] = DEFAULT_DB_PATH,
    namespace: Annotated[
        str | None,
        typer.Option(
            "--tech-stack",
            "-t",
            help="Filter by technology stack.",
        ),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            "-j",
            help="Output as JSON.",
        ),
    ] = False,
) -> None:
    """List indexed guides."""

    console = Console()
    engine = SearchEngine(db)

    if not engine.is_initialized():
        console.print("[yellow]⚠️  Database not initialized. Run 'canon index' first.[/yellow]")
        raise typer.Exit(1)

    guides = engine.list_guides(namespace=namespace)

    if json_output:
        typer.echo(json.dumps([g.model_dump() for g in guides], indent=2))
        return

    if not guides:
        console.print("[yellow]No guides found.[/yellow]")
        return

    table = Table(title="📚 Available Guides")
    table.add_column("ID", style="cyan")
    table.add_column("Tech Stack", style="green")
    table.add_column("Tags")
    table.add_column("Description", max_width=50)

    for guide in guides:
        table.add_row(
            guide.id,
            guide.namespace,
            ", ".join(guide.tags[:3]) + ("..." if len(guide.tags) > 3 else ""),
            guide.description[:50] + "..." if len(guide.description) > 50 else guide.description,
        )

    console.print(table)
    console.print(f"\nTotal: [green]{len(guides)}[/green] guides")


@app.command()
def validate(
    library: Annotated[
        Path,
        typer.Option(
            "--library",
            "-l",
            help="Path to the library directory.",
            exists=True,
        ),
    ] = Path("./library"),
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            "-v",
            help="Show details for all files.",
        ),
    ] = False,
) -> None:
    """Validate library structure and frontmatter."""

    console = Console()
    console.print(f"\n🔍 Validating library: [cyan]{library}[/cyan]\n")

    discovered = discover_guides(library)

    if not discovered:
        console.print("[yellow]⚠️  No guides found.[/yellow]")
        raise typer.Exit(0)

    valid_count = 0
    error_count = 0

    for guide in discovered:
        result = validate_frontmatter(guide.index_path, guide.guide_name)

        if result.success:
            valid_count += 1
            if verbose:
                console.print(f"[green]✓[/green] {guide.id}")
        else:
            error_count += 1
            console.print(f"[red]✗[/red] {guide.id}: {result.error_code} - {result.error_message}")

    console.print()
    console.print(f"Valid: [green]{valid_count}[/green], Errors: [red]{error_count}[/red]")

    if error_count > 0:
        raise typer.Exit(1)


@app.command()
def info(
    db: Annotated[
        Path,
        typer.Option(
            "--db",
            help="Path to the LanceDB database.",
        ),
    ] = DEFAULT_DB_PATH,
) -> None:
    """Show database information."""

    console = Console()
    engine = SearchEngine(db)

    db_info = engine.get_database_info()

    console.print("\n🗄️  [bold]Canon Database Info[/bold]")
    console.print("━" * 40)
    console.print(f"📁 Path: [cyan]{db_info.db_path}[/cyan]")
    console.print(
        f"✅ Initialized: {'[green]Yes[/green]' if db_info.initialized else '[red]No[/red]'}"
    )

    if db_info.initialized:
        console.print(f"📄 Guides: [green]{db_info.guides_count}[/green]")
        console.print(f"📦 Chunks: [green]{db_info.chunks_count}[/green]")
        console.print(f"🧠 Model: [cyan]{db_info.model_name}[/cyan]")
        if db_info.last_indexed_at:
            console.print(f"🕐 Last indexed: [dim]{db_info.last_indexed_at}[/dim]")


if __name__ == "__main__":
    app()
