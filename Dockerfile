FROM python:3.9-slim

# Define a pasta de trabalho
WORKDIR /app

# Instala todas as dependências do MLflow e da nossa Sprint 3 (Silver/Gold)
RUN pip install mlflow boto3 psycopg2-binary pandas pyarrow fastparquet pymysql

# Expõe a porta do painel
EXPOSE 3000

# Comando limpo e direto para iniciar o servidor, sem depender de scripts .sh externos
CMD mlflow server \
    --host 0.0.0.0 \
    --port 3000 \
    --backend-store-uri $MLFLOW_TRACKING_URI \
    --default-artifact-root s3://$BUCKET_NAME/