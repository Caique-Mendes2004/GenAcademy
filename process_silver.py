import boto3
import pandas as pd
import io
from datetime import datetime

# Configuração de conexão com o MinIO
s3_client = boto3.client(
    's3',
    endpoint_url='http://minio:9000', # Nome do serviço na rede Docker
    aws_access_key_id='minio',
    aws_secret_access_key='minio123'
)

def process_bronze_to_silver():
    print("Iniciando pipeline: Bronze -> Silver...")

    
    data_atual = datetime.now().strftime('%Y-%m-%d')
    bucket_name = 'data-lake'
    
    # Novos caminhos particionados
    source_key = f"bronze/cloudtrail/dt={data_atual}/raw_logs.csv"
    destination_key = f"silver/cloudtrail/dt={data_atual}/cleaned_logs.parquet"

    # 1. Lendo o CSV bruto particionado
    print(f"Buscando arquivo em '{bucket_name}/{source_key}'...")
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=source_key)
        df = pd.read_csv(response['Body'])
    except Exception as e:
        print(f"Erro ao buscar o arquivo na Bronze. Verifique se a ingestão rodou hoje. Detalhes: {e}")
        return
    
    linhas_originais = len(df)

    # 2. Transformação: Limpeza e Estruturação
    print("Limpando e processando os dados...")
    
    # Remover linhas totalmente duplicadas
    df_limpo = df.drop_duplicates()
    
    #  Se  quiserlimpar as colunas, pode adicionar as regras aqui.
    # Exemplo: df_limpo = df_limpo.dropna(subset=['sourceIPAddress', 'eventName'])

    linhas_finais = len(df_limpo)
    print(f"Limpeza concluída. De {linhas_originais} para {linhas_finais} linhas.")

    #Salva em formato Parquet na camada Silver
    print(f"Convertendo para Parquet e enviando para '{bucket_name}/{destination_key}'...")
    buffer = io.BytesIO()
    

    df_limpo.to_parquet(buffer, index=False, engine='pyarrow')
    buffer.seek(0)

    s3_client.put_object(
        Bucket=bucket_name,
        Key=destination_key,
        Body=buffer.getvalue()
    )
    
    print("Pipeline concluído com sucesso! Os dados tratados estão na camada Silver.")

if __name__ == "__main__":
    process_bronze_to_silver()