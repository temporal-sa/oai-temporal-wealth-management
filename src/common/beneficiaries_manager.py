import json
import os
import argparse
import uuid  # For generating unique beneficiary IDs
import logging
from typing import List, Dict, Any

# --- Configuration ---
script_dir = os.path.dirname(__file__)
relative_path = '../../data/beneficiaries.json'
BENEFICIARIES_FILE =  os.path.join(script_dir, relative_path)
# logging.basicConfig(level=logging.INFO,
#                     format="%(asctime)s | %(levelname)s | %(filename)s:%(lineno)s | %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class BeneficiariesManager:
    """
    Manages beneficiaries data stored in a JSON file.
    Each client has its own list of beneficiaries, uniquely identified by a beneficiary_id within that client.
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

    def list_beneficiaries(self, client_id: str):
        """
        Retrieves all beneficiaries for a given client ID.
        Args:
            client_id (str): The ID of the client.
        Returns:
            list: A list of beneficiary dictionaries for the specified client, or an empty list if none are found.
        """
        data = self._load_data()
        beneficiaries = data.get(client_id, [])
        return beneficiaries

    def add_beneficiary(self, client_id: str, first_name: str, last_name: str, relationship: str) -> None:
        """
        Adds a new beneficiary to the specified client.
        Generates a unique beneficiary_id for the client.
        Args:
            client_id (str): The ID of the client.
            first_name (str): First name of the beneficiary.
            last_name (str): Last name of the beneficiary.
            relationship (str): Relationship to the client.
        """
        data = self._load_data()

        # Ensure the client ID exists in the data
        if client_id not in data:
            data[client_id] = []

        # Generate a unique beneficiary ID for this client
        existing_ids = {b['beneficiary_id'] for b in data[client_id]}

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

        data[client_id].append(new_beneficiary)
        self._save_data(data)
        logger.info(f"\nBeneficiary '{first_name} {last_name}' (ID: {new_id}) added to client '{client_id}'.")

    def delete_beneficiary(self, client_id: str, beneficiary_id: str) -> None:
        """
        Deletes a beneficiary from the specified client using their unique beneficiary ID.
        Args:
            client_id (str): The ID of the client.
            beneficiary_id (str): The unique ID of the beneficiary to delete.
        """
        data = self._load_data()

        if client_id not in data or not data[client_id]:
            logger.warning(f"\nClient '{client_id}' not found or has no beneficiaries.")
            return

        original_count = len(data[client_id])

        # Filter out the beneficiary to be deleted
        data[client_id] = [
            b for b in data[client_id]
            if b['beneficiary_id'] != beneficiary_id
        ]

        if len(data[client_id]) < original_count:
            self._save_data(data)
            logger.info(f"\nBeneficiary with ID '{beneficiary_id}' deleted from client '{client_id}'.")
        else:
            logger.error(f"\nBeneficiary with ID '{beneficiary_id}' not found in client '{client_id}'.")


# --- Command Line Interface (CLI) Setup ---

def main():
    parser = argparse.ArgumentParser(
        description="Manage beneficiaries for different clients.",
        epilog="Example usage:\n"
               "  python beneficiary_manager.py --list --client-id client123\n"
               "  python beneficiary_manager.py --add --client-id client123 --first-name Jane --last-name Doe --relationship Sister\n"
               "  python beneficiary_manager.py --delete --client-id client123 --beneficiary-id b-4f6a7d12"
    )

    # Global argument for client ID
    parser.add_argument(
        '--client-id',
        type=str,
        required=True,
        help='The ID of the client to manage beneficiaries for.'
    )

    # Mutually exclusive group for actions
    action_group = parser.add_mutually_exclusive_group(required=True)

    action_group.add_argument(
        '--list',
        action='store_true',
        help='List all beneficiaries for the specified client ID.'
    )
    action_group.add_argument(
        '--add',
        action='store_true',
        help='Add a new beneficiary to the specified client ID.'
    )
    action_group.add_argument(
        '--delete',
        action='store_true',
        help='Delete a beneficiary from the specified client ID using its beneficiary ID.'
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
        beneficiaries = manager.list_beneficiaries(args.client_id)
        if not beneficiaries:
            print(f"\nNo beneficiaries found for client ID: '{args.client_id}'")
        else:
            print(f"\n--- Beneficiaries for Client ID: '{args.client_id}' ---")
            print("-" * 50)
            for bene in beneficiaries:
                print(f"  ID: {bene['beneficiary_id']}")
                print(f"  Name: {bene['first_name']} {bene['last_name']}")
                print(f"  Relationship: {bene['relationship']}")
                print("-" * 50)
    elif args.add:
        if not all([args.first_name, args.last_name, args.relationship]):
            parser.error("--add requires --first-name, --last-name, and --relationship.")
        manager.add_beneficiary(args.client_id, args.first_name, args.last_name, args.relationship)
    elif args.delete:
        if not args.beneficiary_id:
            parser.error("--delete requires --beneficiary-id.")
        manager.delete_beneficiary(args.client_id, args.beneficiary_id)


if __name__ == "__main__":
    main()

# python3 beneficiaries_manager.py --client-id 123 --add --first-name John --last-name Doe --relationship son
# python3 beneficiaries_manager.py --client-id 123 --add --first-name Jane --last-name Doe --relationship daughter
# python3 beneficiaries_manager.py --client-id 123 --add --first-name Joan --last-name Doe --relationship spouse
# python3 beneficiaries_manager.py --client-id 234 --add --first-name Fred --last-name Smith --relationship son
# python3 beneficiaries_manager.py --client-id 234 --add --first-name Sandy --last-name Smith --relationship daughter
# python3 beneficiaries_manager.py --client-id 234 --add --first-name Jessica --last-name Smith --relationship daughter
# python beneficiaries_manager.py --client-id 345 --add --first-name Peter --last-name Parker --relationship friend
# python beneficiaries_manager.py --client-id 345 --delete --beneficiary-id b-1bfdd678