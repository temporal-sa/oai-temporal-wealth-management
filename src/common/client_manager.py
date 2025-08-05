import argparse
import json
import os
from datetime import datetime

# --- Configuration ---
script_dir = os.path.dirname(__file__)
clients_relative_path = '../../data/clients.json'
CLIENTS_FILE = os.path.join(script_dir, clients_relative_path)

class ClientManager:
    def __init__(self, file_path: str = CLIENTS_FILE):
        self.file_path = file_path

    def get_client(self, client_id: str) -> dict:
        try:
            print(f"looking for client {client_id} in {self.file_path}")
            with open(self.file_path, "r") as f:
                clients = json.load(f)
            print(f"clients is {clients}")
            return clients.get(client_id, {"error": f"Client {client_id} not found"})
        except Exception as e:
            return {"error": f"Exception occurred while retrieving Client {client_id} error: {e}"}

    def add_client(self, client_id: str, first_name: str,
                   last_name: str, address: str, phone: str,
                   email: str, marital_status: str) -> str:
        try:
            with open(self.file_path, "r+") as f:
                clients = json.load(f)
                if client_id in clients:
                    return "Client already exists"

                new_client = {
                    "first_name": first_name,
                    "last_name": last_name,
                    "address": address,
                    "phone": phone,
                    "email": email,
                    "marital_status": marital_status,
                }
                clients[client_id] = new_client

                f.seek(0)
                json.dump(clients, f, indent=4)
                f.truncate()
                return f"Client {client_id} added"
        except Exception as e:
            return f"Exception occurred while adding Client {client_id} error: {e}"

    def update_client(self, client_id: str, new_info: dict) -> str:
        try:
            with open(self.file_path, "r+") as f:
                clients = json.load(f)
                if client_id in clients:
                    clients[client_id].update(new_info)
                    f.seek(0)
                    json.dump(clients, f, indent=4)
                    f.truncate()
                    return "Client information successfully updated"
                return f"Client {client_id} not found"
        except Exception as e:
            return f"Exception occurred while updating client {client_id} error: {e}"

def main():
    parser = argparse.ArgumentParser(
        description="",
        epilog="Example usage:\n"
               "  python client_manager.py --add --client-id client123 --first-name Jane --last-name Doe --address '123 Main Street' --phone 888-555-1212 --email jd@nowhere.com --marital_status single\n"
               "  python client_manager.py --update --client-id client123 --first-name Jane --last-name Doe --address '123 Main Street' --phone 888-555-1212 --email jd@nowhere.com --marital_status single\n"
               "  python client_manager.py --get --client-id client123"
    )

    # Global argument for Client ID
    parser.add_argument(
        '--client-id',
        type=str,
        required=True,
        help='The ID of the client to manage'
    )

    # Mutually exclusive group for actions
    action_group = parser.add_mutually_exclusive_group(required=True)
    action_group.add_argument(
        '--add',
        action='store_true',
        help='Add a new client with the specified client ID.'
    )
    action_group.add_argument(
        '--update',
        action='store_true',
        help='Update client information for the specified client ID.'
    )
    action_group.add_argument(
        '--get',
        action='store_true',
        help='Retrieve client information for the specified client ID.'
    )
    # Arguments for adding an client
    parser.add_argument(
        '--first-name',
        type=str,
        help='First name of the client (required for --add, optional for --update).'
    )
    parser.add_argument(
        '--last-name',
        type=str,
        help='Last name of the client (required for --add, optional for --update).'
    )
    parser.add_argument(
        '--address',
        type=str,
        help='Address of the client (required for --add, optional for --update).'
    )
    parser.add_argument(
        '--phone',
        type=str,
        help='Phone number of the client (required for --add, optional for --update).'
    )
    parser.add_argument(
        '--email',
        type=str,
        help='Email address of the client (required for --add, optional for --update).'
    )
    parser.add_argument(
        '--marital_status',
        type=str,
        help='Marital Status of the client (required for --add, optional for --update).'
    )

    args = parser.parse_args()
    client_manager = ClientManager()
    all_arguments = [args.first_name, args.last_name, args.address, args.phone, args.email, args.marital_status]
    if args.add:
        print("Adding a client")
        if not all(all_arguments):
            parser.error("--add requires --first-name, --last-name, --address, --phone, --email and --marital_status.")
        result = client_manager.add_client(args.client_id, args.first_name, args.last_name, args.address, args.phone, args.email, args.marital_status)
        print(f"Client {args.client_id} add result {result}")
    elif args.update:
        if not any(all_arguments):
            parser.error("--update requires at least one of --first-name, --last-name, --address, --phone, --email or --marital_status.")
        args_dict = vars(args)
        # filter for non None vars, remove boolean parameters (e.g. what operation) and
        # remove the client as it isn't stored as a property
        update_dict = {k: v for k, v in args_dict.items() if v is not None and not isinstance(v, bool) and k != 'client_id'}
        # print(f"Update dictionary looks like this: {update_dict}")
        result = client_manager.update_client(client_id=args.client_id, new_info=update_dict)
        print(f"Client {args.client_id} update result {result}")
    elif args.get:
        client = client_manager.get_client(client_id=args.client_id)
        print(json.dumps(client, indent=4))

if __name__ == "__main__":
    main()

# python client_manager.py --add --client-id 123 --first-name Don --last-name Doe --address '123 Main Street' --phone 888-555-1212 --email jd@example.com --marital_status married
# python client_manager.py --add --client-id 234 --first-name Frank --last-name Smith --address '234 Main Street' --phone 888-777-1212 --email fs@example.com --marital_status married
# python client_manager.py --get --client-id 123
# python client_manager.py --get --client-id 234
# python client_manager.py --update --client-id 123 --phone 999-555-1212 --email jd@someplace.com