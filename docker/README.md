# Docker Deployment Instructions

This document explains how to run the acred services using Docker.
(You can run individual services on your local machine. See the README.md at the root of the project on how to do this.)

You may want to deploy the docker instances as part of development on your local machine, but since this requires more than 20GB of RAM, you'll typically run this on a server.
 

## Pre-requisites
If you don't have `docker` and `docker-compose` yet, install them for your environment 

  * [Mac](https://docs.docker.com/engine/installation/mac/)
  * [Win](https://docs.docker.com/docker-for-windows/). Notice in the near future you may be able to run [Docker inside WSL on windows](https://nickjanetakis.com/blog/setting-up-docker-for-windows-and-wsl-to-work-flawlessly), but we're not there yet.
  * Linux (method depends on your distribution)
  
## Deployment with test SSL certs

**Note**: Currently, you need to login as `root`! (Otherwise, there are issues with running `docker-compose` and setting up the host environment correctly).

Assuming you are at the root of the `ared` distribution and that you have a proper shell (on Windows use Git Bash or WSL to be able to execute shell scripts correctly):

  1. Copy (and optionally edit) the `docker/env-prod` to `.env`
  2. Initialize Docker Environment Variables: ```source docker/start-env.sh```
    * This sets environment variables and useful aliases on the *host machine* (ie the one running the Docker containers)
    * this also copies the SSL certs when executing on a production server
  3. Build the images: ```docker-compose build```
    * This downloads and builds the images required to run the services described in `docker-compose.yml`
  4. Start Services: `docker-compose up`
  5. Verify the services have started correctly (by checking for error messages in the docker logs and visiting the website)
  

# How it works

The `docker-compose` deployment uses `docker-compose.yml` to configure four *services*:
 * **acredapi**: this is the main one and runs a [uwsgi](https://uwsgi-docs.readthedocs.io/en/latest/index.html) service. This service is based on a standard python docker image, but uses the `docker/Dockerfile-acredapi` to configure it during the `build` phase. During the `up` phase, an environment file is used to override the standard `acred.ini` file. This env file is usually derived from `docker/env-prod` and `docker/start-env` points to the actual location of it.
 * **claimneuralindex** custom image with the `claimneuralindex` library, see `docker/Dockerfile-claimneuralindex`. It loads a vector space of pre-encoded claims/sentences and provides services for encoding incoming query sentences and finding the top k most similar claims in the index. It depends on the `claimencoder` service. The main reason for running this on a separate container is that the neural index requires a lot of RAM, so we only want to load a small number of copies of the embedding space.
 * **claimencoder** custom image with the `claimencoder` library, see `docker/Dockerfile-claimencoder`. It runs a RoBERTa model that has been pre-trained for semantic similarity (ie semantically similar sentences have embeddings which are close to each other). The main reason for running this on a separate container is that the RoBERTa model is not thread-safe, therefore this container only loads a single RoBERTa model.
 * **nginx**: this is a production grade web server. It simply acts as a front for the various **acred** services, but can be configured to do other things. This image is configured at build time by its own docker file (`nginx/Dockerfile.api`), which extends a standard nginx image and adds custom configuration (all of this is contained in the `nginx` folder of the project).
   
## Dockerfiles 
These define the two main images used by the docker compose

### acredapi main `docker/Dockerfile-acredapi`
It set ups the container so that it can execute the uwsgi service. The Dockerfile, essentially:
   * extends a basic python 3.6 image
   * adds a `acred` user 
   * adds various `acred` folders for the main executable files, configuration and logging.
   * copies and installs python requirements needed to run the Flask app
   * copies the main `acred.ini` configuration (note that some of these options are overriden by environment variables)
   * copies python sources and resources needed to run the service (`extra/wsgi.ini` and any scripts)
   * exposes ports 8080 and 9001
   
Note that the `docker-compose.yml` mounts volumes for folder `log/`.
   
### claimencoder `docker/claimencoder`
Similar to the acredapi docker file, but it only includes the `claimencoder` folder and it also installs torch dependencies since it needs to be able to load the RoBERTa sentence encoder. 

The `docker-compose.yml` assigns volumes for `logs` and `/opt/model` which should contain a subfolder with the RoBERTa model. The main idea here is that we do not need to re-build the container if we update the model, instead we can replace the model with a new version on the host and the container will pick it up during container startup. 


### `claimneuralindex` `docker/claimneuralindex`
Similar fo the acredapi docker file, but it only includes the `claimneuralindex` subfolder. The main dependencies required are numpy and `faiss`, which are included as part of the standard `requirements.txt`

The `docker-compose.yml` assigns volumes for `logs` and `/opt/model`, which should contain a subfolder with the neural index. You can update the files on the host machine and just restart the container so it re-loads the embedding space.


### Nginx `Dockerfile`
This is the `nginx/Dockerfile.api` and extends an official [nginx](https://nginx.org/) docker image. It replaces the default configuration with the files in the `nginx` folder:
 * `nginx.conf`: mainly logging and timout configs
 * `acredapi-nginx`: production config
   * serve on port 9000 with SSL and sets up SSL certificate and key files
   * forward all requests to the acredapi service on port 9001 via uwsgi
 * `acredapi-internal-nginx`: test/dev config
   * serve on port 9080 without SSL
   * forward all requests to the acredapi service on port 9001 via uwsgi
