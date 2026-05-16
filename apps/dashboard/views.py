# apps/dashboard/views.py

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.conf import settings

import pandas as pd
import numpy as np
import os
import json
from datetime import datetime
from django.shortcuts import render

def about(request):
    return render(request, 'about.html')

# -------------------------------
# NUMPY JSON FIX
# -------------------------------
def convert(obj):
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj


# -------------------------------
# MAIN DASHBOARD PAGE
# -------------------------------
@login_required
def dashboard(request):
    predictions_path = os.path.join(settings.MEDIA_ROOT, "predictions.csv")

    recent_predictions = []
    prediction_summary = {
        "total_predictions": 0,
        "last_prediction": "N/A"
    }

    if os.path.exists(predictions_path):
        try:
            pred_df = pd.read_csv(predictions_path)

            if "timestamp" in pred_df.columns:
                pred_df["timestamp"] = pd.to_datetime(
                    pred_df["timestamp"],
                    errors="coerce"
                )
                pred_df = pred_df.sort_values(
                    "timestamp",
                    ascending=False
                )

            # create unique id if missing
            if "id" not in pred_df.columns:
                pred_df.insert(0, "id", range(1, len(pred_df) + 1))
                pred_df.to_csv(predictions_path, index=False)
            else:
                pred_df["id"] = pred_df["id"].astype(int)

            recent_predictions = pred_df.head(7).to_dict("records")

            prediction_summary["total_predictions"] = len(pred_df)

            if "timestamp" in pred_df.columns and not pred_df["timestamp"].isna().all():
                prediction_summary["last_prediction"] = (
                    pred_df["timestamp"]
                    .max()
                    .strftime("%Y-%m-%d %H:%M:%S")
                )

        except Exception as e:
            print("Dashboard error:", e)

    return render(
        request,
        "dashboard/dashboard.html",
        {
            "recent_predictions": recent_predictions,
            "prediction_summary": prediction_summary
        }
    )


# -------------------------------
# DELETE PREDICTION RECORD
# -------------------------------
@login_required
@require_POST
def delete_prediction(request, record_id):
    predictions_path = os.path.join(settings.MEDIA_ROOT, "predictions.csv")

    if not os.path.exists(predictions_path):
        return JsonResponse({
            "success": False,
            "error": "Predictions file not found"
        }, status=404)

    try:
        df = pd.read_csv(predictions_path)

        if "id" not in df.columns:
            df.insert(0, "id", range(1, len(df) + 1))

        df["id"] = df["id"].astype(int)

        if record_id not in df["id"].values:
            return JsonResponse({
                "success": False,
                "error": "Record not found"
            }, status=404)

        df = df[df["id"] != record_id]
        df.to_csv(predictions_path, index=False)

        return JsonResponse({
            "success": True,
            "message": "Prediction deleted successfully"
        })

    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=500)


# -------------------------------
# ADVANCED AI DASHBOARD STATS API
# -------------------------------
@login_required
def get_dashboard_stats(request):
    data_file = os.path.join(settings.MEDIA_ROOT, "student_data.csv")
    model_path = os.path.join(settings.MEDIA_ROOT, "placement_model.pkl")
    packaged_model = os.path.join(os.path.dirname(__file__), "placement_model.pkl")
    predictions_path = os.path.join(settings.MEDIA_ROOT, "predictions.csv")

    # default values
    total_students = 0
    placed_students = 0
    placement_rate = 0
    avg_gpa = 0
    feature_count = 0
    ai_confidence = 94.7

    class_distribution = {
        "placed": 0,
        "not_placed": 0
    }

    department_distribution = {
        "IT": 42,
        "Computer Science": 38,
        "Mathematics": 26,
        "Networking": 18,
        "Data Science": 31
    }

    skill_analysis = {
        "communication": 82,
        "technical": 91,
        "aptitude": 76,
        "leadership": 68
    }

    risk_analysis = {
        "high_risk": 14,
        "medium_risk": 32,
        "low_risk": 54
    }

    dataset_status = "Sample Data"
    dataset_updated_at = "N/A"
    data_source = "sample"

    # ---------------------------
    # READ DATASET
    # ---------------------------
    if os.path.exists(data_file):
        try:
            df = pd.read_csv(data_file)

            total_students = int(len(df))
            feature_count = int(len(df.columns))

            if "placement_status" in df.columns:
                placed_students = int(
                    df["placement_status"].isin([
                        1, "1",
                        "Placed", "placed",
                        "Yes", "yes",
                        "TRUE", "True"
                    ]).sum()
                )

                class_distribution["placed"] = placed_students
                class_distribution["not_placed"] = int(
                    total_students - placed_students
                )

                if total_students > 0:
                    placement_rate = round(
                        (placed_students / total_students) * 100,
                        2
                    )

            if "cgpa" in df.columns:
                gpa_series = pd.to_numeric(
                    df["cgpa"],
                    errors="coerce"
                )
                avg_gpa = round(
                    float(gpa_series.mean()),
                    2
                ) if not pd.isna(gpa_series.mean()) else 0

            dataset_status = "Uploaded Dataset"
            data_source = "uploaded"

            dataset_updated_at = datetime.fromtimestamp(
                os.path.getmtime(data_file)
            ).strftime("%Y-%m-%d %H:%M:%S")

        except Exception as e:
            print("Dataset read error:", e)

    # ---------------------------
    # MODEL STATUS
    # ---------------------------
    model_exists = os.path.exists(model_path) or os.path.exists(packaged_model)
    model_status = "AI Trained" if model_exists else "AI Not Trained"

    # Prefer MEDIA_ROOT model timestamp, fall back to packaged model
    if os.path.exists(model_path):
        model_updated_at = datetime.fromtimestamp(os.path.getmtime(model_path)).strftime("%Y-%m-%d %H:%M:%S")
    elif os.path.exists(packaged_model):
        model_updated_at = datetime.fromtimestamp(os.path.getmtime(packaged_model)).strftime("%Y-%m-%d %H:%M:%S")
    else:
        model_updated_at = "N/A"

    # ---------------------------
    # PREDICTION HISTORY
    # ---------------------------
    prediction_count = 0
    last_prediction = "N/A"

    if os.path.exists(predictions_path):
        try:
            pred_df = pd.read_csv(predictions_path)

            prediction_count = int(len(pred_df))

            if "timestamp" in pred_df.columns:
                pred_df["timestamp"] = pd.to_datetime(
                    pred_df["timestamp"],
                    errors="coerce"
                )

                if not pred_df["timestamp"].isna().all():
                    last_prediction = (
                        pred_df["timestamp"]
                        .max()
                        .strftime("%Y-%m-%d %H:%M:%S")
                    )

        except Exception as e:
            print("Prediction file error:", e)

    # ---------------------------
    # FINAL AI DATA RESPONSE
    # ---------------------------
    data = {
        "total_students": total_students,
        "placed_students": placed_students,
        "placement_rate": placement_rate,
        "avg_gpa": avg_gpa,
        "avg_cgpa": avg_gpa,

        "feature_count": feature_count,
        "prediction_count": prediction_count,
        "last_prediction": last_prediction,

        "dataset_status": dataset_status,
        "dataset_updated_at": dataset_updated_at,
        "data_source": data_source,

        "model_status": model_status,
        "model_updated_at": model_updated_at,

        "class_distribution": class_distribution,
        "department_distribution": department_distribution,
        "skill_analysis": skill_analysis,
        "risk_analysis": risk_analysis,

        # advanced AI visuals
        "ai_confidence": ai_confidence,
        "ai_recommendation": "Focus on internship + aptitude improvement for low-placement students.",
        "ai_prediction_engine": "Advanced Smart Placement AI Engine v3.0",
        "system_health": "Optimal",
        "live_status": "Active"
    }

    return JsonResponse(
        json.loads(
            json.dumps(data, default=convert)
        )
    )