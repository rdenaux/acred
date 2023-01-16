#!/bin/bash
# This script downloads and unpacks data required for running acred

echo "This script downloads and unpacks data required for evaluating acred"
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


echo "Fetching evaluation data"
mkdir data
mkdir data/evaluation

echo "Fetching Clef'18 training data from GitHub"
wget -O data/evaluation/clef2018-factchecking-v1.0.tar.gz https://github.com/clef2018-factchecking/clef2018-factchecking/archive/v1.0.tar.gz
echo "Unpacking Clef'18 training data"
tar -xzf data/evaluation/clef2018-factchecking-v1.0.tar.gz -C data/evaluation/

echo "Copying Clef'18 testing data, submissions and scores"
cp data/clef18_submissions_and_scores.zip data/evaluation/
echo "Unpacking Clef'18 testing data"
unzip data/evaluation/clef18_submissions_and_scores.zip -d data/evaluation/

echo "Adding acred-iswc predictions as task2 submission for Clef'18"
mkdir data/evaluation/clef18_fact_checking_lab_submissions_and_scores_and_combinations/task2_submissions/acred-iswc
cp data/acred-iswc___task2_en.zip data/evaluation/clef18_fact_checking_lab_submissions_and_scores_and_combinations/task2_submissions/acred-iswc

echo "Fetching coinfo250 testing data from GitHub"
wget -O data/evaluation/coinform250.json https://github.com/co-inform/Datasets/raw/master/coinform250.json

