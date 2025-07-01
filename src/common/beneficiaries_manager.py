import json
import os
import argparse
import uuid  # For generating unique beneficiary IDs
import logging
from typing import List, Dict, Any

# --- Configuration ---
script_dir = os.path.dirname(__file__)
relative_path = '../data/beneficiaries.json'
BENEFICIARIES_FILE =  os.path.join(script_dir, relative_path)
# logging.basicConfig(level=logging.INFO,
#                     format="%(asctime)s | %(levelname)s | %(filename)s:%(lineno)s | %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class BeneficiariesManager:
    """
    Manages beneficiaries data stored in a JSON file.
    Each account has its own list of beneficiaries, uniquely identified by a beneficiary_id within that account.
    """

    def __init__(self, file_path: str = BENEFICIARIES_FILE):
        """
        Initializes the BeneficiariesManager.
        Args:
            file_path (str): The path to the JSON file where beneficiary data is stored.
        """
        self.file_path = file_path

    def _load_data(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Loads beneficiary data from the JSON file.
        If the file doesn't exist or is empty/invalid, returns an empty dictionary.
        Returns:
            dict: The loaded beneficiary data.
        """
        if not os.path.exists(self.file_path) or os.stat(self.file_path).st_size == 0:
            return {}
        try:
            with open(self.file_path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            logger.warning(f"Warning: Could not decode JSON from '{self.file_path}'. Starting with empty data.")
            return {}
        except Exception as e:
            logger.error(f"Error loading data from '{self.file_path}': {e}")
            return {}

    def _save_data(self, data: Dict[str, List[Dict[str, Any]]]):
        """
        Saves the current beneficiary data to the JSON file.
        Args:
            data (dict): The beneficiary data to save.
        """
        try:
            with open(self.file_path, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving data to '{self.file_path}': {e}")

    def list_beneficiaries(self,  account_id: str):
        """
        Retrieves all beneficiaries for a given account ID.
        Args:
            account_id (str): The ID of the account.
        Returns:
            list: A list of beneficiary dictionaries for the specified account, or an empty list if none are found.
        """
        data = self._load_data()
        beneficiaries = data.get(account_id, [])
        return beneficiaries

    def add_beneficiary(self, account_id: str, first_name: str, last_name: str, relationship: str) -> None:
        """
        Adds a new beneficiary to the specified account.
        Generates a unique beneficiary_id for the account.
        Args:
            account_id (str): The ID of the account.
            first_name (str): First name of the beneficiary.
            last_name (str): Last name of the beneficiary.
            relationship (str): Relationship to the account holder.
        """
        data = self._load_data()

        # Ensure the account ID exists in the data
        if account_id not in data:
            data[account_id] = []

        # Generate a unique beneficiary ID for this account
        existing_ids = {b['beneficiary_id'] for b in data[account_id]}

        # Use UUID for robust uniqueness, then truncate for a shorter, readable ID
        new_id = f"b-{str(uuid.uuid4())[:8]}"
        while new_id in existing_ids:  # Ensure it's truly unique if a rare collision occurs with truncation
            new_id = f"b-{str(uuid.uuid4())[:8]}"

        new_beneficiary = {
            "beneficiary_id": new_id,
            "first_name": first_name,
            "last_name": last_name,
            "relationship": relationship
        }

        data[account_id].append(new_beneficiary)
        self._save_data(data)
        logger.info(f"\nBeneficiary '{first_name} {last_name}' (ID: {new_id}) added to account '{account_id}'.")

    def delete_beneficiary(self, account_id: str, beneficiary_id: str) -> None:
        """
        Deletes a beneficiary from the specified account using their unique beneficiary ID.
        Args:
            account_id (str): The ID of the account.
            beneficiary_id (str): The unique ID of the beneficiary to delete.
        """
        data = self._load_data()

        if account_id not in data or not data[account_id]:
            logger.warning(f"\nAccount '{account_id}' not found or has no beneficiaries.")
            return

        original_count = len(data[account_id])

        # Filter out the beneficiary to be deleted
        data[account_id] = [
            b for b in data[account_id]
            if b['beneficiary_id'] != beneficiary_id
        ]

        if len(data[account_id]) < original_count:
            self._save_data(data)
            logger.info(f"\nBeneficiary with ID '{beneficiary_id}' deleted from account '{account_id}'.")
        else:
            logger.error(f"\nBeneficiary with ID '{beneficiary_id}' not found in account '{account_id}'.")


# --- Command Line Interface (CLI) Setup ---

def main():
    parser = argparse.ArgumentParser(
        description="Manage beneficiaries for different accounts.",
        epilog="Example usage:\n"
               "  python beneficiary_manager.py --list --account-id account123\n"
               "  python beneficiary_manager.py --add --account-id account123 --first-name Jane --last-name Doe --relationship Sister\n"
               "  python beneficiary_manager.py --delete --account-id account123 --beneficiary-id b-4f6a7d12"
    )

    # Global argument for account ID
    parser.add_argument(
        '--account-id',
        type=str,
        required=True,
        help='The ID of the account to manage beneficiaries for.'
    )

    # Mutually exclusive group for actions
    action_group = parser.add_mutually_exclusive_group(required=True)

    action_group.add_argument(
        '--list',
        action='store_true',
        help='List all beneficiaries for the specified account ID.'
    )
    action_group.add_argument(
        '--add',
        action='store_true',
        help='Add a new beneficiary to the specified account ID.'
    )
    action_group.add_argument(
        '--delete',
        action='store_true',
        help='Delete a beneficiary from the specified account ID using its beneficiary ID.'
    )

    # Arguments for adding a beneficiary
    parser.add_argument(
        '--first-name',
        type=str,
        help='First name of the beneficiary (required for --add).'
    )
    parser.add_argument(
        '--last-name',
        type=str,
        help='Last name of the beneficiary (required for --add).'
    )
    parser.add_argument(
        '--relationship',
        type=str,
        help='Relationship of the beneficiary (e.g., "Spouse", "Child", "Friend") (required for --add).'
    )

    # Argument for deleting a beneficiary
    parser.add_argument(
        '--beneficiary-id',
        type=str,
        help='Unique ID of the beneficiary to delete (required for --delete).'
    )

    args = parser.parse_args()

    # Create an instance of the BeneficiariesManager
    manager = BeneficiariesManager()

    # --- Execute actions based on arguments ---
    if args.list:
        beneficiaries = manager.list_beneficiaries(args.account_id)
        if not beneficiaries:
            print(f"\nNo beneficiaries found for account ID: '{args.account_id}'")
        else:
            print(f"\n--- Beneficiaries for Account ID: '{args.account_id}' ---")
            print("-" * 50)
            for bene in beneficiaries:
                print(f"  ID: {bene['beneficiary_id']}")
                print(f"  Name: {bene['first_name']} {bene['last_name']}")
                print(f"  Relationship: {bene['relationship']}")
                print("-" * 50)
    elif args.add:
        if not all([args.first_name, args.last_name, args.relationship]):
            parser.error("--add requires --first-name, --last-name, and --relationship.")
        manager.add_beneficiary(args.account_id, args.first_name, args.last_name, args.relationship)
    elif args.delete:
        if not args.beneficiary_id:
            parser.error("--delete requires --beneficiary-id.")
        manager.delete_beneficiary(args.account_id, args.beneficiary_id)


if __name__ == "__main__":
    main()

# python3 beneficiaries_manager.py --account-id 123 --add --first-name John --last-name Doe --relationship son
# python3 beneficiaries_manager.py --account-id 123 --add --first-name Jane --last-name Doe --relationship daughter
# python3 beneficiaries_manager.py --account-id 123 --add --first-name Joan --last-name Doe --relationship spouse
# python3 beneficiaries_manager.py --account-id 234 --add --first-name Fred --last-name Smith --relationship son
# python3 beneficiaries_manager.py --account-id 234 --add --first-name Sandy --last-name Smith --relationship daughter
# python3 beneficiaries_manager.py --account-id 234 --add --first-name Jessica --last-name Smith --relationship daughter