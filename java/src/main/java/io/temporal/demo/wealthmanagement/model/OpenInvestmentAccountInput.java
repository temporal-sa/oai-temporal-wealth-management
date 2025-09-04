package io.temporal.demo.wealthmanagement.model;

import lombok.Getter;
import lombok.Setter;

@Setter
@Getter
public class OpenInvestmentAccountInput {
    private String client_id;
    private String account_name;
    private float initial_amount;
}
