from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.conf import settings
import pandas as pd
import os
from datetime import datetime
import io
import csv

@login_required
def generate_report(request):
    data_path = os.path.join(settings.MEDIA_ROOT, 'student_data.csv')
    
    if not os.path.exists(data_path):
        messages.error(request, 'No data found. Please upload data first.')
        return redirect('upload_data')
    
    if request.method == 'POST':
        report_type = request.POST.get('report_type', 'placement_summary')
        format_type = request.POST.get('format', 'csv')
        date_from = request.POST.get('date_from')
        date_to = request.POST.get('date_to')
        
        # Load data
        df = pd.read_csv(data_path)
        
        # Apply date filters if needed
        if date_from and date_to and 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            df = df[(df['date'] >= date_from) & (df['date'] <= date_to)]
        
        # Generate report based on type
        if report_type == 'placement_summary':
            return generate_summary_report(df, format_type, request)
        elif report_type == 'student_details':
            return generate_student_report(df, format_type)
        elif report_type == 'model_performance':
            return generate_performance_report(format_type, request)
        
    # GET request - show report form
    data_path = os.path.join(settings.MEDIA_ROOT, 'student_data.csv')
    df = pd.read_csv(data_path)
    
    context = {
        'data_info': {
            'total_students': len(df),
            'has_placement': 'placement_status' in df.columns,
            'columns': df.columns.tolist()
        }
    }
    return render(request, 'reports/generate.html', context)

def generate_summary_report(df, format_type, request):
    # Calculate summary statistics
    summary = {
        'Report Generated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'Total Students': len(df),
        'Placed Students': len(df[df['placement_status'] == 1]) if 'placement_status' in df.columns else 0,
        'Placement Rate': f"{len(df[df['placement_status'] == 1]) / len(df) * 100:.2f}%" if 'placement_status' in df.columns else "N/A"
    }
    
    if 'cgpa' in df.columns:
        summary['Average CGPA'] = f"{df['cgpa'].mean():.2f}"
        summary['Max CGPA'] = f"{df['cgpa'].max():.2f}"
        summary['Min CGPA'] = f"{df['cgpa'].min():.2f}"
    
    if format_type == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="placement_summary_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Metric', 'Value'])
        for key, value in summary.items():
            writer.writerow([key, value])
        return response
    
    elif format_type == 'json':
        return JsonResponse(summary)
    
    return HttpResponse("Report generated", content_type='text/plain')

def generate_student_report(df, format_type):
    if format_type == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="student_details_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        df.to_csv(path_or_buf=response, index=False)
        return response
    
    return HttpResponse("Student report generated", content_type='text/plain')

def generate_performance_report(format_type, request):
    model_path = os.path.join(settings.MEDIA_ROOT, 'placement_model.pkl')
    training_info = request.session.get('training_info', {})
    
    if not os.path.exists(model_path):
        return HttpResponse("No trained model found", content_type='text/plain')
    
    if format_type == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="model_performance_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Metric', 'Value'])
        
        if training_info:
            writer.writerow(['Algorithm', training_info.get('algorithm', 'N/A')])
            writer.writerow(['Accuracy', training_info.get('metrics', {}).get('accuracy', 'N/A')])
            writer.writerow(['Precision', training_info.get('metrics', {}).get('precision', 'N/A')])
            writer.writerow(['Recall', training_info.get('metrics', {}).get('recall', 'N/A')])
            writer.writerow(['F1 Score', training_info.get('metrics', {}).get('f1_score', 'N/A')])
        
        return response
    
    elif format_type == 'json':
        return JsonResponse(training_info)
    
    return HttpResponse("Performance report generated", content_type='text/plain')

@login_required
def download_report(request):
    """Download report in specified format"""
    report_type = request.GET.get('type', 'placement_summary')
    format_type = request.GET.get('format', 'csv')
    
    data_path = os.path.join(settings.MEDIA_ROOT, 'student_data.csv')
    
    if not os.path.exists(data_path):
        return HttpResponse("No data found", status=404)
    
    df = pd.read_csv(data_path)
    
    if report_type == 'placement_summary':
        return generate_summary_report(df, format_type, request)
    elif report_type == 'student_details':
        return generate_student_report(df, format_type)
    elif report_type == 'model_performance':
        return generate_performance_report(format_type, request)
    
    return HttpResponse("Invalid report type", status=400)