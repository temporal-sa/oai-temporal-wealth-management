package io.temporal.demo.wealthmanagement.workflow;

import io.temporal.activity.Activity;
import io.temporal.activity.ActivityInterface;
import io.temporal.activity.ActivityMethod;
import io.temporal.api.enums.v1.EventType;
import io.temporal.api.enums.v1.WorkflowExecutionStatus;
import io.temporal.api.history.v1.HistoryEvent;
import io.temporal.api.workflowservice.v1.DescribeWorkflowExecutionRequest;
import io.temporal.client.WorkflowClient;
import io.temporal.client.WorkflowOptions;
import io.temporal.client.WorkflowStub;
import io.temporal.demo.wealthmanagement.common.ServerInfo;
import io.temporal.demo.wealthmanagement.data.WealthManagementClient;
import io.temporal.demo.wealthmanagement.model.OpenInvestmentAccountInput;
import io.temporal.demo.wealthmanagement.model.OpenInvestmentAccountOutput;
import io.temporal.failure.ApplicationFailure;
import io.temporal.testing.TestWorkflowEnvironment;
import io.temporal.worker.Worker;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CopyOnWriteArrayList;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for the failure scenarios demonstrated from the UI chaos panel, matching
 * tests/test_failure_scenarios.py in the Python version.
 *
 * The workflow runs against stub activities registered under the Python activity names.
 * They record the order they were called in and fail on demand, so no Python worker,
 * Redis or data files are needed.
 */
public class OpenInvestmentAccountWorkflowTest {
    private static final String CLIENT_ID = "C-1";
    private static final String INVESTMENT_ID = "i-test";

    // Activity calls, in order.
    private static final List<String> CALLS = new CopyOnWriteArrayList<>();
    // Transfer IDs passed to debit_linked_account.
    private static final List<String> TRANSFER_IDS = new CopyOnWriteArrayList<>();
    // Per-test failure behavior, keyed by activity name: "reject" raises a non-retryable
    // error; a number N fails the first N attempts with a transient error.
    private static final Map<String, String> FAILURES = new ConcurrentHashMap<>();

    @ActivityInterface
    public interface PythonActivities {
        @ActivityMethod(name = "get_client")
        WealthManagementClient getClient(String clientId);

        @ActivityMethod(name = "open_investment")
        Map<String, Object> openInvestment(Map<String, Object> newAccount);

        @ActivityMethod(name = "remove_investment")
        boolean removeInvestment(String clientId, String investmentId);

        @ActivityMethod(name = "debit_linked_account")
        Map<String, Object> debit(String clientId, double amount, String transferId);

        @ActivityMethod(name = "credit_linked_account")
        Map<String, Object> credit(String clientId, double amount, String transferId);

        @ActivityMethod(name = "register_account")
        String register(String clientId, String investmentId, double amount);
    }

    public static class StubActivities implements PythonActivities {
        private static void maybeFail(String name) {
            String behavior = FAILURES.get(name);
            if (behavior == null) {
                return;
            }
            if (behavior.equals("reject")) {
                throw ApplicationFailure.newNonRetryableFailure(name + " rejected", "Rejected");
            }
            if (Activity.getExecutionContext().getInfo().getAttempt() <= Integer.parseInt(behavior)) {
                throw ApplicationFailure.newFailure(name + " unavailable", "ConnectionError");
            }
        }

        @Override
        public WealthManagementClient getClient(String clientId) {
            CALLS.add("get_client");
            return new WealthManagementClient(clientId, "Sam", "Doe", "1 Main St", "555", "s@example.com", "single");
        }

        @Override
        public Map<String, Object> openInvestment(Map<String, Object> newAccount) {
            CALLS.add("open_investment#" + Activity.getExecutionContext().getInfo().getAttempt());
            maybeFail("open_investment");
            return Map.of("investment_id", INVESTMENT_ID, "name", "Test", "balance", 500.0);
        }

        @Override
        public boolean removeInvestment(String clientId, String investmentId) {
            CALLS.add("remove_investment:" + investmentId);
            return true;
        }

        @Override
        public Map<String, Object> debit(String clientId, double amount, String transferId) {
            CALLS.add("debit:" + amount);
            TRANSFER_IDS.add(transferId);
            maybeFail("debit_linked_account");
            return Map.of();
        }

        @Override
        public Map<String, Object> credit(String clientId, double amount, String transferId) {
            CALLS.add("credit:" + amount);
            assertTrue(transferId.endsWith("-refund"));
            return Map.of();
        }

        @Override
        public String register(String clientId, String investmentId, double amount) {
            CALLS.add("register");
            maybeFail("register_account");
            return "CUST-1";
        }
    }

    private TestWorkflowEnvironment env;
    private WorkflowClient client;

    @BeforeEach
    public void setUp() {
        CALLS.clear();
        TRANSFER_IDS.clear();
        FAILURES.clear();
        env = TestWorkflowEnvironment.newInstance();
        // Without TEMPORAL_TASK_QUEUE_OPEN_ACCOUNT, the workflow and the activities share a task queue
        Worker worker = env.newWorker(ServerInfo.getTaskqueue());
        worker.registerWorkflowImplementationTypes(OpenInvestmentAccountWorkflowImpl.class);
        worker.registerActivitiesImplementations(new StubActivities());
        env.start();
        client = env.getWorkflowClient();
    }

    @AfterEach
    public void tearDown() {
        env.close();
    }

    private OpenInvestmentAccountWorkflow startAndApprove(String workflowId, String promoCode) {
        OpenInvestmentAccountWorkflow workflow = client.newWorkflowStub(OpenInvestmentAccountWorkflow.class,
                WorkflowOptions.newBuilder()
                        .setTaskQueue(ServerInfo.getTaskqueue())
                        .setWorkflowId(workflowId)
                        .build());
        OpenInvestmentAccountInput input = new OpenInvestmentAccountInput();
        input.setClient_id(CLIENT_ID);
        input.setAccount_name("Test");
        input.setInitial_amount(500.0f);
        input.setPromo_code(promoCode);
        WorkflowClient.start(workflow::run, input);
        workflow.verify_kyc();
        workflow.compliance_approved();
        return workflow;
    }

    private OpenInvestmentAccountOutput openAccount(String workflowId) {
        startAndApprove(workflowId, null);
        return client.newUntypedWorkflowStub(workflowId).getResult(OpenInvestmentAccountOutput.class);
    }

    private OpenInvestmentAccountOutput openAccount() {
        return openAccount("open-account-test-" + UUID.randomUUID());
    }

    @Test
    public void sagaHappyPath() {
        OpenInvestmentAccountOutput result = openAccount("happy-path");
        assertTrue(result.isAccount_created());
        assertEquals("Complete", client.newWorkflowStub(OpenInvestmentAccountWorkflow.class, "happy-path").get_current_state());
        assertEquals(List.of("get_client", "open_investment#1", "debit:500.0", "register"), CALLS);
    }

    @Test
    public void sagaRollsBackInReverseWhenCustodianRejects() {
        FAILURES.put("register_account", "reject");
        OpenInvestmentAccountOutput result = openAccount("custodian-rejects");
        assertFalse(result.isAccount_created());
        assertTrue(result.getMessage().contains("register_account rejected"), result.getMessage());
        assertTrue(client.newWorkflowStub(OpenInvestmentAccountWorkflow.class, "custodian-rejects")
                .get_current_state().startsWith("Rolled back"));
        assertEquals(List.of("get_client", "open_investment#1", "debit:500.0", "register",
                "credit:500.0", "remove_investment:" + INVESTMENT_ID), CALLS);
    }

    @Test
    public void sagaUndoesOnlyCompletedSteps() {
        FAILURES.put("debit_linked_account", "reject");
        OpenInvestmentAccountOutput result = openAccount();
        assertFalse(result.isAccount_created());
        // The debit never happened, so there is nothing to refund.
        assertEquals(List.of("get_client", "open_investment#1", "debit:500.0",
                "remove_investment:" + INVESTMENT_ID), CALLS);
    }

    @Test
    public void transientFailuresAreRetriedNotRolledBack() {
        FAILURES.put("open_investment", "2");
        OpenInvestmentAccountOutput result = openAccount();
        assertTrue(result.isAccount_created());
        assertEquals(List.of("get_client", "open_investment#1", "open_investment#2", "open_investment#3",
                "debit:500.0", "register"), CALLS);
    }

    @Test
    public void reopeningWithTheSameWorkflowIdUsesANewTransferId() {
        // The open-account tool reuses the workflow ID for the same account name, so a
        // retry after a rollback must not look like a repeat of the earlier transfer.
        FAILURES.put("register_account", "reject");
        openAccount("same-account-name");
        FAILURES.clear();
        openAccount("same-account-name");
        assertEquals(2, TRANSFER_IDS.size());
        assertNotEquals(TRANSFER_IDS.get(0), TRANSFER_IDS.get(1));
    }

    @Test
    public void promoCodePathBugPausesWorkflowInsteadOfFailingIt() throws InterruptedException {
        String workflowId = "promo-bug";
        startAndApprove(workflowId, "WELCOME-BONUS");

        String failure = null;
        for (int i = 0; i < 40 && failure == null; i++) {
            for (HistoryEvent event : client.fetchHistory(workflowId).getEvents()) {
                if (event.getEventType() == EventType.EVENT_TYPE_WORKFLOW_TASK_FAILED) {
                    // The message is generic; the NullPointerException is in the cause and stack trace
                    failure = event.getWorkflowTaskFailedEventAttributes().getFailure().toString();
                }
            }
            Thread.sleep(250);
        }

        assertNotNull(failure, "the demo bug should fail the workflow task");
        assertTrue(failure.contains("NullPointerException") && failure.contains("welcomeBonus"), failure);
        // Paused, not failed: still running, and the saga never started.
        WorkflowExecutionStatus status = env.getWorkflowServiceStubs().blockingStub()
                .describeWorkflowExecution(DescribeWorkflowExecutionRequest.newBuilder()
                        .setNamespace(env.getNamespace())
                        .setExecution(client.newUntypedWorkflowStub(workflowId).getExecution())
                        .build())
                .getWorkflowExecutionInfo().getStatus();
        assertEquals(WorkflowExecutionStatus.WORKFLOW_EXECUTION_STATUS_RUNNING, status);
        assertFalse(CALLS.contains("open_investment#1"));
        WorkflowStub stub = client.newUntypedWorkflowStub(workflowId);
        stub.terminate("test complete");
    }
}
