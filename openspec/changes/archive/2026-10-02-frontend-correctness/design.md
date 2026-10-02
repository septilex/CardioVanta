# Design
## Context
The frontend UI contains placeholder or inaccurate text describing the model, including "10-year risk", "Thalassemia" (for `thal`), and references to features like "physical activity" which are not in the model. We need to align the frontend strictly with the actual 13-feature schema: `age`, `sex`, `cp`, `trestbps`, `chol`, `fbs`, `restecg`, `thalach`, `exang`, `oldpeak`, `slope`, `ca`, `thal`.

## Decisions
1. **Remove False Capabilities**: Remove phrases like "10-year risk" and "diagnosis", replacing them with accurate descriptions like "Cardiovascular disease presence probability".
2. **Correct Feature Names/Values**: 
   - `thal` is a blood flow feature (normal, fixed defect, reversible defect), not Thalassemia in this dataset context (typically). Wait, the UCI heart disease dataset uses `thal` for Thalassemia or Thallium stress test. The actual meaning in the schema is usually 1=normal, 2=fixed defect, 3=reversable defect. I will check the schema.
   - `chol` is serum cholesterol in mg/dl, not just "LDL".
   - Remove "physical activity" or "exercise frequency".
3. **Sample Assessment Data**: Update the hardcoded sample assessment in the UI to use a real valid set of 13 features.

## Risks
None, this is purely a text and static data change. Visuals remain identical.
