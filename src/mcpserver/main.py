import asyncio
import json
import os
import argparse

from fastmcp import FastMCP
from datetime import datetime

mcp = FastMCP(
    name="My Wealth Management MCP Server",
    on_duplicate_tools="warn")

import bcrypt

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

# --- Configuration ---
script_dir = os.path.dirname(__file__)
user_relative_path = '../../data/users.json'
USERS_FILE =  os.path.join(script_dir, user_relative_path)
accounts_relative_path = '../../data/accounts.json'
ACCOUNTS_FILE = os.path.join(script_dir, accounts_relative_path)

@mcp.tool
def create_user(username: str, password: str, account_id: str) -> str:
    """
    Creates a new user with a hashed password.
    """
    try:
        with open(USERS_FILE, "r+") as f:
            users = json.load(f)
            for user in users:
                if user["username"] == username:
                    return "User already exists"

            hashed_password = get_password_hash(password)
            users.append({"username": username, "password": hashed_password, "account_id": account_id})

            f.seek(0)
            json.dump(users, f, indent=4)
            f.truncate()
        return f"User {username}, account id {account_id} created successfully"
    except Exception as e:
        return f"Unexpected error adding a user {username}, id {account_id}: {e}"

@mcp.tool
def validate_user_account(username: str, password: str) -> dict:
    """
    Validates (or logins into) a user's account and returns their account ID if valid.
    """
    try:
        with open(USERS_FILE, "r") as f:
            users = json.load(f)
        for user in users:
            if user["username"] == username and verify_password(password, user["password"]):
                return { "account_id" : user["account_id"] }
        return { "error": f"Invalid credentials for {username}" }
    except Exception as e:
        return { "error": f"Exception validating user {username} account {e}"}

@mcp.tool
def get_user_account_info(account_id: str) -> dict:
    """
    Retrieves or displays the user's account information.
    """
    try:
        with open(ACCOUNTS_FILE, "r") as f:
            accounts = json.load(f)
        return accounts.get(account_id, {"error": f"User account {account_id} not found"})
    except Exception as e:
        return { "error": f"Exception occurred while retrieving user account {account_id} information: {e}" }

@mcp.tool
def add_user_account_info(account_id: str, first_name: str, last_name: str, address: str, phone: str, email: str, marital_status: str) -> str:
    """
    Adds a user's account information
    """
    try:
        with open(ACCOUNTS_FILE, "r+") as f:
            accounts = json.load(f)
            if account_id in accounts:
                return "Account already exists"

            new_account = {
                "first_name": first_name,
                "last_name": last_name,
                "address": address,
                "phone": phone,
                "email": email,
                "marital_status": marital_status,
                "date_of_last_change" :  datetime.now().isoformat()
            }

            accounts[account_id] = new_account

            f.seek(0)
            json.dump(accounts, f, indent=4)
            f.truncate()
            return "Account information added successfully."
    except Exception as e:
        return f"Exception occurred while adding user account {account_id} information: {e}"


@mcp.tool
def edit_user_account_info(account_id: str, new_info: dict) -> str:
    """
    Allows a user to modify or change their existing account information.
    """
    try:
        with open(ACCOUNTS_FILE, "r+") as f:
            accounts = json.load(f)
            if account_id in accounts:
                accounts[account_id].update(new_info)
                accounts[account_id]["date_of_last_change"] = datetime.now().isoformat()
                f.seek(0)
                json.dump(accounts, f, indent=4)
                f.truncate()
                return "User account information updated successfully."
            return "User account not found."
    except Exception as e:
        return f"Error while editing user account information. {e}"

def main():
    parser = argparse.ArgumentParser(description="MCPServer with selectable transport")
    parser.add_argument(
        "--mode",
        choices=["stdio", "http"],
        default="stdio",
        help="Select transport mode: stdio or http",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host for HTTP server (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Port for HTTP server (default: 8080)"
    )
    args = parser.parse_args()

    if args.mode == "stdio":
        print("Running MCPServer in stdio mode.")
        mcp.run()
    else:
        print(f"Running MCPServer in HTTP mode on {args.host}:{args.port}")
        mcp.run(transport="http",
                host=args.host,
                port=args.port)

if __name__ == "__main__":
    main()
