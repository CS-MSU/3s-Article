#!/bin/bash
# We assume running this from the script directory
job_directory=$PWD/.job
# data_dir="${SCRATCH}/project/LizardLips"
for i in {4..8};do
    for j in {1..3};do
        echo $i $j
        job_file="${job_directory}/WOFOST${i}${j}.job"

        echo "#!/bin/bash
#SBATCH --job-name=${i}${j}_WOFOST.job
#SBATCH --output=$HOME/agriculture/3s-Article/.out/OUT_${i}${j}.out
#SBATCH --error=$HOME/agriculture/3s-Article/.out/ERR_${i}${j}.err
#SBATCH --time=1-00:00
#SBATCH --mem=8000
#SBATCH --ntasks=1
#SBATCH --partition=cpu
/trinity/shared/opt/python-3.6.8/bin/python3.6 $HOME/agriculture/3s-Article/run_wofost.py --x1 ${i} --x2 ${j}" > $job_file
    sbatch $job_file
    done
done
