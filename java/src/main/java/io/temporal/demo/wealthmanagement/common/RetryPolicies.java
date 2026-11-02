package io.temporal.demo.wealthmanagement.common;

import io.temporal.common.RetryOptions;

import java.time.Duration;

/**
 * Retry options shared by the workflows. They match retry_policies.py in the Python version.
 *
 * Activities retry indefinitely: a downstream outage pauses the workflow instead of failing it,
 * and it carries on as soon as the dependency recovers. The maximum interval is kept short so
 * that recovery is visible within seconds during a demo. Errors raised as non-retryable
 * (business-rule failures) still fail immediately.
 *
 * Pair these with a start-to-close timeout (one attempt), never a schedule-to-close timeout
 * (all attempts), or an outage times out instead of being waited out.
 */
public final class RetryPolicies {
    private RetryPolicies() {
    }

    // Tool / business-system activities.
    public static final RetryOptions TOOL_RETRY_OPTIONS = RetryOptions.newBuilder()
            .setInitialInterval(Duration.ofSeconds(1))
            .setBackoffCoefficient(2)
            .setMaximumInterval(Duration.ofSeconds(5))
            .build();
}
