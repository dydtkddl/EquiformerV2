"""
CLI command for running scientific validation.

Usage:
    surfscreen validate --all
    surfscreen validate --units
    surfscreen validate --report output.html
"""

import click
from pathlib import Path
import json


@click.group()
def validate():
    """Scientific validation commands."""
    pass


@validate.command()
@click.option('--output', '-o', type=click.Path(), help='Output report path')
@click.option('--format', '-f', type=click.Choice(['json', 'md', 'html']), default='html')
def units(output, format):
    """Validate all unit conversions."""
    from surfscreen.validation import verify_all_conversions, ValidationReporter
    from surfscreen.validation.physics import ValidationStatus, ValidationResult
    
    click.echo("🔬 Validating unit conversions...")
    
    results = verify_all_conversions()
    reporter = ValidationReporter("Unit Conversion Validation")
    
    for name, passed in results.items():
        reporter.add_result(ValidationResult(
            name=f"Unit Conversion: {name}",
            status=ValidationStatus.PASS if passed else ValidationStatus.FAIL,
            message=f"{name} roundtrip conversion {'passed' if passed else 'failed'}"
        ))
    
    summary = reporter.get_summary()
    click.echo(f"\n✅ PASS: {summary['PASS']}")
    click.echo(f"❌ FAIL: {summary['FAIL']}")
    
    if output:
        output_path = Path(output)
        if format == 'json':
            reporter.to_json(output_path)
        elif format == 'md':
            reporter.to_markdown(output_path)
        else:
            reporter.to_html(output_path)
        click.echo(f"\n📄 Report saved to: {output_path}")
    
    if not reporter.is_valid():
        raise SystemExit(1)


@validate.command()
@click.option('--molecule', '-m', default='CO', help='Molecule name')
@click.option('--surface', '-s', default='Cu(111)', help='Surface name')
@click.option('--energy', '-e', type=float, required=True, help='Calculated E_ads (eV)')
def adsorption(molecule, surface, energy):
    """Validate adsorption energy calculation."""
    from surfscreen.validation import (
        validate_adsorption_energy_range,
        validate_adsorption_vs_reference,
        get_adsorption_reference,
    )
    
    click.echo(f"🔬 Validating {molecule}/{surface} adsorption energy...")
    click.echo(f"   Calculated E_ads = {energy:.3f} eV")
    
    # Check range
    range_result = validate_adsorption_energy_range(energy, "chemisorption")
    click.echo(f"\n{_status_emoji(range_result.status)} {range_result.message}")
    
    # Check vs reference
    ref_result = validate_adsorption_vs_reference(energy, molecule, surface)
    click.echo(f"{_status_emoji(ref_result.status)} {ref_result.message}")
    
    # Show reference if available
    ref = get_adsorption_reference(molecule, surface)
    if ref:
        click.echo(f"\n📚 Reference: {ref.energy_eV:.3f} ± {ref.energy_error:.3f} eV")
        click.echo(f"   Method: {ref.method}")
        click.echo(f"   Source: {ref.reference}")


@validate.command('all')
@click.option('--output', '-o', type=click.Path(), default='validation_report.html')
@click.option('--verbose', '-v', is_flag=True)
def validate_all(output, verbose):
    """Run all validation checks and generate report."""
    import numpy as np
    from surfscreen.validation import (
        ValidationReporter,
        verify_all_conversions,
        validate_adsorption_energy_range,
        ADSORPTION_REFERENCES,
    )
    from surfscreen.validation.physics import ValidationStatus, ValidationResult
    
    click.echo("🔬 Running comprehensive validation suite...")
    reporter = ValidationReporter("SurfScreen Scientific Validation")
    
    # 1. Unit conversions
    click.echo("\n📐 Checking unit conversions...")
    unit_results = verify_all_conversions()
    for name, passed in unit_results.items():
        reporter.add_result(ValidationResult(
            name=f"Unit: {name}",
            status=ValidationStatus.PASS if passed else ValidationStatus.FAIL,
            message=f"{name} conversion {'valid' if passed else 'invalid'}"
        ))
        if verbose:
            click.echo(f"   {'✅' if passed else '❌'} {name}")
    
    # 2. Reference data integrity
    click.echo("\n📚 Checking reference data...")
    for ref in ADSORPTION_REFERENCES:
        valid = ref.energy_eV < 0 and ref.energy_error > 0
        reporter.add_result(ValidationResult(
            name=f"Reference: {ref.molecule}/{ref.surface}",
            status=ValidationStatus.PASS if valid else ValidationStatus.FAIL,
            message=f"E_ads = {ref.energy_eV:.3f} eV ({ref.method})"
        ))
        if verbose:
            click.echo(f"   {'✅' if valid else '❌'} {ref.molecule}/{ref.surface}: {ref.energy_eV:.3f} eV")
    
    # 3. Physical thresholds
    click.echo("\n⚙️ Checking physical thresholds...")
    from surfscreen.validation import VALIDATION_THRESHOLDS
    threshold_checks = [
        ('chemisorption_min < chemisorption_max', 
         VALIDATION_THRESHOLDS['chemisorption_min'] < VALIDATION_THRESHOLDS['chemisorption_max']),
        ('physisorption_min < physisorption_max',
         VALIDATION_THRESHOLDS['physisorption_min'] < VALIDATION_THRESHOLDS['physisorption_max']),
        ('fmax_default > 0',
         VALIDATION_THRESHOLDS['fmax_default'] > 0),
        ('energy_drift_max > 0',
         VALIDATION_THRESHOLDS['energy_drift_max'] > 0),
    ]
    
    for name, valid in threshold_checks:
        reporter.add_result(ValidationResult(
            name=f"Threshold: {name}",
            status=ValidationStatus.PASS if valid else ValidationStatus.FAIL,
            message=name
        ))
        if verbose:
            click.echo(f"   {'✅' if valid else '❌'} {name}")
    
    # Summary
    summary = reporter.get_summary()
    click.echo(f"\n{'='*50}")
    click.echo(f"📊 SUMMARY")
    click.echo(f"   ✅ PASS: {summary['PASS']}")
    click.echo(f"   ❌ FAIL: {summary['FAIL']}")
    click.echo(f"   ⚠️ WARNING: {summary['WARNING']}")
    click.echo(f"{'='*50}")
    
    if reporter.is_valid():
        click.echo("\n✅ All validations PASSED")
    else:
        click.echo("\n❌ Some validations FAILED")
    
    # Save report
    output_path = Path(output)
    reporter.to_html(output_path)
    click.echo(f"\n📄 Report saved to: {output_path.absolute()}")
    
    if not reporter.is_valid():
        raise SystemExit(1)


def _status_emoji(status):
    """Get emoji for validation status."""
    from surfscreen.validation.physics import ValidationStatus
    return {
        ValidationStatus.PASS: "✅",
        ValidationStatus.FAIL: "❌",
        ValidationStatus.WARNING: "⚠️",
        ValidationStatus.SKIPPED: "⏭️",
    }.get(status, "❓")
