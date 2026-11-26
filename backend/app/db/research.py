"""
Research evaluation queries. Each one JOINs the relational tables from sql/001_research_schema.sql.

All SQL is static (no user input reaches it), and every query runs in a read-only transaction.
"""
from typing import Any, Dict, List, Optional

from backend.app.core.config import Settings
from backend.app.db.postgres import ResearchDatabaseUnavailable, connect

# 1. INNER JOINs: every metric with the model version, cohort and method that produced it.
EVALUATION_TABLE_SQL = """
SELECT mv.version, mv.serialization, c.code AS cohort, c.name AS cohort_name, c.role AS cohort_role,
       c.n_patients, e.method, e.evaluated_on, e.source, m.metric, m.value
FROM metrics m
JOIN evaluations e     ON e.id = m.evaluation_id
JOIN model_versions mv ON mv.id = e.model_version_id
JOIN cohorts c         ON c.id = e.cohort_id
ORDER BY mv.version, c.code, e.method, m.metric
"""

# 2. LEFT JOINs + GROUP BY: every version, including those with no evaluation rows (count 0).
VERSION_COVERAGE_SQL = """
SELECT mv.version, mv.serialization, mv.calibration,
       COUNT(e.id) AS evaluation_count,
       COALESCE(ARRAY_AGG(DISTINCT c.code) FILTER (WHERE c.code IS NOT NULL), '{}') AS cohorts
FROM model_versions mv
LEFT JOIN evaluations e ON e.model_version_id = mv.id
LEFT JOIN cohorts c     ON c.id = e.cohort_id
GROUP BY mv.id, mv.version, mv.serialization, mv.calibration
ORDER BY mv.version
"""

# 3. Anti-join (LEFT JOIN ... WHERE IS NULL): cohorts no registered model version has been evaluated on.
UNEVALUATED_COHORTS_SQL = """
SELECT c.code, c.name, c.country, c.n_patients, c.role
FROM cohorts c
LEFT JOIN evaluations e ON e.cohort_id = c.id
WHERE e.id IS NULL
ORDER BY c.code
"""


def _rows(cursor: Any) -> List[Dict[str, Any]]:
    names = [d.name for d in cursor.description]
    return [dict(zip(names, row)) for row in cursor.fetchall()]


def research_evaluations(cfg: Optional[Settings] = None) -> Dict[str, List[Dict[str, Any]]]:
    """The three JOIN results. Raises MissingSecretError or ResearchDatabaseUnavailable."""
    with connect(cfg) as conn:
        import psycopg

        try:
            with conn.cursor() as cur:
                evaluations = _rows(cur.execute(EVALUATION_TABLE_SQL))
                coverage = _rows(cur.execute(VERSION_COVERAGE_SQL))
                unevaluated = _rows(cur.execute(UNEVALUATED_COHORTS_SQL))
        except psycopg.Error as e:
            raise ResearchDatabaseUnavailable(f"research query failed ({type(e).__name__})") from None
    for row in evaluations:
        row["value"] = float(row["value"])
        row["evaluated_on"] = row["evaluated_on"].isoformat()
    for row in coverage:
        row["cohorts"] = sorted(row["cohorts"])
    return {"evaluations": evaluations, "version_coverage": coverage, "unevaluated_cohorts": unevaluated}
