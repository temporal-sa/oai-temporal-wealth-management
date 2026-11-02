package io.temporal.demo.wealthmanagement.data;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Getter;
import lombok.Setter;

@Getter
@Setter
public class InvestmentClient {
    @JsonProperty("first_name")
    String firstName;
    @JsonProperty("last_name")
    String lastName;
    String address;
    String phone;
    String email;
    @JsonProperty("marital_status")
    String maritalStatus;
}
