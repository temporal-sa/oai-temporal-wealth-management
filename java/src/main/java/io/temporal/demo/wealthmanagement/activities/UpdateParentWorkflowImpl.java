package io.temporal.demo.wealthmanagement.activities;

import io.temporal.client.WorkflowClient;
import io.temporal.client.WorkflowStub;
import io.temporal.demo.wealthmanagement.common.ServerInfo;
import io.temporal.demo.wealthmanagement.common.TemporalClient;
import io.temporal.demo.wealthmanagement.data.UpdateAccountOpeningStateInput;
import io.temporal.serviceclient.WorkflowServiceStubs;

public class UpdateParentWorkflowImpl implements UpdateParentWorkflow {

    @Override
    public void changeState(String parentWorkflowId, String accountName, String state) {
        try {
            WorkflowServiceStubs service = TemporalClient.getWorkflowServiceStubs();
            WorkflowClient client = WorkflowClient.newInstance(service);
            WorkflowStub parent = client.newUntypedWorkflowStub(parentWorkflowId);
            // Build parameter
            UpdateAccountOpeningStateInput parameter = new UpdateAccountOpeningStateInput();
            parameter.setAccountName(accountName);
            parameter.setState(state);
            // signal the parent workflow
            parent.signal("update_account_opening_state", parameter);
        } catch (Exception ex) {
            String message = String.format("Exception while notifying parent. ParentWFID %s, State %s, ServerInfo %s", parentWorkflowId, state, ServerInfo.getServerInfo());
            throw new RuntimeException(message, ex);
        }
    }
}
