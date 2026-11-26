# Explanation feedback

## ADDED Requirements

### Requirement: Anonymous feedback can be created, read, updated and deleted
The system SHALL store explanation feedback as MongoDB documents and SHALL expose create, read, update and
delete operations over HTTP.

#### Scenario: Create
- **WHEN** a client posts `{helpful, section, model_version}`
- **THEN** the response is 201 with a `Location` header and a one-time edit token

#### Scenario: Update or delete needs the edit token
- **WHEN** a client changes or deletes feedback without the token, or with a wrong one
- **THEN** the response is 401 or 403 and the document is unchanged

### Requirement: No personal or clinical data
Feedback documents SHALL contain only the fields in the design. Free text, clinical inputs, probabilities and
identifiers SHALL be rejected.

#### Scenario: Extra fields
- **WHEN** a client posts a field outside the schema
- **THEN** the response is 422 and nothing is stored
