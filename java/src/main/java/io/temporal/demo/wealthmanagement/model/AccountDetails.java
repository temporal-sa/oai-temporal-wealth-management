package io.temporal.demo.wealthmanagement.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.*;

@Getter
@Setter
@AllArgsConstructor
@NoArgsConstructor
public class AccountDetails {
    @JsonProperty("investment_id")
    private String investmentId;
    private String name;
    private double balance;

    @Override
    public String toString() {
        return "   ID: " + investmentId + "\n" +
               "   Name: " + name + "\n" +
               "   Balance: " + balance + "\n" +
               "--------------------";
    }
}
