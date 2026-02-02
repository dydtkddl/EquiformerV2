"""
SurfScreen CLI - Main Entry Point

모든 명령어 그룹을 통합하는 메인 진입점
"""

import click

from surfscreen.cli.utils import _setup_verbose


@click.group()
@click.version_option(version="0.3.0", prog_name="surfscreen")
@click.option(
    "--verbose", "-v",
    type=click.Choice(['0', '1', '2', '3', '4', 'silent', 'low', 'medium', 'high', 'debug'],
                      case_sensitive=False),
    default='2',
    callback=_setup_verbose,
    expose_value=False,
    is_eager=True,
    help="Verbosity level: 0=silent, 1=low, 2=medium, 3=high, 4=debug"
)
def cli():
    """SurfScreen: Enterprise Surface Adsorption Screening Platform
    
    Use --verbose/-v to control output detail level:
      0/silent : Only errors
      1/low    : Main steps only  
      2/medium : Progress info (default)
      3/high   : Detailed calculations
      4/debug  : Full debugging output
    """
    pass


# ============ Register Command Groups ============

def _register_commands():
    """명령어 그룹 등록"""
    from surfscreen.cli.molecule import molecule_group
    from surfscreen.cli.surface import surface_group
    from surfscreen.cli.screen import screen_group
    from surfscreen.cli.md import md_group
    from surfscreen.cli.analysis import analysis_group
    from surfscreen.cli.export import export_group, plot_group
    from surfscreen.cli.adsorb import config_group, adsorb_group
    from surfscreen.cli.template import template_group, checkpoint_group
    from surfscreen.cli.api import api_group
    from surfscreen.cli.validate import validate as validate_group
    
    cli.add_command(molecule_group, "molecule")
    cli.add_command(surface_group, "surface")
    cli.add_command(screen_group, "screen")
    cli.add_command(md_group, "md")
    cli.add_command(analysis_group, "analysis")
    cli.add_command(export_group, "export")
    cli.add_command(plot_group, "plot")
    cli.add_command(config_group, "config")
    cli.add_command(adsorb_group, "adsorb")
    cli.add_command(template_group, "template")
    cli.add_command(checkpoint_group, "checkpoint")
    cli.add_command(api_group, "api")
    cli.add_command(validate_group, "validate")


# Register on import
_register_commands()


# ============ Convenience Alias ============

main = cli


if __name__ == "__main__":
    cli()
