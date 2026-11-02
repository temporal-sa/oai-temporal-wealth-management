package io.temporal.demo.wealthmanagement.common;

import io.temporal.api.cloud.cloudservice.v1.CloudServiceGrpc;
import io.temporal.client.WorkflowClient;
import io.temporal.client.WorkflowClientOptions;
import io.temporal.common.converter.CodecDataConverter;
import io.temporal.common.converter.DataConverter;
import io.temporal.common.converter.DefaultDataConverter;
import io.temporal.common.converter.GlobalDataConverter;
import io.temporal.demo.wealthmanagement.claimcheck.ClaimCheckCodec;
import io.temporal.serviceclient.SimpleSslContextBuilder;
import io.temporal.serviceclient.WorkflowServiceStubs;
import io.temporal.serviceclient.WorkflowServiceStubsOptions;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import javax.annotation.PostConstruct;
import javax.net.ssl.SSLException;
import java.io.FileInputStream;
import java.io.FileNotFoundException;
import java.io.InputStream;
import java.util.Collections;

@Component
public class TemporalClient {

    @Autowired
    private ClaimCheckCodec claimCheckCodec;

    private static TemporalClient instance; // Not ideal

    @PostConstruct()
    public void init() {
        System.out.println("TemporalClient Initialization complete.");
        instance = this;
    }

    public static ClaimCheckCodec getClaimCheckCodec() {
        return instance.claimCheckCodec;
    }

    public static WorkflowServiceStubs getWorkflowServiceStubs() throws FileNotFoundException, SSLException {
        WorkflowServiceStubsOptions.Builder workflowServiceStubsOptionsBuilder =
                WorkflowServiceStubsOptions.newBuilder();

        if (!ServerInfo.getCertPath().equals("") && !"".equals(ServerInfo.getKeyPath())) {
            // Handle mTLS certificates
            InputStream clientCert = new FileInputStream(ServerInfo.getCertPath());
            InputStream clientKey = new FileInputStream(ServerInfo.getKeyPath());
            workflowServiceStubsOptionsBuilder.setSslContext(
                    SimpleSslContextBuilder.forPKCS8(clientCert, clientKey).build()
            );
        }

        String targetEndpoint = ServerInfo.getAddress();
        workflowServiceStubsOptionsBuilder.setTarget(targetEndpoint);
        WorkflowServiceStubs service = null;

        if (!ServerInfo.getAddress().equals("localhost:7233")) {
            // if not local server, then use the workflowServiceStubsOptionsBuilder
            service = WorkflowServiceStubs.newServiceStubs(workflowServiceStubsOptionsBuilder.build());
        } else {
            service = WorkflowServiceStubs.newLocalServiceStubs();
        }

        return service;
    }

    public static WorkflowClient get() throws FileNotFoundException, SSLException {
        System.out.println("<<<<SERVER INFO>>>>:\n " + ServerInfo.getServerInfo());
        WorkflowServiceStubs service = getWorkflowServiceStubs();
        return WorkflowClient.newInstance(service);
    }

}
