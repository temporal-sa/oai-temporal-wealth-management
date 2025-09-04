package io.temporal.demo.wealthmanagement.workflow;

import io.grpc.Server;
import io.temporal.activity.ActivityOptions;
import io.temporal.api.common.v1.WorkflowExecution;
import io.temporal.demo.wealthmanagement.activities.UpdateParentWorkflow;
import io.temporal.demo.wealthmanagement.common.ServerInfo;
import io.temporal.demo.wealthmanagement.data.UpdateAccountOpeningStateInput;
import io.temporal.demo.wealthmanagement.data.WealthManagementClient;
import io.temporal.demo.wealthmanagement.model.InvestmentAccount;
import io.temporal.demo.wealthmanagement.model.OpenInvestmentAccountOutput;
import io.temporal.spring.boot.WorkflowImpl;
import io.temporal.demo.wealthmanagement.model.OpenInvestmentAccountInput;
import io.temporal.workflow.ActivityStub;
import io.temporal.workflow.ExternalWorkflowStub;
import io.temporal.workflow.Workflow;
import org.slf4j.Logger;

import java.time.Duration;
import java.util.HashMap;

@WorkflowImpl
public class OpenInvestmentAccountWorkflowImpl implements OpenInvestmentAccountWorkflow {
    private WealthManagementClient client;
    private OpenInvestmentAccountInput inputs;
    private boolean initialized = false;
    private boolean kycVerified = false;
    private boolean complianceReviewed = false;
    private String currentState = "Initializing";

    private final ActivityStub activityStub = Workflow.newUntypedActivityStub(
            ActivityOptions.newBuilder().
                    setTaskQueue(ServerInfo.getTaskqueue()).
                    setStartToCloseTimeout(Duration.ofSeconds(5)).build());

    private final UpdateParentWorkflow updateParent = Workflow.newActivityStub(
            UpdateParentWorkflow.class,
            ActivityOptions.newBuilder().
                    setTaskQueue(ServerInfo.getTaskqueueOpenAccount()).
                    setStartToCloseTimeout(Duration.ofSeconds(5)).build());


    @Override
    public OpenInvestmentAccountOutput run(OpenInvestmentAccountInput inputs) {
        Logger log = Workflow.getLogger(OpenInvestmentAccountWorkflowImpl.class);
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

        // finally, create/open the account
        log.info("Creating a new investment account");


        // Build the new account
        InvestmentAccount newAccount = new InvestmentAccount(this.inputs.getClient_id(),
                this.inputs.getAccount_name(), this.inputs.getInitial_amount());

        HashMap<Object, Object> returnValue = new HashMap<>();
        returnValue =  activityStub.execute("open_investment", returnValue.getClass(), newAccount);

        setState("Complete");

        OpenInvestmentAccountOutput result = new OpenInvestmentAccountOutput();
        result.setAccount_created(returnValue != null);
        result.setMessage(returnValue != null ?
                "investment account created " : "An unexpected error occurred creating investment account");

        return result;
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
    public String update_client_details() {
        return "";
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
        String parentWfId = Workflow.getInfo().getParentWorkflowId().orElse("<missing parent workflow id>");
        // use an activity because the parent is on a different Task Queue
        updateParent.changeState(parentWfId, this.inputs.getAccount_name(), state);
    }
}
