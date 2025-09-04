package io.temporal.demo.wealthmanagement.activities;

import io.temporal.activity.ActivityInterface;
import io.temporal.activity.ActivityMethod;

@ActivityInterface
public interface UpdateParentWorkflow {
    @ActivityMethod
    void changeState(String parentWorkflowId, String accountName, String state);
}
