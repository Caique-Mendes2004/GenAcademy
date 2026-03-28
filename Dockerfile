FROM python:3.9-slim

RUN pip install mlflow==2.6.0 psycopg2-binary boto3 pymysql

RUN mkdir -p /mlflow

WORKDIR /mlflow

RUN echo '#!/bin/bash \n\
python -c "import boto3; \
import os; \
s3 = boto3.client(\"s3\", \
endpoint_url=os.environ.get(\"MLFLOW_S3_ENDPOINT_URL\"), \
aws_access_key_id=os.environ.get(\"AWS_ACCESS_KEY_ID\"), \
aws_secret_access_key=os.environ.get(\"AWS_SECRET_ACCESS_KEY\")); \
bucket = os.environ.get(\"BUCKET_NAME\"); \
try: \
    s3.create_bucket(Bucket=bucket); \
    print(\"Bucket criado com sucesso!\"); \
except Exception as e: \
    if \"BucketAlreadyOwnedByYou\" in str(e): \
        print(\"Bucket já existe.\"); \
    else: \
        print(f\"Erro: {e}\"); \
" \n\
\n\
mlflow server \
--backend-store-uri $MLFLOW_TRACKING_URI \
--default-artifact-root s3://$BUCKET_NAME/ \
--host 0.0.0.0 \
--port 3000 > \
' > /mlflow/start_mlflow.sh

RUN chmod +x /mlflow/start_mlflow.sh

EXPOSE 3000

CMD ["/bin/bash", "/mlflow/start_mlflow.sh"]