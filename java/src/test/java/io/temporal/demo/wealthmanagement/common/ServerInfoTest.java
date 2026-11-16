package io.temporal.demo.wealthmanagement.common;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

/** USE_CLAIM_CHECK must mean the same thing here as in the Python components (common/util.py str_to_bool). */
class ServerInfoTest {

    @Test
    void acceptsTheSameTrueValuesAsPython() {
        for (String value : new String[] {"true", "TRUE", "True", "t", "yes", "YES", "y", "1", " 1 "}) {
            assertTrue(ServerInfo.isTrue(value), value);
        }
    }

    @Test
    void everythingElseIsOff() {
        for (String value : new String[] {"false", "f", "no", "n", "0", "", "on", "2", null}) {
            assertFalse(ServerInfo.isTrue(value), String.valueOf(value));
        }
    }
}
