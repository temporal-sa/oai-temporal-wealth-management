package io.temporal.demo.wealthmanagement.data;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Getter
@Setter
@AllArgsConstructor
@NoArgsConstructor
public class WealthManagementClient {
    @JsonProperty("client_id")
    String clientId;
    @JsonProperty("first_name")
    String firstName;
    @JsonProperty("last_name")
    String lastName;
    String address;
    String phone;
    String email;
    @JsonProperty("marital_status")
    String maritalStatus;

    public WealthManagementClient(String clientId, InvestmentClient investmentClient) {
        this(clientId, investmentClient.getFirstName(), investmentClient.getFirstName(),
                investmentClient.getAddress(), investmentClient.getPhone(),
                investmentClient.getEmail(), investmentClient.getMaritalStatus());
    }
}
