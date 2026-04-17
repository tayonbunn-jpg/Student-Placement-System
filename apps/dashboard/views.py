from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
import pandas as pd
import os
from django.conf import settings
from datetime import datetime

@login_required
def dashboard(request):
    predictions_path = os.path.join(settings.MEDIA_ROOT, 'predictions.csv')
    recent_predictions = []
    prediction_summary = {
        'total_predictions': 0,
        'last_prediction': 'N/A'
    }

    if os.path.exists(predictions_path):
        try:
            pred_df = pd.read_csv(predictions_path)
            pred_df['timestamp'] = pd.to_datetime(pred_df['timestamp'], errors='coerce')
            pred_df = pred_df.sort_values('timestamp', ascending=False)
            recent_predictions = pred_df.head(7).to_dict('records')
            prediction_summary['total_predictions'] = len(pred_df)
            prediction_summary['last_prediction'] = pred_df['timestamp'].max().strftime('%Y-%m-%d %H:%M:%S') if not pred_df['timestamp'].isna().all() else 'N/A'
        except Exception:
            recent_predictions = []
            prediction_summary = {
                'total_predictions': 0,
                'last_prediction': 'N/A'
            }

    return render(request, 'dashboard/dashboard.html', {
        'recent_predictions': recent_predictions,
        'prediction_summary': prediction_summary
    })

@login_required
def get_dashboard_stats(request):
    # Try to load data if it exists
    data_file = os.path.join(settings.MEDIA_ROOT, 'student_data.csv')
    
    if os.path.exists(data_file):
        try:
            df = pd.read_csv(data_file)
            total_students = len(df)
            placed_students = 0
            placement_rate = 0
            avg_cgpa = 0
            feature_count = len([col for col in df.columns if col != 'placement_status'])
            class_distribution = {'placed': 0, 'not_placed': 0}

            if total_students > 0 and 'placement_status' in df.columns:
                placed_students = df['placement_status'].isin([
                    1, '1', 'Placed', 'placed', 'PLACED', 'Yes', 'yes', 'TRUE', 'True'
                ]).sum()
                class_distribution['placed'] = int(placed_students)
                class_distribution['not_placed'] = int(total_students - placed_students)
                placement_rate = round((placed_students / total_students) * 100, 2)
            else:
                class_distribution['not_placed'] = int(total_students)

            if total_students > 0 and 'cgpa' in df.columns:
                cgpa_series = pd.to_numeric(df['cgpa'], errors='coerce')
                avg_cgpa = round(cgpa_series.mean(), 2) if not pd.isna(cgpa_series.mean()) else 0

            data_source = 'uploaded'
            dataset_status = 'Uploaded'
            dataset_updated_at = datetime.fromtimestamp(os.path.getmtime(data_file)).strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
            total_students = 0
            placed_students = 0
            placement_rate = 0
            avg_cgpa = 0
            feature_count = 0
            class_distribution = {'placed': 0, 'not_placed': 0}
            data_source = 'sample'
            dataset_status = 'Sample Data'
            dataset_updated_at = 'N/A'
    else:
        # Sample data for demonstration
        total_students = 150
        placed_students = 98
        placement_rate = 65.33
        avg_cgpa = 7.8
        feature_count = 0
        data_source = 'sample'
        dataset_status = 'Sample Data'
        dataset_updated_at = 'N/A'
    
    model_path = os.path.join(settings.MEDIA_ROOT, 'placement_model.pkl')
    predictions_path = os.path.join(settings.MEDIA_ROOT, 'predictions.csv')
    if os.path.exists(predictions_path):
        try:
            predictions_df = pd.read_csv(predictions_path)
            prediction_count = len(predictions_df)
            predictions_df['timestamp'] = pd.to_datetime(predictions_df['timestamp'], errors='coerce')
            last_prediction = predictions_df['timestamp'].max().strftime('%Y-%m-%d %H:%M:%S') if not predictions_df['timestamp'].isna().all() else 'N/A'
        except Exception:
            prediction_count = 0
            last_prediction = 'N/A'
    else:
        prediction_count = 0
        last_prediction = 'N/A'

    model_exists = os.path.exists(model_path)
    model_status = 'Trained' if model_exists else 'Not Trained'
    model_updated_at = datetime.fromtimestamp(os.path.getmtime(model_path)).strftime('%Y-%m-%d %H:%M:%S') if model_exists else 'N/A'

    data = {
        'total_students': total_students,
        'placed_students': placed_students,
        'placement_rate': placement_rate,
        'avg_cgpa': avg_cgpa,
        'data_source': data_source,
        'dataset_status': dataset_status,
        'dataset_updated_at': dataset_updated_at,
        'feature_count': feature_count,
        'class_distribution': class_distribution,
        'model_status': model_status,
        'model_updated_at': model_updated_at,
        'prediction_count': prediction_count,
        'last_prediction': last_prediction
    }
    return JsonResponse(data)