# 🚀 Arquitetura da Aplicação - Plataforma de Análise com IA

## 📌 Visão Geral

Esta aplicação implementa uma arquitetura moderna de dados e inteligência artificial, combinando:

* Data Lake (MinIO)
* Processamento de dados (pipelines em Python)
* Machine Learning (detecção de anomalias)
* LLM (Agent com ferramentas)
* Backend (FastAPI)
* Frontend (React)
* Banco relacional (PostgreSQL)
* Vector Database (RAG)

O objetivo é permitir **análise inteligente de dados**, com **detecção de anomalias** e **respostas em linguagem natural** para o usuário.

---

# 🧱 Arquitetura Geral

A arquitetura segue um fluxo dividido em três camadas principais:

```text
Usuário → Frontend → Backend → IA / Dados / ML
```

---

# 👤 Fluxo do Usuário

1. O usuário acessa o sistema via **Frontend (React)**
2. Realiza autenticação
3. Interage com o sistema (dashboard ou perguntas)
4. As requisições são enviadas para o **FastAPI**
5. O backend decide se:

   * consulta dados no PostgreSQL
   * aciona o Agent (LLM)
   * executa análise de anomalias

---

# ⚙️ Backend (FastAPI)

O backend atua como **orquestrador central**, sendo responsável por:

* Autenticação de usuários
* Exposição de APIs
* Integração com:

  * PostgreSQL
  * Data Lake (MinIO)
  * Modelo de ML
  * Agent (LLM)

---

# 🗄️ PostgreSQL (Camada Operacional)

Responsável por armazenar dados de **baixa latência e uso operacional**:

* Usuários
* Configurações
* Métricas agregadas
* Anomalias detectadas
* Insights gerados pela IA

👉 Não armazena dados brutos ou datasets grandes

---

# 🪣 Data Lake (MinIO)

Estruturado em três camadas:

## 🥉 Bronze

* Dados brutos (CSV)
* Origem: dataset do Kaggle
* Sem tratamento

---

## 🥈 Silver

* Dados tratados e limpos
* Conversão para Parquet
* Aplicação de:

  * limpeza
  * filtragem
  * enriquecimento

---

## 🥇 Gold

* Dados organizados por domínio:

  * Custo
  * Performance
  * Segurança
* Prontos para análise e consumo

---

# 🔄 Pipeline de Dados

## Ingestão

```text
Kaggle → Pipeline → MinIO Bronze
```

## Processamento

```text
Bronze → Pipeline → Silver → Pipeline → Gold
```

---

# 🤖 Machine Learning (Detecção de Anomalias)

* Algoritmo utilizado: **Isolation Forest**
* Entrada: dados da camada Gold
* Saída:

  * anomaly_score
  * classificação (normal/anômalo)

## Fluxo:

```text
Gold → Modelo → Resultado → PostgreSQL
```

---

# 🧪 MLflow

Responsável por:

* Versionamento do modelo
* Registro de experimentos
* Gestão do ciclo de vida do modelo

---

# 🧠 IA (Agent com LLM)

O sistema utiliza um **Agent com LLM**, capaz de responder perguntas do usuário.

## Funcionamento:

```text
Usuário → FastAPI → Agent (LLM)
```

O Agent utiliza ferramentas (tools):

* PostgreSQL → dados estruturados
* VectorDB → contexto semântico
* Gold (via pipeline) → dados analíticos

---

# 🔍 Vector Database (RAG)

Responsável por armazenar embeddings e permitir:

* busca semântica
* recuperação de contexto
* suporte ao Agent

## Fluxo:

```text
Gold → Pipeline de Embeddings → VectorDB
```

---

# 🔄 Integração com IA

O Agent combina múltiplas fontes:

```text
LLM
 ├── PostgreSQL (métricas e anomalias)
 ├── VectorDB (contexto)
 └── Dados analíticos (Gold)
```

---

# 📊 Domínios de Dados

## 💰 Custo

* timestamp
* requests
* cost

## ⚡ Performance

* latency
* requests
* peak usage
* status

## 🔐 Segurança

* eventos
* acessos suspeitos
* anomaly_score
* risk_level

---

# 🐳 Docker

Toda a aplicação é executada em containers:

* Frontend
* Backend (FastAPI)
* PostgreSQL
* MinIO
* MLflow
* VectorDB

---

# 🔄 Versionamento

O código e pipelines são versionados via GitHub.

---

# 🧠 Decisões de Arquitetura

### Separação de responsabilidades

* PostgreSQL → dados operacionais
* MinIO → dados analíticos
* ML → inteligência
* LLM → explicabilidade

---

### Escalabilidade

* Data Lake permite crescimento de dados
* PostgreSQL garante baixa latência
* MLflow permite evolução do modelo

---

### Flexibilidade

* Agent pode integrar novas tools facilmente
* Novos modelos podem ser adicionados

---

# 🏁 Conclusão

A arquitetura combina:

* Engenharia de dados
* Machine Learning
* Inteligência Artificial
* APIs modernas

Resultando em uma plataforma capaz de:

* Detectar anomalias automaticamente
* Explicar comportamentos com IA
* Escalar para grandes volumes de dados

---

## Integrantes do Projeto

Abaixo, os integrantes listados em **ordem alfabética**:

- **Armando Bertolli** — armando.bertolli@gmail.com — RA **211192** - QA
- **Caique Pinto** — fmendes767@gmail.com — RA **223007** - Dev
- **Diego Juan Isaquiel Mizael** — diegoisaquiel1@gmail.com — RA **222545** - Scrum Master
- **Gabriel Henrique Domingues de Oliveira** — gabrieloliveira2758@gmail.com - RA **222398** - QA
- **Giovana Pontes Merguizo** — giovana.merguizo@outlook.com — RA **223397** - Dev
- **Guilherme Bordignon Janczak** — guijanck@gmail.com — RA **222688** - Dev
- **Gustavo Figueiredo Passos** — gustavofp111@gmail.com — RA **222560** - Dev
- **João Luiz Orlandini Alves** — joao.luiz.orlandini@gmail.com — RA **223497** - PO
- **Leonardo Barbosa Gonçalves** — leonardo.goncalves16@outlook.com — RA **211923** - Dev
- **Lucas Laureano Jorge da Silva** — lucaslaureanojorgesilva@hotmail.com —  RA **222679** - Tech Lead

---

## Estrutura Esperada do Projeto

```bash
GenAcademy/
├── data/
├── notebooks/
├── src/
├── models/
├── docs/
├── README.md
└── requirements.txt
