package io.temporal.demo.wealthmanagement.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.Setter;

@Getter
@Setter
@AllArgsConstructor
public class InvestmentAccount {
    @JsonProperty("client_id")
    private String clientId;
    private String name;
    private double balance;
}