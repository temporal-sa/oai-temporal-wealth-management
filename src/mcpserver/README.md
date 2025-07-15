# MCP Server for Wealth Management

Provides additional capabilities for managing wealth management accounts. Operations include:

* Create User - Adds a new user record
* Validate Account - Allows a user to log in and returns their account id
* Add Account Info - Adds a user's account information (e.g. name, address, phone, etc)
* View Account Info - Retrieves a user's account information
* Edit Account Info - Provides a way to update account information

## Prerequisites

* [Poetry](https://python-poetry.org/docs/) - Python Dependency Management

## Running the MCP Server
```bash
poetry run python src/mcpserver/main.py 
```

or you can run the shell script after installing the dependencies
```bash
./src/mcpserver/runmcp.sh
```

## Configuring Claude Desktop 

To configure in Claude Desktop for testing,
Add an entry to claude_desktop_config.json that looks like this:
```json
  "mcpServers": {
    "wealth-management": {
      "command": "/full/path/to/oai-wealth-management/src/mcpserver/runmcp.sh"
    }
  }
```
and restart Claude Desktop.

## Using Claude Desktop to interact with the MCP Server

You can then do things like this in Claude: 
```text
I want to create a new wealth management account.
```
Could you please provide your desired username and password to begin the account creation process?

```text
username: johnsmith, password: password, account id: 234
```
I'll create your new wealth management account with those credentials....

Now I need to collect personal information...

```text
Name: John Smith, address: 234 Main Street, Phone: 888-555-1212, email: jsmith@gmail.com, maritial status: married
```
Excellent! Your wealth management account has been successfully created and set up

Note that the user accounts initially created are:

* Account 123 -> jamesdoe/password
* Account 234 -> johnsmith/password 
