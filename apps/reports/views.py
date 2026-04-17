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
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

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
        elif report_type == 'individual_student':
            student_id = request.POST.get('student_id')
            return generate_individual_student_report(df, format_type, student_id, request)
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
    
    elif format_type == 'pdf':
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        
        title = Paragraph("Placement Summary Report", styles['Title'])
        story.append(title)
        story.append(Spacer(1, 12))
        
        for key, value in summary.items():
            story.append(Paragraph(f"{key}: {value}", styles['Normal']))
        
        doc.build(story)
        buffer.seek(0)
        
        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="placement_summary_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf"'
        return response
    
    return HttpResponse("Report generated", content_type='text/plain')

def generate_student_report(df, format_type):
    if format_type == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="student_details_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        df.to_csv(path_or_buf=response, index=False)
        return response
    
    elif format_type == 'json':
        return JsonResponse(df.to_dict('records'), safe=False)
    
    elif format_type == 'pdf':
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        
        title = Paragraph("Student Details Report", styles['Title'])
        story.append(title)
        story.append(Spacer(1, 12))
        
        # Add table or list of students
        for _, row in df.iterrows():
            story.append(Paragraph(f"Student ID: {row.get('student_id', 'N/A')}", styles['Heading3']))
            for col in df.columns:
                if col != 'student_id':
                    story.append(Paragraph(f"{col.title()}: {row[col]}", styles['Normal']))
            story.append(Spacer(1, 6))
        
        doc.build(story)
        buffer.seek(0)
        
        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="student_details_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf"'
        return response
    
    return HttpResponse("Student report generated", content_type='text/plain')

def generate_individual_student_report(df, format_type, student_id, request):
    if not student_id:
        return HttpResponse("Student ID is required", status=400)
    
    # Find student in data
    student_data = df[df['student_id'].astype(str) == str(student_id)]
    if student_data.empty:
        return HttpResponse(f"Student with ID {student_id} not found", status=404)
    
    student_info = student_data.iloc[0].to_dict()
    
    # Check for predictions
    predictions_path = os.path.join(settings.MEDIA_ROOT, 'predictions.csv')
    prediction_info = {}
    if os.path.exists(predictions_path):
        pred_df = pd.read_csv(predictions_path)
        student_pred = pred_df[pred_df['student_id'].astype(str) == str(student_id)]
        if not student_pred.empty:
            prediction_info = student_pred.iloc[-1].to_dict()  # Get latest prediction
    
    if format_type == 'pdf':
        return generate_student_pdf_report(student_info, prediction_info)
    elif format_type == 'json':
        return JsonResponse({
            'student_info': student_info,
            'prediction_info': prediction_info
        })
    elif format_type == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="student_{student_id}_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Field', 'Value'])
        for key, value in student_info.items():
            writer.writerow([key, value])
        if prediction_info:
            writer.writerow([])
            writer.writerow(['Prediction Field', 'Value'])
            for key, value in prediction_info.items():
                writer.writerow([key, value])
        return response
    
    return HttpResponse("Individual student report generated", content_type='text/plain')

def generate_student_pdf_report(student_info, prediction_info):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    # Title
    title = Paragraph(f"Student Report - ID: {student_info.get('student_id', 'N/A')}", styles['Title'])
    story.append(title)
    story.append(Spacer(1, 12))
    
    # Student Information
    story.append(Paragraph("Student Information", styles['Heading2']))
    for key, value in student_info.items():
        story.append(Paragraph(f"{key.title()}: {value}", styles['Normal']))
    story.append(Spacer(1, 12))
    
    # Prediction Information
    if prediction_info:
        story.append(Paragraph("Latest Prediction", styles['Heading2']))
        for key, value in prediction_info.items():
            if key != 'student_id':  # Avoid duplicate student_id
                story.append(Paragraph(f"{key.title()}: {value}", styles['Normal']))
    else:
        story.append(Paragraph("No prediction history found for this student.", styles['Normal']))
    
    doc.build(story)
    buffer.seek(0)
    
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="student_{student_info.get("student_id", "unknown")}_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf"'
    return response

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
    
    elif format_type == 'pdf':
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        
        title = Paragraph("Model Performance Report", styles['Title'])
        story.append(title)
        story.append(Spacer(1, 12))
        
        if training_info:
            story.append(Paragraph(f"Algorithm: {training_info.get('algorithm', 'N/A')}", styles['Normal']))
            metrics = training_info.get('metrics', {})
            story.append(Paragraph(f"Accuracy: {metrics.get('accuracy', 'N/A')}", styles['Normal']))
            story.append(Paragraph(f"Precision: {metrics.get('precision', 'N/A')}", styles['Normal']))
            story.append(Paragraph(f"Recall: {metrics.get('recall', 'N/A')}", styles['Normal']))
            story.append(Paragraph(f"F1 Score: {metrics.get('f1_score', 'N/A')}", styles['Normal']))
        else:
            story.append(Paragraph("No training information available.", styles['Normal']))
        
        doc.build(story)
        buffer.seek(0)
        
        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="model_performance_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf"'
        return response
    
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
    elif report_type == 'individual_student':
        student_id = request.GET.get('student_id')
        return generate_individual_student_report(df, format_type, student_id, request)
    elif report_type == 'model_performance':
        return generate_performance_report(format_type, request)
    
    return HttpResponse("Invalid report type", status=400)