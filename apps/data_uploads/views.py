import pandas as pd
import os
import json
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.http import JsonResponse
from apps.authentication.models import ActivityLog

@login_required
def upload_data(request):
    if request.method == 'POST':
        if 'file' not in request.FILES:
            messages.error(request, 'Please select a file to upload.')
            return redirect('upload_data')

        file = request.FILES['file']

        if file.name.endswith('.csv'):
            try:
                df = pd.read_csv(file)
            except Exception as e:
                messages.error(request, f'Error reading CSV file: {str(e)}')
                return redirect('upload_data')
        elif file.name.endswith(('.xlsx', '.xls')):
            try:
                df = pd.read_excel(file)
            except Exception as e:
                messages.error(request, f'Error reading Excel file: {str(e)}')
                return redirect('upload_data')
        else:
            messages.error(request, 'Please upload CSV or Excel file only.')
            return redirect('upload_data')

        os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
        data_path = os.path.join(settings.MEDIA_ROOT, 'student_data.csv')
        df.to_csv(data_path, index=False)

        ActivityLog.objects.create(
            user=request.user,
            action='upload_data',
            description=f'Uploaded student data file {file.name}',
            metadata={
                'file_name': file.name,
                'total_rows': len(df),
                'columns': df.columns.tolist(),
                'has_target': 'placement_status' in df.columns
            }
        )

        data_info = {
            'total_rows': len(df),
            'columns': df.columns.tolist(),
            'column_types': df.dtypes.astype(str).to_dict(),
            'has_target': 'placement_status' in df.columns
        }
        request.session['data_info'] = data_info
        request.session['preview_data'] = df.head(10).to_dict('records')

        messages.success(request, f'Data uploaded successfully! {len(df)} records loaded.')
        return redirect('list_models')

    data_info = request.session.get('data_info', None)
    preview_data = request.session.get('preview_data', None)

    return render(request, 'data_upload/upload.html', {
        'data_info': data_info,
        'preview_data': preview_data
    })


@login_required
def preprocess_data(request):
    data_path = os.path.join(settings.MEDIA_ROOT, 'student_data.csv')

    if not os.path.exists(data_path):
        messages.error(request, 'No data found. Please upload data first.')
        return redirect('upload_data')

    df = pd.read_csv(data_path)

    if request.method == 'POST':
        handle_missing = request.POST.get('handle_missing', 'drop')
        scaling = request.POST.get('scaling', 'none')
        encoding = request.POST.get('encoding', 'label')

        preprocessing_steps = []

        if handle_missing == 'drop':
            before = len(df)
            df = df.dropna()
            after = len(df)
            if before != after:
                preprocessing_steps.append(f'Dropped {before - after} rows with missing values')
        elif handle_missing == 'mean':
            numeric_cols = df.select_dtypes(include=['number']).columns
            for col in numeric_cols:
                if df[col].isnull().any():
                    df[col] = df[col].fillna(df[col].mean())
                    preprocessing_steps.append(f'Filled missing values in {col} with mean')

        if encoding != 'none':
            categorical_cols = df.select_dtypes(include=['object']).columns
            if 'placement_status' in categorical_cols:
                categorical_cols = [c for c in categorical_cols if c != 'placement_status']
            for col in categorical_cols:
                if encoding == 'label':
                    from sklearn.preprocessing import LabelEncoder
                    le = LabelEncoder()
                    df[col] = le.fit_transform(df[col].astype(str))
                    preprocessing_steps.append(f'Label encoded: {col}')
                elif encoding == 'onehot':
                    df = pd.get_dummies(df, columns=[col], prefix=col)
                    preprocessing_steps.append(f'One-hot encoded: {col}')

        if scaling != 'none':
            numeric_cols = df.select_dtypes(include=['number']).columns
            if 'placement_status' in numeric_cols:
                numeric_cols = [c for c in numeric_cols if c != 'placement_status']
            from sklearn.preprocessing import StandardScaler, MinMaxScaler
            if scaling == 'standard':
                scaler = StandardScaler()
                df[numeric_cols] = scaler.fit_transform(df[numeric_cols])
                preprocessing_steps.append('Applied Standard Scaling to numeric features')
            elif scaling == 'minmax':
                scaler = MinMaxScaler()
                df[numeric_cols] = scaler.fit_transform(df[numeric_cols])
                preprocessing_steps.append('Applied Min-Max Scaling to numeric features')

        df.to_csv(data_path, index=False)

        request.session['preprocessing_steps'] = preprocessing_steps
        request.session['preprocessed_data_info'] = {
            'total_rows': len(df),
            'columns': df.columns.tolist(),
            'has_target': 'placement_status' in df.columns
        }

        messages.success(request, 'Data preprocessing completed! ' + ' | '.join(preprocessing_steps))
        return redirect('list_models')

    context = {
        'df_info': {
            'rows': len(df),
            'columns': len(df.columns),
            'column_names': df.columns.tolist(),
            'missing_values': df.isnull().sum().to_dict(),
            'missing_percentage': (df.isnull().sum() / len(df) * 100).to_dict(),
            'numeric_cols': df.select_dtypes(include=['number']).columns.tolist(),
            'categorical_cols': df.select_dtypes(include=['object']).columns.tolist(),
            'sample_data': df.head(10).to_dict('records')
        }
    }
    return render(request, 'data_upload/preprocess.html', context)