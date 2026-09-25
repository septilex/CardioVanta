from fastapi import APIRouter, Query, HTTPException, Request
from typing import Optional
import logging
from backend.app.schemas.predict import (
    PredictRequest, PredictResponse, PredictionResult,
    DevelopmentRangeWarning, ExplanationResult, MetadataResult
)
from src.inference.predict import InferenceEngine

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/predict", response_model=PredictResponse)
def predict_endpoint(
    request: Request,
    payload: PredictRequest,
    threshold: Optional[float] = Query(None, ge=0.0, le=1.0)
):
    try:
        # Get the initialized inference engine from app state
        engine: InferenceEngine = request.app.state.inference_engine
        
        # Determine out-of-range features manually based on schema
        out_features = []
        for feature in engine.schema["features"]:
            if feature["type"] == "continuous":
                val = getattr(payload, feature["name"])
                if val < feature["min"] or val > feature["max"]:
                    out_features.append(feature["name"])
                    
        # Predict
        pred_res = engine.predict(payload.model_dump(), apply_threshold=threshold)
        
        # Explain
        exp_res = engine.explain(payload.model_dump())
        shap_exp_res = engine.explain_shap_equivalent(payload.model_dump())
        
        if threshold is None:
            t_status = "no_validated_production_threshold_configured"
        else:
            t_status = "mathematical_model_operating_point"
            
        prediction = PredictionResult(
            probability=pred_res["probability"],
            threshold_applied=pred_res["threshold_applied"],
            class_=pred_res["class"],
            threshold_status=t_status
        )
        
        development_range_warning = DevelopmentRangeWarning(
            outside_development_range=pred_res["outside_development_range"],
            features=out_features,
            note=pred_res["development_range_note"]
        )
        
        explanation = ExplanationResult(
            intercept=exp_res["intercept"],
            contributions=exp_res["contributions"],
            decision_function_log_odds=exp_res["decision_function_log_odds"],
            note=exp_res["note"]
        )
        
        from backend.app.schemas.predict import ShapEquivalentExplanationResult
        shap_explanation = ShapEquivalentExplanationResult(
            expected_value=shap_exp_res["expected_value"],
            contributions=shap_exp_res["contributions"],
            decision_function_log_odds=shap_exp_res["decision_function_log_odds"],
            note=shap_exp_res["note"]
        )
        
        # We know metadata["model_configuration"] and ["calibration_configuration"] exist, but let's check exact keys
        metadata = MetadataResult(
            package_version=engine.metadata.get("package_version", "unknown"),
            model_type=engine.metadata.get("model_configuration", {}).get("algorithm", "Logistic Regression"),
            calibration_method=engine.metadata.get("calibration_configuration", {}).get("method", "sigmoid")
        )
        
        response_obj = PredictResponse(
            prediction=prediction,
            development_range_warning=development_range_warning,
            explanation=explanation,
            shap_equivalent_explanation=shap_explanation,
            metadata=metadata
        )
        
        # Emit prediction telemetry
        try:
            import time
            start_time = getattr(request.state, "start_time", time.time())
            latency_ms = (time.time() - start_time) * 1000
            
            logger.info("Prediction event", extra={
                "event_type": "prediction_event",
                "request_id": getattr(request.state, "request_id", None),
                "endpoint": request.url.path,
                "package_version": metadata.package_version,
                "model_type": metadata.model_type,
                "calibration_method": metadata.calibration_method,
                "status_code": 200,
                "latency_ms": latency_ms,
                "prediction_probability": prediction.probability,
                "threshold_status": prediction.threshold_status,
                "outside_development_range": development_range_warning.outside_development_range,
                "out_of_range_features": development_range_warning.features,
            })
        except Exception as log_err:
            logger.error(f"Telemetry logging failed: {log_err}", exc_info=True)
            
        return response_obj
    except Exception as e:
        logger.error(f"Inference failed: {e}")
        # Return 500 without leaking stack trace
        raise HTTPException(status_code=500, detail="Internal inference failure")

