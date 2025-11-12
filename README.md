# 🚗 GPS Tracking System - Data Lakehouse Architecture

Sistema de rastreo GPS vehicular en tiempo real basado en una **arquitectura Data Lakehouse**, combinando procesamiento **batch**, **serving** y **analytics** para lograr alta disponibilidad, escalabilidad y análisis en tiempo real.

---

## 🧠 Descripción General

Este proyecto implementa un **ecosistema de datos distribuido** para procesar, almacenar y analizar información GPS proveniente de dispositivos vehiculares.  
Integra varias tecnologías open-source bajo una arquitectura **Lambda**, permitiendo tanto procesamiento en lote como análisis en streaming.

---

## 🎯 Objetivos del Proyecto

- Capturar y almacenar datos GPS de vehículos en tiempo real.  
- Procesar eventos mediante pipelines **PySpark ETL**.  
- Distribuir los datos entre diferentes capas (Batch, Serving, Analytics).  
- Permitir consultas OLAP de baja latencia y resiliencia ante fallos.  
- Orquestar los servicios mediante contenedores Docker.

---

## 🏗️ Arquitectura General
                       🛰️ Dispositivos GPS
                            │
                            ▼
             ┌─────────────────────────────┐
             │      PostgreSQL + PostGIS    │
             │     (Batch Layer / OLTP)     │
             └─────────────┬───────────────┘
                           │
                 ⚙️ PySpark ETL Pipeline
                           │
            ┌──────────────┴──────────────┐
            │                             │
  ┌───────────────────────┐     ┌───────────────────────┐
  │     Apache Cassandra  │     │      Apache Druid     │
  │   (Serving Layer)     │     │   (Analytics / OLAP)  │
  └───────────────────────┘     └───────────────────────┘
            │                             │
            ▼                             ▼
  🔹 Consultas rápidas IoT         Dashboards analíticos
  🔹 Alta disponibilidad           🔹 Consultas SQL en tiempo real
  🔹 Escalabilidad horizontal      🔹 Agregaciones OLAP


---

## ⚙️ Stack Tecnológico

| Componente | Versión / Tipo | Descripción |
|-------------|----------------|--------------|
| **PostgreSQL + PostGIS** | 14+ / 18 | Base transaccional (OLTP / Batch) |
| **Apache Cassandra** | 4.x | Capa de Serving distribuida (IoT Time-Series) |
| **Apache Druid** | 28.x | Capa analítica OLAP de baja latencia |
| **PySpark** | 3.x | Procesamiento y ETL de datos |
| **Docker Compose** | Latest | Orquestación de servicios |
| **Python** | 3.12+ | Scripts de sincronización y automatización |

---

## 📊 Flujo de Datos

1. **Ingesta de datos:**  
   Los dispositivos GPS generan eventos que se almacenan inicialmente en **PostgreSQL**.  
2. **Procesamiento (ETL):**  
   **PySpark** extrae los datos, los transforma y los distribuye hacia **Cassandra** y **Druid**.  
3. **Cassandra (Serving Layer):**  
   Optimizada para consultas rápidas y resiliencia ante fallos.  
4. **Druid (Analytics Layer):**  
   Permite análisis OLAP y dashboards en tiempo real.

---


---

## 🚀 Despliegue

### 1️⃣ Clonar el repositorio
```bash
git clone https://github.com/tu-usuario/ProyectoGPS.git
cd ProyectoGPS

docker-compose -f cassandra-stack/docker-compose.yml up -d
docker-compose -f druid-stack/docker-compose.yml up -d

Conclusión

Este sistema demuestra cómo combinar tecnologías OLTP, NoSQL y OLAP bajo una arquitectura moderna de Data Lakehouse, capaz de:

Procesar y distribuir datos GPS a gran escala.

Permitir análisis en tiempo real y consultas históricas.

Escalar horizontalmente mediante contenedores.

Servir como base para proyectos de IoT, Big Data y Streaming Analytics.

Autor

Luis Alejandro Chabur Guevara
Data Engineer - BI & Analytics
📅 Versión: 1.0 — Noviembre 2025



