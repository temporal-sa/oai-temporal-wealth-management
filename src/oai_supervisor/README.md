# Wealth Management Agent Example using OpenAI Agents SDK
Demonstrates how to use OpenAI Agents SDK using handoffs to other agents. 

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

Example Output
```
Welcome to ABC Wealth Management. How can I help you?
Enter your message: Who are my beneficiaries? 
Supervisor Agent Could you please provide your account ID?
Enter your message: 234
Supervisor Agent: Skipping item: HandoffCallItem
Handed off from Supervisor Agent to Beneficiary Agent
Beneficiary Agent: Calling a tool
Beneficiary Agent: Tool call output: [{'beneficiary_id': 'b-97fba0db', 'first_name': 'Fred', 'last_name': 'Smith', 'relationship': 'son'}, {'beneficiary_id': 'b-c259e04f', 'first_name': 'Sandy', 'last_name': 'Smith', 'relationship': 'daughter'}, {'beneficiary_id': 'b-480b64e7', 'first_name': 'Jessica', 'last_name': 'Smith', 'relationship': 'daughter'}]
Beneficiary Agent Here are your beneficiaries:

1. **Fred Smith** - Son
2. **Sandy Smith** - Daughter
3. **Jessica Smith** - Daughter

Would you like to add, delete, or do something else with your beneficiaries?
Enter your message: What investment accounts do I have?
Beneficiary Agent: Skipping item: HandoffCallItem
Handed off from Beneficiary Agent to Supervisor Agent
Supervisor Agent: Skipping item: HandoffCallItem
Handed off from Supervisor Agent to Investment Agent
Investment Agent: Calling a tool
Investment Agent: Tool call output: [{'investment_id': 'i-6afa7b82', 'name': 'Checking', 'balance': 203.45}, {'investment_id': 'i-723c0a6f', 'name': 'Savings', 'balance': 375.81}, {'investment_id': 'i-e960edaf', 'name': 'Retirement', 'balance': 24648.63}]
Investment Agent Here are your investment accounts and their balances:

1. **Checking**: $203.45
2. **Savings**: $375.81
3. **Retirement**: $24,648.63

Would you like to open a new investment account, close an existing one, or perform another action?
Enter your message: quit
```

You can also add and delete beneficiaries and open and close investment accounts.