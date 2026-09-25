# Spec Delta

## Purpose

Establishes a stateless, offline methodology for detecting distribution shifts and support-boundary violations in production telemetry, treating probabilities as health-related data without processing sensitive raw patient features.

## ADDED Requirements

### Requirement: Prediction Probability Drift Detection
The system SHALL evaluate prediction probability distribution shifts using a robust two-sample Kolmogorov-Smirnov (KS) methodology. To explicitly handle ties, constant probabilities, and small-sample uncertainty, the system SHALL calculate permutation-based Monte Carlo p-value estimation using at least 10,000 permutations.
The exact permutation procedure SHALL: combine the frozen reference probabilities and production probabilities, preserve the observed reference and production sample sizes, randomly permute the pooled labels using a reproducible deterministic seed, recompute the KS D-statistic, and repeat at least 10,000 times. The system SHALL define finite-sample p-value handling appropriately (e.g., `p = (sum(D_perm >= D_obs) + 1) / (B + 1)`) to avoid reporting an impossible finite-simulation p=0. The system SHALL report the observed D and permutation-based p-value.
The system MUST compare production log samples strictly against the baseline distribution of the 242 development set predictions. The system MUST NOT use the 61 locked test samples as a baseline.
The system SHALL require both statistical significance (e.g., permutation p-value < 0.05) and a meaningful effect size (the KS D-statistic) to declare statistical drift; a p-value alone is insufficient. Drift is ONLY declared if all three of the following are true: 1) minimum observation eligibility is met, 2) statistical evidence is present, and 3) the KS D-statistic meets a predefined ENGINEERING MONITORING POLICY threshold (e.g., D >= 0.2). This threshold is not statistically validated, clinically validated, or evidence of model failure/clinical deterioration.

#### Scenario: Significant prediction shift detected
- **WHEN** the KS test evaluates a production log window where probabilities exhibit both statistically significant differences (permutation p-value) and a meaningful effect size (KS D-statistic) compared to the development baseline
- **THEN** the system declares statistical drift in the output report
- **THEN** the system explicitly states this is a statistical shift and does not infer clinical deterioration, model failure, or performance degradation

### Requirement: Minimum Observation Policy
The system SHALL enforce a 50-observation minimum as a strict operational eligibility threshold. The system SHALL NOT declare drift unless the provided production log window contains a minimum of 50 valid, consecutive prediction events.

#### Scenario: Below minimum sample window
- **WHEN** the system is provided a log file containing fewer than 50 valid events
- **THEN** the system aborts the statistical test, declares insufficient evidence, and outputs a warning without rendering a drift conclusion

### Requirement: Privacy, Retention, and Access Policy
The system SHALL treat `prediction_probability` as sensitive health-related telemetry. The system SHALL parse structured operational telemetry that explicitly excludes the 13 raw clinical input features. The system SHALL enforce a configurable retention policy (defaulting to 30 days) and restrict access to authorized MLOps personnel.

#### Scenario: Malformed telemetry containing features
- **WHEN** the system encounters unexpected JSON log structures containing raw patient features
- **THEN** the system ignores the raw features and processes only the defined operational and model metadata

### Requirement: Offline Stateless Execution
The system SHALL execute drift analysis as an offline, stateless script that parses log exports and generates a report, without requiring a database or modifying the production Vercel application.

#### Scenario: Execution in CI/CD or locally
- **WHEN** the script is executed against a JSON log file
- **THEN** it completes the analysis entirely in memory in a deterministic manner and outputs the results to stdout or a file

### Requirement: Support-Boundary Violation Monitoring
The system SHALL evaluate the frequency of out-of-development-range prediction flags as strict support-boundary violations, rather than comparing them to an unjustified conventional stochastic baseline.

#### Scenario: Spike in support-boundary violations
- **WHEN** the rate of out-of-range flags significantly exceeds expected data-support assumptions
- **THEN** the system logs a data-quality warning in the drift report

### Requirement: Concept Drift Limitation
The system SHALL explicitly acknowledge in its reports that true concept drift and real performance degradation cannot be measured because CardioVanta does not collect post-prediction ground-truth outcomes.

#### Scenario: Reporting limitations
- **WHEN** a drift report is generated
- **THEN** the report contains a disclaimer stating that performance degradation cannot be evaluated without ground-truth evidence

### Requirement: No Automated Interventions or Dashboards
The system SHALL ONLY output human-readable drift reports. It SHALL NOT trigger automated model retraining, model replacement, or clinical alerting. It SHALL NOT include frontend dashboards, chatbots, or LLM integrations.

#### Scenario: Drift report generation
- **WHEN** statistical drift is confidently detected
- **THEN** the report outlines the severity based on effect size, but takes no automated system-level action
