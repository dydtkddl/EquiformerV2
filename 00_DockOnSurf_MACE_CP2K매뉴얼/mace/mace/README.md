This directory contains various example input files for running DockOnSurf with MACE.

To avoid integrating MACE directly into the DockOnSurf environment, 
we use an approach where we generate a script from the input file (run_opt.py). 
An example of the run_opt.py files created by DockOnSurf is provided. 
This script can be run with a .gen coordinates file format in a MACE environment, 
provided the correct path to the model is set up. 

Thus, in the DockOnsurf procedure, the script is executed in a separated environment where MACE and Torch are installed.

To use this setup in a SLURM queue system, follow these steps:

    1. Load the DockOnSurf environment.
    2. Use a submission script (.sh file in the DOS.inp) which deactivate the DockOnSurf environment and activate the environment with MACE and Torch installed.

To install the MACE environment, we recommend following the procedure outlined in the official documentation:

https://mace-docs.readthedocs.io/en/latest/guide/installation.html