# Wealth Management Agent Example using OpenAI Agents SDK
Demonstrates how to use OpenAI Agents with Temporal. It demonstrates how to use handoffs to other agents. 
The supervisor agent is responsible for directing the actions to the appropriate helper agents.   

Scenarios currently implemented include
* Add Beneficiary - add a new beneficiary to your account
* List Beneficiaries - shows a list of beneficiaries and their relationship to the account owner
* Delete Beneficiary - delete a beneficiary from your account
* Open Investment Account - opens a new investment account
* List Investments - shows a list of accounts and their current balances
* Close Investment Account - closes an investment account
* 
## Prerequisites

* [Poetry](https://python-poetry.org/docs/) - Python Dependency Management
* [Redis](https://redis.io/downloads/) - Redis - Optional. Only needed if you want to use the Claim Check pattern. 

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
```bash
export OPENAI_API_KEY=sk-proj-....
```

## Set up Claim Check / Redis (optional)

An optional configuration is to substitute the data sent to Temporal (e.g. function/method parameters and return values)
with an ID. This is known as the [Claim Check Pattern](https://www.enterpriseintegrationpatterns.com/patterns/messaging/StoreInLibrary.html). 
The original data is stored in Redis. This uses a 
[Custom Payload Codec](https://docs.temporal.io/develop/python/converters-and-encryption#custom-payload-codec) 
that intercepts data going to Temporal Cloud, replaces it with a GUID. When the data is retrieved, it looks up the GUID 
replaces it with the data stored in Redis.

```bash
cp setclaimcheck.example setclaimcheck.sh
chmod +x setclaimcheck.sh
```

Now edit the setclaimcheck.sh file and fill in the location of Redis
It should look something like this:
```bash
export USE_CLAIM_CHECK=true
export REDIS_HOST=localhost
export REDIS_PORT=6379
```

Save the file and be sure that you have Redis running. 

## Running the Demo Locally
Start Temporal Locally.

```bash
temporal server start-dev
```

### Start the Worker
This assumes you are already in the src/temporal_supervisor folder. 
```bash
cd src/temporal_supervisor
./startlocalworker.sh
```

In another terminal, start the Console UX
### Start the Command Line UX
```bash
cd src/temporal_supervisor
./startlocalux.sh
```

## Running the Demo in Temporal Cloud

Copy the setcloudenv.example to setcloudenv.sh in the src/temporal_supervisor folder.

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

### Start the Console UX
```bash
cd src/temporal_supervisor
./startcloudux.sh <Workflow ID>
```

Example output:
```text
Using mTLS authentication
Checking to see if the workflow is already running...
Workflow is not currently running. Will start it.
Starting workflow using WMAgent43

Welcome to ABC Wealth Management. How can I help you?
Enter your message: Who are my beneficiaries?
User: Who are my beneficiaries?
Supervisor Agent Could you please provide your account ID so I can assist you further?
Enter your message: 123
User: 123
Supervisor Agent: Skipping item: HandoffCallItem
Handed off from Supervisor Agent to Beneficiary Agent
Beneficiary Agent: Calling a tool
Beneficiary Agent: Tool call output: [{'beneficiary_id': 'b-1b011a72', 'first_name': 'John', 'last_name': 'Doe', 'relationship': 'son'}, {'beneficiary_id': 'b-3bc09dd2', 'first_name': 'Jane', 'last_name': 'Doe', 'relationship': 'daughter'}, {'beneficiary_id': 'b-14c4b7ec', 'first_name': 'Joan', 'last_name': 'Doe', 'relationship': 'spouse'}]
Beneficiary Agent Here are your current beneficiaries:

1. **John Doe** - Son
2. **Jane Doe** - Daughter
3. **Joan Doe** - Spouse

Would you like to add, delete, or make any other changes to your beneficiaries?
Enter your message: what investment accounts do I have?
User: what investment accounts do I have?
Beneficiary Agent: Skipping item: HandoffCallItem
Handed off from Beneficiary Agent to Supervisor Agent
Supervisor Agent: Skipping item: HandoffCallItem
Handed off from Supervisor Agent to Investment Agent
Investment Agent: Calling a tool
Investment Agent: Tool call output: [{'investment_id': 'i-8f494d01', 'name': 'Checking', 'balance': 1000.0}, {'investment_id': 'i-1872ae24', 'name': 'Savings', 'balance': 2312.08}, {'investment_id': 'i-8846d0b8', 'name': '401K', 'balance': 11070.89}]
Investment Agent Here are your current investment accounts and their balances:

1. **Checking** - $1,000.00
2. **Savings** - $2,312.08
3. **401K** - $11,070.89

Would you like to open a new account, close an existing one, or perform any other actions?
Enter your message: end
```

You can also add and delete beneficiaries and open and close investment accounts.

Here is a sample event history shown in the Temporal UX

![](../../images/temporal-event-history.png)