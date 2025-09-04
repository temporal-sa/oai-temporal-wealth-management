# Temporal Spring Boot Console Hello

## Prerequisites
* [Temporal CLI](https://docs.temporal.io/cli#install)
* Java SDK
* Optionally [Temporal Cloud namespace](https://pages.temporal.io/get-cloud)
   
## Running Locally
Start Temporal Server locally
```shell
temporal server start-dev
```

To run the app locally, without using a container:

```shell
./gradlew bootRun
```

To initiate a workflow using the console application:

```shell
./gradlew startWorkflow
```

To initiate the workflow using a local development server from the command line:

```shell
temporal workflow start \
  --workflow-id Test1 \
  --type HelloWorkflow \
  --task-queue HelloTemporalWorld \
  --input '{ "name": "First LastName"}'
```
## Run the Worker using Docker

Build the docker container by running the following command: 

```shell
./gradlew clean build
./buildcontainer.sh 
```

By default, this container is expecting Temporal Server to be running locally.

## Running Worker in Docker Using Temporal Cloud

Set the following environment variables: 
```shell
export TEMPORAL_NAMESPACE="<namespace>.<accountId>>"
export TEMPORAL_ENDPOINT=<namespace>.<accountId>.tmprl.cloud:7233
export TEMPORAL_CLIENT_KEY="/path/to/your/key"
export TEMPORAL_CLIENT_CERT="/path/to/your/cert.pem"
# optional
# export TEMPORAL_INSECURE_TRUST_MANAGER="true"
```
Then start the worker by running the following command:

```shell
./runontc.sh
```

To initiate a workflow using the console application:

```shell
./startworkflowontc.sh 
```

To initiate the workflow using Temporal Cloud from the command line, set the following
environment variables. These need to match the same values that were set above:

```shell
temporal env set dev.namespace $TEMPORAL_NAMESPACE
temporal env set dev.address $TEMPORAL_ENDPOINT
temporal env set dev.tls-cert-path $TEMPORAL_CLIENT_CERT
temporal env set dev.tls-key-path $TEMPORAL_CLIENT_KEY 
```

Then reference the name of the environment in your temporal command:

```shell
temporal workflow start \
  --workflow-id Test1 \
  --type HelloWorkflow \
  --task-queue HelloTemporalWorld \
  --input '{ "name": "First LastName"}' \
  --env dev
```
