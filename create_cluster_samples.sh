# File: create_cluster_samples.sh
# Author: Ewerton Belchior
#
# Goal: Script to generate samples, run wirecell sigproc/img/clustering and save output in txt format for evaluation
#
# Usage: bash create_cluster_samples.sh
#

#!/bin/bash

# choose sbndcode version. This is used for folder naming only.
SBNDCODE_VERSION="v10_04_07"
# choose process: "cosmics", "nu_spill", "nuecc", "numucc" or "data".
PROCESS="cosmics"
# [data only] choose run
RUN="14766"
# events to process. Should be greater than 0.
NEVT=10
# [MC only] Use CellTree module to dump waveforms from Signal Processing step: true or false.
DUMPWAVEFORM=false
# [MC only] Use CellTree module to save simEdepos from APA in JSON. APA should be consistent with the save_apa parameter defined in FCL_CELLTREE: "apa0" or "apa1".
TRUTHDEPOS_SAVEAPA="apa0"

# set DIR
WORKDIR=/exp/sbnd/data/users/$USER/Wirecell_Clustering/work
OUTDIR=/exp/sbnd/data/users/$USER/Wirecell_Clustering/out

# FCLs for various steps
FCL_GEN=""
#FCL_G4=g4_sce_lite_ew.fcl # for sbndcode v09_91_02
FCL_G4=standard_g4_sbnd.fcl # for sbndcode v10_04_07
FCL_SIGPROC=wirecell_sim_sp_sbnd.fcl
FCL_IMGCLUS=$WORKDIR/wcp-porting-img/sbnd/wcls-img-clus.fcl
FCL_CELLTREE=$WORKDIR/larsoft_v10_04_07/srcs/larreco/larreco/WireCell/celltree_sbnd.fcl # APA in this fcl should be consistent with the one defined above in TRUTHDEPOS_SAVEAPA.

# ROOT macros
ROOT_DUMPWAVEFORM=dump_waveform.C

# define FCLs and output dir
if [ "$PROCESS" == "nu_spill" ]; then
  FCL_GEN=prodgenie_nu_spill_tpc_sbnd.fcl                   # Simulates GENIE neutrino interactions from the BNB beam with the beam spill structure, inside the TPC volume (with a 10 cm padding on each side)
  OUTDIR=$OUTDIR/$SBNDCODE_VERSION/nu_spill
elif [ "$PROCESS" == "nuecc" ]; then
  FCL_GEN=prodgenie_intrnue_singleinteraction_tpc_sbnd.fcl  #Simulates GENIE nue and anue neutrino interactions from the BNB beam
  OUTDIR=$OUTDIR/nuecc
elif [ "$PROCESS" == "numucc" ]; then
  FCL_GEN==prodgenie_nu_singleinteraction_tpc_sbnd.fcl      #Simulates GENIE neutrino interactions from the BNB beam forcing one interaction per event
  OUTDIR=$OUTDIR/numucc
elif [ "$PROCESS" == "cosmics" ]; then
  FCL_GEN=prodgenie_bnb_nu_cosmic_sbnd.fcl                  #Generation of neutrinos from Booster Neutrino Beam with cosmic rays
  #OUTDIR=$OUTDIR/bnb_nu_cosmic
  #OUTDIR=$OUTDIR/$SBNDCODE_VERSION/bnb_nu_cosmic_additional
  OUTDIR=$OUTDIR/$SBNDCODE_VERSION/bnb_nu_cosmic
elif [ "$PROCESS" == "data" ]; then
  FCL_SIGPROC=wirecell_sp_data_sbnd.fcl
  FCL_IMGCLUS=$WORKDIR/wcp-porting-img/sbnd/wcls-img-clus-data.fcl    # TODO: I can't find this fcl
  NEVT=20
  if [ "$RUN" == "14766" ]; then
    # TODO: this file is not there
    INPUT_DATA=/pnfs/sbn/data_add/sbnd/keepup/decoded-raw/filtered/00/decoded-raw_filtered_data_evb01_EventBuilder1_art1_run14766_15_20240711T232712-26f87ae3-e712-42f8-bd2b-65981bf66afd.root
    OUTDIR=$OUTDIR/run14766
  elif [ "$RUN" == "18005" ]; then
     # TODO: I can't find this fcl
    INPUT_DATA=/pnfs/sbn/data_add/sbnd/commissioning/run18005_decoded/decode_data_EventBuilder7_p2_art2_run18005_9_strmOffBeamZeroBias_20241215T065538-2def51e6-052f-4777-a377-a16fb74e8fc7.root
    OUTDIR=$OUTDIR/run18005
  fi
fi

# output for various steps
OUTPUT_GEN=$OUTDIR/gen.root
OUTPUT_G4=$OUTDIR/g4.root
OUTPUT_SIGPROC=$OUTDIR/sigproc.root

# clone img-clus repo
#cd $WORKDIR
#if [ ! -d "wcp-porting-img" ]; then
#  git clone https://github.com/HaiwangYu/wcp-porting-img.git
#fi

# create output dir
if [ ! -d "$OUTDIR" ]; then
  mkdir -p $OUTDIR
fi

# setup sbndcode
source /cvmfs/sbnd.opensciencegrid.org/products/sbnd/setup_sbnd.sh
setup sbndcode $SBNDCODE_VERSION -q e26:prof

# steps to process depends on MC or Data
if [ "$PROCESS" != "data" ]; then
  echo "Processing MC..."
  # gen
  lar -n $NEVT -c $FCL_GEN -o $OUTPUT_GEN

  # g4
  #lar -n $NEVT -c $WORKDIR/$FCL_G4 -s $OUTPUT_GEN -o $OUTPUT_G4 # for sbndcode v09_91_02
  lar -n $NEVT -c $FCL_G4 -s $OUTPUT_GEN -o $OUTPUT_G4 # for sbndcode v10_04_07
  
  # sigproc
  lar -n $NEVT -c $FCL_SIGPROC -s $OUTPUT_G4 -o $OUTPUT_SIGPROC
else
  echo "Processing data..."
  # sigproc
  lar -n $NEVT -c $FCL_SIGPROC -s $INPUT_DATA -o $OUTPUT_SIGPROC
fi


# Bee output destination
if [ ! -d "$OUTDIR/data" ]; then
  for i in $(seq 0 $((NEVT - 1)))
  do
    mkdir -p $OUTDIR/data/$i
  done
fi


# img-clus configuration
export WIRECELL_PATH=$WORKDIR/img-clus-configs/cfg:$WIRECELL_PATH
#export WIRECELL_PATH=/exp/sbnd/app/users/yuhw/wire-cell-data:$WIRECELL_PATH
export WIRECELL_PATH=$WORKDIR/img-clus-configs/wire-cell-data:$WIRECELL_PATH


# img-clus
for i in $(seq 0 $((NEVT - 1)))
do
  start_clus=$(date +%s) # for execution time only
  echo " Processing clustering for event $i ..."
  #mkdir -p $OUTDIR/data/$i
  lar -n 1 --nskip $i -c $FCL_IMGCLUS -s $OUTPUT_SIGPROC -o tmp.root >& $OUTDIR/lar-imgclus_$i.log
  python $WORKDIR/wcp-porting-img/sbnd/merge-zip.py
  bash $WORKDIR/wcp-porting-img/upload-to-bee.sh mabc.zip >& $OUTDIR/bee_$i.log
  mv clus-apa0-face0.tar.gz $OUTDIR/clus-apa0-face0_$i.tar.gz
  mv clus-apa1-face1.tar.gz $OUTDIR/clus-apa1-face1_$i.tar.gz
  mv mabc-apa0-face0.zip $OUTDIR/mabc-apa0-face0_$i.zip
  mv mabc-apa1-face1.zip $OUTDIR/mabc-apa1-face1_$i.zip
  mv mabc.zip $OUTDIR/mabc_$i.zip                                 #TODO: can't find mabc.zip file
  python $WORKDIR/unzip_file.py $OUTDIR/mabc_$i.zip $WORKDIR/
  mv $WORKDIR/data/0/0-channel-deadarea.json $OUTDIR/data/$i/$i-channel-deadarea.json
  mv $WORKDIR/data/0/0-clustering-0-0.json $OUTDIR/data/$i/$i-clustering-0-0.json
  mv $WORKDIR/data/0/0-clustering-1-1.json $OUTDIR/data/$i/$i-clustering-1-1.json
  mv $WORKDIR/data/0/0-img-0-0.json $OUTDIR/data/$i/$i-img-0-0.json
  mv $WORKDIR/data/0/0-img-1-1.json $OUTDIR/data/$i/$i-img-1-1.json
  rm -rf $WORKDIR/data
  rm clus-apa* mabc* Roo*root tmp.root cputime.db memory.db messages.log errors.log hists_*root sbnd-data-check.root
  end_clus=$(date +%s) # for execution time only
  echo "Clustering total time: $((end_clus - start_clus)) seconds"
done

# truthDepos clustering (MC only)
if [ "$PROCESS" != "data" ]; then
  for i in $(seq 0 $((NEVT - 1)))
  do
    echo " Processing truthDepos clustering for event $i ..."
    lar -n1 --nskip $i -c $FCL_CELLTREE $OUTPUT_G4 # G4 has simEnergyDepos. Check FCL_CELLTREE for which apa is being saved
    if [[ "$TRUTHDEPOS_SAVEAPA" == "apa0" ]]; then
      mv bee/data/0/0-truthDepo.json $OUTDIR/data/$i/$i-truthDepo-apa0.json
    elif [[ "$TRUTHDEPOS_SAVEAPA" == "apa1" ]]; then
      mv bee/data/0/0-truthDepo.json $OUTDIR/data/$i/$i-truthDepo-apa1.json
    fi
    if $DUMPWAVEFORM; then
      lar -n1 --nskip $i -c $FCL_CELLTREE $OUTPUT_SIGPROC # SP has SimChannells and decon waveforms
      root -l -b -q $WORKDIR/$ROOT_DUMPWAVEFORM
      mv waveform.root $OUTDIR/waveform_$i.root
    fi
    rm -rf bee celltree.root cputime.db errors.log memory.db messages.log
  done
fi


# upload to bee server and save url
cd $OUTDIR
zip -r data.zip data
cd -
bash $WORKDIR/wcp-porting-img/upload-to-bee.sh $OUTDIR/data.zip >& $OUTDIR/bee_merged.log
cat $OUTDIR/bee_merged.log


# clustering/truthDepos info for clustering evaluation (MC only)
if [ "$PROCESS" != "data" ]; then

  NEWOUTDIR=$OUTDIR/xyz-coordinates

  # truthDepos info
  X=6
  Y=7
  Z=8
  TIME=9
  CHARGE=10
  CLUSTERID=12
  E=13

  if [ ! -d "$NEWOUTDIR" ]; then
    mkdir -p $NEWOUTDIR
  fi
  for i in $(seq 0 $((NEVT - 1)))
  do
    mkdir -p $NEWOUTDIR/$i
    if [[ "$TRUTHDEPOS_SAVEAPA" == "apa0" ]]; then
      head -n $X $OUTDIR/data/$i/$i-truthDepo-apa0.json | tail -n 1 | cut -c 6- | rev | cut -c 3- | rev | tr ',' '\n' > $NEWOUTDIR/$i/x_truth_apa0.txt
      head -n $Y $OUTDIR/data/$i/$i-truthDepo-apa0.json | tail -n 1 | cut -c 6- | rev | cut -c 3- | rev | tr ',' '\n' > $NEWOUTDIR/$i/y_truth_apa0.txt
      head -n $Z $OUTDIR/data/$i/$i-truthDepo-apa0.json | tail -n 1 | cut -c 6- | rev | cut -c 3- | rev | tr ',' '\n' > $NEWOUTDIR/$i/z_truth_apa0.txt
      head -n $TIME $OUTDIR/data/$i/$i-truthDepo-apa0.json | tail -n 1 | cut -c 6- | rev | cut -c 3- | rev | tr ',' '\n' > $NEWOUTDIR/$i/t_truth_apa0.txt
      head -n $CHARGE $OUTDIR/data/$i/$i-truthDepo-apa0.json | tail -n 1 | cut -c 6- | rev | cut -c 3- | rev | tr ',' '\n' > $NEWOUTDIR/$i/q_truth_apa0.txt
      head -n $CLUSTERID $OUTDIR/data/$i/$i-truthDepo-apa0.json | tail -n 1 | cut -c 15- | rev | cut -c 3- | rev | tr ',' '\n' > $NEWOUTDIR/$i/id_truth_apa0.txt
      head -n $E $OUTDIR/data/$i/$i-truthDepo-apa0.json | tail -n 1 | cut -c 6- | rev | cut -c 3- | rev | tr ',' '\n' > $NEWOUTDIR/$i/e_truth_apa0.txt
    elif [[ "$TRUTHDEPOS_SAVEAPA" == "apa1" ]]; then
      head -n $X $OUTDIR/data/$i/$i-truthDepo-apa1.json | tail -n 1 | cut -c 6- | rev | cut -c 3- | rev | tr ',' '\n' > $NEWOUTDIR/$i/x_truth_apa1.txt
      head -n $Y $OUTDIR/data/$i/$i-truthDepo-apa1.json | tail -n 1 | cut -c 6- | rev | cut -c 3- | rev | tr ',' '\n' > $NEWOUTDIR/$i/y_truth_apa1.txt
      head -n $Z $OUTDIR/data/$i/$i-truthDepo-apa1.json | tail -n 1 | cut -c 6- | rev | cut -c 3- | rev | tr ',' '\n' > $NEWOUTDIR/$i/z_truth_apa1.txt
      head -n $TIME $OUTDIR/data/$i/$i-truthDepo-apa1.json | tail -n 1 | cut -c 6- | rev | cut -c 3- | rev | tr ',' '\n' > $NEWOUTDIR/$i/t_truth_apa1.txt
      head -n $CHARGE $OUTDIR/data/$i/$i-truthDepo-apa1.json | tail -n 1 | cut -c 6- | rev | cut -c 3- | rev | tr ',' '\n' > $NEWOUTDIR/$i/q_truth_apa1.txt
      head -n $CLUSTERID $OUTDIR/data/$i/$i-truthDepo-apa1.json | tail -n 1 | cut -c 15- | rev | cut -c 3- | rev | tr ',' '\n' > $NEWOUTDIR/$i/id_truth_apa1.txt
      head -n $E $OUTDIR/data/$i/$i-truthDepo-apa1.json | tail -n 1 | cut -c 6- | rev | cut -c 3- | rev | tr ',' '\n' > $NEWOUTDIR/$i/e_truth_apa1.txt
    fi
  done

  # clustering info
  for i in $(seq 0 $((NEVT - 1)))
  do
    awk -F'[][]' '{if (NF>2) print $2}' $OUTDIR/data/$i/$i-clustering-0-0.json | tr ',' '\n' > $NEWOUTDIR/$i/id_clustering_apa0.txt
    awk -F'[][]' '{if (NF>4) print $4}' $OUTDIR/data/$i/$i-clustering-0-0.json | tr ',' '\n' > $NEWOUTDIR/$i/q_clustering_apa0.txt
    awk -F'[][]' '{if (NF>6) print $6}' $OUTDIR/data/$i/$i-clustering-0-0.json | tr ',' '\n' > $NEWOUTDIR/$i/x_clustering_apa0.txt
    awk -F'[][]' '{if (NF>8) print $8}' $OUTDIR/data/$i/$i-clustering-0-0.json | tr ',' '\n' > $NEWOUTDIR/$i/y_clustering_apa0.txt  
    awk '{sub(/^.*z/, ""); print}' $OUTDIR/data/$i/$i-clustering-0-0.json | cut -c 4- | rev | cut -c 3- | rev | tr ',' '\n' > $NEWOUTDIR/$i/z_clustering_apa0.txt
    awk -F'[][]' '{if (NF>2) print $2}' $OUTDIR/data/$i/$i-clustering-1-1.json | tr ',' '\n' > $NEWOUTDIR/$i/id_clustering_apa1.txt
    awk -F'[][]' '{if (NF>4) print $4}' $OUTDIR/data/$i/$i-clustering-1-1.json | tr ',' '\n' > $NEWOUTDIR/$i/q_clustering_apa1.txt
    awk -F'[][]' '{if (NF>6) print $6}' $OUTDIR/data/$i/$i-clustering-1-1.json | tr ',' '\n' > $NEWOUTDIR/$i/x_clustering_apa1.txt
    awk -F'[][]' '{if (NF>8) print $8}' $OUTDIR/data/$i/$i-clustering-1-1.json | tr ',' '\n' > $NEWOUTDIR/$i/y_clustering_apa1.txt  
    awk '{sub(/^.*z/, ""); print}' $OUTDIR/data/$i/$i-clustering-1-1.json | cut -c 4- | rev | cut -c 3- | rev | tr ',' '\n' > $NEWOUTDIR/$i/z_clustering_apa1.txt  
  done

fi