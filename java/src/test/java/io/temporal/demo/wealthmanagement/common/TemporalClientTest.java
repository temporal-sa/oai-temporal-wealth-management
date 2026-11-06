package io.temporal.demo.wealthmanagement.common;

import io.temporal.api.common.v1.Payload;
import io.temporal.client.WorkflowClientOptions;
import io.temporal.common.converter.CodecDataConverter;
import io.temporal.payload.codec.PayloadCodec;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

class TemporalClientTest {

    private static final PayloadCodec IDENTITY_CODEC = new PayloadCodec() {
        @Override
        public List<Payload> encode(List<Payload> payloads) {
            return payloads;
        }

        @Override
        public List<Payload> decode(List<Payload> payloads) {
            return payloads;
        }
    };

    @Test
    void claimCheckOnUsesCodecDataConverter() {
        WorkflowClientOptions options = TemporalClient.clientOptions("ns", true, IDENTITY_CODEC);
        assertEquals("ns", options.getNamespace());
        assertInstanceOf(CodecDataConverter.class, options.getDataConverter());
    }

    @Test
    void claimCheckOffKeepsDefaultConverterAndAllowsNullCodec() {
        WorkflowClientOptions options = TemporalClient.clientOptions("ns", false, null);
        assertEquals("ns", options.getNamespace());
        assertFalse(options.getDataConverter() instanceof CodecDataConverter);
    }

    @Test
    void claimCheckOnWithoutCodecFailsClearly() {
        assertThrows(IllegalStateException.class, () -> TemporalClient.clientOptions("ns", true, null));
    }
}
