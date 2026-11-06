package io.temporal.demo.wealthmanagement.workflow;

import io.temporal.activity.ActivityOptions;
import io.temporal.demo.wealthmanagement.activities.UpdateParentWorkflow;
import io.temporal.demo.wealthmanagement.common.RetryPolicies;
import io.temporal.demo.wealthmanagement.common.ServerInfo;
import io.temporal.demo.wealthmanagement.data.WealthManagementClient;
import io.temporal.demo.wealthmanagement.model.InvestmentAccount;
import io.temporal.demo.wealthmanagement.model.OpenInvestmentAccountOutput;
import io.temporal.failure.ActivityFailure;
import io.temporal.failure.ApplicationFailure;
import io.temporal.spring.boot.WorkflowImpl;
import io.temporal.demo.wealthmanagement.model.OpenInvestmentAccountInput;
import io.temporal.workflow.ActivityStub;
import io.temporal.workflow.Saga;
import io.temporal.workflow.Workflow;
import org.slf4j.Logger;

import java.time.Duration;
import java.util.HashMap;
import java.util.Map;
import java.util.Optional;

@WorkflowImpl
public class OpenInvestmentAccountWorkflowImpl implements OpenInvestmentAccountWorkflow {
    // Welcome-bonus promotion: a percentage of the initial deposit, up to MAX_BONUS.
    // *** Bug-In-Workflow-Code ***
    // Intentional bug for the "Bug in workflow code" demo: the promo code is "WELCOME-BONUS" (hyphen),
    // but BONUS_RATES is keyed by "WELCOME_BONUS" (underscore), so the lookup in welcomeBonus returns null.
    // To fix it, uncomment the first line below and comment out the second.
    // private static final Map<String, Double> BONUS_RATES = Map.of("WELCOME-BONUS", 0.01);
    private static final Map<String, Double> BONUS_RATES = Map.of("WELCOME_BONUS", 0.01);
    private static final double MAX_BONUS = 500.0;

    private final Logger log = Workflow.getLogger(OpenInvestmentAccountWorkflowImpl.class);
    private WealthManagementClient client;
    private OpenInvestmentAccountInput inputs;
    private boolean initialized = false;
    private boolean kycVerified = false;
    private boolean complianceReviewed = false;
    private String currentState = "Initializing";

    // The activities are implemented in Python, so they are called by name on the Python task queue.
    // The start-to-close timeout bounds a single attempt only, so an outage is retried for as long as it lasts.
    private final ActivityStub activityStub = Workflow.newUntypedActivityStub(
            ActivityOptions.newBuilder().
                    setTaskQueue(ServerInfo.getTaskqueue()).
                    setStartToCloseTimeout(Duration.ofSeconds(30)).
                    setRetryOptions(RetryPolicies.TOOL_RETRY_OPTIONS).build());

    private final UpdateParentWorkflow updateParent = Workflow.newActivityStub(
            UpdateParentWorkflow.class,
            ActivityOptions.newBuilder().
                    setTaskQueue(ServerInfo.getTaskqueueOpenAccount()).
                    setStartToCloseTimeout(Duration.ofSeconds(5)).
                    setRetryOptions(RetryPolicies.TOOL_RETRY_OPTIONS).build());


    @Override
    public OpenInvestmentAccountOutput run(OpenInvestmentAccountInput inputs) {
        log.info("Started workflow {}", inputs);
        this.inputs = inputs;

        log.info("Retrieving current client information. Task queue is {}", ServerInfo.getTaskqueue());
        this.client = activityStub.execute("get_client", WealthManagementClient.class, inputs.getClient_id());

        log.info("Client {} details details {}", this.inputs.getClient_id(), this.client);
        this.initialized = true;
        setState("Waiting KYC");

        // Wait until the user has validated their information is correct
        log.info("Waiting for KYC Verification");
        Workflow.await( () -> this.kycVerified );

        setState("Waiting Compliance Review");

        log.info("Waiting for Compliance Review");
        Workflow.await( () -> this.complianceReviewed );

        setState("Compliance review has been approved. Creating Investment Account");
        return openAccount();
    }

    /**
     * Saga: create, fund, and register the account.
     *
     * Each completed step registers how to undo it. If a later step fails with a non-retryable
     * error, the compensations run in reverse order. Transient failures never get here:
     * activities retry until they succeed.
     */
    @SuppressWarnings("unchecked")
    private OpenInvestmentAccountOutput openAccount() {
        String clientId = inputs.getClient_id();
        double amount = inputs.getInitial_amount();
        double bonus = inputs.getPromo_code() != null ? welcomeBonus(inputs) : 0.0;
        // Idempotency key: stable across activity retries and worker restarts. The chat gives
        // every account opening its own workflow ID, but the key also includes the run ID so that
        // a workflow started again with the same ID (e.g. by hand, from the CLI or the scenario
        // runner) can't look like a repeat of an earlier transfer.
        String transferId = Workflow.getInfo().getWorkflowId() + "-" + Workflow.getInfo().getRunId() + "-initial-deposit";

        Saga saga = new Saga(new Saga.Options.Builder().setParallelCompensation(false).build());
        try {
            setState("Creating the account record.");
            InvestmentAccount newAccount = new InvestmentAccount(clientId, inputs.getAccount_name(), amount + bonus);
            HashMap<String, Object> account = activityStub.execute("open_investment", HashMap.class, newAccount);
            String investmentId = (String) account.get("investment_id");
            saga.addCompensation(() -> compensate("removing the account record",
                    "remove_investment", clientId, investmentId));

            setState(String.format("Transferring $%,.2f from the linked bank account.", amount));
            activityStub.execute("debit_linked_account", HashMap.class, clientId, amount, transferId);
            saga.addCompensation(() -> compensate(String.format("refunding $%,.2f to the linked bank account", amount),
                    "credit_linked_account", clientId, amount, transferId + "-refund"));

            setState("Registering the account with the custodian.");
            activityStub.execute("register_account", String.class, clientId, investmentId, amount);
        } catch (ActivityFailure e) {
            String reason = reason(e);
            setState("Failed: " + reason + ". Rolling back.");
            saga.compensate();
            setState("Rolled back. The account was not opened: " + reason + ".");

            OpenInvestmentAccountOutput result = new OpenInvestmentAccountOutput();
            result.setAccount_created(false);
            result.setMessage("The account was not opened: " + reason);
            return result;
        }

        setState("Complete");

        OpenInvestmentAccountOutput result = new OpenInvestmentAccountOutput();
        result.setAccount_created(true);
        result.setMessage("investment account created");
        return result;
    }

    private static double welcomeBonus(OpenInvestmentAccountInput inputs) {
        double rate = BONUS_RATES.get(inputs.getPromo_code());
        return Math.min(inputs.getInitial_amount() * rate, MAX_BONUS);
    }

    private void compensate(String description, String activityName, Object... args) {
        setState("Rolling back: " + description + ".");
        // Compensations are activities too, so they are retried until they succeed
        activityStub.execute(activityName, Object.class, args);
    }

    // The business reason for a non-retryable activity failure, such as the custodian rejecting the account
    private static String reason(ActivityFailure e) {
        Throwable cause = e.getCause();
        if (cause instanceof ApplicationFailure applicationFailure) {
            return applicationFailure.getOriginalMessage();
        }
        return cause != null ? cause.getMessage() : e.getMessage();
    }

    @Override
    public String get_current_state() {
        return this.currentState;
    }

    @Override
    public WealthManagementClient get_client_details() {
        // wait until we're initialized
        Workflow.await(() -> this.initialized);
        return this.client;
    }

    @Override
    public String update_client_details(Map<String, Object> clientDetails) {
        log.info("Updating client information for {}", this.inputs.getClient_id());
        String result = activityStub.execute("update_client", String.class,
                this.inputs.getClient_id(), clientDetails);
        this.kycVerified = true;
        return result;
    }

    @Override
    public void verify_kyc() {
        Workflow.await(() -> this.initialized);
        this.kycVerified = true;
    }

    @Override
    public void compliance_approved() {
        Workflow.await(() -> this.initialized && this.kycVerified);
        this.complianceReviewed = true;
    }

    private void setState(String state) {
        this.currentState = state;
        updateParentState(state);
    }

    private void updateParentState(String state) {
        Optional<String> parentWfId = Workflow.getInfo().getParentWorkflowId();
        if (parentWfId.isEmpty()) {
            return;
        }
        // use an activity because the parent is on a different Task Queue
        updateParent.changeState(parentWfId.get(), this.inputs.getAccount_name(), state, Workflow.getInfo().getWorkflowId());
    }
}
