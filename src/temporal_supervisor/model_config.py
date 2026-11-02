"""The model the agents call, wrapped for the chaos panel's LLM failures.

The OpenAI Agents plugin runs every model call in its invoke_model_activity, so
anything raised here is an activity failure and is retried by LLM_RETRY_POLICY.
Real OpenAI 429s are already handled by the plugin, which turns the response's
Retry-After header into the activity's next retry delay.
"""

from datetime import timedelta

from agents import OpenAIChatCompletionsModel
from temporalio.exceptions import ApplicationError

from common.chaos_manager import ChaosFlag
from temporal_supervisor.chaos import inject_failure

# Stands in for the Retry-After header of a real 429.
RATE_LIMIT_RETRY_AFTER = timedelta(seconds=15)


def rate_limited(message: str) -> ApplicationError:
    return ApplicationError(message, type="ModelRateLimited", next_retry_delay=RATE_LIMIT_RETRY_AFTER)


class ChaosAwareOpenAIModel(OpenAIChatCompletionsModel):
    async def get_response(self, *args, **kwargs):
        await inject_failure(ChaosFlag.LLM_DOWN, ConnectionError("OpenAI API unavailable"))
        await inject_failure(ChaosFlag.LLM_RATE_LIMITED, rate_limited("OpenAI API rate limit exceeded (HTTP 429)"))
        return await super().get_response(*args, **kwargs)
