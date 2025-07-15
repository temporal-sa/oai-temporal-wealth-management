import json
import os

from fastmcp import FastMCP
from datetime import datetime

mcp = FastMCP(
    name="My Wealth Management MCP Server",
    port=7070,
    log_level="INFO",
    on_duplicate_tools="warn")

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

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

            hashed_password = pwd_context.hash(password)
            users.append({"username": username, "password": hashed_password, "account_id": account_id})

            f.seek(0)
            json.dump(users, f, indent=4)
            f.truncate()
        return "User created successfully"
    except Exception as e:
        return f"Unexpected error adding a user: {e}"

@mcp.tool
def validate_account(username: str, password: str) -> str:
    """
    Validates a user's account and returns their account ID if valid.
    """
    try:
        with open(USERS_FILE, "r") as f:
            users = json.load(f)
        for user in users:
            if user["username"] == username and pwd_context.verify(password, user["password"]):
                return user["account_id"]
        return "Invalid credentials"
    except Exception as e:
        return "Exception validating account {e}"


@mcp.resource("account://{account_id}/info")
def get_account_info(account_id: str) -> dict:
    """
    Retrieves a user's account information.
    """
    try:
        with open(ACCOUNTS_FILE, "r") as f:
            accounts = json.load(f)
        return accounts.get(account_id, {"error": "Account not found"})
    except Exception as e:
        return { "error": f"Exception occurred while retrieving account information: {e}" }

@mcp.tool
def add_account_info(account_id: str, first_name: str, last_name: str, address: str, phone: str, email: str, marital_status: str) -> str:
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
        return f"Exception occurred while adding account information: {e}"

@mcp.tool
def view_account_info(account_id: str) -> dict:
    """
    Returns the users account information.
    """
    try:
        with open(ACCOUNTS_FILE, "r") as f:
            accounts = json.load(f)
            if account_id in accounts:
                return accounts[account_id]
            return { "error": "Account not found" }
    except Exception as e:
        return { "error": f"Exception occurred while retrieving account information: {e}" }

@mcp.tool
def edit_account_info(account_id: str, new_info: dict) -> str:
    """
    Edits a user's account information.
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
                return "Account information updated successfully."
            return "Account not found."
    except Exception as e:
        return f"Error while editing account information. {e}"

if __name__ == "__main__":
    mcp.run()
