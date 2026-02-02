"""
SurfScreen CLI - API Commands

REST API 서버 관리 명령어
"""

import os
import secrets
import click
from pathlib import Path

from surfscreen.cli.utils import console


# ============ API Command Group ============

@click.group(name="api")
def api_group():
    """REST API server operations"""
    pass


@api_group.command("start")
@click.option("--host", "-h", default="0.0.0.0", help="Server host")
@click.option("--port", "-p", default=8000, type=int, help="Server port")
@click.option("--reload", "-r", is_flag=True, help="Enable auto-reload (dev mode)")
@click.option("--workers", "-w", default=1, type=int, help="Number of workers")
@click.option("--debug", is_flag=True, help="Enable debug mode (no auth)")
def api_start(host, port, reload, workers, debug):
    """Start the REST API server"""
    console.print("\n[bold cyan]🚀 Starting SurfScreen API Server[/bold cyan]\n")
    console.print(f"  Host: {host}")
    console.print(f"  Port: {port}")
    console.print(f"  Workers: {workers}")
    console.print(f"  Reload: {reload}")
    console.print(f"  Debug: {debug}")
    console.print()
    
    if debug:
        os.environ["SURFSCREEN_DEBUG"] = "true"
        console.print("[yellow]⚠ Debug mode enabled - API key authentication disabled[/yellow]\n")
    
    try:
        import uvicorn
        
        console.print(f"[green]✓[/green] API Docs: http://{host}:{port}/docs")
        console.print(f"[green]✓[/green] ReDoc: http://{host}:{port}/redoc")
        console.print(f"[green]✓[/green] OpenAPI: http://{host}:{port}/openapi.json")
        console.print()
        
        uvicorn.run(
            "surfscreen.api.main:app",
            host=host,
            port=port,
            reload=reload,
            workers=workers if not reload else 1
        )
        
    except ImportError:
        console.print("[red]Error: uvicorn not installed[/red]")
        console.print("Install with: pip install uvicorn[standard]")
    except Exception as e:
        console.print(f"[red]Error starting server: {e}[/red]")


@api_group.command("generate-key")
@click.option("--length", "-l", default=32, type=int, help="Key length")
def api_generate_key(length):
    """Generate a new API key"""
    key = secrets.token_urlsafe(length)
    
    console.print("\n[bold]🔑 New API Key Generated[/bold]\n")
    console.print(f"  [cyan]{key}[/cyan]\n")
    console.print("Add to your .env file:")
    console.print(f"  SURFSCREEN_API_KEY={key}\n")
    console.print("Or set as environment variable:")
    console.print(f"  export SURFSCREEN_API_KEY={key}")


@api_group.command("docs")
@click.option("--port", "-p", default=8000, type=int, help="Server port")
def api_docs(port):
    """Show API documentation URLs"""
    console.print("\n[bold]📚 SurfScreen API Documentation[/bold]\n")
    console.print(f"  Swagger UI: http://localhost:{port}/docs")
    console.print(f"  ReDoc: http://localhost:{port}/redoc")
    console.print(f"  OpenAPI JSON: http://localhost:{port}/openapi.json")


@api_group.command("export-schema")
@click.option("--output", "-o", default="openapi.json", help="Output file path")
def api_export_schema(output):
    """Export OpenAPI schema to JSON file"""
    console.print("\n[bold]📄 Exporting OpenAPI Schema[/bold]\n")
    
    try:
        from surfscreen.api.main import app
        import json
        
        schema = app.openapi()
        
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w") as f:
            json.dump(schema, f, indent=2)
        
        console.print(f"[green]✓[/green] Schema exported to: {output_path.absolute()}")
        
    except ImportError as e:
        console.print(f"[red]Error: {e}[/red]")
        console.print("Make sure FastAPI is installed: pip install fastapi")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@api_group.command("status")
@click.option("--host", "-h", default="localhost", help="API host")
@click.option("--port", "-p", default=8000, type=int, help="API port")
def api_status(host, port):
    """Check API server status"""
    import urllib.request
    import urllib.error
    import json
    
    console.print(f"\n[bold]🔍 Checking API Status at {host}:{port}[/bold]\n")
    
    try:
        url = f"http://{host}:{port}/health"
        
        with urllib.request.urlopen(url, timeout=5) as response:
            data = json.loads(response.read().decode())
            
            console.print(f"[green]✓[/green] Status: {data.get('status', 'unknown')}")
            console.print(f"  Version: {data.get('version', 'unknown')}")
            console.print(f"  Engines: {', '.join(data.get('engines', []))}")
            
    except urllib.error.URLError:
        console.print(f"[red]✗[/red] Server not responding at {host}:{port}")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@api_group.command("jobs")
@click.option("--host", "-h", default="localhost", help="API host")
@click.option("--port", "-p", default=8000, type=int, help="API port")
@click.option("--status", "-s", default=None, help="Filter by status")
@click.option("--api-key", "-k", default=None, help="API key (or set SURFSCREEN_API_KEY)")
def api_jobs(host, port, status, api_key):
    """List jobs from running API server"""
    import urllib.request
    import urllib.error
    import json
    
    key = api_key or os.environ.get("SURFSCREEN_API_KEY", "dev-key-change-me")
    
    console.print(f"\n[bold]📋 Jobs from {host}:{port}[/bold]\n")
    
    try:
        url = f"http://{host}:{port}/api/v1/jobs"
        if status:
            url += f"?status_filter={status}"
        
        req = urllib.request.Request(url)
        req.add_header("X-API-Key", key)
        
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            jobs = data.get("jobs", [])
            
            if not jobs:
                console.print("  No jobs found")
                return
            
            from rich.table import Table
            table = Table()
            table.add_column("ID", style="cyan")
            table.add_column("Type", style="green")
            table.add_column("Status")
            table.add_column("Progress")
            table.add_column("Created")
            
            for job in jobs:
                status_style = {
                    "pending": "yellow",
                    "running": "blue",
                    "completed": "green",
                    "failed": "red",
                    "cancelled": "dim"
                }.get(job.get("status"), "")
                
                table.add_row(
                    job.get("job_id", ""),
                    job.get("job_type", ""),
                    f"[{status_style}]{job.get('status', '')}[/{status_style}]",
                    f"{job.get('progress', 0):.1f}%",
                    job.get("created_at", "")[:19] if job.get("created_at") else ""
                )
            
            console.print(table)
            
    except urllib.error.URLError as e:
        console.print(f"[red]✗[/red] Connection error: {e}")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


__all__ = ["api_group"]
