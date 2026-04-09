# =============================================================
# CAMADA GOLD RESUMIDA — COST / PERFORMANCE / SECURITY
# =============================================================

import io
from typing import Optional, List
from datetime import datetime

import boto3
import numpy as np
import pandas as pd
from botocore.exceptions import ClientError

# ── Configurações Blindadas ──────────────────────────────────
S3_ENDPOINT_URL = "http://minio:9000"
AWS_ACCESS_KEY_ID = "minio"
AWS_SECRET_ACCESS_KEY = "minio123"
BUCKET_NAME = "data-lake" 

UNIT_COST = 0.000004
DOMAINS = ["cost", "performance", "security"]

# ── Cliente MinIO ────────────────────────────────────────────
def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=S3_ENDPOINT_URL,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name="us-east-1",
    )

s3_client = get_s3_client()

# ── Utilidades de bucket / diretórios ───────────────────────
def ensure_bucket_exists(bucket_name: str) -> None:
    try:
        s3_client.head_bucket(Bucket=bucket_name)
    except ClientError:
        print(f"Bucket '{bucket_name}' não encontrado. Criando...")
        s3_client.create_bucket(Bucket=bucket_name)

# ── IO (Em Memória) ──────────────────────────────────────────
def upload_buffer_to_minio(buffer: io.BytesIO, object_key: str) -> None:
    """Envia um buffer de memória direto para o MinIO"""
    s3_client.put_object(
        Bucket=BUCKET_NAME, 
        Key=object_key, 
        Body=buffer.getvalue()
    )

def read_parquet_from_minio(object_key: str) -> pd.DataFrame:
    response = s3_client.get_object(Bucket=BUCKET_NAME, Key=object_key)
    buffer = io.BytesIO(response["Body"].read())
    return pd.read_parquet(buffer)

def prepare_dataframe_for_table_export(df: pd.DataFrame) -> pd.DataFrame:
    export_df = df.copy()
    for col in export_df.columns:
        if pd.api.types.is_datetime64_any_dtype(export_df[col]):
            export_df[col] = export_df[col].dt.strftime("%Y-%m-%d %H:%M:%S")

    if "cost" in export_df.columns:
        export_df["cost"] = export_df["cost"].map(lambda x: f"{float(x):.8f}")
    return export_df

def save_outputs_and_upload(df: pd.DataFrame, domain: str, base_filename: str) -> None:
    data_atual = datetime.now().strftime('%Y-%m-%d')
    
    parquet_filename = f"{base_filename}.parquet"
    csv_filename = f"{base_filename}.csv"
    xlsx_filename = f"{base_filename}.xlsx"

    # Chaves (caminhos virtuais) no MinIO
    parquet_key = f"gold/{domain}/dt={data_atual}/{parquet_filename}"
    csv_key = f"gold/{domain}/dt={data_atual}/{csv_filename}"
    xlsx_key = f"gold/{domain}/dt={data_atual}/{xlsx_filename}"

    export_df = prepare_dataframe_for_table_export(df)

    print(f"Enviando {domain} direto para s3://{BUCKET_NAME}/gold/{domain}/dt={data_atual}/ ...")

    # 1. Salvar e enviar Parquet (em memória)
    parquet_buffer = io.BytesIO()
    df.to_parquet(parquet_buffer, index=False)
    upload_buffer_to_minio(parquet_buffer, parquet_key)

    # 2. Salvar e enviar CSV (em memória)
    csv_buffer = io.BytesIO()
    export_df.to_csv(csv_buffer, index=False, sep=";", encoding="utf-8-sig")
    upload_buffer_to_minio(csv_buffer, csv_key)

    # 3. Salvar e enviar Excel (em memória)
    try:
        xlsx_buffer = io.BytesIO()
        # openpyxl é obrigatório para escrever excel em buffer
        with pd.ExcelWriter(xlsx_buffer, engine='openpyxl') as writer:
            export_df.to_excel(writer, index=False, sheet_name=domain)
        upload_buffer_to_minio(xlsx_buffer, xlsx_key)
    except Exception as exc:
        print(f"Aviso: não foi possível gerar XLSX para {domain}: {exc}\n(Verifique se a biblioteca 'openpyxl' está instalada)")

# ── Descoberta do arquivo de entrada ─────────────────────────
def minio_key_exists(bucket_name: str, key: str) -> bool:
    try:
        s3_client.head_object(Bucket=bucket_name, Key=key)
        return True
    except ClientError:
        return False

def list_possible_parquet_keys(bucket_name: str) -> List[str]:
    found: List[str] = []
    paginator = s3_client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket_name):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if key.lower().endswith(".parquet") and ("silver" in key.lower() or "cleaned" in key.lower()):
                found.append(key)
    return found

def find_input_key_in_minio() -> Optional[str]:
    data_atual = datetime.now().strftime('%Y-%m-%d')
    chave_esperada = f"silver/cloudtrail/dt={data_atual}/cleaned_logs.parquet"
    if minio_key_exists(BUCKET_NAME, chave_esperada):
        return chave_esperada

    possible_keys = list_possible_parquet_keys(BUCKET_NAME)
    if possible_keys:
        return possible_keys[-1]
    return None

# ── Utilidades ──────────────────────────────────────────────
def safe_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    denominator = denominator.replace(0, np.nan)
    return (numerator / denominator).replace([np.inf, -np.inf], np.nan).fillna(0)

def zscore(series: pd.Series) -> pd.Series:
    std = series.std()
    if pd.isna(std) or std == 0:
        return pd.Series(0, index=series.index, dtype="float64")
    return (series - series.mean()) / std

# ── Normalização de nomes de coluna ──────────────────────────
def normalize_input_columns(df: pd.DataFrame) -> pd.DataFrame:
    alias_groups = {
        "timestamp": ["timestamp", "eventtime", "time"],
        "user_hash": ["user_hash", "hashed_user", "user"],
        "event": ["event", "eventname"],
        "resource": ["resource", "resourceid"],
        "hour": ["hour"],
        "hora_completa": ["hora_completa"], # <- Assegura leitura da hora completa
        "day_of_week": ["day_of_week", "weekday"],
        "is_weekend": ["is_weekend", "weekend"],
    }
    current_cols = {col.lower(): col for col in df.columns}
    rename_map = {}
    for target, aliases in alias_groups.items():
        if target not in df.columns:
            for alias in aliases:
                if alias in current_cols:
                    rename_map[current_cols[alias]] = target
                    break
    if rename_map:
        df = df.rename(columns=rename_map)
    return df

# ── Inferência de serviço ────────────────────────────────────
def infer_service(event: str) -> str:
    e = str(event or "").strip()
    if e.startswith(("Describe", "Run", "Start", "Stop", "Terminate")): return "ec2"
    if e.startswith(("GetBucket", "PutBucket", "GetObject", "PutObject", "List")): return "s3"
    if e.startswith(("GetUser", "GetRole", "GetPolicy", "CreateUser", "Attach")): return "iam"
    return "other_services"

# ── Leitura e preparação ─────────────────────────────────────
def load_and_prepare_cleaned_logs() -> pd.DataFrame:
    minio_key = find_input_key_in_minio()
    if not minio_key:
        raise FileNotFoundError("Arquivo Parquet da Silver não encontrado no MinIO.")

    print(f"Lendo arquivo do MinIO: s3://{BUCKET_NAME}/{minio_key}")
    df = read_parquet_from_minio(minio_key).copy()

    df.columns = [str(col).strip() for col in df.columns]
    df = normalize_input_columns(df)

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp"]).copy()

    df["event"] = df["event"].fillna("unknown").astype(str)
    df["user_hash"] = df["user_hash"].fillna("unknown").astype(str)
    
    # <- MUDANÇA ESTRUTURAL: Agrupando por Minuto em vez de Hora
    df["bucket_min_ts"] = df["timestamp"].dt.floor("min")
    df["date"] = df["bucket_min_ts"].dt.date
    df["hora_completa"] = df["bucket_min_ts"].dt.strftime("%H:%M") # <- Cria a hora bonitinha
    df["hour"] = df["bucket_min_ts"].dt.hour.astype(int) # <- Mantém o inteiro só pros cálculos
    
    return df.sort_values("timestamp").reset_index(drop=True)

# ── Bases de Dados ───────────────────────────────────────────
def build_cost_dataset(cleaned_df: pd.DataFrame) -> pd.DataFrame:
    print("Gerando COST...")
    cost_df = cleaned_df.copy()
    cost_df["service"] = cost_df["event"].apply(infer_service)
    # Trocamos "hour" por "hora_completa"
    cost_df = cost_df.groupby(["bucket_min_ts", "date", "hora_completa", "service"], as_index=False).agg(
        requests=("event", "size")
    )
    cost_df["cost"] = (cost_df["requests"].astype("float64") * UNIT_COST).round(8)
    return cost_df.rename(columns={"bucket_min_ts": "timestamp"})

def build_performance_dataset(cleaned_df: pd.DataFrame) -> pd.DataFrame:
    print("Gerando PERFORMANCE...")
    # Trocamos "hour" por "hora_completa"
    perf_df = cleaned_df.groupby(["bucket_min_ts", "date", "hora_completa"], as_index=False).agg(
        requests=("event", "size"),
        unique_users=("user_hash", "nunique")
    )
    return perf_df.rename(columns={"bucket_min_ts": "timestamp"})

def build_security_dataset(cleaned_df: pd.DataFrame) -> pd.DataFrame:
    print("Gerando SECURITY...")
    sec_df = cleaned_df.groupby(["bucket_min_ts", "date", "hora_completa", "hour", "user_hash"], as_index=False).agg(
        requests=("event", "size")
    )
    sec_df["requests_zscore"] = zscore(sec_df["requests"]).round(4)
    sec_df["is_off_hours"] = sec_df["hour"].isin([0, 1, 2, 3, 4, 5, 23])
    sec_df["risk_level"] = np.where(sec_df["requests_zscore"] > 2.5, "alto", "normal")
    
    # Remove a coluna numérica 'hour' do arquivo final (ninguém vai ver ela, apenas a hora_completa)
    sec_df = sec_df.drop(columns=["hour"])
    return sec_df.rename(columns={"bucket_min_ts": "timestamp"})

# ── Processo principal ───────────────────────────────────────
def process_gold() -> None:
    print("Iniciando pipeline Gold (em memória)...\n")
    ensure_bucket_exists(BUCKET_NAME)

    cleaned_df = load_and_prepare_cleaned_logs()

    cost_df = build_cost_dataset(cleaned_df)
    performance_df = build_performance_dataset(cleaned_df)
    security_df = build_security_dataset(cleaned_df)

    save_outputs_and_upload(cost_df, "cost", "cost")
    save_outputs_and_upload(performance_df, "performance", "performance")
    save_outputs_and_upload(security_df, "security", "security")

    print("\n✅ Pipeline Gold concluído e enviado diretamente para o MinIO!")

if __name__ == "__main__":
    process_gold()