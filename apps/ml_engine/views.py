from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.http import JsonResponse
import pandas as pd
import os
import json
from apps.authentication.models import ActivityLog
from .ml_models import PlacementPredictor

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
    
    if request.method == 'POST':
        # Get student data from form
        student_data = {}
        
        # Required fields
        if 'cgpa' in request.POST:
            student_data['cgpa'] = float(request.POST.get('cgpa', 0))
        
        if 'skills' in request.POST:
            student_data['skills'] = request.POST.get('skills', '')
        
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
                    'prediction': str(prediction)
                }
            )
            
            context = {
                'prediction': prediction,
                'show_result': True,
                'student_data': student_data
            }
            return render(request, 'ml_engine/predict.html', context)
        except Exception as e:
            messages.error(request, f'Error making prediction: {str(e)}')
            return render(request, 'ml_engine/predict.html')
    
    # GET request - show prediction form
    return render(request, 'ml_engine/predict.html')

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