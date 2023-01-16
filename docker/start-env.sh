#!/bin/bash
# Sets environment variables on the host machine,
#  i.e. the machine where the `docker-compose` will be run
# Run with source ./start-env.sh

if [ "$1" != "" ]; then
    echo "Starting env $1"
    export ENV_TYPE=$1
else
    echo "Assuming prod env"
    export ENV_TYPE="prod"  # assume prod by default
fi    

# define variables we can refer to in the `docker-compose.yml`
#  these refer to files/folders on the host machine
#  which can be mapped to paths in the containers
export ACRED_docker_env=.env
export ACRED_docker_logdir=./log/

export DATA=./data
export DL_MODEL=${DATA}/model

export ACRED_docker_acred_data_dir=${DATA}/

if [ -d ${DL_MODEL}/semantic_encoder ] && [ -L ${DL_MODEL}/claim-embeddings ] && [ -L ${DL_MODEL}/check_worthiness ];
then
    echo "Linking to models in prod environment"
    export ACRED_docker_acred_model_dir=${DL_MODEL}/
else
    echo "*** Could not find expected models in ${DL_MODEL}"
fi


## Ports on the host machine

# API (always https)
export ACRED_docker_api_port=443
export ACRED_docker_html_port=80
