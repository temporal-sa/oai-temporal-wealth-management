import json
import os
import uuid
import argparse

script_dir = os.path.dirname(__file__)
relative_path = '../data/investments.json'
INVESTMENTS_FILE =  os.path.join(script_dir, relative_path)

class InvestmentAccountManager:
    def __init__(self, json_file=INVESTMENTS_FILE):
        self.json_file = json_file
        self._load_data()

    def _load_data(self):
        """Loads investment account data from the JSON file."""
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
        """Saves current investment account data to the JSON file."""
        with open(self.json_file, 'w') as f:
            json.dump(self.data, f, indent=2)

    def list_investment_accounts(self, user_account_id):
        """
        Returns a list of investment accounts for a given user_account_id.
        Returns an empty list if the user_account_id does not exist.
        """
        if user_account_id not in self.data:
            return []  # No accounts for this user

        return self.data.get(user_account_id, [])

    def add_investment_account(self, user_account_id, name, balance):
        """
        Adds a new investment account to a user's portfolio.
        Automatically generates a unique investment_id.
        Creates the user_account_id if it doesn't exist.
        """
        try:
            balance = float(balance)
            if balance < 0:
                print("Error: Balance cannot be negative.")
                return None
        except ValueError:
            print("Error: Balance must be a numeric value.")
            return None

        if user_account_id not in self.data:
            self.data[user_account_id] = []

        # Generate a unique beneficiary ID for this account
        existing_ids = {i['investment_id'] for i in self.data[user_account_id]}

        # Use UUID for robust uniqueness, then truncate for a shorter, readable ID
        new_investment_id = f"i-{str(uuid.uuid4())[:8]}"
        while new_investment_id in existing_ids:
            new_investment_id = f"i-{str(uuid.uuid4())[:8]}"

        new_account = {
            "investment_id": new_investment_id,
            "name": name,
            "balance": balance
        }

        self.data[user_account_id].append(new_account)
        self._save_data()
        return new_account  # Return the newly added account details

    def delete_investment_account(self, user_account_id, investment_id):
        """
        Deletes an investment account for a given user_account_id and investment_id.
        Returns True if deleted, False otherwise.
        """
        if user_account_id not in self.data:
            return False  # User account not found

        initial_count = len(self.data[user_account_id])

        # Filter out the account to be deleted
        self.data[user_account_id] = [
            account for account in self.data[user_account_id]
            if account["investment_id"] != investment_id
        ]

        if len(self.data[user_account_id]) < initial_count:
            # If the list is now empty for this user, we might want to remove the user_account_id entry entirely
            if not self.data[user_account_id]:
                del self.data[user_account_id]
            self._save_data()
            return True
        else:
            return False  # Investment account not found for this user


def main():
    parser = argparse.ArgumentParser(
        description="Manage your investment accounts via the command line."
    )

    # Subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # --- List Command ---
    list_parser = subparsers.add_parser("list", help="List investment accounts for a user.")
    list_parser.add_argument("user_account_id", type=str, help="The ID of the user account.")

    # --- Add Command ---
    add_parser = subparsers.add_parser("add", help="Add a new investment account.")
    add_parser.add_argument("user_account_id", type=str, help="The ID of the user account to add to.")
    add_parser.add_argument("name", type=str, help="The name of the investment account (e.g., 'Roth IRA').")
    add_parser.add_argument("balance", type=float, help="The initial balance of the investment account.")

    # --- Delete Command ---
    delete_parser = subparsers.add_parser("delete", help="Delete an investment account.")
    delete_parser.add_argument("user_account_id", type=str, help="The ID of the user account.")
    delete_parser.add_argument("investment_id", type=str, help="The ID of the investment account to delete.")

    args = parser.parse_args()

    manager = InvestmentAccountManager()

    if args.command == "list":
        accounts = manager.list_investment_accounts(args.user_account_id)
        if accounts:
            print(f"\nInvestment Accounts for User '{args.user_account_id}':")
            for account in accounts:
                print(f"  ID: {account['investment_id']}")
                print(f"  Name: {account['name']}")
                print(f"  Balance: ${account['balance']:.2f}")
                print("-" * 20)
        else:
            print(f"No investment accounts found for user '{args.user_account_id}'.")

    elif args.command == "add":
        new_account = manager.add_investment_account(args.user_account_id, args.name, args.balance)
        if new_account:
            print(f"\nSuccessfully added new investment account to user '{args.user_account_id}':")
            print(f"  ID: {new_account['investment_id']}")
            print(f"  Name: {new_account['name']}")
            print(f"  Balance: ${new_account['balance']:.2f}")

    elif args.command == "delete":
        if manager.delete_investment_account(args.user_account_id, args.investment_id):
            print(
                f"\nSuccessfully deleted investment account '{args.investment_id}' for user '{args.user_account_id}'.")
        else:
            print(f"\nCould not delete investment account '{args.investment_id}' for user '{args.user_account_id}'. "
                  "Check if both the user account ID and investment account ID are correct.")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()


## Creating Sample Data
# python investment_account_manager.py add 123 "Checking" 1000.00
# python investment_account_manager.py add 123 "Savings" 2312.08
# python investment_account_manager.py add 123 "401K" 11070.89
# python investment_account_manager.py add 234 "Checking" 203.45
# python investment_account_manager.py add 234 "Savings" 375.81
# python investment_account_manager.py add 234 "Retirement" 24648.63
# python investment_account_manager.py list 123
# will have to replace the last parameter
# python investment_account_manager.py delete 123 i-0009bbfd
# then add it back in
# python investment_account_manager.py add 123 "401K" 11070.89

