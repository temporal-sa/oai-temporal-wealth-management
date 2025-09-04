package io.temporal.demo.wealthmanagement.model;

import lombok.Getter;
import lombok.Setter;

@Getter
@Setter
public class OpenInvestmentAccountOutput {
    private boolean account_created;
    private String message;
}
