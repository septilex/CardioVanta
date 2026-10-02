# Proposal
## Why
The frontend currently contains factual inaccuracies regarding the model's capabilities and features. It mentions "10-year risk", "LDL", "Thalassemia", and uses diagnostic wording which is factually incorrect and potentially hazardous. It must be aligned with the actual 13-feature model schema and constrained to avoid claiming diagnostic or clinical capabilities.

## What Changes
- Audit and update all frontend text to remove unsupported claims ("10-year risk", "LDL", "physical activity", diagnostic claims).
- Align feature descriptions (e.g., `thal`, `ca`, `chol`) with the real model schema.
- Update the sample assessment UI to use real model data rather than fabricated factors.
- Maintain all existing visual designs, animations, and layouts.

## Capabilities
### Modified Capabilities
- **Frontend Text and Explanations**: Text will be corrected to accurately reflect the model's actual inputs and outputs without unsupported clinical claims.
