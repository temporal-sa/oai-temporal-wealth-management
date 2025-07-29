import os

from temporalio.service import TLSConfig

class ClientHelper:
    def __init__(self):
        self.address = os.getenv("TEMPORAL_ADDRESS","127.0.0.1:7233")
        self.namespace = os.getenv("TEMPORAL_NAMESPACE","default")
        self.tlsCertPath = os.getenv("TEMPORAL_CERT_PATH","")
        self.tlsKeyPath = os.getenv("TEMPORAL_KEY_PATH","")
        self.taskQueue = os.getenv("TEMPORAL_TASK_QUEUE", "Supervisor")

    def get_tls_config(self) -> TLSConfig:
        tls = None
        if self.tlsCertPath and self.tlsKeyPath:
            print("Using mTLS authentication")
            with open(self.tlsCertPath, "rb") as f:
                cert = f.read()
            with open(self.tlsKeyPath, "rb") as f:
                key = f.read()

            tls = TLSConfig(client_cert=cert,
                            client_private_key=key)
        return tls