# Purpose: Read and convert json file to text files. 
#          Input are json files after image clustering jobs
#          json files contain the truth and clustering information about the tracks
# Author:  Prabhjot Singh (prabhjot@fnal.gov)
# Date:    5 Nov 2025
# Command: run this script. No need to setup any environment variables
#          ./jsontotext.sh apa0
#          ./jsontotext.sh apa1


#!/bin/bash

OUTDIR=/exp/sbnd/data/users/prabhjot/wirecell_clustering/cluster_evaluation/runcode
FILEDIR=/exp/sbnd/data/users/prabhjot/wirecell_clustering/developcode/wcp-porting-validation/sbnd/Results_MC_2viewactive_2viewdead_newXin                       # TODO: we need to find a way to loop over all
                                                                                                              # sub-directories and still need to know the
                                                                                                              # information from where events came

#TODO: we should loop over both APAs in single loop
TRUTHDEPOS_SAVEAPA=${1}
NEVT=12 # Number of events to process
SBNDCODE_VERSION="v10_06_00"
PROCESS="nu_spill"

echo "Processing for TRUTHDEPOS_SAVEAPA = $TRUTHDEPOS_SAVEAPA"
echo "Number of events to process: $NEVT"

# make the subdirectory in the output area if it already does not exist
SUBDIR=${OUTDIR}/$(basename $FILEDIR) # subdirectory in output area for evaluation 
if [ ! -d "$SUBDIR" ]; then
  mkdir $SUBDIR
fi

SUBDIR=${SUBDIR}/${SBNDCODE_VERSION}
if [ ! -d "$SUBDIR" ]; then
  mkdir $SUBDIR
fi

SUBDIR=${SUBDIR}/${PROCESS}
if [ ! -d "$SUBDIR" ]; then
  mkdir $SUBDIR
fi

# cd to subdirectory
# TODO: can we avoid cd command?
cd $SUBDIR  

# copy mabc-apa0-face0.zip and mabc-apa1-face1.zip to output area
# unzip the files if not already unzipped
if [[ "$TRUTHDEPOS_SAVEAPA" == "apa0" ]]; then
  cp ${FILEDIR}/mabc-apa0-face0.zip ${SUBDIR}
  unzip mabc-apa0-face0.zip -d ${SUBDIR}
else 
  cp ${FILEDIR}/mabc-apa1-face1.zip ${SUBDIR}
  unzip mabc-apa1-face1.zip -d ${SUBDIR}
fi

# clustering/truthDepos info for clustering evaluation (MC only)
NEWOUTDIR=$SUBDIR/xyz-coordinates # output directory for xyz coordinates text files

if [ ! -d "$NEWOUTDIR" ]; then
  mkdir -p $NEWOUTDIR
fi

# truthDepos info
X=6                 # Index of X coordinate in json file
Y=7                 # Index of Y coordinate in json file
Z=8                 # Index of Z coordinate in json file
TIME=9              # Index of time coordinate in json file
CLUSTERID=11        # Index of cluster ID in json file
CHARGE=12           # Index of charge in json file
E=13                # Index of energy in json file

# loop over events
for ((i=0; i<$NEVT; i++))
do
  echo "Processing event $i"

  # create event directory if it does not exist
  EVTDIR=${NEWOUTDIR}/$i
  if [ ! -d "$EVTDIR" ]; then
    mkdir -p $EVTDIR
  fi

  # input and output file names
  JSONFILE=${FILEDIR}/tru-${TRUTHDEPOS_SAVEAPA}-$i.json
  OUTFILE_X=${EVTDIR}/x_truth_${TRUTHDEPOS_SAVEAPA}.txt
  OUTFILE_Y=${EVTDIR}/y_truth_${TRUTHDEPOS_SAVEAPA}.txt
  OUTFILE_Z=${EVTDIR}/z_truth_${TRUTHDEPOS_SAVEAPA}.txt
  OUTFILE_TIME=${EVTDIR}/time_truth_${TRUTHDEPOS_SAVEAPA}.txt
  OUTFILE_CLUSTERID=${EVTDIR}/clusterid_truth_${TRUTHDEPOS_SAVEAPA}.txt
  OUTFILE_CHARGE=${EVTDIR}/charge_truth_${TRUTHDEPOS_SAVEAPA}.txt
  OUTFILE_E=${EVTDIR}/energy_truth_${TRUTHDEPOS_SAVEAPA}.txt

  # read json file and extract xyz coordinates along with other information
  head -n $X $JSONFILE          | tail -n 1 | cut -c 6-   | rev | cut -c 3- | rev | tr ',' '\n' > $OUTFILE_X
  head -n $Y $JSONFILE          | tail -n 1 | cut -c 6-   | rev | cut -c 3- | rev | tr ',' '\n' > $OUTFILE_Y
  head -n $Z $JSONFILE          | tail -n 1 | cut -c 6-   | rev | cut -c 3- | rev | tr ',' '\n' > $OUTFILE_Z
  head -n $TIME $JSONFILE       | tail -n 1 | cut -c 6-   | rev | cut -c 3- | rev | tr ',' '\n' > $OUTFILE_TIME
  head -n $CLUSTERID $JSONFILE  | tail -n 1 | cut -c 15-  | rev | cut -c 3- | rev | tr ',' '\n' > $OUTFILE_CLUSTERID
  head -n $CHARGE $JSONFILE     | tail -n 1 | cut -c 6-   | rev | cut -c 3- | rev | tr ',' '\n' > $OUTFILE_CHARGE
  head -n $E $JSONFILE          | tail -n 1 | cut -c 6-   | rev | cut -c 3- | rev | tr ',' '\n' > $OUTFILE_E
done # end loop over events

# clustering info
# loop over events
for ((i=0; i<$NEVT; i++))
do
  echo "Processing event $i for clustering info"

  if [[ "$TRUTHDEPOS_SAVEAPA" == "apa0" ]]; then
    apa=0
    face=0
  else 
    apa=1
    face=1
  fi

  EVTDIR=${NEWOUTDIR}/$i
  JSONFILE_Reco=${FILEDIR}/data/${i}/${i}-clustering-apa$apa-face$face.json
  OUTFILE_Reco_X=${EVTDIR}/x_clustering_apa$apa.txt
  OUTFILE_Reco_Y=${EVTDIR}/y_clustering_apa$apa.txt
  OUTFILE_Reco_Z=${EVTDIR}/z_clustering_apa$apa.txt
  OUTFILE_Reco_ClusterID=${EVTDIR}/clusterid_clustering_apa$apa.txt
  OUTFILE_Reco_Charge=${EVTDIR}/charge_clustering_apa$apa.txt

  # read json file and extract xyz coordinates along with other information
  jq '.x[]' $JSONFILE_Reco > $OUTFILE_Reco_X
  jq '.y[]' $JSONFILE_Reco > $OUTFILE_Reco_Y
  jq '.z[]' $JSONFILE_Reco > $OUTFILE_Reco_Z
  jq '.cluster_id[]' $JSONFILE_Reco > $OUTFILE_Reco_ClusterID
  jq '.q[]' $JSONFILE_Reco > $OUTFILE_Reco_Charge
done