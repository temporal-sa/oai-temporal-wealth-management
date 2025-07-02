# Wealth Management Agent Example using OpenAI Agents SDK
Demonstrates how to use OpenAI Agents SDK using handoffs to other agents. 

The OpenAI Agents SDK version of this example is located [here](src/oai_supervisor/README.md)
The Temporal version of this example is located [here](src/temporal_supervisor/README.md) 

Scenarios currently implemented include
* Add Beneficiary - add a new beneficiary to your account
* List Beneficiaries - shows a list of beneficiaries and their relationship to the account owner
* Delete Beneficiary - delete a beneficiary from your account
* Open Investment Account - opens a new investment account
* List Investments - shows a list of accounts and their current balances
* Close Investment Account - closes an investment account

## Prerequisites

* [Poetry](https://python-poetry.org/docs/) - Python Dependency Management
* [OpenAI API Key] (https://platform.openai.com/api-keys) -

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

See the OpenAI Agents SDK Version [here](src/oai_supervisor/README.md)
And the Temporal version of this example is located [here](src/temporal_supervisor/README.md)

![](images/architecture.png)