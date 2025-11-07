# 🚗 GPS Tracking System - Multi-Database Architecture

Sistema de rastreo GPS en tiempo real con arquitectura de bases de datos distribuidas optimizado para diferentes cargas de trabajo.

## 🏗️ Arquitectura

```
PostgreSQL (OLTP)
    ↓
    ├─→ Cassandra (Time-series & IoT data)
    └─→ Druid (Analytics & OLAP)
```

### Componentes

- **PostgreSQL**: Base de datos transaccional principal (OLTP)
- **Cassandra**: Almacenamiento de series temporales para datos IoT
- **Druid**: Motor de analytics para consultas OLAP en tiempo real
- **Scripts de sincronización**: Python scripts para ETL automático

## 📋 Requisitos

### Software
- Python 3.12+
- PostgreSQL 14+
- Apache Cassandra 4.x
- Apache Druid 28.x
- Docker & Docker Compose (opcional)

### Dependencias Python
```bash
pip install psycopg2-binary cassandra-driver gevent requests
```

## 🚀 Instalación

### 1. Clonar el repositorio
```bash
git clone https://github.com/tu-usuario/gps-tracking-system.git
cd gps-tracking-system
```

### 2. Configurar PostgreSQL

```sql
-- Crear base de datos
CREATE DATABASE proyecto_mis_datos;

-- Ejecutar schemas (ver /database/schemas/)
\i database/schemas/postgresql_schema.sql
```

### 3. Configurar Cassandra

```bash
# Iniciar Cassandra
docker-compose -f cassandra-stack/docker-compose.yml up -d

# Crear keyspace y tablas
cqlsh -f database/schemas/cassandra_schema.cql
```

### 4. Configurar Druid

```bash
# Iniciar Druid
docker-compose -f druid-stack/docker-compose.yml up -d

# Verificar servicios
curl http://localhost:8888/status
```

### 5. Configurar scripts de sincronización

Editar archivos de configuración en `/scripts/`:

**sync_postgres_to_cassandra.py**
```python
PG_CONFIG = {
    'host': '127.0.0.1',
    'port': 5432,
    'dbname': 'proyecto_mis_datos',
    'user': 'postgres',
    'password': 'tu_password'
}

CASSANDRA_HOSTS = ['localhost']
CASSANDRA_KEYSPACE = 'gps_tracking'
```

**sync_postgres_to_druid.py**
```python
PG_CONFIG = {
    'host': '127.0.0.1',
    'port': 5432,
    'database': 'proyecto_mis_datos',
    'user': 'postgres',
    'password': 'tu_password'
}

DRUID_ROUTER_URL = 'http://localhost:8888'
```

## 🔄 Uso

### Sincronización manual

```bash
# Sincronizar a Cassandra
python scripts/sync_postgres_to_cassandra.py

# Sincronizar a Druid
python scripts/sync_postgres_to_druid.py

# Sincronizar ambos
python scripts/sync_all.py
```

### Sincronización automática

**Linux/Mac (crontab)**
```bash
# Cada 5 minutos
*/5 * * * * cd /ruta/proyecto && python scripts/sync_all.py >> logs/sync.log 2>&1
```

**Windows (Task Scheduler)**
```bash
# Ejecutar run_sync.bat cada 5 minutos
schtasks /create /tn "GPS Sync" /tr "C:\proyecto\scripts\run_sync.bat" /sc minute /mo 5
```

## 📊 Modelo de Datos

### PostgreSQL (Normalizado)

```
event_record
├── record_id (PK)
├── time_stamp_event
├── vehicle_id (FK)
├── device_id (FK)
├── event_id (FK)
├── user_id (FK)
├── geom (PostGIS)
├── speed, altitude, angle
└── ...

vehicle → company
device → manufacturer
event_type
user
```

### Cassandra (Desnormalizado)

```
event_record (partitioned by vehicle_id, time_stamp_event)
├── Todos los campos desnormalizados
├── Optimizado para queries por vehículo
└── Retention: ilimitado
```

### Druid (Columnar OLAP)

```
gps_events
├── Timestamp: time_stamp_event
├── Dimensions: vehicle, company, event, user, location
├── Metrics: speed, distance, satellites
├── Granularity: MINUTE
└── Segment: DAY
```

## 🔍 Queries de Ejemplo

### Cassandra (CQL)
```sql
-- Últimos eventos de un vehículo
SELECT * FROM event_record 
WHERE vehicle_id = 1 
  AND time_stamp_event > '2025-11-06'
LIMIT 100;
```

### Druid (SQL)
```sql
-- Velocidad promedio por vehículo (última hora)
SELECT 
  vehicle_plate,
  AVG(speed) as avg_speed,
  MAX(speed) as max_speed,
  COUNT(*) as event_count
FROM gps_events
WHERE __time > CURRENT_TIMESTAMP - INTERVAL '1' HOUR
GROUP BY vehicle_plate
ORDER BY avg_speed DESC;

-- Distancia recorrida por compañía (hoy)
SELECT 
  company_name,
  SUM(total_distance) as distance_km
FROM gps_events
WHERE __time >= CURRENT_TIMESTAMP - INTERVAL '1' DAY
GROUP BY company_name;
```

## 📈 Rendimiento

| Base de Datos | Throughput | Latencia | Caso de Uso |
|---------------|-----------|----------|-------------|
| PostgreSQL | ~1K writes/s | < 10ms | Transacciones OLTP |
| Cassandra | ~10K writes/s | < 5ms | IoT time-series |
| Druid | ~100K queries/s | < 100ms | Analytics OLAP |

### Métricas de sincronización

- **Cassandra**: ~140 registros/segundo
- **Druid**: ~30 registros/segundo (incluyendo pre-agregaciones)
- **Checkpoint**: Sincronización incremental automática

## 🛠️ Troubleshooting

### Error: "FD already registered" (psycopg3 + gevent)
**Solución**: Usar `psycopg2-binary` en lugar de `psycopg3`
```bash
pip uninstall psycopg
pip install psycopg2-binary
```

### Cassandra: Connection timeout a IPs internas Docker
**Solución**: Usar `127.0.0.1` explícitamente en lugar de `localhost`

### Druid: Task FAILED
**Solución**: Verificar logs en `http://localhost:8888/unified-console.html`

## 📁 Estructura del Proyecto

```
gps-tracking-system/
├── README.md
├── requirements.txt
├── .gitignore
├── database/
│   └── schemas/
│       ├── postgresql_schema.sql
│       ├── cassandra_schema.cql
│       └── druid_spec.json
├── scripts/
│   ├── sync_postgres_to_cassandra.py
│   ├── sync_postgres_to_druid.py
│   ├── sync_all.py
│   ├── run_sync.bat
│   └── temp/
├── cassandra-stack/
│   └── docker-compose.yml
├── druid-stack/
│   └── docker-compose.yml
└── logs/
```


⭐ Si este proyecto te fue útil, considera darle una estrella en GitHub!
