package io.temporal.demo.workflowstarter;

import io.temporal.client.WorkflowClient;
import io.temporal.workflow.Workflow;
import org.slf4j.Logger;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.CommandLineRunner;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class StartTheWorkflow implements CommandLineRunner {

    @Autowired
    private WorkflowClient client;

    public static void main(String[] args) {
        SpringApplication.run(StartTheWorkflow.class, args);
    }

    @Override
    public void run(String... args) throws Exception {
        Logger log = Workflow.getLogger(StartTheWorkflow.class);
        log.info("Initiating the workflow..");

//        String suffix = RandomStringUtils.random(8, true, true);
//
//        WorkflowOptions options = WorkflowOptions.newBuilder().
//                setTaskQueue(AppConfig.QUEUE_NAME).
//                setWorkflowId("Hello-"+suffix).
//                build();
//
//        String nameSuffix = RandomStringUtils.random(4, true, true);
//
//        OpenAccountWorkflow workflow = client.newWorkflowStub(OpenAccountWorkflow.class, options);
//        OpenInvestmentAccountInput parameters = new OpenInvestmentAccountInput();
//        parameters.setName("Name" + nameSuffix);
//        WorkflowResult result = workflow.run(parameters);
//        log.info("The response from the workflow {}",result.getGreeting());
        System.exit(0);
    }
}
