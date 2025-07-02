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
Supervisor Agent Could you please provide your account ID so I can assist you further?
Enter your message: 123
Supervisor Agent: Skipping item: HandoffCallItem
Handed off from Supervisor Agent to Beneficiary Agent
Beneficiary Agent: Calling a tool
Beneficiary Agent: Tool call output: [{'beneficiary_id': 'b-1b011a72', 'first_name': 'John', 'last_name': 'Doe', 'relationship': 'son'}, {'beneficiary_id': 'b-3bc09dd2', 'first_name': 'Jane', 'last_name': 'Doe', 'relationship': 'daughter'}, {'beneficiary_id': 'b-14c4b7ec', 'first_name': 'Joan', 'last_name': 'Doe', 'relationship': 'spouse'}]
Beneficiary Agent Here are your current beneficiaries:

1. **John Doe** - Son
2. **Jane Doe** - Daughter
3. **Joan Doe** - Spouse

Would you like to add, delete, or make any changes to your beneficiaries?
Enter your message: show investment accounts
Beneficiary Agent: Skipping item: HandoffCallItem
Handed off from Beneficiary Agent to Supervisor Agent
Supervisor Agent: Skipping item: HandoffCallItem
Handed off from Supervisor Agent to Investment Agent
Investment Agent: Calling a tool
Investment Agent: Tool call output: [{'investment_id': 'i-8f494d01', 'name': 'Checking', 'balance': 1000.0}, {'investment_id': 'i-1872ae24', 'name': 'Savings', 'balance': 2312.08}, {'investment_id': 'i-8846d0b8', 'name': '401K', 'balance': 11070.89}]
Investment Agent Here are your investment accounts and their balances:

1. **Checking**: $1,000.00
2. **Savings**: $2,312.08
3. **401K**: $11,070.89

Would you like to open a new account, close an existing one, or see more details about any account?
Enter your message: quit
```

You can also add and delete beneficiaries and open and close investment accounts.