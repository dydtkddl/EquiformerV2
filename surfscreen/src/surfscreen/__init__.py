"""
SurfScreen: Enterprise-grade surface adsorption screening platform
"""

__version__ = "0.2.0"

from surfscreen.molecule import MoleculeBuilder
from surfscreen.surface import SurfaceBuilder
from surfscreen.calculator import Calculator, CalculatorFactory
from surfscreen.adsorption import AdsorptionSystem

# MD Engine
from surfscreen.md import MDEngine, MDConfig

# Analysis Suite
from surfscreen.analysis import (
    StructuralAnalyzer,
    DynamicsAnalyzer,
    ThermodynamicAnalyzer
)

# Visualization
from surfscreen.visualization import (
    create_energy_distribution_plot,
    create_msd_plot,
    create_rdf_plot,
    create_boltzmann_plot,
    create_arrhenius_plot
)

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
    
    # Analysis
    "StructuralAnalyzer",
    "DynamicsAnalyzer",
    "ThermodynamicAnalyzer",
    
    # Visualization
    "create_energy_distribution_plot",
    "create_msd_plot",
    "create_rdf_plot",
    "create_boltzmann_plot",
    "create_arrhenius_plot",
]
