package io.temporal.demo.wealthmanagement.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;

import java.io.File;
import java.io.IOException;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

import io.temporal.demo.wealthmanagement.data.InvestmentClient;
import io.temporal.demo.wealthmanagement.data.WealthManagementClient;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.CommandLineRunner;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import picocli.CommandLine.Option;
import picocli.CommandLine.ArgGroup;

public class InvestmentClientManager {
    private final String filePath;
    private final ObjectMapper objectMapper;

    public InvestmentClientManager() {
        this("../data/clients.json");
    }
    // The constructor initializes the file path and ObjectMapper.
    public InvestmentClientManager(String filePath) {
        this.filePath = filePath;
        // The ObjectMapper is configured to pretty-print the JSON output.
        this.objectMapper = new ObjectMapper().enable(SerializationFeature.INDENT_OUTPUT);
    }

    // Adds a new client to the file.
    // Throws an IOException if there's an issue with file I/O.
    public String addClient(String clientId, InvestmentClient newClient) throws IOException {
        Map<String, InvestmentClient> clients = loadClients();
        if (clients.containsKey(clientId)) {
            return "Client already exists.";
        }
        clients.put(clientId, newClient);
        saveClients(clients);
        return "Client " + clientId + " added successfully.";
    }

    // Updates an existing client with new information.
    // The newInfo map contains the fields to be updated.
    public String updateClient(String clientId, Map<String, Object> newInfo) throws IOException {
        Map<String, InvestmentClient> clients = loadClients();
        if (!clients.containsKey(clientId)) {
            return "Client " + clientId + " not found.";
        }

        // Get the existing client object and update its properties from the newInfo map.
        InvestmentClient clientToUpdate = clients.get(clientId);
        if (newInfo.containsKey("firstName")) clientToUpdate.setFirstName((String) newInfo.get("firstName"));
        if (newInfo.containsKey("lastName")) clientToUpdate.setLastName((String) newInfo.get("lastName"));
        if (newInfo.containsKey("address")) clientToUpdate.setAddress((String) newInfo.get("address"));
        if (newInfo.containsKey("phone")) clientToUpdate.setPhone((String) newInfo.get("phone"));
        if (newInfo.containsKey("email")) clientToUpdate.setEmail((String) newInfo.get("email"));
        if (newInfo.containsKey("maritalStatus")) clientToUpdate.setMaritalStatus((String) newInfo.get("maritalStatus"));

        saveClients(clients);
        return "Client information successfully updated.";
    }

    // Retrieves a client by their ID.
    // Returns the Client object or null if not found.
    public InvestmentClient getClient(String clientId) throws IOException {
        Map<String, InvestmentClient> clients = loadClients();
        return clients.getOrDefault(clientId, null);
    }

    // Private helper method to load all clients from the JSON file.
    private Map<String, InvestmentClient> loadClients() throws IOException {
        File file = new File(filePath);
        if (!file.exists()) {
            return new HashMap<>();
        }
        return objectMapper.readValue(file, objectMapper.getTypeFactory().constructMapType(HashMap.class, String.class, WealthManagementClient.class));
    }

    // Private helper method to save the clients map to the JSON file.
    private void saveClients(Map<String, InvestmentClient> clients) throws IOException {
        File file = new File(filePath);
        File parentDir = file.getParentFile();
        if (parentDir != null && !parentDir.exists()) {
            parentDir.mkdirs();
        }
        objectMapper.writeValue(file, clients);
    }
}

class DefaultApplicationArguments implements ApplicationArguments {
    private final String[] args;
    private final Map<String, List<String>> optionArgs = new HashMap<>();

    public DefaultApplicationArguments(String... args) {
        this.args = args;
        for (int i = 0; i < args.length; i++) {
            if (args[i].startsWith("--")) {
                String optionName = args[i].substring(2);
                optionArgs.put(optionName, new java.util.ArrayList<>());
                while (i + 1 < args.length && !args[i + 1].startsWith("--")) {
                    optionArgs.get(optionName).add(args[i + 1]);
                    i++;
                }
            }
        }
    }

    @Override
    public String[] getSourceArgs() {
        return args;
    }

    @Override
    public Set<String> getOptionNames() {
        return optionArgs.keySet();
    }

    @Override
    public boolean containsOption(String name) {
        return optionArgs.containsKey(name);
    }

    @Override
    public List<String> getOptionValues(String name) {
        return optionArgs.get(name);
    }

    @Override
    public List<String> getNonOptionArgs() {
        return List.of(new String[0]);
    }
}



// This is the main application class that handles command-line parsing.
// It uses the ClientManager class to perform the actual operations.
/*
@SpringBootApplication
class ClientManagerApp implements CommandLineRunner {

    @ArgGroup(exclusive = true, multiplicity = "1")
    private Action action;

    static class Action {
        @Option(names = "--add", required = true, description = "Add a new client.")
        boolean add;

        @Option(names = "--update", required = true, description = "Update an existing client.")
        boolean update;

        @Option(names = "--get", required = true, description = "Get client information.")
        boolean get;
    }

    @Option(names = "--client-id", required = true, description = "The ID of the client.")
    private String clientId;

    @Option(names = "--first-name", description = "First name of the client.")
    private String firstName;

    @Option(names = "--last-name", description = "Last name of the client.")
    private String lastName;

    @Option(names = "--address", description = "Address of the client.")
    private String address;

    @Option(names = "--phone", description = "Phone number of the client.")
    private String phone;

    @Option(names = "--email", description = "Email address of the client.")
    private String email;

    @Option(names = "--marital-status", description = "Marital status of the client.")
    private String maritalStatus;

    // This is the single instance of the class that manages clients.
    private final InvestmentClientManager clientManager = new InvestmentClientManager();

    @Override
    public void run(String... args) throws Exception {
        // We use ApplicationArguments to parse the command-line parameters.
        ApplicationArguments appArgs = new DefaultApplicationArguments(args);

        String clientId = null;
        if (appArgs.containsOption("client-id")) {
            clientId = appArgs.getOptionValues("client-id").get(0);
        } else {
            System.err.println("Error: --client-id is a required parameter.");
            return;
        }

        if (appArgs.containsOption("add")) {
            addClient(appArgs, clientId);
        } else if (appArgs.containsOption("update")) {
            updateClient(appArgs, clientId);
        } else if (appArgs.containsOption("get")) {
            getClient(clientId);
        } else {
            System.err.println("Error: No action specified. Use --add, --update, or --get.");
        }

        System.out.println("Press Ctrl-C to exit.");
    }

    private void addClient(ApplicationArguments args, String clientId) throws IOException {
        List<String> firstNameList = args.getOptionValues("first-name");
        List<String> lastNameList = args.getOptionValues("last-name");
        List<String> addressList = args.getOptionValues("address");
        List<String> phoneList = args.getOptionValues("phone");
        List<String> emailList = args.getOptionValues("email");
        List<String> maritalStatusList = args.getOptionValues("marital_status");

        if (firstNameList == null || lastNameList == null || addressList == null || phoneList == null || emailList == null || maritalStatusList == null) {
            System.err.println("Error: --add requires all client information fields.");
            return;
        }

        InvestmentClient newClient = new InvestmentClient();
        newClient.setFirstName(firstNameList.get(0));
        newClient.setLastName(lastNameList.get(0));
        newClient.setAddress(addressList.get(0));
        newClient.setPhone(phoneList.get(0));
        newClient.setEmail(emailList.get(0));
        newClient.setMaritalStatus(maritalStatusList.get(0));

        String result = clientManager.addClient(clientId, newClient);
        System.out.println(result);
    }

    private void updateClient(ApplicationArguments args, String clientId) throws IOException {
        Map<String, Object> newInfo = new HashMap<>();
        if (args.containsOption("first-name")) newInfo.put("firstName", args.getOptionValues("first-name").get(0));
        if (args.containsOption("last-name")) newInfo.put("lastName", args.getOptionValues("last-name").get(0));
        if (args.containsOption("address")) newInfo.put("address", args.getOptionValues("address").get(0));
        if (args.containsOption("phone")) newInfo.put("phone", args.getOptionValues("phone").get(0));
        if (args.containsOption("email")) newInfo.put("email", args.getOptionValues("email").get(0));
        if (args.containsOption("marital-status")) newInfo.put("maritalStatus", args.getOptionValues("marital-status").get(0));

        if (newInfo.isEmpty()) {
            System.err.println("Error: --update requires at least one field to update.");
            return;
        }

        String result = clientManager.updateClient(clientId, newInfo);
        System.out.println(result);
    }

    private void getClient(String clientId) throws IOException {
        InvestmentClient client = clientManager.getClient(clientId);
        if (client != null) {
            ObjectMapper mapper = new ObjectMapper().enable(SerializationFeature.INDENT_OUTPUT);
            System.out.println(mapper.writeValueAsString(client));
        } else {
            System.out.println("Client " + clientId + " not found.");
        }
    }

    public static void main(String[] args) {
        SpringApplication.run(ClientManagerApp.class, args);
    }
}

 */

/*
 * Testing Scenarios:
 *  ./gradlew testClientMgr --args='--add --client-id 123 --first-name Don --last-name Doe --address "123 Main Street" --phone 888-555-1212 --email jd@example.com --marital_status married'
 *  ./gradlew testClientMgr --args='--add --client-id 234 --first-name Frank --last-name Smith --address "234 Main Street" --phone 888-777-1212 --email fs@example.com --marital_status married'
 *  ./gradlew testClientMgr --args='--get --client-id 123'
 *  ./gradlew testClientMgr --args='--get --client-id 234'
 *  ./gradlew testClientMgr --args='--update --client-id 123 --phone 999-555-1212 --email jd@someplace.com'
 */
