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
public class UpdateAccountOpeningStateInput {
    @JsonProperty("account_name")
    private String accountName;
    private String state;
}
