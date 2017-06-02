#!/bin/bash

#===== PATHS ===== #
tablesheet="test_dataset/TableSheet_test.csv"
path2configfile="./config.json"
path2programsJSON="test_dataset/PROGS.json"

#========================================================================================
#----------  CREATE CONFIG FILE:  ----------------------------------------------

scripts/create_configfile.py $tablesheet $path2configfile $path2programsJSON

#========================================================================================
#----------  NOW START RUNNING SNAKEMAKE:  ----------------------------------------------

pathout=$( python -c "import sys, json; print(json.load(sys.stdin)['PATHOUT'])" < $path2configfile)

snakemake -s BSseq_pipeline.py --configfile $path2configfile -d $pathout
