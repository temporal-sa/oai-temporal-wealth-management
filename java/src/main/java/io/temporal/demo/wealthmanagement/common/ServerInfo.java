package io.temporal.demo.wealthmanagement.common;

import java.util.HashMap;
import java.util.Locale;
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

    public static Boolean useClaimCheck() {
        return isTrue(getEnv("USE_CLAIM_CHECK", "false"));
    }

    /**
     * Whether a flag's value means on. Accepts the values the Python components' str_to_bool
     * accepts (true, t, yes, y or 1, in any case), so every component agrees on whether payloads
     * are claim-checked. Boolean.parseBoolean accepted only "true": with USE_CLAIM_CHECK=1 the
     * Python components claim-checked payloads this worker couldn't read.
     */
    static boolean isTrue(String value) {
        if (value == null) {
            return false;
        }
        return switch (value.trim().toLowerCase(Locale.ROOT)) {
            case "true", "t", "yes", "y", "1" -> true;
            default -> false;
        };
    }

    public static Map<String, String> getServerInfo() {
        Map<String, String> info = new HashMap<>();
        info.put("certPath", getCertPath());
        info.put("keyPath", getKeyPath());
        info.put("namespace", getNamespace());
        info.put("address", getAddress());
        info.put("taskQueue", getTaskqueue());
        info.put("useClaimCheck", useClaimCheck().toString());
        return info;
    }

    private static String getEnv(String key, String defaultValue) {
        String value = System.getenv(key);
        return value != null && !value.isEmpty() ? value : defaultValue;
    }
}
