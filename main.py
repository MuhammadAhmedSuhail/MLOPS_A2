from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
from datetime import timedelta
import requests
from bs4 import BeautifulSoup
import pandas as pd
import os

# Default arguments for DAG
default_args = {
    'owner': 'user',
    'depends_on_past': False,
    'start_date': days_ago(1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# Scrape data from websites
def scraper():
    urls = ['https://www.dawn.com/', 'https://www.bbc.com/']
    collected_data = []
    for url in urls:
        res = requests.get(url)
        soup = BeautifulSoup(res.text, 'html.parser')
        elements = soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        items = [(elem.name, elem.get_text(strip=True)) for elem in elements]
        collected_data.extend(items)
    return collected_data

# Clean and format data
def transform_data(ti):
    raw_data = ti.xcom_pull(task_ids='extract_task')
    df = pd.DataFrame(raw_data, columns=['HTML_Tag', 'Text'])
    df['Text'] = df['Text'].replace(r'\n|\r', ' ', regex=True).str.strip()
    df.to_csv('processed_data.csv', index=False)

# Store data with version control
def save_data():
    local_csv = 'processed_data.csv'
    dvc_repo = 'dvc_storage'
    dvc_data_path = os.path.join(dvc_repo, 'data')
    os.makedirs(dvc_data_path, exist_ok=True)
    final_path = os.path.join(dvc_data_path, local_csv)
    os.rename(local_csv, final_path)
    os.chdir(dvc_repo)
    os.system('dvc add ' + final_path)
    os.system('dvc commit')
    os.system('dvc push')

# Define the DAG
with DAG(
    'automated_data_pipeline',
    default_args=default_args,
    description='DAG to handle data scraping, processing, and versioning',
    schedule_interval=timedelta(days=1),
) as dag:

    extract_task = PythonOperator(
        task_id='extract_task',
        python_callable=scraper,
    )

    transform_task = PythonOperator(
        task_id='transform_task',
        python_callable=transform_data,
    )

    storage_task = PythonOperator(
        task_id='store_data',
        python_callable=save_data,
    )

    extract_task >> transform_task >> storage_task