# GenAcademy

## Agente de Otimização de Infraestrutura Educacional (SaaS Scalability Agent)

Este repositório contém o desenvolvimento de um projeto de **LLM aplicado à nuvem**, com foco em **otimização de infraestrutura, análise de logs e suporte à tomada de decisão em ambientes SaaS educacionais**.

O projeto utiliza como base o dataset do Kaggle:

- **Dataset:** [AWS CloudTrails Dataset from FLAWS Cloud](https://www.kaggle.com/datasets/nobukim/aws-cloudtrails-dataset-from-flaws-cloud?select=nineteenFeaturesDf.csv)

---

## Objetivo do Projeto

O objetivo deste projeto é construir um **Agente Inteligente de Escalabilidade e FinOps** para um ambiente educacional SaaS, capaz de:

- analisar logs de infraestrutura em nuvem;
- identificar padrões de uso e picos de acesso;
- gerar recomendações inteligentes de escalabilidade;
- apoiar a redução de custos operacionais;
- melhorar a performance da plataforma em horários críticos de uso.

---

## Contexto da Solução

O **Agente de Otimização de Infraestrutura Educacional** foi idealizado para atuar como um assistente inteligente dentro de um dashboard administrativo do **GenAcademy**, auxiliando gestores técnicos e de negócio a interpretar dados de uso da aplicação.

Exemplo de insight gerado pelo agente:

> “Notei que a Escola X apresenta um pico de uso às 08:00, o que está sobrecarregando o banco de dados. Sugiro provisionar mais instâncias de leitura nesse horário para evitar latência para os alunos.”

---

## Arquitetura de Dados

O projeto segue uma abordagem inspirada em **Arquitetura Medalhão**, com foco em organização analítica e governança de dados.

### Bronze
Armazenamento dos **logs brutos** de acesso, eventos de nuvem e utilização de serviços como CloudFront, Lambda, EC2 e demais componentes monitorados.

### Prata
Camada de **tratamento e agregação**, agrupando os acessos por padrões relevantes, como:

- horário escolar;
- turnos (manhã, tarde e noite);
- comportamento de uso por escola, turma ou perfil de usuário.

### Ouro
Camada analítica com geração de indicadores estratégicos, como:

- custo por aluno;
- custo por escola;
- janelas de maior consumo;
- padrões de sobrecarga e necessidade de escalabilidade.

---

## Papel do LLM no Projeto

O LLM será utilizado como um **agente interpretador e recomendador**, capaz de transformar métricas técnicas em orientações acionáveis para o negócio.

### Principais funções do agente:
- interpretar eventos e padrões presentes nos logs;
- identificar anomalias de uso;
- sugerir ações de escalabilidade;
- apoiar estratégias de **FinOps**;
- traduzir informações técnicas em linguagem clara para administradores da plataforma.

---

## Valor Gerado para o SaaS

Com essa solução, o GenAcademy poderá obter benefícios como:

- **redução de custos em infraestrutura**;
- **melhor aproveitamento de recursos computacionais**;
- **prevenção de gargalos de performance**;
- **maior disponibilidade do ambiente para alunos e escolas**;
- **suporte inteligente à gestão operacional da plataforma**.

---

## Tecnologias e Conceitos Envolvidos

Este projeto envolve conceitos e práticas como:

- Large Language Models (LLM)
- Cloud Computing
- Observabilidade
- FinOps
- Arquitetura Medalhão
- Processamento e análise de logs
- Otimização de infraestrutura SaaS
- Inteligência aplicada à operação em nuvem

---

## Integrantes do Projeto

Abaixo, os integrantes listados em **ordem alfabética**:

- **Armando Bertolli** — armando.bertolli@gmail.com — **211192**
- **Caique Pinto** — fmendes767@gmail.com — **223007**
- **Diego Juan Isaquiel Mizael** — diegoisaquiel1@gmail.com — **222545**
- **Gabriel Henrique Domingues de Oliveira** — gabrieloliveira2758@gmail.com — **222398**
- **Giovana Pontes Merguizo** — giovana.merguizo@outlook.com — **223397**
- **Guilherme Bordignon Janczak** — guijanck@gmail.com — **222688**
- **Gustavo Figueiredo Passos** — gustavofp111@gmail.com — **222560**
- **João Luiz Orlandini Alves** — joao.luiz.orlandini@gmail.com — **223497**
- **Leonardo Barbosa Gonçalves** — leonardo.goncalves16@outlook.com — **211923**
- **Lucas Laureano Jorge da Silva** — lucaslaureanojorgesilva@hotmail.com — **222679**

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
