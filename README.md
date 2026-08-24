# Banking Customer Behaviour Shift Detection
# Using Cross-Attribute Activity Deviations

Final-year major project: an AI/ML banking customer intelligence system.

This application uses **synthetic demo data only**. It does not store real account numbers, PINs, CVVs, card numbers, or real customer banking information.

## Features

1. Analyze customer, transaction, engagement, and branch data  
2. Individual behavioural profiles from 12 months of history  
3. Behaviour-shift detection using cross-attribute activity deviations  
4. Isolation Forest anomaly detection  
5. Behaviour Shift Score (0–100)  
6. Shift classes: Normal, Mild, Significant, Critical  
7. XGBoost churn probability  
8. Comparison with Logistic Regression and Random Forest  
9–10. SHAP explanations for individual and global churn drivers  
11–12. Future customer value and high-value customers at risk  
13. K-Means segmentation  
14–16. Branch analytics, high-shift branches, and customer value at risk  
17–18. Personalized retention strategies and risk alerts  
19–20. AI banking assistant and interactive dashboard  
21–23. CSV upload/validation, built-in demo data, and model evaluation  
24. Churn, behaviour, value, branch, high-risk, retention, and model reports  

## Technology stack

- Frontend: HTML5, CSS3, JavaScript, Bootstrap 5, Chart.js  
- Backend: Python Flask  
- Database: SQLite (`database/banking.db`) — open with DB Browser for SQLite  
- ML: Pandas, NumPy, Scikit-learn, XGBoost, Isolation Forest, K-Means, SHAP, Joblib  

## Run on Windows (VS Code)

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m scripts.initialize
python app.py
```

Then open http://127.0.0.1:5000

Default administrator login:

- Username: `admin`
- Password: `Admin@123`

Initialization creates the SQLite database, generates the synthetic dataset, trains models, and writes scores. It can take several minutes.

## Project structure

```
app.py
config.py
database/          schema.sql, db helpers, banking.db
ml/                data generator, behaviour shift, features, training, retention
routes/            Flask blueprints
services/          analytics, assistant, reports, dataset validation
templates/         HTML pages
static/            CSS and Chart.js dashboards
dataset/           exported CSV demo files
models/            saved Joblib models and metrics.json
uploads/           user CSV uploads
scripts/initialize.py
```

## Dataset

Default synthetic scale:

- 6,500 customers  
- 80 branches  
- 12 months of behaviour  
- 130,000 transactions  

CSV templates are written to `dataset/` after initialization. Upload replacement files from **Dataset**.

## Models

- Churn: XGBoost Classifier (primary), compared with Logistic Regression and Random Forest  
- Anomaly: Isolation Forest  
- Future value: XGBoost Regressor  
- Segmentation: K-Means (k=5)  
- Explainability: SHAP TreeExplainer  

Metrics: accuracy, precision, recall, F1, ROC-AUC, PR-AUC, confusion matrix, MAE, RMSE, R², silhouette score.
