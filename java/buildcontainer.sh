#!/bin/bash

./gradlew clean build
docker build -t hello-app --build-arg=JAR_FILE=build/libs/hello-app.jar .
# see runlocal.sh and runontc.sh for launching the container
