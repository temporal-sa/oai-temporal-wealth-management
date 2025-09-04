package io.temporal.demo.wealthmanagement.common;

import io.temporal.api.cloud.cloudservice.v1.CloudServiceGrpc;
import io.temporal.client.WorkflowClient;
import io.temporal.client.WorkflowClientOptions;
import io.temporal.serviceclient.SimpleSslContextBuilder;
import io.temporal.serviceclient.WorkflowServiceStubs;
import io.temporal.serviceclient.WorkflowServiceStubsOptions;

import javax.net.ssl.SSLException;
import java.io.FileInputStream;
import java.io.FileNotFoundException;
import java.io.InputStream;

public class TemporalClient {

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
        WorkflowServiceStubs service = getWorkflowServiceStubs();
        WorkflowClientOptions.Builder builder = WorkflowClientOptions.newBuilder();

        System.out.println("<<<<SERVER INFO>>>>:\n " + ServerInfo.getServerInfo());
        WorkflowClientOptions clientOptions = builder.setNamespace(ServerInfo.getNamespace()).build();

        // client that can be used to start and signal workflows
        WorkflowClient client = WorkflowClient.newInstance(service, clientOptions);
        return client;
    }
    
}
