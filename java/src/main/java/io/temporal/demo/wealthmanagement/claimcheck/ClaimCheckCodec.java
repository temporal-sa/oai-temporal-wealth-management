package io.temporal.demo.wealthmanagement.claimcheck;

import com.google.protobuf.ByteString;
import io.temporal.api.common.v1.Payload;
import io.temporal.common.converter.DataConverterException;
import io.temporal.common.converter.EncodingKeys;
import io.temporal.payload.codec.PayloadCodec;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Component;

import javax.annotation.Nonnull;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.UUID;
import java.util.stream.Collectors;

@Component
public class ClaimCheckCodec implements PayloadCodec {
    Logger logger = LoggerFactory.getLogger(ClaimCheckCodec.class);
    private final ByteString METADATA_ENCODING = ByteString.copyFromUtf8("claim-checked");
    private final String CLAIM_CHECK_CODEC_KEY = "temporal.io/claim-check-codec";
    private final String CLAIM_CHECK_CODEC_VERSION = "v1";

    private final RedisTemplate<String, Payload> redisTemplate;

    ClaimCheckCodec(RedisTemplate<String, Payload> redisTemplate) {
        logger.info("Constructing ClaimCheckCodec. RedisTemplate is {}", redisTemplate);
        this.redisTemplate = redisTemplate;
    }

    @Nonnull
    @Override
    public List<Payload> encode(@Nonnull List<Payload> payloads) {
        return payloads.stream().map(this::encodePayload).collect(Collectors.toList());
    }

    @Nonnull
    @Override
    public List<Payload> decode(@Nonnull List<Payload> payloads) {
        return payloads.stream().map(this::decodePayload).collect(Collectors.toList());
    }

    private Payload encodePayload(Payload payload) {
        String id = UUID.randomUUID().toString();

        redisTemplate.opsForValue().set(id, payload);

        return Payload.newBuilder()
                .putMetadata(EncodingKeys.METADATA_ENCODING_KEY,METADATA_ENCODING)
                .putMetadata(CLAIM_CHECK_CODEC_KEY,ByteString.copyFromUtf8(CLAIM_CHECK_CODEC_VERSION))
                .setData(ByteString.copyFromUtf8(id))
                .build();
    }

    private Payload decodePayload(Payload source) {
        // make sure we're dealing with only claim-checked payloads
        logger.info("Incoming payload is {} = {}",
                EncodingKeys.METADATA_ENCODING_KEY,
                source.getMetadataOrDefault(
                        EncodingKeys.METADATA_ENCODING_KEY,
                        ByteString.copyFrom("<missing>",  StandardCharsets.UTF_8)
                ).toStringUtf8());
        if (!METADATA_ENCODING.equals(source.getMetadataOrDefault(EncodingKeys.METADATA_ENCODING_KEY,null))) {
            logger.info("bypassing source as it isn't claim-checked value is {} ", source.getMetadataOrDefault(EncodingKeys.METADATA_ENCODING_KEY,null));
            return source;
        }

        String redisId;
        try {
            // get the redis id
            redisId = source.getData().toStringUtf8();
            logger.info("===> The redis id is {}", redisId);
            // and retrieve the data from Redis
            Payload decodedPayload =  redisTemplate.opsForValue().get(redisId);
            logger.info("The data from Redis is {}", decodedPayload);
            return decodedPayload;
        } catch (Exception ex)
        {
            logger.error("Error when retrieving redis key ", ex);
            throw new DataConverterException(ex);
        }
    }
}
