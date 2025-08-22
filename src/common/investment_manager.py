import json
import os
from dataclasses import dataclass

import uuid
import argparse

script_dir = os.path.dirname(__file__)
relative_path = '../../data/investments.json'
INVESTMENTS_FILE =  os.path.join(script_dir, relative_path)

@dataclass
class InvestmentAccount:
    client_id: str
    name: str
    balance: float

class InvestmentManager:
    def __init__(self, json_file=INVESTMENTS_FILE):
        self.json_file = json_file
        self._load_data()

    def _load_data(self):
        """Loads investment client data from the JSON file."""
        if os.path.exists(self.json_file):
            with open(self.json_file, 'r') as f:
                try:
                    self.data = json.load(f)
                    # Ensure the top level is a dictionary
                    if not isinstance(self.data, dict):
                        print(f"Warning: JSON file '{self.json_file}' has an invalid root structure. Re-initializing.")
                        self.data = {}
                except json.JSONDecodeError:
                    print(f"Warning: JSON file '{self.json_file}' is corrupted or empty. Initializing with empty data.")
                    self.data = {}
        else:
            self.data = {}

    def _save_data(self):
        """Saves current investment client data to the JSON file."""
        with open(self.json_file, 'w') as f:
            json.dump(self.data, f, indent=2)

    def list_investment_accounts(self, client_id):
        """
        Returns a list of investment accounts for a given client_id.
        Returns an empty list if the client_id does not exist.
        """
        if client_id not in self.data:
            return []  # No investment accounts for this client

        return self.data.get(client_id, [])

    def add_investment_account(self, new_account: InvestmentAccount):
        """
        Adds a new investment account to a client's portfolio.
        Automatically generates a unique investment_id.
        Creates the client_id if it doesn't exist.
        """
        try:
            if new_account.balance < 0:
                print("Error: Balance cannot be negative.")
                return None
        except ValueError:
            print("Error: Balance must be a numeric value.")
            return None

        if new_account.client_id not in self.data:
            self.data[new_account.client_id] = []

        # Generate a unique beneficiary ID for this investment account
        existing_ids = {i['investment_id'] for i in self.data[new_account.client_id]}

        # Use UUID for robust uniqueness, then truncate for a shorter, readable ID
        new_investment_id = f"i-{str(uuid.uuid4())[:8]}"
        while new_investment_id in existing_ids:
            new_investment_id = f"i-{str(uuid.uuid4())[:8]}"

        new_investment_account = {
            "investment_id": new_investment_id,
            "name": new_account.name,
            "balance": new_account.balance
        }

        self.data[new_account.client_id].append(new_investment_account)
        self._save_data()
        return new_investment_account  # Return the newly added investment account details

    def delete_investment_account(self, client_id, investment_id):
        """
        Deletes an investment account for a given client_id and investment_id.
        Returns True if deleted, False otherwise.
        """
        if client_id not in self.data:
            return False  # Client not found

        initial_count = len(self.data[client_id])

        # Filter out the account to be deleted
        self.data[client_id] = [
            investment_account for investment_account in self.data[client_id]
            if investment_account["investment_id"] != investment_id
        ]

        if len(self.data[client_id]) < initial_count:
            # If the list is now empty for this client, we might want to remove the client_id entry entirely
            if not self.data[client_id]:
                del self.data[client_id]
            self._save_data()
            return True
        else:
            return False  # Investment account not found for this client


def main():
    parser = argparse.ArgumentParser(
        description="Manage your investment accounts via the command line."
    )

    # Subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # --- List Command ---
    list_parser = subparsers.add_parser("list", help="List investment accounts for a client.")
    list_parser.add_argument("client_id", type=str, help="The ID of the client.")

    # --- Add Command ---
    add_parser = subparsers.add_parser("add", help="Add a new investment account.")
    add_parser.add_argument("client_id", type=str, help="The ID of the client to add to.")
    add_parser.add_argument("name", type=str, help="The name of the investment account (e.g., 'Roth IRA').")
    add_parser.add_argument("balance", type=float, help="The initial balance of the investment account.")

    # --- Delete Command ---
    delete_parser = subparsers.add_parser("delete", help="Delete an investment account.")
    delete_parser.add_argument("client_id", type=str, help="The ID of the client.")
    delete_parser.add_argument("investment_id", type=str, help="The ID of the investment account to delete.")

    args = parser.parse_args()

    manager = InvestmentManager()

    if args.command == "list":
        investment_accounts = manager.list_investment_accounts(args.client_id)
        if investment_accounts:
            print(f"\nInvestment Accounts for Client '{args.client_id}':")
            for investment_account in investment_accounts:
                print(f"  ID: {investment_account['investment_id']}")
                print(f"  Name: {investment_account['name']}")
                print(f"  Balance: ${investment_account['balance']:.2f}")
                print("-" * 20)
        else:
            print(f"No investment accounts found for Client '{args.client_id}'.")

    elif args.command == "add":
        new_account = manager.add_investment_account(args.client_id, args.name, args.balance)
        if new_account:
            print(f"\nSuccessfully added new investment account to client '{args.client_id}':")
            print(f"  ID: {new_account['investment_id']}")
            print(f"  Name: {new_account['name']}")
            print(f"  Balance: ${new_account['balance']:.2f}")

    elif args.command == "delete":
        if manager.delete_investment_account(args.client_id, args.investment_id):
            print(
                f"\nSuccessfully deleted investment account '{args.investment_id}' for client '{args.client_id}'.")
        else:
            print(f"\nCould not delete investment account '{args.investment_id}' for client '{args.client_id}'. "
                  "Check if both the client ID and investment account ID are correct.")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()


## Creating Sample Data
# python investment_manager.py add 123 "Checking" 1000.00
# python investment_manager.py add 123 "Savings" 2312.08
# python investment_manager.py add 123 "401K" 11070.89
# python investment_manager.py add 234 "Checking" 203.45
# python investment_manager.py add 234 "Savings" 375.81
# python investment_manager.py add 234 "Retirement" 24648.63
# python investment_manager.py list 123
# will have to replace the last parameter
# python investment_manager.py delete 123 i-0009bbfd
# then add it back in
# python investment_manager.py add 123 "401K" 11070.89

