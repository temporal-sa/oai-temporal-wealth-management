package io.temporal.demo.wealthmanagement;

import io.temporal.client.WorkflowClient;
import io.temporal.demo.wealthmanagement.activities.UpdateParentWorkflow;
import io.temporal.demo.wealthmanagement.activities.UpdateParentWorkflowImpl;
import io.temporal.demo.wealthmanagement.common.ServerInfo;
import io.temporal.demo.wealthmanagement.common.TemporalClient;
import io.temporal.demo.wealthmanagement.workflow.OpenInvestmentAccountWorkflowImpl;
import io.temporal.serviceclient.WorkflowServiceStubs;
import io.temporal.worker.Worker;
import io.temporal.worker.WorkerFactory;
import io.temporal.workflow.Workflow;
import org.slf4j.Logger;
import org.springframework.boot.CommandLineRunner;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

import java.util.UUID;

@SpringBootApplication
public class StartTheWorker implements CommandLineRunner {

    public static void main(String[] args) {
        // NOTE that ${random.uuid} in properties will not work since
        // you receive a new random value per-component under SpringBoot's creation
        System.setProperty("APP_UUID", UUID.randomUUID().toString());
        SpringApplication.run(StartTheWorker.class, args);
    }

    @Override
    public void run(String... args) throws Exception {
        Logger log = Workflow.getLogger(StartTheWorker.class);
        log.info("Starting the workers...");
        // Since we're disabling the workers, we need to
        // add them here
        WorkflowServiceStubs service = TemporalClient.getWorkflowServiceStubs();
        WorkflowClient client = WorkflowClient.newInstance(service);
        WorkerFactory workerFactory = WorkerFactory.newInstance(client);
        Worker worker = workerFactory.newWorker(ServerInfo.getTaskqueueOpenAccount());
        worker.registerWorkflowImplementationTypes(OpenInvestmentAccountWorkflowImpl.class);
        worker.registerActivitiesImplementations(new UpdateParentWorkflowImpl());
        workerFactory.start();
    }
}
