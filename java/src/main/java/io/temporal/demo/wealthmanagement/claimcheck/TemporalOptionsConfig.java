package io.temporal.demo.wealthmanagement.claimcheck;

import io.temporal.client.WorkflowClientOptions;
import io.temporal.common.converter.CodecDataConverter;
import io.temporal.common.converter.DefaultDataConverter;
import io.temporal.demo.wealthmanagement.common.ServerInfo;
import io.temporal.spring.boot.TemporalOptionsCustomizer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import javax.annotation.Nonnull;
import java.util.Collections;

@Configuration
public class TemporalOptionsConfig {
    private final Logger logger = LoggerFactory.getLogger(TemporalOptionsConfig.class);

    @Autowired
    private ClaimCheckCodec claimCheckCodec;

    @Bean
    // Allows us to customize the client to hook up a DataConverter, if necessary.
    public TemporalOptionsCustomizer<WorkflowClientOptions.Builder> customClientOptions() {
        return new TemporalOptionsCustomizer<>() {
            @Nonnull
            @Override
            public WorkflowClientOptions.Builder customize(
                    @Nonnull WorkflowClientOptions.Builder optionsBuilder) {
                // wire up the codec server
                if (ServerInfo.useClaimCheck()) {
                    logger.info("***> Wiring up Claim Check Codec");
                    optionsBuilder.setDataConverter(new CodecDataConverter(DefaultDataConverter.newDefaultInstance(), Collections.singletonList(claimCheckCodec)));
                }
                return optionsBuilder;
            }
        };
    }
}
