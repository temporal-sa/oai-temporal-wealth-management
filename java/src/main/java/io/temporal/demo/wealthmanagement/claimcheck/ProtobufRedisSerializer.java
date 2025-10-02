package io.temporal.demo.wealthmanagement.claimcheck;

import com.google.protobuf.Message;
import org.springframework.data.redis.serializer.RedisSerializer;
import org.springframework.data.redis.serializer.SerializationException;

public class ProtobufRedisSerializer<T extends Message> implements RedisSerializer<T> {

    private final Class<T> protobufMessageType;

    public ProtobufRedisSerializer(Class<T> protobufMessageType) {
        this.protobufMessageType = protobufMessageType;
    }

    @Override
    public byte[] serialize(T object) throws SerializationException {
        if (object == null) {
            return null;
        }
        return object.toByteArray();
    }

    @Override
    public T deserialize(byte[] bytes) throws SerializationException {
        if (bytes == null) {
            return null;
        }
        try {
            // Use a Protobuf parser to parse the byte array back into a message object
            return (T) protobufMessageType.getMethod("parseFrom", byte[].class).invoke(null, bytes);
        } catch (Exception e) {
            throw new SerializationException("Could not deserialize Protobuf message", e);
        }
    }
}
