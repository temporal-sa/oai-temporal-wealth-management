package io.temporal.demo.wealthmanagement.workflow;

import io.temporal.demo.wealthmanagement.data.WealthManagementClient;
import io.temporal.demo.wealthmanagement.model.OpenInvestmentAccountInput;
import io.temporal.demo.wealthmanagement.model.OpenInvestmentAccountOutput;
import io.temporal.workflow.*;

@WorkflowInterface
public interface OpenInvestmentAccountWorkflow {
    @WorkflowMethod
    OpenInvestmentAccountOutput run(OpenInvestmentAccountInput inputs);

    @QueryMethod
    String get_current_state();

    @UpdateMethod
    WealthManagementClient get_client_details();

    @UpdateMethod
    String update_client_details(/* tbd */);

    @SignalMethod
    void verify_kyc();

    @SignalMethod
    void compliance_approved();

}
