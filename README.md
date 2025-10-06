# Tool for evaluation of Wire-Cell clustering


## Goal

A tool for evaluating the performance of WireCell clustering algorithm. Make a full chain of sample generation, wirecell simulation, signal processing, imaging and clustering. Evaluate the performance of the clustering algorithm based on two metrics: charge-weighted efficiency and purity.

## How to get the code:

git clone https://github.com/ebelchio12/wirecell-clustering.git

## Requirements:

This tool requires python, matplotlib, sklearn and jupyter-notebook.

## File details:

- **Clustering v0_30_2.ipynb**
  - General information on how to setup sbndcode, larreco, wirecell, etc. Look at this notebook first.
  - Open a web browser and paste: *http://localhost:8888/tree*
    - Navigate through folders until you find the notebook. Click on it to open.

- **create_cluster_samples.sh**
  - bash script to run a full chain of sample generation, wirecell simulation, signal processing, imaging and clustering. Saves output in .txt format for clustering evaluation.
    - Usage: *bash create_cluster_samples.sh*

- **main_cluster_eval.ipynb**
  - Driver notebook to run the evaluation of Wire-Cell clustering with the help of an external notebook (clustering_eval.ipynb).
    - Log in to your sbndgpvm02 area and download the code:<br>
      *git clone https://github.com/ebelchio12/wirecell-clustering.git*
      - Setup any version of sbndcode:
        - *source /cvmfs/sbnd.opensciencegrid.org/products/sbnd/setup_sbnd.sh*
        - *setup sbndcode v09_91_02 -q e26:prof*
      - Start jupyter:
        - *~/.local/bin/jupyter-notebook --MultiKernelManager.default_kernel_name=bash --no-browser --port=8080*
    - On your local machine/laptop:
      - Create an SSH tunnel: *ssh -L 8080:localhost:8080 username@sbndgpvm02.fnal.gov*
      - Open a web browser and paste: *http://localhost:8080/tree*
      - Click on *wirecell-clustering > main_cluster_eval.ipynb*
      - Go to the top of the notebook and click *Run > Run All Cells*
   
- **clustering_eval.ipynb**
  - an external notebook to be run by main_cluster_eval.ipynb. It is automatically run.


