# process_gold.py
# =============================================================
# CAMADA GOLD RESUMIDA — COST / PERFORMANCE / SECURITY
# =============================================================

import io
import os
from typing import Optional, List, Set

import boto3
import numpy as np
import pandas as pd
from botocore.exceptions import ClientError

# ── Configurações ────────────────────────────────────────────
S3_ENDPOINT_URL = os.getenv("MLFLOW_S3_ENDPOINT_URL", "http://minio:9000")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "minio")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "minio123")
BUCKET_NAME = os.getenv("BUCKET_NAME", "data-lake")

LOCAL_BASE_DIR = os.getenv("GOLD_OUTPUT_DIR", "/app/data-lake/gold")
UNIT_COST = float(os.getenv("UNIT_COST", "0.000004"))

DOMAINS = ["cost", "performance", "security"]

GOLD_SOURCE_PATH = os.getenv("GOLD_SOURCE_PATH")
GOLD_SOURCE_KEY = os.getenv("GOLD_SOURCE_KEY")

LOCAL_CANDIDATES = [
    GOLD_SOURCE_PATH,
    "/app/cleaned_logs.parquet",
    "/app/cleaned.logs.parquet",
    "/app/logs_clean.parquet",
    "/app/data-lake/silver/cleaned_logs.parquet",
    "/app/data-lake/silver/cleaned.logs.parquet",
    "/app/data-lake/silver/logs_clean.parquet",
    "/app/data-lake/silver/cloudtrail/cleaned_logs.parquet",
    "/app/data-lake/silver/cloudtrail/cleaned.logs.parquet",
    "/app/data-lake/silver/cloudtrail/logs_clean.parquet",
    "./cleaned_logs.parquet",
    "./cleaned.logs.parquet",
    "./logs_clean.parquet",
]

MINIO_CANDIDATES = [
    GOLD_SOURCE_KEY,
    "silver/cleaned_logs.parquet",
    "silver/cleaned.logs.parquet",
    "silver/logs_clean.parquet",
    "silver/cloudtrail/cleaned_logs.parquet",
    "silver/cloudtrail/cleaned.logs.parquet",
    "silver/cloudtrail/logs_clean.parquet",
]

REQUIRED_COLS = {
    "timestamp",
    "user_hash",
    "event",
    "resource",
    "hour",
    "day_of_week",
    "is_weekend",
}


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
        print(f"Bucket '{bucket_name}' já existe.")
    except ClientError:
        print(f"Bucket '{bucket_name}' não encontrado. Criando...")
        s3_client.create_bucket(Bucket=bucket_name)
        print(f"Bucket '{bucket_name}' criado com sucesso.")


def ensure_local_dirs() -> None:
    os.makedirs(LOCAL_BASE_DIR, exist_ok=True)
    for domain in DOMAINS:
        os.makedirs(os.path.join(LOCAL_BASE_DIR, domain), exist_ok=True)


def ensure_minio_prefixes() -> None:
    for domain in DOMAINS:
        s3_client.put_object(Bucket=BUCKET_NAME, Key=f"gold/{domain}/.keep", Body=b"")
    print("Prefixos gold/ garantidos no MinIO.")


# ── IO ───────────────────────────────────────────────────────
def upload_file_to_minio(local_path: str, object_key: str) -> None:
    s3_client.upload_file(local_path, BUCKET_NAME, object_key)
    print(f"Upload concluído: s3://{BUCKET_NAME}/{object_key}")


def read_parquet_from_minio(object_key: str) -> pd.DataFrame:
    response = s3_client.get_object(Bucket=BUCKET_NAME, Key=object_key)
    buffer = io.BytesIO(response["Body"].read())
    return pd.read_parquet(buffer)


def prepare_dataframe_for_table_export(df: pd.DataFrame) -> pd.DataFrame:
    export_df = df.copy()

    for col in export_df.columns:
        if pd.api.types.is_datetime64_any_dtype(export_df[col]):
            export_df[col] = export_df[col].dt.strftime("%Y-%m-%d %H:%M:%S")

    # Formatação visual para custo não parecer zerado no Excel/CSV
    if "cost" in export_df.columns:
        export_df["cost"] = export_df["cost"].map(lambda x: f"{float(x):.8f}")

    return export_df


def save_outputs_and_upload(df: pd.DataFrame, domain: str, base_filename: str) -> None:
    parquet_filename = f"{base_filename}.parquet"
    csv_filename = f"{base_filename}.csv"
    xlsx_filename = f"{base_filename}.xlsx"

    local_parquet_path = os.path.join(LOCAL_BASE_DIR, domain, parquet_filename)
    local_csv_path = os.path.join(LOCAL_BASE_DIR, domain, csv_filename)
    local_xlsx_path = os.path.join(LOCAL_BASE_DIR, domain, xlsx_filename)

    parquet_key = f"gold/{domain}/{parquet_filename}"
    csv_key = f"gold/{domain}/{csv_filename}"
    xlsx_key = f"gold/{domain}/{xlsx_filename}"

    # Parquet mantém tipos originais
    df.to_parquet(local_parquet_path, index=False)

    # CSV e XLSX são preparados para leitura humana
    export_df = prepare_dataframe_for_table_export(df)

    export_df.to_csv(
        local_csv_path,
        index=False,
        sep=";",
        encoding="utf-8-sig",
    )

    try:
        export_df.to_excel(local_xlsx_path, index=False, sheet_name=domain)
        xlsx_created = True
    except Exception as exc:
        xlsx_created = False
        print(f"Aviso: não foi possível gerar XLSX para {domain}: {exc}")

    upload_file_to_minio(local_parquet_path, parquet_key)
    upload_file_to_minio(local_csv_path, csv_key)

    if xlsx_created:
        upload_file_to_minio(local_xlsx_path, xlsx_key)

    print(f"Arquivos gerados: {local_parquet_path}")
    print(f"Arquivos gerados: {local_csv_path}")
    if xlsx_created:
        print(f"Arquivos gerados: {local_xlsx_path}")


# ── Descoberta do arquivo de entrada ─────────────────────────
def resolve_local_input_path() -> Optional[str]:
    checked: List[str] = []

    for path in LOCAL_CANDIDATES:
        if not path:
            continue
        checked.append(path)
        if os.path.exists(path):
            print(f"Arquivo local encontrado: {path}")
            return path

    print("Nenhum arquivo local encontrado. Caminhos verificados:")
    for item in checked:
        print(f" - {item}")

    return None


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
            key_lower = key.lower()

            if not key_lower.endswith(".parquet"):
                continue

            if (
                "silver" in key_lower
                or "cleaned" in key_lower
                or "logs_clean" in key_lower
                or "cloudtrail" in key_lower
            ):
                found.append(key)

    return found


def find_input_key_in_minio() -> Optional[str]:
    for key in MINIO_CANDIDATES:
        if key and minio_key_exists(BUCKET_NAME, key):
            print(f"Arquivo encontrado no MinIO por chave conhecida: {key}")
            return key

    possible_keys = list_possible_parquet_keys(BUCKET_NAME)

    preferred_suffixes = (
        "cleaned_logs.parquet",
        "cleaned.logs.parquet",
        "logs_clean.parquet",
    )

    for key in possible_keys:
        if key.endswith(preferred_suffixes):
            print(f"Arquivo encontrado no MinIO por sufixo: {key}")
            return key

    if possible_keys:
        print("Nenhuma chave padrão encontrada, mas achei estes parquets candidatos no bucket:")
        for key in possible_keys[:20]:
            print(f" - {key}")

        print(f"Usando o primeiro candidato encontrado: {possible_keys[0]}")
        return possible_keys[0]

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
        "timestamp": ["timestamp", "eventtime", "event_time", "time"],
        "user_hash": ["user_hash", "userhash", "user_id_hash", "hashed_user", "user"],
        "event": ["event", "eventname", "event_name"],
        "resource": ["resource", "resourceid", "resource_id", "resourcename", "resource_name"],
        "hour": ["hour"],
        "day_of_week": ["day_of_week", "dayofweek", "weekday"],
        "is_weekend": ["is_weekend", "weekend"],
    }

    current_cols = {col.lower(): col for col in df.columns}
    rename_map = {}

    for target, aliases in alias_groups.items():
        if target in df.columns:
            continue

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

    direct_map = {
        "RunInstances": "ec2",
        "DescribeInstances": "ec2",
        "DescribeSnapshots": "ec2",
        "DescribeSnapshotAttribute": "ec2",
        "DescribeVolumes": "ec2",
        "DescribeVpcs": "ec2",
        "DescribeSecurityGroups": "ec2",
        "DescribeSubnets": "ec2",
        "DescribeKeyPairs": "ec2",
        "CreateDefaultVpc": "ec2",
        "DescribeSpotPriceHistory": "ec2",
        "GetBucketAcl": "s3",
        "GetBucketLocation": "s3",
        "ListBuckets": "s3",
        "AssumeRole": "sts",
        "GetCallerIdentity": "sts",
        "GetAccountPasswordPolicy": "iam",
        "GetAccountSummary": "iam",
        "ListAccountAliases": "iam",
        "ListMFADevices": "iam",
        "GetUser": "iam",
        "GetPolicy": "iam",
        "GetPolicyVersion": "iam",
        "ListPolicies": "iam",
        "ListPolicyVersions": "iam",
        "ListAttachedUserPolicies": "iam",
        "ListEntitiesForPolicy": "iam",
        "GenerateCredentialReport": "iam",
        "CreateLogStream": "logs",
        "DescribeDBInstances": "rds",
        "DescribeLoadBalancers": "elb",
        "DescribeTrails": "cloudtrail",
    }

    if e in direct_map:
        return direct_map[e]

    if e.startswith(("GetBucket", "PutBucket", "DeleteBucket", "ListBucket", "CreateBucket")):
        return "s3"

    if e.startswith(("GetObject", "PutObject", "DeleteObject", "AbortMultipartUpload", "CompleteMultipartUpload")):
        return "s3"

    if e.startswith(
        (
            "Describe",
            "Run",
            "Start",
            "Stop",
            "Terminate",
            "Reboot",
            "CreateVpc",
            "CreateSubnet",
            "CreateSecurityGroup",
            "AuthorizeSecurityGroup",
            "RevokeSecurityGroup",
        )
    ):
        return "ec2"

    if "Function" in e or e.startswith(("Invoke", "CreateFunction", "UpdateFunction", "DeleteFunction", "ListFunctions")):
        return "lambda"

    if e.startswith(("AssumeRole", "GetCallerIdentity", "DecodeAuthorizationMessage")):
        return "sts"

    if e.startswith(
        (
            "GetUser",
            "GetRole",
            "GetPolicy",
            "ListUsers",
            "ListRoles",
            "ListPolicies",
            "ListMFA",
            "CreateUser",
            "CreateRole",
            "Attach",
            "Detach",
            "GenerateCredentialReport",
            "ListAccountAliases",
            "GetAccount",
        )
    ):
        return "iam"

    if e.startswith(("CreateLog", "PutLog", "FilterLog", "DescribeLog", "GetLog", "DeleteLog")):
        return "logs"

    if e.startswith(("DescribeDB", "CreateDB", "ModifyDB", "DeleteDB")):
        return "rds"

    if e.startswith(("DescribeLoadBalancer", "CreateLoadBalancer", "DeleteLoadBalancer")):
        return "elb"

    if e.startswith(("DescribeTrail", "CreateTrail", "GetTrail", "UpdateTrail", "DeleteTrail")):
        return "cloudtrail"

    if e.startswith(("CreateQueue", "DeleteQueue", "SendMessage", "ReceiveMessage", "ChangeMessageVisibility", "GetQueue", "ListQueues")):
        return "sqs"

    if e.startswith(("Publish", "Subscribe", "Unsubscribe", "CreateTopic", "DeleteTopic", "ListTopics")):
        return "sns"

    if e.startswith(("CreateTable", "UpdateTable", "DeleteTable", "PutItem", "GetItem", "Query", "Scan", "BatchWriteItem", "BatchGetItem", "DescribeTable")):
        return "dynamodb"

    if e.startswith(("StartQueryExecution", "GetQueryResults", "StopQueryExecution")):
        return "athena"

    if e.startswith(("PutMetric", "GetMetric", "ListMetrics")):
        return "cloudwatch"

    return "unknown"


# ── Leitura e preparação ─────────────────────────────────────
def load_and_prepare_cleaned_logs() -> pd.DataFrame:
    local_path = resolve_local_input_path()

    if local_path:
        print(f"Lendo arquivo local: {local_path}")
        df = pd.read_parquet(local_path).copy()
    else:
        minio_key = find_input_key_in_minio()

        if not minio_key:
            raise FileNotFoundError(
                "Arquivo de entrada não encontrado.\n"
                "Verifique uma destas opções:\n"
                "1. Defina GOLD_SOURCE_PATH com o caminho local do parquet\n"
                "2. Defina GOLD_SOURCE_KEY com a chave exata no MinIO\n"
                "3. Garanta que exista um arquivo parquet na camada silver, por exemplo:\n"
                "   - silver/cleaned_logs.parquet\n"
                "   - silver/cleaned.logs.parquet\n"
                "   - silver/logs_clean.parquet\n"
                "   - silver/cloudtrail/logs_clean.parquet"
            )

        print(f"Lendo arquivo do MinIO: s3://{BUCKET_NAME}/{minio_key}")
        df = read_parquet_from_minio(minio_key).copy()

    df.columns = [str(col).strip() for col in df.columns]
    df = normalize_input_columns(df)

    missing = REQUIRED_COLS.difference(df.columns)
    if missing:
        raise ValueError(
            f"Colunas obrigatórias ausentes no parquet: {sorted(missing)}\n"
            f"Colunas encontradas: {list(df.columns)}"
        )

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp"]).copy()

    df["event"] = df["event"].fillna("unknown").astype(str)
    df["user_hash"] = df["user_hash"].fillna("unknown").astype(str)
    df["resource"] = df["resource"].fillna("unknown").astype(str)

    df["bucket_hour_ts"] = df["timestamp"].dt.floor("h")
    df["date"] = df["bucket_hour_ts"].dt.date
    df["hour"] = df["bucket_hour_ts"].dt.hour.astype(int)
    df["day_of_week"] = df["bucket_hour_ts"].dt.dayofweek.astype(int)
    df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)

    print("Schema lido com sucesso.")
    print(f"Total de linhas lidas: {len(df):,}")
    print(f"Colunas disponíveis: {list(df.columns)}")

    return df.sort_values("timestamp").reset_index(drop=True)


# ── Base horária ─────────────────────────────────────────────
def build_hourly_event_base(cleaned_df: pd.DataFrame) -> pd.DataFrame:
    base = (
        cleaned_df.groupby(["bucket_hour_ts", "date", "hour", "day_of_week", "is_weekend"], as_index=False)
        .agg(
            requests=("event", "size"),
            unique_events=("event", "nunique"),
            unique_users=("user_hash", "nunique"),
            unique_resources=("resource", "nunique"),
        )
        .sort_values("bucket_hour_ts")
        .reset_index(drop=True)
    )

    dominant = (
        cleaned_df.groupby(["bucket_hour_ts", "event"])
        .size()
        .reset_index(name="event_count")
        .sort_values(["bucket_hour_ts", "event_count", "event"], ascending=[True, False, True])
        .drop_duplicates(subset=["bucket_hour_ts"])
        .rename(columns={"event": "dominant_event"})
    )

    base = base.merge(
        dominant[["bucket_hour_ts", "dominant_event"]],
        on="bucket_hour_ts",
        how="left",
    )

    base["dominant_event"] = base["dominant_event"].fillna("unknown").astype(str)
    return base


def get_rare_events(cleaned_df: pd.DataFrame) -> Set[str]:
    event_freq = cleaned_df["event"].value_counts()
    if event_freq.empty:
        return set()

    rare_threshold = event_freq.quantile(0.10)
    return set(event_freq[event_freq <= rare_threshold].index.astype(str))


# ── COST ─────────────────────────────────────────────────────
def build_cost_dataset(cleaned_df: pd.DataFrame) -> pd.DataFrame:
    print("Processando COST...")

    cost_source = cleaned_df.copy()
    cost_source["service"] = cost_source["event"].apply(infer_service).astype(str)

    cost_df = (
        cost_source.groupby(
            ["bucket_hour_ts", "date", "hour", "service"],
            as_index=False,
        )
        .agg(
            eventTime=("timestamp", "min"),
            requests=("event", "size"),
            unique_events=("event", "nunique"),
        )
        .sort_values(["bucket_hour_ts", "service"])
        .reset_index(drop=True)
    )

    # Mais precisão para o custo não parecer zerado
    cost_df["cost"] = (cost_df["requests"].astype("float64") * UNIT_COST).round(8)
    cost_df = cost_df.rename(columns={"bucket_hour_ts": "timestamp"})

    final_cols = [
        "timestamp",
        "eventTime",
        "date",
        "hour",
        "service",
        "requests",
        "unique_events",
        "cost",
    ]

    return cost_df[final_cols].sort_values(["timestamp", "service"]).reset_index(drop=True)


# ── PERFORMANCE ──────────────────────────────────────────────
def build_performance_dataset(cleaned_df: pd.DataFrame) -> pd.DataFrame:
    print("Processando PERFORMANCE...")

    perf_df = build_hourly_event_base(cleaned_df)

    perf_df["requests_prev_period"] = perf_df["requests"].shift(1)
    perf_df["requests_growth_pct"] = (
        safe_divide(
            perf_df["requests"] - perf_df["requests_prev_period"],
            perf_df["requests_prev_period"],
        ) * 100
    ).round(2)

    perf_df["rolling_requests_3"] = perf_df["requests"].rolling(3, min_periods=1).mean().round(2)

    global_mean = perf_df["requests"].mean()
    perf_df["is_peak"] = perf_df["requests"] > (global_mean * 1.5)

    perf_df["performance_status"] = np.select(
        [
            perf_df["is_peak"],
            perf_df["requests_growth_pct"].fillna(0) > 100,
        ],
        [
            "pico",
            "crescimento_abrupto",
        ],
        default="normal",
    )

    perf_df["performance_status"] = perf_df["performance_status"].astype(str)
    perf_df = perf_df.rename(columns={"bucket_hour_ts": "timestamp"})

    final_cols = [
        "timestamp",
        "date",
        "hour",
        "requests",
        "unique_users",
        "unique_resources",
        "requests_growth_pct",
        "rolling_requests_3",
        "is_peak",
        "performance_status",
    ]

    return perf_df[final_cols].sort_values("timestamp").reset_index(drop=True)


# ── SECURITY ─────────────────────────────────────────────────
def build_security_dataset(cleaned_df: pd.DataFrame, performance_df: pd.DataFrame) -> pd.DataFrame:
    print("Processando SECURITY...")

    base = build_hourly_event_base(cleaned_df)
    rare_events = get_rare_events(cleaned_df)

    rare_by_period = (
        cleaned_df.assign(is_rare_event=cleaned_df["event"].isin(rare_events))
        .groupby("bucket_hour_ts", as_index=False)
        .agg(rare_events_count=("is_rare_event", "sum"))
    )

    security_df = base.merge(rare_by_period, on="bucket_hour_ts", how="left")
    security_df["rare_events_count"] = security_df["rare_events_count"].fillna(0).astype(int)

    security_df["rare_events_ratio_pct"] = (
        safe_divide(security_df["rare_events_count"], security_df["requests"]) * 100
    ).round(2)

    security_df["requests_zscore"] = zscore(security_df["requests"]).round(4)
    security_df["rare_events_zscore"] = zscore(security_df["rare_events_count"]).round(4)

    security_df["anomaly_score"] = (
        security_df[["requests_zscore", "rare_events_zscore"]]
        .abs()
        .mean(axis=1)
        .round(4)
    )

    security_df["is_off_hours"] = security_df["hour"].isin([0, 1, 2, 3, 4, 5, 23])

    perf_cols = performance_df[["timestamp", "is_peak"]].rename(columns={"timestamp": "bucket_hour_ts"})
    security_df = security_df.merge(perf_cols, on="bucket_hour_ts", how="left")
    security_df["is_peak"] = security_df["is_peak"].fillna(False)

    security_df["is_unusual_access"] = (
        (security_df["anomaly_score"] > 2.5)
        | (security_df["rare_events_ratio_pct"] > 10)
        | (security_df["is_off_hours"] & (security_df["requests"] > security_df["requests"].median()))
    )

    security_df["risk_level"] = np.select(
        [
            security_df["anomaly_score"] > 4,
            security_df["anomaly_score"] > 2.5,
        ],
        [
            "alto",
            "médio",
        ],
        default="baixo",
    )

    def build_reason(row: pd.Series) -> str:
        reasons = []
        if row["is_off_hours"]:
            reasons.append("acesso_fora_do_horario")
        if row["rare_events_count"] > 0:
            reasons.append("evento_raro")
        if row["anomaly_score"] > 2.5:
            reasons.append("score_anomalia_alto")
        if bool(row.get("is_peak", False)):
            reasons.append("pico_de_requisicoes")
        return "|".join(reasons) if reasons else "normal"

    security_df["reason"] = security_df.apply(build_reason, axis=1).astype(str)
    security_df["dominant_event"] = security_df["dominant_event"].fillna("unknown").astype(str)
    security_df["risk_level"] = security_df["risk_level"].astype(str)

    security_df = security_df.rename(columns={"bucket_hour_ts": "timestamp"})

    final_cols = [
        "timestamp",
        "date",
        "hour",
        "requests",
        "dominant_event",
        "rare_events_count",
        "rare_events_ratio_pct",
        "anomaly_score",
        "is_unusual_access",
        "risk_level",
        "reason",
    ]

    return security_df[final_cols].sort_values("timestamp").reset_index(drop=True)


# ── Processo principal ───────────────────────────────────────
def process_gold() -> None:
    print("Iniciando pipeline Gold...\n")

    ensure_local_dirs()
    ensure_bucket_exists(BUCKET_NAME)
    ensure_minio_prefixes()

    cleaned_df = load_and_prepare_cleaned_logs()

    cost_df = build_cost_dataset(cleaned_df)
    performance_df = build_performance_dataset(cleaned_df)
    security_df = build_security_dataset(cleaned_df, performance_df)

    save_outputs_and_upload(cost_df, "cost", "cost")
    save_outputs_and_upload(performance_df, "performance", "performance")
    save_outputs_and_upload(security_df, "security", "security")

    print("\nPipeline Gold concluído com sucesso!")
    print("Arquivos gerados:")
    print(" - data-lake/gold/cost/cost.parquet")
    print(" - data-lake/gold/cost/cost.csv")
    print(" - data-lake/gold/cost/cost.xlsx")
    print(" - data-lake/gold/performance/performance.parquet")
    print(" - data-lake/gold/performance/performance.csv")
    print(" - data-lake/gold/performance/performance.xlsx")
    print(" - data-lake/gold/security/security.parquet")
    print(" - data-lake/gold/security/security.csv")
    print(" - data-lake/gold/security/security.xlsx")


if __name__ == "__main__":
    process_gold()