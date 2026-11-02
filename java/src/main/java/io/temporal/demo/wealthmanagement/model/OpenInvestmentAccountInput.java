package io.temporal.demo.wealthmanagement.model;

import lombok.Getter;
import lombok.Setter;

@Setter
@Getter
public class OpenInvestmentAccountInput {
    private String client_id;
    private String account_name;
    private float initial_amount;
    // Set when a promotion is running for the new account (e.g. "WELCOME-BONUS")
    private String promo_code;
}
