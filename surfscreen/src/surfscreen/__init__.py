"""
SurfScreen: Enterprise-grade surface adsorption screening platform
"""

__version__ = "0.3.0"

from surfscreen.molecule import MoleculeBuilder
from surfscreen.surface import SurfaceBuilder
from surfscreen.calculator import Calculator, CalculatorFactory
from surfscreen.adsorption import AdsorptionSystem

# MD Engine
from surfscreen.md import MDEngine, MDConfig, MDReportGenerator

# Analysis Suite
from surfscreen.analysis import (
    StructuralAnalyzer,
    DynamicsAnalyzer,
    ThermodynamicAnalyzer,
    PhononAnalyzer,
    CoverageAnalyzer
)

# Visualization
from surfscreen.visualization import (
    create_energy_distribution_plot,
    create_msd_plot,
    create_rdf_plot,
    create_boltzmann_plot,
    create_arrhenius_plot
)

# Export
from surfscreen.export import ExportManager, ExportConfig

# Checkpoint
from surfscreen.checkpoint import CheckpointManager, ScreeningCheckpoint, MDCheckpoint

# Templates
from surfscreen.templates import TemplateEngine, WorkflowTemplate

__all__ = [
    # Core
    "MoleculeBuilder",
    "SurfaceBuilder", 
    "Calculator",
    "CalculatorFactory",
    "AdsorptionSystem",
    
    # MD
    "MDEngine",
    "MDConfig",
    "MDReportGenerator",
    
    # Analysis
    "StructuralAnalyzer",
    "DynamicsAnalyzer",
    "ThermodynamicAnalyzer",
    "PhononAnalyzer",
    "CoverageAnalyzer",
    
    # Visualization
    "create_energy_distribution_plot",
    "create_msd_plot",
    "create_rdf_plot",
    "create_boltzmann_plot",
    "create_arrhenius_plot",
    
    # Export
    "ExportManager",
    "ExportConfig",
    
    # Checkpoint
    "CheckpointManager",
    "ScreeningCheckpoint",
    "MDCheckpoint",
    
    # Templates
    "TemplateEngine",
    "WorkflowTemplate",
]

