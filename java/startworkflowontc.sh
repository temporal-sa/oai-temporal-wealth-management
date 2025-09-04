#!/bin/bash

# be sure to set the TEMPORAL_NAMESPACE environment variable
if [ -z "${TEMPORAL_NAMESPACE}" ]
then
  echo "Please set the TEMPORAL_NAMESPACE environment variable and re-run the script."
  exit 1
fi

if [ -z "${TEMPORAL_ENDPOINT}" ]
then
  echo "Please set the TEMPORAL_ENDPOINT environment variable and re-run the script."
  exit 2
fi

if [ -z "${TEMPORAL_CLIENT_KEY}" ]
then
  echo "Please set the TEMPORAL_CLIENT_KEY environment variable and re-run the script."
  exit 3
fi

if [ -z "${TEMPORAL_CLIENT_CERT}" ]
then
  echo "Please set the TEMPORAL_CLIENT_CERT environment variable and re-run the script."
  exit 4
fi

if [ -z "${TEMPORAL_INSECURE_TRUST_MANAGER}" ]
then
  echo "Warning. TEMPORAL_INSECURE_TRUST_MANAGER environment variable was not set. Defaulting to false."
  export $TEMPORAL_INSECURE_TRUST_MANAGER=false
fi

# Use Temporal Cloud spring profile
export SPRING_PROFILE="tc,noworker"
export APP_COMMANDS="-Dspring.profiles.active=$SPRING_PROFILE -Dspring.temporal.namespace=$TEMPORAL_NAMESPACE -Dspring.temporal.connection.target=$TEMPORAL_ENDPOINT -Dspring.temporal.connection.mtls.insecure-trust-manager=$TEMPORAL_INSECURE_TRUST_MANAGER -Dspring.temporal.connection.mtls.key-file=$TEMPORAL_CLIENT_KEY -Dspring.temporal.connection.mtls.cert-chain-file=$TEMPORAL_CLIENT_CERT"

# echo "$APP_COMMANDS"

# make sure we have the latest build
./gradlew clean build

# and now run the worker locally but using Temporal Cloud
java -cp ./build/libs/hello-app.jar $APP_COMMANDS -Dloader.main=io.temporal.springboot.example.workflowstarter.StartTheWorkflow org.springframework.boot.loader.PropertiesLauncher


