-- Seed data. Every figure is copied from a committed report, named in evaluations.source.
-- Idempotent: re-running inserts nothing new.

INSERT INTO model_versions (model_id, version, serialization, calibration, registered_on) VALUES
    ('cardiovanta-lr13', '1.0.0', 'joblib',        'sigmoid, ensemble of 5 calibrators', '2026-10-31'),
    ('cardiovanta-lr13', '1.1.0', 'joblib',        'sigmoid, pooled out-of-fold (H2.1)', '2026-11-15'),
    ('cardiovanta-lr13', '1.1.1', 'portable_json', 'sigmoid, pooled out-of-fold (H2.1)', '2026-11-16')
ON CONFLICT (model_id, version) DO NOTHING;

INSERT INTO cohorts (code, name, country, n_patients, role) VALUES
    ('cleveland_dev',    'Cleveland Clinic development rows',     'United States', 242, 'development'),
    ('cleveland_locked', 'Cleveland Clinic locked test rows',     'United States',  61, 'held_out_test'),
    ('hungary',          'Hungarian Institute of Cardiology',     'Hungary',       294, 'external'),
    ('long_beach_va',    'Long Beach VA Medical Center',          'United States', 200, 'external')
ON CONFLICT (code) DO NOTHING;

INSERT INTO evaluations (model_version_id, cohort_id, method, evaluated_on, source)
SELECT mv.id, c.id, e.method, e.evaluated_on::date, e.source
FROM (VALUES
    ('1.0.0', 'cleveland_locked', 'locked test (evaluated once)', '2026-09-21', 'reports/phase2c_final_evaluation.json'),
    ('1.0.0', 'cleveland_dev',    'nested CV, 20 repeats (H2.1)', '2026-11-01', 'reports/h2_1_calibration_confirmation.md'),
    ('1.1.0', 'cleveland_dev',    'nested CV, 20 repeats (H2.1)', '2026-11-01', 'reports/h2_1_calibration_confirmation.md')
) AS e (version, cohort_code, method, evaluated_on, source)
JOIN model_versions mv ON mv.model_id = 'cardiovanta-lr13' AND mv.version = e.version
JOIN cohorts c ON c.code = e.cohort_code
ON CONFLICT (model_version_id, cohort_id, method) DO NOTHING;

INSERT INTO metrics (evaluation_id, metric, value)
SELECT ev.id, m.metric, m.value
FROM (VALUES
    ('1.0.0', 'cleveland_locked', 'locked test (evaluated once)', 'accuracy',          0.852459),
    ('1.0.0', 'cleveland_locked', 'locked test (evaluated once)', 'roc_auc',           0.906926),
    ('1.0.0', 'cleveland_locked', 'locked test (evaluated once)', 'sensitivity',       0.821429),
    ('1.0.0', 'cleveland_locked', 'locked test (evaluated once)', 'specificity',       0.878788),
    ('1.0.0', 'cleveland_dev',    'nested CV, 20 repeats (H2.1)', 'roc_auc',           0.911200),
    ('1.0.0', 'cleveland_dev',    'nested CV, 20 repeats (H2.1)', 'calibration_slope', 1.267000),
    ('1.0.0', 'cleveland_dev',    'nested CV, 20 repeats (H2.1)', 'ece',               0.058900),
    ('1.0.0', 'cleveland_dev',    'nested CV, 20 repeats (H2.1)', 'brier',             0.117400),
    ('1.1.0', 'cleveland_dev',    'nested CV, 20 repeats (H2.1)', 'roc_auc',           0.910900),
    ('1.1.0', 'cleveland_dev',    'nested CV, 20 repeats (H2.1)', 'calibration_slope', 1.003000),
    ('1.1.0', 'cleveland_dev',    'nested CV, 20 repeats (H2.1)', 'ece',               0.039800),
    ('1.1.0', 'cleveland_dev',    'nested CV, 20 repeats (H2.1)', 'brier',             0.116000)
) AS m (version, cohort_code, method, metric, value)
JOIN model_versions mv ON mv.model_id = 'cardiovanta-lr13' AND mv.version = m.version
JOIN cohorts c ON c.code = m.cohort_code
JOIN evaluations ev ON ev.model_version_id = mv.id AND ev.cohort_id = c.id AND ev.method = m.method
ON CONFLICT (evaluation_id, metric) DO NOTHING;
