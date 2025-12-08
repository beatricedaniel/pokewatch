"""
PokeWatch ML Pipeline DAG

Orchestrates the complete machine learning pipeline using KubernetesPodOperator:
1. Data Collection: Fetch Pokemon card prices from API
2. Preprocessing: Feature engineering and data transformation
3. Model Training: Train baseline model and log to MLflow
4. Model Reload: Trigger API to reload the new model

Schedule: Daily at 2 AM UTC
Architecture: Same Docker image, different commands per task

IMPORTANT: Replace DOCKERHUB_USER with your actual Docker Hub username
"""
from datetime import timedelta
from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator
from airflow.utils.dates import days_ago
from kubernetes.client import models as k8s

# Default arguments for all tasks
default_args = {
    'owner': 'pokewatch',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

# Load secrets from Kubernetes secret (created on VM)
env_from_secrets = [
    k8s.V1EnvFromSource(
        secret_ref=k8s.V1SecretEnvSource(name='pokewatch-secrets')
    )
]

# Single image for all tasks - replace DOCKERHUB_USER with your username
POKEWATCH_IMAGE = "beatricedaniel/pokewatch:latest"

# Define DAG
with DAG(
    dag_id='pokewatch_ml_pipeline',
    description='PokeWatch ML Pipeline: Collect → Preprocess → Train → Reload',
    tags=['pokewatch', 'ml', 'production'],
    schedule_interval='0 2 * * *',  # Daily at 2 AM UTC
    start_date=days_ago(1),
    catchup=False,
    default_args=default_args,
    doc_md=__doc__,
) as dag:

    # Task 1: Data Collection
    collect_data = KubernetesPodOperator(
        task_id='collect_data',
        name='collect-data',
        namespace='pokewatch',
        image=POKEWATCH_IMAGE,
        cmds=['python', '-m', 'pokewatch.data.collectors.daily_price_collector'],
        arguments=['--days', '7', '--format', 'parquet'],
        env_from=env_from_secrets,
        is_delete_operator_pod=True,
        get_logs=True,
        log_events_on_failure=True,
        doc_md="""
        ### Data Collection Task

        Fetches Pokemon card prices from the Pokemon Price Tracker API.
        - Runs in isolated pod with pokewatch image
        - Collects 7 days of price history
        - Saves raw data to Parquet format
        - Pod is deleted after completion
        """,
    )

    # Task 2: Preprocessing
    preprocess_data = KubernetesPodOperator(
        task_id='preprocess_data',
        name='preprocess-data',
        namespace='pokewatch',
        image=POKEWATCH_IMAGE,
        cmds=['python', '-m', 'pokewatch.data.preprocessing.make_features'],
        env_from=env_from_secrets,
        is_delete_operator_pod=True,
        get_logs=True,
        log_events_on_failure=True,
        doc_md="""
        ### Preprocessing Task

        Performs feature engineering on raw price data.
        - Reads data from previous task
        - Applies feature transformations
        - Outputs processed features
        """,
    )

    # Task 3: Model Training
    train_model = KubernetesPodOperator(
        task_id='train_model',
        name='train-model',
        namespace='pokewatch',
        image=POKEWATCH_IMAGE,
        cmds=['python', '-m', 'pokewatch.models.train_baseline'],
        env_from=env_from_secrets,
        is_delete_operator_pod=True,
        get_logs=True,
        log_events_on_failure=True,
        doc_md="""
        ### Model Training Task

        Trains the baseline fair price prediction model.
        - Trains baseline model (moving average)
        - Logs experiment to MLflow on DagsHub
        - Registers model in MLflow registry
        """,
    )

    # Task 4: Reload Model in API
    reload_model = KubernetesPodOperator(
        task_id='reload_model',
        name='reload-model',
        namespace='pokewatch',
        image='curlimages/curl:latest',
        cmds=[
            'curl',
            '-X', 'POST',
            '-f',  # Fail on HTTP errors
            '-s',  # Silent
            '-w', '\\nHTTP Status: %{http_code}\\n',
            'http://pokewatch-api.pokewatch.svc.cluster.local:8000/reload'
        ],
        is_delete_operator_pod=True,
        get_logs=True,
        log_events_on_failure=True,
        doc_md="""
        ### Model Reload Task

        Triggers the API to reload the latest model from MLflow.
        - Uses lightweight curl image
        - Calls /reload endpoint on the API service
        - API reloads model without restart
        """,
    )

    # Define task dependencies (sequential pipeline)
    collect_data >> preprocess_data >> train_model >> reload_model
