#!/bin/sh
# This script downloads and unpacks data required for running acred
#
echo "This script downloads and unpacks data required for running acred"
echo " "

if ! command -v wget &> /dev/null
then
    echo "wget is necessary to run this script. Please install it."
    exit
fi

if ! command -v tar &> /dev/null
then
    echo "tar is necessary to run this script. Please install it."
    exit
fi

if ! command -v unzip &> /dev/null
then
    echo "unzip is necessary to run this script. Please install it."
    exit
fi


mkdir data
echo "Fetching DB of claims"
wget -O data/claims-from-ClaimReviews-45K.csv https://zenodo.org/record/4030305/files/claims-from-ClaimReviews-45K.csv?download=1
wget -O data/sentences-extractedFrom-Articles-40K.csv https://zenodo.org/record/4030305/files/sentences-extractedFrom-Articles-40K.csv?download=1
wget -O data/claimReviews-pruned-45K.jsonl https://zenodo.org/record/4030305/files/claimReviews-pruned-45K.jsonl?download=1

mkdir data/model
echo ""
echo "Fetching DeepLearning models"
echo "Fetching sentence encoder"
wget -O data/model/semantic_encoder.zip https://zenodo.org/record/4030305/files/semantic_encoder.zip?download=1
unzip data/model/semantic_encoder.zip -d data/model/


echo "Fetching stance detection model"
mkdir data/model/stance
wget -O data/model/saved_fnc1_classifier_acc_0.92.tar.gz https://zenodo.org/record/4030305/files/saved_fnc1_classifier_acc_0.92.tar.gz?download=1
tar -xzf data/model/saved_fnc1_classifier_acc_0.92.tar.gz -C data/model/stance


echo "Fetching checkworthiness model"
wget -O data/model/check_worthiness_acc_0.95.zip https://zenodo.org/record/4030305/files/check_worthiness_acc_0.95.zip?download=1
unzip data/model/check_worthiness_acc_0.95.zip -d data/model/
ln -sr data/model/check_worthiness_acc_0.95 data/model/check_worthiness 

echo "Fetching embeddings for sentences in DB "
wget -O data/model/claim_dev_embs_85K_20200426.tar.gz https://zenodo.org/record/4030305/files/claim_dev_embs_85K_20200426.tar.gz?download=1
tar -zxf data/model/claim_dev_embs_85K_20200426.tar.gz -C data/model/
ln -sr data/model/claim_dev_embs_85K_20200426 data/model/claim-embeddings

cp data/fnc1-classifier.json data/model/stance/saved_fnc1_classifier_acc_0.92
