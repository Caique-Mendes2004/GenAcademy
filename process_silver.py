import boto3
import pandas as pd
import io
import hashlib
from datetime import datetime

# Configuração de conexão com o MinIO
s3_client = boto3.client(
    's3',
    endpoint_url='http://minio:9000',
    aws_access_key_id='minio',
    aws_secret_access_key='minio123'
)

def hash_user_id(valor):
    # Aplica um hash SHA-256 no ID do usuário (LGPD)
    if pd.isna(valor): return None
    return hashlib.sha256(str(valor).encode('utf-8')).hexdigest()

def mask_ip(ip):
    # Mascara os últimos octetos do IP (LGPD)
    if pd.isna(ip): return None
    partes = str(ip).split('.')
    if len(partes) == 4:
        return f"{partes[0]}.{partes[1]}.***.***"
    return "***" # Fallback para IPv6 ou formatos inesperados

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
    
    # Padronizar nomes de colunas para lowercase
    df_limpo.columns = [col.strip().lower() for col in df_limpo.columns]

    # Removendo nulos críticos (assumindo nomes padrão do CloudTrail em minúsculo)
    colunas_base = ['eventtime', 'eventname']
    df_limpo = df_limpo.dropna(subset=[c for c in colunas_base if c in df_limpo.columns])

    # Tipagem e mapeamento
    if 'eventtime' in df_limpo.columns:
        df_limpo['eventtime'] = pd.to_datetime(df_limpo['eventtime'], errors='coerce')
        df_limpo = df_limpo.dropna(subset=['eventtime']) # Remove falhas de conversão

    # Aplicar LGPD: Hash no userId e mascarar IPs
    col_user = 'useridentity_accountid' if 'useridentity_accountid' in df_limpo.columns else 'useridentity'
    if col_user in df_limpo.columns:
        df_limpo['user_hash'] = df_limpo[col_user].apply(hash_user_id)
    else:
        df_limpo['user_hash'] = 'unknown'

    # Mascaramento de IP
    if 'sourceipaddress' in df_limpo.columns:
        df_limpo['masked_ip'] = df_limpo['sourceipaddress'].apply(mask_ip)

    # Enriquecimento - Features Temporais para ML
    df_limpo['timestamp'] = df_limpo['eventtime']
    df_limpo['hour'] = df_limpo['timestamp'].dt.hour
    df_limpo['day_of_week'] = df_limpo['timestamp'].dt.dayofweek
    df_limpo['is_weekend'] = df_limpo['day_of_week'].apply(lambda x: 1 if x >= 5 else 0)
    # Garantindo a criação das colunas padronizadas caso os nomes originais variem
    df_limpo['event'] = df_limpo['eventname'] if 'eventname' in df_limpo.columns else 'unknown'
    df_limpo['resource'] = df_limpo['resources'] if 'resources' in df_limpo.columns else 'unknown'

    colunas_finais = ['timestamp', 'user_hash', 'event', 'resource', 'hour', 'day_of_week', 'is_weekend']
    df_limpo = df_limpo[colunas_finais]


    linhas_finais = len(df_limpo)
    print(f"Limpeza concluída. De {linhas_originais} para {linhas_finais} linhas.")

    # Salva em formato Parquet na camada Silver
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