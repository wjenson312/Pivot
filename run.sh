#!/bin/bash
# Clean runner script that removes all conda interference

# Unset ALL conda-related environment variables
unset CONDA_EXE
unset CONDA_PYTHON_EXE
unset CONDA_SHLVL
unset CONDA_PREFIX
unset CONDA_DEFAULT_ENV
unset CONDA_PROMPT_MODIFIER
unset _CE_CONDA
unset GSETTINGS_SCHEMA_DIR_CONDA_BACKUP
unset GSETTINGS_SCHEMA_DIR
unset PROJ_LIB

# Remove conda from PATH
export PATH=$(echo $PATH | sed -e 's|/opt/anaconda3/bin:||g' -e 's|/opt/anaconda3/condabin:||g' -e 's|:/opt/anaconda3/bin||g' -e 's|:/opt/anaconda3/condabin||g')

# Activate the virtual environment in clean state
source .venv/bin/activate

# Run the application
python "$@"
