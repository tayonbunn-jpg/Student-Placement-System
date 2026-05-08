import os
import pandas as pd
from datetime import datetime

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings

from apps.ml_engine.ml_models import PlacementPredictor
from apps.authentication.models import ActivityLog

FIELD_LABELS = {
    'cgpa': 'CGPA',
    'iq': 'IQ',
    'ssc_marks': 'SSC Marks',
    'hsc_marks': 'HSC Marks',
    'degree_marks': 'Degree Marks',
    'work_experience': 'Work Experience (Years)',
    'internships': 'Number of Internships',
    'projects': 'Number of Projects',
    'workshops': 'Workshops / Certifications',
    'aptitude_score': 'Aptitude Score',
    'soft_skills_rating': 'Soft Skills Rating',
    'extra_curricular': 'Extra Curricular Activities',
    'placement_training': 'Placement Training',
    'student_id': 'Student ID',
}


def parse_numeric_input(value):
    """Safely parse a numeric input, returning None if invalid."""
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


# ─────────────────────────────────────────────────────────────────────────────
# TRAIN MODEL
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def train_model(request):
    model_path = os.path.join(settings.MEDIA_ROOT, 'placement_model.pkl')
    # Use the file saved by the upload view
    data_path = os.path.join(settings.MEDIA_ROOT, 'student_data.csv')

    # Read data_info from session (set by upload_data view)
    data_info = request.session.get('data_info', None)

    # If no session data_info but file exists, rebuild it
    if not data_info and os.path.exists(data_path):
        try:
            df_check = pd.read_csv(data_path)
            data_info = {
                'total_rows': len(df_check),
                'columns': df_check.columns.tolist(),
                'has_target': 'placement_status' in df_check.columns,
            }
            request.session['data_info'] = data_info
        except Exception:
            pass

    if request.method == 'POST':
        model_name = request.POST.get('algorithm', 'random_forest')
        test_size = float(request.POST.get('test_size', 0.2))

        if not os.path.exists(data_path):
            messages.error(request, 'No data found. Please upload your dataset first.')
            return redirect('upload_data')

        try:
            df = pd.read_csv(data_path)

            if 'placement_status' not in df.columns:
                messages.error(request, 'Dataset missing placement_status column. Please re-upload labeled data.')
                return render(request, 'ml_engine/train.html', {'data_info': data_info})

            predictor = PlacementPredictor()
            metrics = predictor.train_model(df, test_size=test_size)
            predictor.save_model(model_path)

            # Save training info to session so template can show it
            training_info = {
                'algorithm': model_name,
                'test_size': test_size,
                'total_samples': len(df),
                'features': predictor.feature_names or [],
                'accuracy': round(metrics.get('accuracy', 0) * 100, 2),
                'f1_score': round(metrics.get('f1_score', 0), 4),
            }
            request.session['training_info'] = training_info

            ActivityLog.objects.create(
                user=request.user,
                action='train',
                description=f'Trained {model_name} model on {len(df)} records',
                metadata=metrics
            )

            messages.success(
                request,
                f'Model trained successfully on {len(df)} records. '
                f'Accuracy: {training_info["accuracy"]}% | F1: {training_info["f1_score"]}'
            )
            return redirect('list_models')

        except Exception as e:
            import traceback
            traceback.print_exc()
            messages.error(request, f'Training failed: {str(e)}')
            return render(request, 'ml_engine/train.html', {'data_info': data_info})

    # GET
    training_info = request.session.get('training_info', None)

    return render(request, 'ml_engine/train.html', {
        'data_info': data_info,
        'training_info': training_info,
    })


# ─────────────────────────────────────────────────────────────────────────────
# MAKE PREDICTION
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def make_prediction(request):
    model_path = os.path.join(settings.MEDIA_ROOT, 'placement_model.pkl')

    predictor = PlacementPredictor()

    try:
        if not os.path.exists(model_path):
            messages.error(request, 'No trained model found. Please train a model first.')
            return redirect('train_model')

        predictor.load_model(model_path)

    except Exception as e:
        messages.error(request, f'Model corrupted or incompatible. Please retrain. Error: {str(e)}')
        return redirect('train_model')

    feature_names = predictor.feature_names or []
    field_labels = {name: FIELD_LABELS.get(name, name.replace('_', ' ').title()) for name in feature_names}
    feature_fields = [{'name': name, 'label': field_labels[name]} for name in feature_names]

    if request.method == 'POST':
        student_data = {}

        for feature in feature_names:
            student_data[feature] = parse_numeric_input(request.POST.get(feature, ''))

        if 'student_id' in request.POST:
            student_data['student_id'] = request.POST.get('student_id', '')

        df = pd.DataFrame([student_data])

        try:
            results = predictor.predict(df)
            result = results[0]  # dict with 'prediction', 'confidence', 'probability'

            ActivityLog.objects.create(
                user=request.user,
                action='predict',
                description=f'Predicted placement for student {student_data.get("student_id", "unknown")}',
                metadata={
                    'student_data': student_data,
                    'prediction': result['prediction'],
                    'confidence': result['confidence'],
                }
            )

            predictions_path = os.path.join(settings.MEDIA_ROOT, 'predictions.csv')
            prediction_record = {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'student_id': student_data.get('student_id', ''),
                'prediction': result['prediction'],
                'confidence': result['confidence'] or 0,
            }
            for feature in feature_names:
                prediction_record[feature] = student_data.get(feature, '')

            predictions_df = pd.DataFrame([prediction_record])
            if os.path.exists(predictions_path):
                predictions_df.to_csv(predictions_path, mode='a', header=False, index=False)
            else:
                os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
                predictions_df.to_csv(predictions_path, index=False)

            messages.success(request, 'Prediction complete. The result has been saved.')

            for field in feature_fields:
                field['value'] = student_data.get(field['name'], '')

            student_id_value = student_data.get('student_id', '')
            student_details = [(field['label'], student_data.get(field['name'], '')) for field in feature_fields]

            return render(request, 'ml_engine/predict.html', {
                'prediction': result['prediction'],
                'confidence': result['confidence'],
                'show_result': True,
                'student_data': student_data,
                'feature_fields': feature_fields,
                'student_id_value': student_id_value,
                'student_details': student_details,
            })

        except Exception as e:
            messages.error(request, f'Error making prediction: {str(e)}')

            for field in feature_fields:
                field['value'] = student_data.get(field['name'], '')

            student_id_value = student_data.get('student_id', '')
            student_details = [(field['label'], student_data.get(field['name'], '')) for field in feature_fields]

            return render(request, 'ml_engine/predict.html', {
                'student_data': student_data,
                'feature_fields': feature_fields,
                'student_id_value': student_id_value,
                'student_details': student_details,
            })

    # GET
    for field in feature_fields:
        field['value'] = ''

    student_id_value = ''
    student_details = [(field['label'], '') for field in feature_fields]

    return render(request, 'ml_engine/predict.html', {
        'student_data': {},
        'feature_fields': feature_fields,
        'student_id_value': student_id_value,
        'student_details': student_details,
    })


# ─────────────────────────────────────────────────────────────────────────────
# LIST MODELS
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def list_models(request):
    model_path = os.path.join(settings.MEDIA_ROOT, 'placement_model.pkl')

    models = []
    if os.path.exists(model_path):
        size_kb = round(os.path.getsize(model_path) / 1024, 2)
        trained_at = datetime.fromtimestamp(
            os.path.getmtime(model_path)
        ).strftime('%Y-%m-%d %H:%M:%S')

        try:
            predictor = PlacementPredictor()
            predictor.load_model(model_path)
            feature_count = len(predictor.feature_names or [])
            model_type = predictor.selected_model_name or 'Unknown'
        except Exception:
            feature_count = 'N/A'
            model_type = 'Unknown'

        models.append({
            'name': 'placement_model.pkl',
            'trained_at': trained_at,
            'size_kb': size_kb,
            'feature_count': feature_count,
            'model_type': model_type,
        })

    recent_logs = ActivityLog.objects.filter(
        action='train'
    ).order_by('-id')[:10]

    return render(request, 'ml_engine/models.html', {
        'models': models,
        'recent_logs': recent_logs,
    })


# ─────────────────────────────────────────────────────────────────────────────
# PREDICTION HISTORY
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def prediction_history(request):
    predictions_path = os.path.join(settings.MEDIA_ROOT, 'predictions.csv')

    predictions = []
    columns = []
    error = None

    if os.path.exists(predictions_path):
        try:
            df = pd.read_csv(predictions_path)
            df = df.iloc[::-1].reset_index(drop=True)  # most recent first
            columns = list(df.columns)
            predictions = df.to_dict(orient='records')
        except Exception as e:
            error = f'Could not load prediction history: {str(e)}'
    else:
        error = 'No predictions have been made yet.'

    if request.method == 'POST' and request.POST.get('action') == 'clear_all':
        try:
            if os.path.exists(predictions_path):
                os.remove(predictions_path)
            messages.success(request, 'Prediction history cleared.')
        except Exception as e:
            messages.error(request, f'Could not clear history: {str(e)}')
        return redirect('prediction_history')

    return render(request, 'ml_engine/prediction_history.html', {
        'predictions': predictions,
        'columns': columns,
        'error': error,
        'total': len(predictions),
    })