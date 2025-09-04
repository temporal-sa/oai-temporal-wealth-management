package io.temporal.demo.wealthmanagement.common;

import java.util.HashMap;
import java.util.Map;

public class ServerInfo {

    public static String getCertPath() {
        return getEnv("TEMPORAL_CERT_PATH", "");
    }

    public static String getKeyPath() {
        // check first for a specific pkcs8 env var, if null/empty then check for generic env var
        String keyPath = System.getenv("TEMPORAL_KEY_PKCS8_PATH");
        return keyPath != null && !keyPath.isEmpty() ? keyPath : getEnv("TEMPORAL_KEY_PATH", "");
    }

    public static String getNamespace() {
        return getEnv("TEMPORAL_NAMESPACE", "default");
    }

    public static String getAddress() {
        return getEnv("TEMPORAL_ADDRESS", "localhost:7233");
    }

    public static String getTaskqueue() {
        return getEnv("TEMPORAL_TASK_QUEUE", "Supervisor");
    }

    public static String getTaskqueueOpenAccount() {
        return getEnv("TEMPORAL_TASK_QUEUE_OPEN_ACCOUNT", getTaskqueue());
    }

    public static Map<String, String> getServerInfo() {
        Map<String, String> info = new HashMap<>();
        info.put("certPath", getCertPath());
        info.put("keyPath", getKeyPath());
        info.put("namespace", getNamespace());
        info.put("address", getAddress());
        info.put("taskQueue", getTaskqueue());
        return info;
    }

    private static String getEnv(String key, String defaultValue) {
        String value = System.getenv(key);
        return value != null && !value.isEmpty() ? value : defaultValue;
    }
}
