from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.http import JsonResponse
import pandas as pd
import numpy as np
import os
import json
from datetime import datetime
from apps.authentication.models import ActivityLog
from .ml_models import PlacementPredictor

FIELD_LABELS = {
    'cgpa': 'CGPA (0-10)',
    'skills': 'Clinical Skills Score',
    'internships': 'Internship Experience (months)',
    'projects': 'Number of Clinical Projects',
    'communication': 'Communication Score',
}

def parse_numeric_input(value, default=0.0):
    if value is None:
        return default
    value = str(value).strip()
    if value == '':
        return default
    try:
        return float(value)
    except ValueError:
        if ',' in value:
            items = [item.strip() for item in value.split(',') if item.strip()]
            return float(len(items))
        return default

@login_required
def train_model(request):
    data_path = os.path.join(settings.MEDIA_ROOT, 'student_data.csv')
    
    if not os.path.exists(data_path):
        messages.error(request, 'No data found. Please upload data first.')
        return redirect('upload_data')
    
    df = pd.read_csv(data_path)
    
    if 'placement_status' not in df.columns:
        messages.error(request, 'Data must contain "placement_status" column for training.')
        return redirect('upload_data')
    
    if request.method == 'POST':
        algorithm = request.POST.get('algorithm', 'random_forest')
        test_size = float(request.POST.get('test_size', 0.2))
        
        try:
            # Initialize predictor
            predictor = PlacementPredictor()
            
            # Train the model
            metrics, probabilities = predictor.train_model(df, algorithm)
            
            # Save model
            model_path = os.path.join(settings.MEDIA_ROOT, 'placement_model.pkl')
            predictor.save_model(model_path)
            
            # Store training info
            training_info = {
                'algorithm': algorithm,
                'test_size': test_size,
                'metrics': metrics,
                'total_samples': len(df),
                'features': predictor.feature_names
            }
            request.session['training_info'] = training_info
            
            ActivityLog.objects.create(
                user=request.user,
                action='train_model',
                description=f'Trained model using {algorithm}',
                metadata={
                    'algorithm': algorithm,
                    'total_samples': len(df),
                    'metrics': metrics
                }
            )
            
            # Calculate feature importance if available
            if hasattr(predictor.current_model, 'feature_importances_'):
                feature_importance = dict(zip(predictor.feature_names, 
                                             predictor.current_model.feature_importances_.tolist()))
                request.session['feature_importance'] = feature_importance
            
            messages.success(request, f'🎉 Model trained successfully! Accuracy: {metrics["accuracy"]:.2%}')
            return redirect('predict')
            
        except Exception as e:
            messages.error(request, f'Error training model: {str(e)}')
            return redirect('train_model')
    
    # GET request - show training page
    training_info = request.session.get('training_info', None)
    
    context = {
        'data_info': {
            'total_samples': len(df),
            'features': [col for col in df.columns if col != 'placement_status'],
            'target': 'placement_status',
            'class_distribution': df['placement_status'].value_counts().to_dict()
        },
        'training_info': training_info
    }
    return render(request, 'ml_engine/train.html', context)

@login_required
def make_prediction(request):
    model_path = os.path.join(settings.MEDIA_ROOT, 'placement_model.pkl')
    
    if not os.path.exists(model_path):
        messages.error(request, 'No trained model found. Please train a model first.')
        return redirect('train_model')
    
    predictor = PlacementPredictor()
    predictor.load_model(model_path)
    
    feature_names = predictor.feature_names or []
    field_labels = {name: FIELD_LABELS.get(name, name.replace('_', ' ').title()) for name in feature_names}
    feature_fields = [{'name': name, 'label': field_labels[name]} for name in feature_names]

    if request.method == 'POST':
        # Get student data from form, using the model's trained feature set
        student_data = {}
        for feature in feature_names:
            student_data[feature] = parse_numeric_input(request.POST.get(feature, ''))

        if 'student_id' in request.POST:
            student_data['student_id'] = request.POST.get('student_id', '')

        # Create DataFrame
        df = pd.DataFrame([student_data])

        # Predict
        try:
            predictions = predictor.predict(df)
            prediction = predictions[0]

            ActivityLog.objects.create(
                user=request.user,
                action='predict',
                description=f'Predicted placement for student {student_data.get("student_id", "unknown")}',
                metadata={
                    'student_data': student_data,
                    'prediction': prediction
                }
            )

            # Save prediction record for later review
            predictions_path = os.path.join(settings.MEDIA_ROOT, 'predictions.csv')
            prediction_record = {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'student_id': student_data.get('student_id', ''),
                'prediction': prediction.get('prediction', ''),
                'confidence': prediction.get('confidence', 0)
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
            # Add values to feature_fields
            for field in feature_fields:
                field['value'] = student_data.get(field['name'], '')
            student_id_value = student_data.get('student_id', '')
            student_details = [(field['label'], student_data.get(field['name'], '')) for field in feature_fields]
            context = {
                'prediction': prediction,
                'show_result': True,
                'student_data': student_data,
                'feature_fields': feature_fields,
                'student_id_value': student_id_value,
                'student_details': student_details
            }
            return render(request, 'ml_engine/predict.html', context)
        except Exception as e:
            messages.error(request, f'Error making prediction: {str(e)}')
            # Add values to feature_fields
            for field in feature_fields:
                field['value'] = student_data.get(field['name'], '')
            student_id_value = student_data.get('student_id', '')
            student_details = [(field['label'], student_data.get(field['name'], '')) for field in feature_fields]
            return render(request, 'ml_engine/predict.html', {
                'student_data': student_data,
                'feature_fields': feature_fields,
                'student_id_value': student_id_value,
                'student_details': student_details
            })

    # GET request - show prediction form
    # Add empty values
    for field in feature_fields:
        field['value'] = ''
    student_id_value = ''
    student_details = [(field['label'], '') for field in feature_fields]
    return render(request, 'ml_engine/predict.html', {
        'student_data': {},
        'feature_fields': feature_fields,
        'student_id_value': student_id_value,
        'student_details': student_details
    })

@login_required
def prediction_history(request):
    predictions_path = os.path.join(settings.MEDIA_ROOT, 'predictions.csv')
    predictions = []
    if os.path.exists(predictions_path):
        try:
            predictions_df = pd.read_csv(predictions_path)
            if 'timestamp' in predictions_df.columns:
                predictions_df = predictions_df.sort_values('timestamp', ascending=False)
            predictions = predictions_df.to_dict('records')
        except Exception as e:
            messages.error(request, f'Unable to load prediction history: {str(e)}')

    context = {
        'predictions': predictions,
        'has_predictions': len(predictions) > 0
    }
    return render(request, 'ml_engine/prediction_history.html', context)

@login_required
def list_models(request):
    """List all trained models"""
    model_path = os.path.join(settings.MEDIA_ROOT, 'placement_model.pkl')
    training_info = request.session.get('training_info', None)
    
    context = {
        'has_model': os.path.exists(model_path),
        'training_info': training_info,
        'feature_importance': request.session.get('feature_importance', None)
    }
    return render(request, 'ml_engine/models.html', context)