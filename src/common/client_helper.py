import os

from temporalio.envconfig import ClientConfig
from common.util import str_to_bool

class ClientHelper:
    def __init__(self):
        self.client_config = ClientConfig.load_client_connect_config()
        # hack to stuff in a default value if it isn't set
        if self.client_config.get('target_host') is None:
            self.client_config['target_host'] = '127.0.0.1:7233'

        self.address = self.client_config.get('target_host')
        self.namespace = self.client_config.get('namespace')
        self.taskQueue = os.getenv("TEMPORAL_TASK_QUEUE", "Supervisor")
        self.skipOpenAIPlugin = str_to_bool(os.getenv("SKIP_OPENAI_PLUGIN", "False"))
        print(f"******* Skip OpenAI Plugin? {self.skipOpenAIPlugin} *******")
