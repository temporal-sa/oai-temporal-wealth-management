package io.temporal.demo.wealthmanagement.data;

import io.temporal.demo.wealthmanagement.model.AccountDetails;
import lombok.Data;
import java.util.List;
import java.util.Map;
@Data
public class InvestmentData {
    private Map<String, List<AccountDetails>> data;
}
