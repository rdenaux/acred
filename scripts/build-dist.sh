#!/bin/bash
echo "This script builds a release of acred"
echo "Creating dirs"
mkdir -p build
DATE=$(date +"%Y%m%d")
DIRN=acred-$DATE
echo "Building dist in bild/$DIRN"
mkdir -p build/$DIRN
mkdir -p build/$DIRN/log
mkdir -p build/$DIRN/requirements

# resource dirs
cp -r nginx build/$DIRN/
cp -r docker build/$DIRN/
cp -r wsgi build/$DIRN/
cp -r scripts build/$DIRN/

# resource files
cp factchecker_urls.txt build/$DIRN/

# main library modules
cp -r acred build/$DIRN/
cp -r acredapi build/$DIRN/
cp -r claimencoder build/$DIRN/
cp -r claimneuralindex build/$DIRN/
cp -r esiutils build/$DIRN/
cp -r semantic_analyzer build/$DIRN/
cp -r stance build/$DIRN/
cp -r worthiness build/$DIRN/


# scripts possibly useful for testing without Docker
cp runsrv.py build/$DIRN/

# needed for building docker images
cp requirements.txt build/$DIRN/
cp requirements-torch.txt build/$DIRN/
cp docker-compose.yml build/$DIRN/


# documentation
cp README.md build/$DIRN/
cp CHANGELOG.md build/$DIRN/

# default (dev) configuration
cp acred.ini build/$DIRN/

# make sure start-env.sh is executable 
dos2unix docker/start-env.sh

echo "Packing into tar.gz"
cd build/
tar -czvf $DIRN.tar.gz $DIRN
cd ../
echo "done"
