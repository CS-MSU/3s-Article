#!/bin/bash
#SBATCH --partition=nomosix
#SBATCH --job-name=wofost
#SBATCH --mem=4G
#SBATCH --time=5-0:0
#SBATCH --output=wofost.slurm.log
Rscript /net/wonderland/home/foo/myscript.R


