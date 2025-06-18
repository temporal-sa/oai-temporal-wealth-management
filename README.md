# Wealth Management Agent Example using OpenAI Agents SDK
Demonstrates how to use OpenAI Agents SDK using handoffs to other agents. 

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

## Running the agent
```bash
source setoaikey.sh
poetry run python src/oai_supervisor/main.py
```

You can ask for your beneficiaries or investment accounts. In either case, you will be prompted to enter in an account ID which at this time can be anyting
