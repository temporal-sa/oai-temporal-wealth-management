package io.temporal.demo.wealthmanagement.service;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.temporal.demo.wealthmanagement.model.AccountDetails;
import io.temporal.demo.wealthmanagement.model.InvestmentAccount;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.CommandLineRunner;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

import java.io.File;
import java.io.IOException;
import java.util.*;

import org.apache.commons.cli.*;

public class InvestmentManager {

    private final ObjectMapper objectMapper = new ObjectMapper();
    private Map<String, List<AccountDetails>> data = new HashMap<>();
    private String jsonFilePath;

    public InvestmentManager() {
        this("../data/investments.json");
    }
    public InvestmentManager(String jsonFilePath) {
        this.jsonFilePath = jsonFilePath;
        this.loadData();
    }

    private void loadData() {
        File file = new File(jsonFilePath);
        if (file.exists() && file.length() > 0) {
            try {
                TypeReference<Map<String, List<AccountDetails>>> typeRef = new TypeReference<Map<String, List<AccountDetails>>>() {};
                this.data = objectMapper.readValue(file, typeRef);
            } catch (IOException e) {
                System.err.println("Warning: JSON file '" + jsonFilePath + "' is corrupted or empty. Initializing with empty data.");
                this.data = new HashMap<>();
            }
        } else {
            System.out.println("No existing data file found. Starting with empty data.");
            this.data = new HashMap<>();
        }
    }

    private void saveData() {
        try {
            File file = new File(jsonFilePath);
            file.getParentFile().mkdirs(); // Ensure the directory exists
            objectMapper.writerWithDefaultPrettyPrinter().writeValue(file, this.data);
        } catch (IOException e) {
            System.err.println("Error: Could not save data to file. " + e.getMessage());
        }
    }

    public List<AccountDetails> listInvestmentAccounts(String clientId) {
        return this.data.getOrDefault(clientId, Collections.emptyList());
    }

    public AccountDetails addInvestmentAccount(InvestmentAccount newAccount) {
        if (newAccount.getBalance() < 0) {
            System.err.println("Error: Balance cannot be negative.");
            return null;
        }

        this.data.putIfAbsent(newAccount.getClientId(), new ArrayList<>());

        String newInvestmentId = "i-" + UUID.randomUUID().toString().substring(0, 8);
        AccountDetails accountDetails = new AccountDetails(newInvestmentId, newAccount.getName(), newAccount.getBalance());

        this.data.get(newAccount.getClientId()).add(accountDetails);
        this.saveData();
        return accountDetails;
    }

    public boolean deleteInvestmentAccount(String clientId, String investmentId) {
        if (!this.data.containsKey(clientId)) {
            return false;
        }

        List<AccountDetails> accounts = this.data.get(clientId);
        boolean wasRemoved = accounts.removeIf(account -> account.getInvestmentId().equals(investmentId));

        if (wasRemoved) {
            if (accounts.isEmpty()) {
                this.data.remove(clientId);
            }
            this.saveData();
        }
        return wasRemoved;
    }
}
/*
@SpringBootApplication
class InvestmentManagerCliRunner implements CommandLineRunner {

    private final InvestmentManager investmentManager = new InvestmentManager();

    @Override
    public void run(String... args) throws Exception {
        // Create the options for the command-line arguments
        Options options = new Options();

        options.addOption(null, "list", false, "List investment accounts for a client.");
        options.addOption(null, "add", false, "Add a new investment account.");
        options.addOption(null, "delete", false, "Delete an investment account.");

        options.addOption(Option.builder("c").longOpt("client-id").hasArg().desc("The ID of the client.").build());
        options.addOption(Option.builder("n").longOpt("name").hasArg().desc("The name of the investment account.").build());
        options.addOption(Option.builder("b").longOpt("balance").hasArg().desc("The initial balance of the account.").build());
        options.addOption(Option.builder("i").longOpt("investment-id").hasArg().desc("The ID of the investment account to delete.").build());

        CommandLineParser parser = new DefaultParser();
        HelpFormatter formatter = new HelpFormatter();
        CommandLine cmd = null;

        try {
            cmd = parser.parse(options, args);
            if (cmd.hasOption("list")) {
                String clientId = cmd.getOptionValue("client-id");
                if (clientId == null) {
                    System.err.println("Error: 'client-id' is required for the 'list' command.");
                    formatter.printHelp("investment_manager", options);
                    return;
                }
                List<AccountDetails> accounts = investmentManager.listInvestmentAccounts(clientId);
                // Print the list of accounts
                if (accounts.isEmpty()) {
                    System.out.println("No accounts found for client: " + clientId);
                } else {
                    System.out.println("Accounts for client " + clientId + ":");
                    accounts.forEach(System.out::println); // Assumes AccountDetails has a good toString()
                }

            } else if (cmd.hasOption("add")) {
                String clientId = cmd.getOptionValue("client-id");
                String name = cmd.getOptionValue("name");
                String balanceStr = cmd.getOptionValue("balance");
                if (clientId == null || name == null || balanceStr == null) {
                    System.err.println("Error: 'client-id', 'name', and 'balance' are required for the 'add' command.");
                    formatter.printHelp("investment_manager", options);
                    return;
                }
                try {
                    double balance = Double.parseDouble(balanceStr);
                    AccountDetails newAccount = investmentManager.addInvestmentAccount(new InvestmentAccount(clientId, name, balance));
                    if (newAccount != null) {
                        System.out.println("Successfully added account: " + newAccount);
                    }
                } catch (NumberFormatException e) {
                    System.err.println("Error: Balance must be a numeric value.");
                }

            } else if (cmd.hasOption("delete")) {
                String clientId = cmd.getOptionValue("client-id");
                String investmentId = cmd.getOptionValue("investment-id");
                if (clientId == null || investmentId == null) {
                    System.err.println("Error: 'client-id' and 'investment-id' are required for the 'delete' command.");
                    formatter.printHelp("investment_manager", options);
                    return;
                }
                boolean deleted = investmentManager.deleteInvestmentAccount(clientId, investmentId);
                if (deleted) {
                    System.out.println("Successfully deleted account " + investmentId + " for client " + clientId + ".");
                } else {
                    System.err.println("Could not delete account. Check the client ID and investment ID.");
                }

            } else {
                formatter.printHelp("investment_manager", options);
            }
        } catch (ParseException e) {
            System.err.println("Error parsing command line arguments: " + e.getMessage());
            formatter.printHelp("investment_manager", options);
        }

        // Ensure the application exits after running the command
        if (cmd == null || !cmd.hasOption("help")) {
            System.exit(0);
        }
    }

    public static void main(String[] args) {
        SpringApplication.run(InvestmentManagerCliRunner.class, args);
    }
}
 */

/* Sample Data
 * ./gradlew testInvestmentMgr --args='--list --client-id 123'
 * ./gradlew testInvestmentMgr --args='--add --client-id 456 --name 401K --balance 875.00'
 * ./gradlew testInvestmentMgr --args='--delete --client-id 456 --investment-id i-d361aab2'
 */