"""
SurfScreen CLI - Template & Checkpoint Commands

워크플로우 템플릿 및 체크포인트 관리 명령어
"""

import click
from pathlib import Path

from surfscreen.cli.utils import console, Table


# ============ Template Command Group ============

@click.group(name="template")
def template_group():
    """Workflow template management"""
    pass


@template_group.command("list")
def template_list():
    """List available templates"""
    from surfscreen.templates import TemplateEngine
    
    engine = TemplateEngine()
    templates = engine.list_templates()
    
    if not templates:
        console.print("[yellow]No templates found. Run 'surfscreen template install-defaults' first.[/yellow]")
        return
        
    table = Table(title="Available Templates")
    table.add_column("Name")
    table.add_column("Description")
    table.add_column("Version")
    
    for t in templates:
        table.add_row(t["name"], t["description"], t["version"])
        
    console.print(table)


@template_group.command("install-defaults")
def template_install_defaults():
    """Install default workflow templates"""
    from surfscreen.templates import install_default_templates
    
    console.print("[bold]Installing default templates...[/bold]")
    install_default_templates()
    console.print("[green]✓[/green] Default templates installed")


@template_group.command("run")
@click.argument("template_name")
@click.option("--var", "-v", multiple=True, help="Variable override (key=value)")
@click.option("--dry-run", is_flag=True, help="Show commands without executing")
@click.option("--output-dir", "-o", default=".", help="Working directory")
def template_run(template_name, var, dry_run, output_dir):
    """Run a workflow template"""
    from surfscreen.templates import TemplateEngine
    
    variables = {}
    for v in var:
        if "=" in v:
            key, value = v.split("=", 1)
            variables[key] = value
            
    engine = TemplateEngine()
    result = engine.run_template(template_name, variables, dry_run=dry_run, output_dir=output_dir)
    
    if result["success"]:
        console.print("[green]✓[/green] Template completed successfully")
    else:
        console.print("[red]✗[/red] Template failed")


# ============ Checkpoint Command Group ============

@click.group(name="checkpoint")
def checkpoint_group():
    """Checkpoint and resume management"""
    pass


@checkpoint_group.command("status")
@click.argument("checkpoint_dir")
def checkpoint_status(checkpoint_dir):
    """Show checkpoint status"""
    from surfscreen.checkpoint import CheckpointManager
    
    manager = CheckpointManager(checkpoint_dir)
    status = manager.get_status()
    
    console.print(f"\n[bold]📍 Checkpoint: {checkpoint_dir}[/bold]\n")
    console.print(f"Total tasks: {status['total']}")
    console.print(f"Completed: {status['completed']}")
    console.print(f"Pending: {status['pending']}")
    console.print(f"Failed: {status['failed']}")


@checkpoint_group.command("reset-failed")
@click.argument("checkpoint_dir")
@click.option("--confirm", is_flag=True, help="Skip confirmation")
def checkpoint_reset_failed(checkpoint_dir, confirm):
    """Reset failed tasks to pending"""
    from surfscreen.checkpoint import CheckpointManager
    
    manager = CheckpointManager(checkpoint_dir)
    failed_count = manager.count_failed()
    
    if failed_count == 0:
        console.print("[green]No failed tasks to reset[/green]")
        return
    
    if not confirm:
        if not click.confirm(f"Reset {failed_count} failed tasks to pending?"):
            return
    
    manager.reset_failed()
    console.print(f"[green]✓[/green] Reset {failed_count} tasks to pending")


@checkpoint_group.command("list-pending")
@click.argument("checkpoint_dir")
@click.option("--limit", "-n", default=10, help="Max items to show")
def checkpoint_list_pending(checkpoint_dir, limit):
    """List pending tasks"""
    from surfscreen.checkpoint import CheckpointManager
    
    manager = CheckpointManager(checkpoint_dir)
    pending = manager.list_pending(limit=limit)
    
    console.print(f"\n[bold]⏳ Pending tasks ({len(pending)})[/bold]\n")
    for task in pending:
        console.print(f"  • {task['name']}")


@checkpoint_group.command("clean")
@click.argument("checkpoint_dir")
@click.option("--force", is_flag=True, help="Skip confirmation")
def checkpoint_clean(checkpoint_dir, force):
    """Delete checkpoint and start fresh"""
    import shutil
    
    if not force:
        if not click.confirm(f"Delete all checkpoints in {checkpoint_dir}?"):
            return
    
    path = Path(checkpoint_dir)
    if path.exists():
        shutil.rmtree(path)
        console.print(f"[green]✓[/green] Checkpoint deleted: {checkpoint_dir}")
    else:
        console.print(f"[yellow]Checkpoint not found: {checkpoint_dir}[/yellow]")


__all__ = ["template_group", "checkpoint_group"]
