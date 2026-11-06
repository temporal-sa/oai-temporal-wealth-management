# Java Open Investment Account Worker

An optional Java (Spring Boot) implementation of `OpenInvestmentAccountWorkflow`, the child workflow
the Open Account Agent starts to open a new investment account. It is a drop-in replacement for the
Python version in [`src/temporal_supervisor/workflows/open_account_workflow.py`](../src/temporal_supervisor/workflows/open_account_workflow.py):
same KYC and compliance steps, same saga (create the account record, debit the linked bank account,
register with the custodian, with compensations in reverse order), and the same status updates
signalled to the parent chat workflow.

The workflow has no business logic of its own. It calls the Python activities by name (`get_client`,
`open_investment`, `remove_investment`, `debit_linked_account`, `credit_linked_account`,
`register_account`) on the Python worker's task queue (`TEMPORAL_TASK_QUEUE`, default `Supervisor`),
so the Python worker must be running too, and the chaos panel's flags apply unchanged. The only Java
activity is the one that signals status changes to the parent workflow; it runs on the Open Account
task queue with the workflow.

As in the Python version, the `update_client_details` update saves the customer's changes (through the
Python `update_client` activity) and completes KYC.

## Prerequisites

* [Java JDK 25](https://adoptium.net/) - the Gradle wrapper (`./gradlew`, Gradle 9.8.2) is included, so no separate Gradle install is needed
* Everything the Python demo needs (Temporal CLI, Redis, uv, OpenAI API key). See the [Temporal README](../src/temporal_supervisor/README.md).

## Running Locally

Start Temporal (`temporal server start-dev`) and Redis (`redis-server`).

The Open Account task queue name is passed as the first argument to both workers. Start the Python
worker with it, so the supervisor starts the child workflow on that queue (and doesn't register the
Python version of the workflow):

```bash
cd src/temporal_supervisor
./startlocalworker.sh Open-Account-Java
```

Then, from the repository root, start the Java worker with the same name:

```bash
cd java
./startlocalworker.sh Open-Account-Java
```

The script sets `TEMPORAL_TASK_QUEUE_OPEN_ACCOUNT` from the argument, sources `../setclaimcheck.sh`
if it exists (claim check is optional) and runs `./gradlew runWorker`. It connects to `127.0.0.1:7233`, namespace `default`, as set
in `src/main/resources/application.yaml`. When claim check is enabled, the Java worker uses the Redis at
`spring.data.redis` in `application.yaml` (`localhost:6379`), not `REDIS_HOST` / `REDIS_PORT`.

Start the API and the UX as described in the [Temporal README](../src/temporal_supervisor/README.md),
and send the compliance approval with `src/temporal_supervisor/localsendcomplianceapproval.sh` as usual.

To try the Java workflow without the chat or an OpenAI key, run the open-account scenarios against it
(with this worker running): `src/temporal_supervisor/startlocalopenaccount.sh Open-Account-Java`. See
"Testing the Open Account workflow on its own" in the [Temporal README](../src/temporal_supervisor/README.md).

## Running with Temporal Cloud

Create `setcloudenv.sh` in the repository root (copy `src/temporal_supervisor/setcloudenv.example`)
as described in the [Temporal README](../src/temporal_supervisor/README.md#running-the-demo-in-temporal-cloud).
Start the Python worker with the queue name, then the Java worker with the same name:

```bash
cd src/temporal_supervisor
./startcloudworker.sh Open-Account-Java
```

```bash
cd java
./startcloudworker.sh Open-Account-Java
```

The Java cloud script can be run from any directory. It sources `../setclaimcheck.sh` (if it exists) and `../setcloudenv.sh`, maps `TEMPORAL_TLS_CLIENT_CERT_PATH` to the
`TEMPORAL_CERT_PATH` the Java worker reads, uses the Spring profile `tc`
(`src/main/resources/application-tc.yaml`), and runs `./gradlew runWorker`. With this profile, the
claim check Redis comes from `REDIS_HOST` / `REDIS_PORT` (default `localhost:6379`).

Java's TLS needs the client key as an unencrypted PKCS8 key (`-----BEGIN PRIVATE KEY-----`). If
`TEMPORAL_TLS_CLIENT_KEY_PATH` points to a different format, the script stops and prints the command
to convert it, for example:

```bash
openssl pkcs8 -topk8 -nocrypt -in /path/to/key.key -out /path/to/key.pkcs8.key
```

Then add the converted key to `setcloudenv.sh` (the Python components keep using
`TEMPORAL_TLS_CLIENT_KEY_PATH`):

```bash
export TEMPORAL_KEY_PKCS8_PATH="/path/to/key.pkcs8.key"
```

## Bug in the workflow code (chaos panel)

The chaos panel's **Bug in workflow code** switch gives new account openings the promo code
`WELCOME-BONUS`. In `src/main/java/io/temporal/demo/wealthmanagement/workflow/OpenInvestmentAccountWorkflowImpl.java`,
`BONUS_RATES` is keyed by `"WELCOME_BONUS"` (underscore), so `welcomeBonus` throws a
`NullPointerException` right after compliance approval. The exception fails the workflow task, not the
workflow, so the workflow stays **Running**, paused at that line. To fix it, use the commented-out
`BONUS_RATES` line above it and restart the Java worker; the workflow resumes on the next
workflow-task retry. Re-arm the bug afterwards, from the repository root:

```bash
git checkout java/src/main/java/io/temporal/demo/wealthmanagement/workflow/OpenInvestmentAccountWorkflowImpl.java
```

See [Failure scenarios](../src/temporal_supervisor/README.md#failure-scenarios-chaos-panel) for the other scenarios.

## Tests

The saga, retry and workflow-bug tests use the Temporal Java SDK's in-memory test environment with
stub activities, so no Temporal server, Redis or OpenAI key is needed:

```bash
cd java
./gradlew test
```
