# ISWC reproducibility

This document describes how to use `acred` to reproduce the results described in our paper at [ISWC'20](https://iswc2020.semanticweb.org/)

## Hardware and Software Requirements
We run `acred` on a single linux server with 32GB RAM using the `docker-compose` deployment. You'll also need several GB of disk space and we recommend using an SSD. You will need root access to the machine as this is needed by `docker-compose`.

## Installation
See [docker](tree/master/docker/README.md) for specific details on how to customise the docker deployment. Here we summarise the steps.

1. Either clone the `acred` repo from GitHub, or download a recent release and unpack it on the installation server. In the subsequent steps we assume you are inside the `acred` root folder.
2. Download data and models by executing:
``` shell
scripts/fetch_data.sh
```
This will take a good 10 minutes, depending on your internet connection, as this downloads and unpacks a couple of GBs of data (mostly the deep-learning model weights). This data is downloaded from [zenodo](https://zenodo.org/record/4030305#.X2EsV2gzaHt) and contains the database of 85K sentences used as ground credibility signals as well as the pre-trained weights for the various models used in `acred`: semantic sentence similarity, stance detection and checkworthiness.
3. Configure docker environment:
  * execute `cp docker/env-prod .env` to copy the "production" settings for acred
  * if necessary edit file `docker/start-env.sh` to configure the ports where you will expose the REST API, by default we use the standard http and https ports, but you can change them by editing the last 2 lines in the file.
  * execute `source docker/start-env.sh` to set environment variables needed when building and running docker images
4. Build docker images:
``` shell
docker-compose build
```
This will build the docker images as specified in the `docker-compose.yml` file. This can take around 10 minutes.
5. Launch the application. If everything went well, you should now be able to launch the application:
```shell
docker-compose up -d
```
This will configure a virtual network and launch the various services (containers) described in the docker-compose file. Some of these containers can take a while to load all resources needed. In particular the `claimneuralindex` needs to load the embeddings and create an index for them before being able to reply to queries. 

If everything went OK, you should now have a deployment of `acred` on you server. 
You can check this by opening a browser and visiting page https://ACREDAPI/acred/api/v1/uptime where `ACREDAPI` is the ip (and port, if changed above) of the server. This should display a simple json message.

You can further verify that everything is working correctly by requesting a review for a specific claim:
```
https://ACREDAPI/acred/api/v1/acred/reviewer/credibility/claim?claim=garlic%20cures%20cancer
```

This should return a JSON response, but its abbreviated version should look like
``` json
[{
  "@context" : "http://coinform.eu",
  "@type": "AggQSentCredReview",
  "additionalType" : ["CredibilityReview", "Review"],
  "author" : {...},
  "dateCreated" : "...",
  "isBasedOn" : [...],
  "itemReviewed": {...},
  "reviewRating": {...},
  "text" : "Sentence `garlic cures cancer` seems *not credible* as it *agrees with*:\n\n * `The Garlic Heals Cancer`\nthat seems *not credible* based on [fact-check](https://www.newtral.es/el-ajo-no-previene-ni-cura-el-cancer/20190327/) by [Newtral](https://www.newtral.es/) with textual claim-review rating 'falso'"
}]
```

Once this is working, you are ready to reproduce the evaluations.


# Reproducing Evaluations
In order to run the evaluations you should have a working deployment of `acred` as described above. You can run the evaluations from the server itself, or from another machine where you have access to the `acred` code (via git clone or unpacking a release). We also assume you have a python 3 interpreter available with common libraries like `requests`, `pandas` and `sklearn`, which you will need to execute the prediction and scoring scripts.

## Get evaluation data
We provide a script for downloading the evaluation data for 2 of our evaluation datasets: `clef18` and `coinfo250`.
Simply execute:

```
scripts/fetch_eval_data.sh
```

This should add a few files and folders under `data/evaluation`

(For FakeNewsNet, you need to follow more involved instructions as you need to retrieve the text from the articles using webscraping. See below.)

## Clef'18
We'll use the official python scorer for Clef'18 Task 2, so we need to generate a zip with the `acred` predictions and place them in the right place. To do that, execute the following commands:

``` shell
export CLEF18_TE_DIR=data/evaluation/clef18_fact_checking_lab_submissions_and_scores_and_combinations
mkdir -p ${CLEF18_TE_DIR}/task2_submissions/acred/acred_task2_en 
```
To generate the predictions, we provide `scripts/pred_clef2018.py` which reads the input files and sends them to an `acred` REST API. By default, we assume this is deployed on `localhost`, if this is not the case, please edit `scripts/pred_clef2018-config.json` to point to the correct ip and port. Then you can run the following command to generate the credibility reviews and Clef'18 label predictions (`TRUE`, `FALSE` or `HALF-TRUE`; this should take about 3 minutes, depending on your server hardware):

``` shell
python scripts/pred_clef2018.py -config scripts/pred_clef2018-config.json -inputFolder ${CLEF18_TE_DIR}/task2_gold/English -outFolder ${CLEF18_TE_DIR}/task2_submissions/acred/acred_task2_en 
```
 
The scoring script expects a zip file, so you need to create this using script:
 
``` shell
zip -j ${CLEF18_TE_DIR}/task2_submissions/acred/acred___task2_en.zip ${CLEF18_TE_DIR}/task2_submissions/acred/acred_task2_en/*.txt
```

Now that you have generated the predictions, you can run the scoring script as follows:

``` shell
pushd ${CLEF18_TE_DIR}
python score_competition_task2.py
```

This should print a lot of output. At the end it should print two tables, we are interested in the first table. If you scroll up to the top of the table, you should see:

```
========================================= TASK2 RESULTS FOR EN ==========================================
                           MAE             Macro MAE       ACC             Macro F1        Macro Recall
=========================================================================================================
TEAM: acred-iswc
  contrastive1             0.6835          0.6990          0.4676          0.4247          0.4367
  contrastive1-debates     0.5690          0.5970          0.5862          0.5297          0.5376
  contrastive1-speeches    0.7654          0.7720          0.3827          0.3499          0.3661
  primary                  0.6475          0.6052          0.3813          0.3741          0.4202
  primary-debates          0.5862          0.5048          0.4483          0.4454          0.5255
  primary-speeches         0.6914          0.6683          0.3333          0.3167          0.3539
=========================================================================================================
TEAM: acred
  primary                  0.6619          0.6185          0.3741          0.3627          0.4136
  primary-debates          0.5862          0.4897          0.4655          0.4582          0.5558
  primary-speeches         0.7160          0.6947          0.3086          0.2886          0.3275
=========================================================================================================
other teams...
```

To go back to the root `acred` folder you can simply execute:
``` shell
popd
```

## coinfo250
We assume you already executed `scripts/fetch_eval_data.sh` and that you have a terminal open at the root folder of the `acred` project (or release).

You can directly generate the credibility reviews and label predictions by executing the following script (remember to replace `ACREDAPI` for the ip and port for your deployment; this can take about 10 minutes, depending on your hardware):

``` shell
mkdir data/evaluation/coinform250_reviews
python scripts/pred_coinfo250.py -inputJson data/evaluation/coinform250.json -outDir data/evaluation/coinform250_reviews/ -credpred_url https://ACREDAPI/acred/api/v1/tweet/claim/credibility
```

Once this is finished, you should be able to execute the scoring script by executing:

``` shell
python scripts/score_coinfo250.py
```

This should output something like:
```
Scoring credibility accuracy of 248 coinform250 tweets
  accuracy:  0.2742
  f1_macro:  0.2137
  precision: 0.2084
  recall:    0.2530
```

## FakeNewsNet Politifact

First, you need to follow the instructions at the [FakeNewsNet GitHub repo](https://github.com/KaiDMML/FakeNewsNet) to download the data. Since the dataset published only contains the gold label and URLs of the articles, you need to run a script to crawl the URLs. In our ISWC evaluation we only used:
 * `news_source`: `politifact`
 * `label`: `fake` and `real`
 * `data_features_to_collect`: **news_articles** only
 
You can directly generate the credibility reviews and label predictions by executing the following script:

``` shell
mkdir data/evaluation/fakeNewsnet_reviews
python scripts/pred_fakeNewsNet.py -fakeNewsNetFolder data/evaluation/fakeNewsNet -output_dir data/evaluation/fakeNewsnet_reviews/ -acredapi_url https://ACREDAPI
```

Once this is finished, you should be able to execute the scoring script by executing:

``` shell
python scripts/score_fakeNewsNet.py -fakeNewsNetFolder data/evaluation/fakeNewsNet -predictions_csv data/evaluation/fakeNewsnet_reviews/predictions.csv
```


# Limitations
Reproducibility limitation: some of code in the version of `acred` we used during experimentation relied on proprietary code from Expert System which had to be removed from the code released. This code is used during the analysis of long texts like articles, as it identifies sentences which may be claims based on its relevance to topics and the presence of named entities. We plan to replace this code with sentence detection via NLTK and a custom checkworthiness detection model. This should mainly affect results on `FakeNewsNet` (articles), but not `Clef'18` (claims) or `coinform250` (tweets, most of which do not contain links to other web pages).


