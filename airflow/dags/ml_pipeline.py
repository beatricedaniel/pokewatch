"""
PokeWatch ML Pipeline DAG

Orchestrates the complete machine learning pipeline using KubernetesPodOperator:
1. Run Full Pipeline: Collect → Preprocess → Train (all in one pod to share data)
2. Reload Model: Trigger API to reload the new model

Schedule: Daily at 2 AM UTC
Architecture: Single pod for data pipeline, separate pod for API reload

Note: Data collection, preprocessing, and training run in a single pod because
KubernetesPodOperator pods are ephemeral - data doesn't persist between pods.
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

# Single image for all tasks
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

    # Task 1: Full ML Pipeline (Collect → Preprocess → Train)
    # Runs all steps in a single pod to share data between steps
    run_pipeline = KubernetesPodOperator(
        task_id='run_pipeline',
        name='ml-pipeline',
        namespace='pokewatch',
        image=POKEWATCH_IMAGE,
        cmds=['bash', '-c'],
        arguments=[
            '''
            set -e
            echo "=== Step 1: Data Collection ==="
            python -m pokewatch.data.collectors.daily_price_collector --days 7 --format parquet

            echo "=== Step 2: Feature Engineering ==="
            python -m pokewatch.data.preprocessing.make_features

            echo "=== Step 3: Model Training ==="
            python -m pokewatch.models.train_baseline

            echo "=== Pipeline Complete ==="
            '''
        ],
        env_from=env_from_secrets,
        is_delete_operator_pod=True,
        get_logs=True,
        log_events_on_failure=True,
        startup_timeout_seconds=300,
        doc_md="""
        ### Full ML Pipeline Task

        Runs the complete ML pipeline in a single pod:
        1. **Data Collection**: Fetches Pokemon card prices from API (7 days history)
        2. **Preprocessing**: Feature engineering and data transformation
        3. **Model Training**: Trains baseline model and logs to MLflow/DagsHub

        All steps run in one pod to share data between stages.
        Pod is deleted after completion.
        """,
    )

    # Task 2: Reload Model in API
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

    # Define task dependencies
    run_pipeline >> reload_model
