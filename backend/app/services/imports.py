"""Bounded, atomic research-metric imports; no clinical or free-text columns."""
import csv
import io
import re
from datetime import date
from decimal import Decimal, InvalidOperation

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

HEADERS = ("model_id", "model_version", "cohort_code", "evaluation_method", "evaluation_date", "source", "metric_name", "metric_value")
MAX_BYTES = 262144
MAX_ROWS = 500
METHODS = {"external_validation", "nested_cv", "holdout"}
METRICS = {"roc_auc", "accuracy", "sensitivity", "specificity", "brier", "ece", "log_loss", "calibration_slope"}


def parse_csv(data: bytes, filename: str, content_type: str):
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "CSV exceeds 256 KiB.")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}\.csv", filename or "") or content_type not in ("text/csv", "application/vnd.ms-excel"):
        raise HTTPException(422, "Choose a CSV file with a simple filename.")
    try:
        reader = csv.DictReader(io.StringIO(data.decode("utf-8"), newline=""), strict=True)
        if tuple(reader.fieldnames or ()) != HEADERS:
            raise ValueError()
        rows, seen = [], set()
        for row in reader:
            if len(rows) >= MAX_ROWS or None in row or any(v is None for v in row.values()):
                raise ValueError()
            if row["model_id"] != "cardiovanta-lr13" or not re.fullmatch(r"\d{1,3}\.\d{1,3}\.\d{1,3}", row["model_version"]):
                raise ValueError()
            if not re.fullmatch(r"[a-z][a-z0-9_]{0,39}", row["cohort_code"]):
                raise ValueError()
            if row["evaluation_method"] not in METHODS or row["metric_name"] not in METRICS:
                raise ValueError()
            # Source is a repository report identifier, never arbitrary prose or a URL.
            if not re.fullmatch(r"reports/[a-z0-9_]{1,80}\.(md|json)", row["source"]):
                raise ValueError()
            when = date.fromisoformat(row["evaluation_date"])
            if not date(2000, 1, 1) <= when <= date.today():
                raise ValueError()
            value = Decimal(row["metric_value"])
            upper = 10 if row["metric_name"] in ("log_loss", "calibration_slope") else 1
            if not value.is_finite() or not 0 <= value <= upper or value.as_tuple().exponent < -6:
                raise ValueError()
            key = tuple(row[k] for k in ("model_id", "model_version", "cohort_code", "evaluation_method", "metric_name"))
            if key in seen:
                raise HTTPException(409, "CSV contains duplicate metrics.")
            seen.add(key)
            rows.append({**row, "evaluation_date": when, "metric_value": value})
        if not rows:
            raise ValueError()
        return rows
    except (UnicodeError, ValueError, InvalidOperation, csv.Error):
        raise HTTPException(422, "Invalid research CSV. Check the template, field values and 500-row limit.") from None


def write_rows(db: Session, rows):
    """Caller owns one transaction. Duplicate existing metrics reject the entire batch."""
    evaluations = {}
    for row in rows:
        identity = (row["model_version"], row["cohort_code"], row["evaluation_method"])
        if identity not in evaluations:
            model = db.scalar(text("SELECT id FROM model_versions WHERE model_id=:model_id AND version=:model_version"), row)
            cohort = db.scalar(text("SELECT id FROM cohorts WHERE code=:cohort_code"), row)
            if not model or not cohort:
                raise HTTPException(422, "CSV references an unregistered model or cohort.")
            params = {**row, "model": model, "cohort": cohort}
            existing = db.execute(text("SELECT id, source, evaluated_on FROM evaluations WHERE model_version_id=:model AND cohort_id=:cohort AND method=:evaluation_method"), params).first()
            if existing:
                if existing.source != row["source"] or existing.evaluated_on != row["evaluation_date"]:
                    raise HTTPException(409, "Evaluation provenance conflicts with existing metadata.")
                evaluation = existing.id
            else:
                evaluation = db.scalar(text("INSERT INTO evaluations(model_version_id,cohort_id,method,evaluated_on,source) VALUES (:model,:cohort,:evaluation_method,:evaluation_date,:source) RETURNING id"), params)
            evaluations[identity] = (evaluation, row["source"], row["evaluation_date"])
        evaluation, source, when = evaluations[identity]
        if source != row["source"] or when != row["evaluation_date"]:
            raise HTTPException(409, "Rows disagree about evaluation provenance.")
        db.execute(text("INSERT INTO metrics(evaluation_id,metric,value) VALUES (:evaluation,:metric_name,:metric_value)"), {**row, "evaluation": evaluation})

