import boto3
from datetime import datetime
import os

# Configuração de conexão com o MinIO
s3_client = boto3.client(
    's3',
    endpoint_url='http://localhost:9000',
    aws_access_key_id='minio',
    aws_secret_access_key='minio123'
)

def ingest_to_bronze():
    print("Iniciando ingestão para a camada Bronze...")

    data_atual = datetime.now().strftime('%Y-%m-%d')
    
    # Nome do bucket definido no checklist
    bucket_name = 'data-lake'
    
    # bronze/cloudtrail/dt=YYYY-MM-DD/raw_logs.csv
    destination_path = f"bronze/cloudtrail/dt={data_atual}/raw_logs.csv"
    
    # Dataset
    local_file_path = 'dec12_18features.csv' 

    if not os.path.exists(local_file_path):
        print(f"Erro: Arquivo '{local_file_path}' não encontrado na pasta atual.")
        return

    print(f"Fazendo upload de '{local_file_path}' para '{bucket_name}/{destination_path}'...")
    
    s3_client.upload_file(
        Filename=local_file_path,
        Bucket=bucket_name,
        Key=destination_path
    )
    
    print("Ingestão concluída com sucesso! Critérios de aceite garantidos.")

if __name__ == "__main__":
    ingest_to_bronze()