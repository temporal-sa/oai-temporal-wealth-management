"""Retry policies shared by the workflows.

Both retry indefinitely: a downstream outage pauses the agent instead of failing
the conversation, and it carries on as soon as the dependency recovers. The
maximum interval is kept short so that recovery is visible within seconds during
a demo. Errors raised as non-retryable (business-rule failures) still fail
immediately.

Pair these with start_to_close_timeout (one attempt), never
schedule_to_close_timeout (all attempts), or an outage times out instead of
being waited out.
"""

from datetime import timedelta

from temporalio.common import RetryPolicy

# Tool / business-system activities.
TOOL_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=1),
    backoff_coefficient=2,
    maximum_interval=timedelta(seconds=5),
)

# Model (LLM) calls. A rate-limited call overrides this backoff with the
# server's Retry-After delay (see model_config.ChaosAwareOpenAIModel).
LLM_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=1),
    backoff_coefficient=2,
    maximum_interval=timedelta(seconds=10),
)
