# Wealth Management Agent Example using OpenAI Agents SDK
Demonstrates how to use OpenAI Agents with Temporal. It demonstrates how to use handoffs to other agents. 
The supervisor agent is responsible for directing the actions to the appropriate helper agents.   

Scenarios currently implemented include
* List Beneficiaries - shows a list of beneficiaries and their relationship to the account owner
* List Investments - shows a list of accounts and their current balances

## Prerequisties

* [Poetry](https://python-poetry.org/docs/) - Python Dependency Management

## Set up Python Environment
```bash
poetry install
```

## Set up your OpenAI API Key
 
```bash
cp setoaikey.example setoaikey.sh
chmod +x setoaikey.sh
```

Now edit the setoaikey.sh file and paste in your OpenAI API Key.
It should look something like this:
```text
export OPENAI_API_KEY=sk-proj-....
```

## Running the Demo Locally
Start Temporal Locally.

```bash
temporal server start-dev
```

### Start the Worker
```bash
./startlocalworker.sh
```

### Start the Command Line UX
```bash
./startlocalux.sh
```

You can ask for your beneficiaries or investment accounts. In either case, you will be prompted to enter in an account ID which at this time can be anything

## Running the Demo in Temporal Cloud

Copy the setcloudenv.example to setcloudenv.sh

```bash
cp setcloundenv.sh setcloudenv.sh
```

Edit setcloudenv.sh to match your Temporal Cloud account:
```bash
export TEMPORAL_ADDRESS=<namespace>.<accountID>.tmprl.cloud:7233
export TEMPORAL_NAMESPACE=<namespace>.<accountID>
export TEMPORAL_CERT_PATH="/path/to/cert.pem"
export TEMPORAL_KEY_PATH="/path/to/key.key"
```
### Start the Worker
```bash
cd src/temporal_supervisor
./startcloudworker.sh
```
In a new terminal, run the the UX, passing in a Workflow ID 

### Start the Command Line UX
```bash
cd src/temporal_supervisor
./startcloudux.sh <Workflow ID>
```

You can ask for your beneficiaries or investment accounts. In either case, you will be prompted to enter in an account ID which at this time can be anything