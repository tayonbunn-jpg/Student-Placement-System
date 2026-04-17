# Student Placement Prediction System

A Django-based machine learning application for predicting student placement outcomes using MongoDB as the database backend.

## Features

- User authentication and authorization
- Data upload and preprocessing
- Machine learning model training and prediction
- Interactive dashboard with real-time statistics
- Report generation (PDF/Excel)
- MongoDB integration with SQLite fallback

## Setup Instructions

### 1. Environment Setup

```bash
# Clone the repository
git clone <repository-url>
cd student-placement-prediction-system

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
# source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. MongoDB Setup

#### Option A: MongoDB Atlas (Cloud - Recommended)

1. Create a free account at [MongoDB Atlas](https://www.mongodb.com/atlas)
2. Create a new cluster
3. Go to "Network Access" and whitelist your IP address (or 0.0.0.0/0 for testing)
4. Go to "Database Access" and create a database user
5. Go to "Clusters" > "Connect" > "Connect your application"
6. Copy the connection string

#### Option B: Local MongoDB

1. Install MongoDB locally
2. Start MongoDB service
3. Use default connection: `mongodb://localhost:27017`

### 3. Environment Configuration

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` file with your MongoDB details:
   ```env
   # For MongoDB Atlas:
   MONGODB_URI=mongodb+srv://username:password@cluster0.xxxxx.mongodb.net/placement_system?retryWrites=true&w=majority
   MONGODB_DATABASE=placement_system
   MONGODB_USERNAME=your_username
   MONGODB_PASSWORD=your_password

   # For local MongoDB:
   MONGODB_URI=mongodb://localhost:27017/placement_system
   MONGODB_DATABASE=placement_system
   MONGODB_USERNAME=
   MONGODB_PASSWORD=

   # Django settings
   SECRET_KEY=your-secret-key-here
   DEBUG=True
   ALLOWED_HOSTS=127.0.0.1,localhost
   ```

### 4. Database Migration

```bash
# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

### 5. Run the Application

```bash
# Start development server
python manage.py runserver

# Access the application at http://127.0.0.1:8000/
```

## Database Configuration

The application is configured to:
1. First attempt to connect to MongoDB using the provided connection string
2. Automatically fall back to SQLite if MongoDB is unavailable
3. Display connection status in the console during startup

## Project Structure

```
placement_system/
├── apps/
│   ├── authentication/    # User authentication
│   ├── dashboard/         # Main dashboard and statistics
│   ├── data_uploads/      # File upload and preprocessing
│   ├── ml_engine/         # ML model training and prediction
│   └── reports/           # Report generation
├── templates/             # HTML templates
├── static/                # Static files
├── media/                 # Uploaded files
├── placement_system/      # Django settings
└── requirements.txt       # Python dependencies
```

## API Endpoints

- `/` - Home/Dashboard
- `/dashboard/` - Main dashboard
- `/upload/` - Data upload
- `/ml/train/` - Model training
- `/ml/predict/` - Prediction interface
- `/reports/` - Report generation
- `/admin/` - Django admin panel

## Technologies Used

- **Backend**: Django 4.2, Python 3.11
- **Database**: MongoDB (with Djongo), SQLite fallback
- **Frontend**: Bootstrap 5, Chart.js, jQuery
- **ML**: Scikit-learn, XGBoost, Pandas, NumPy
- **Reports**: ReportLab, OpenPyXL

## Development

### Running Tests

```bash
python manage.py test
```

### Code Formatting

```bash
# Install black and isort
pip install black isort

# Format code
black .
isort .
```

## Deployment

### Environment Variables for Production

```env
DEBUG=False
SECRET_KEY=your-production-secret-key
ALLOWED_HOSTS=your-domain.com,www.your-domain.com
MONGODB_URI=your-production-mongodb-uri
```

### Using Gunicorn

```bash
pip install gunicorn
gunicorn placement_system.wsgi:application --bind 0.0.0.0:8000
```

## Troubleshooting

### MongoDB Connection Issues

1. Verify your MongoDB Atlas IP whitelist
2. Check your connection string format
3. Ensure database user has proper permissions
4. The application will automatically fall back to SQLite if MongoDB fails

### Common Errors

- **ServerSelectionTimeoutError**: Check MongoDB connection string and network access
- **Authentication failed**: Verify username/password in connection string
- **No module named 'djongo'**: Run `pip install -r requirements.txt`

## License

This project is licensed under the MIT License.