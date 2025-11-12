"""
Sincronización PostgreSQL -> Druid usando PySpark
Procesamiento distribuido de eventos GPS en tiempo real
"""
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, to_json, struct, lit, current_timestamp,
    unix_timestamp, from_unixtime, concat_ws
)
from pyspark.sql.types import *
import requests
import json
from datetime import datetime, timedelta
import logging
import time
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== CONFIGURACIÓN ====================
PG_CONFIG = {
    'host': '127.0.0.1',
    'port': '5432',
    'database': 'proyecto_mis_datos',
    'user': 'postgres',
    'password': 'admin123'
}

DRUID_CONFIG = {
    'router_url': 'http://localhost:8888',
    'datasource': 'gps_events'
}

TEMP_DIR = os.path.join(os.path.dirname(__file__), 'temp')
CHECKPOINT_FILE = os.path.join(TEMP_DIR, 'last_sync.txt')

# ==================== SPARK SESSION ====================
def create_spark_session():
    """Crear sesión de Spark con configuración optimizada"""
    logger.info("🚀 Inicializando Spark Session...")
    
    spark = SparkSession.builder \
        .appName("PostgreSQL-to-Druid-GPS-Sync") \
        .config("spark.driver.memory", "2g") \
        .config("spark.executor.memory", "2g") \
        .config("spark.sql.shuffle.partitions", "4") \
        .config("spark.jars", "postgresql-42.7.1.jar") \
        .getOrCreate()
    
    spark.sparkContext.setLogLevel("WARN")
    logger.info("✅ Spark Session creada")
    return spark

# ==================== CHECKPOINT ====================
def ensure_temp_dir():
    """Crear directorio temporal"""
    if not os.path.exists(TEMP_DIR):
        os.makedirs(TEMP_DIR)
        logger.info(f"📁 Directorio creado: {TEMP_DIR}")

def get_last_sync_time():
    """Obtener último timestamp sincronizado"""
    ensure_temp_dir()
    
    try:
        if os.path.exists(CHECKPOINT_FILE):
            with open(CHECKPOINT_FILE, 'r') as f:
                timestamp_str = f.read().strip()
                last_sync = datetime.fromisoformat(timestamp_str)
                logger.info(f"📅 Última sync: {last_sync}")
                return last_sync
    except Exception as e:
        logger.warning(f"⚠️  Error leyendo checkpoint: {e}")
    
    # Default: últimas 24 horas
    default = datetime.now() - timedelta(hours=24)
    logger.info(f"📅 Sincronizando desde: {default}")
    return default

def save_last_sync_time(timestamp):
    """Guardar checkpoint"""
    ensure_temp_dir()
    try:
        with open(CHECKPOINT_FILE, 'w') as f:
            f.write(timestamp.isoformat())
        logger.info(f"💾 Checkpoint guardado: {timestamp}")
    except Exception as e:
        logger.warning(f"⚠️  Error guardando checkpoint: {e}")

# ==================== EXTRACCIÓN POSTGRESQL ====================
def extract_from_postgres(spark, last_sync_time):
    """Extraer datos de PostgreSQL usando Spark JDBC"""
    logger.info("🔌 Conectando a PostgreSQL con Spark...")
    
    jdbc_url = f"jdbc:postgresql://{PG_CONFIG['host']}:{PG_CONFIG['port']}/{PG_CONFIG['database']}"
    
    # Query optimizado con filtro de tiempo
    query = f"""
    (SELECT 
        e.record_id::text as record_id,
        e.time_stamp_event,
        e.created_at,
        e.vehicle_id,
        v.plate as vehicle_plate,
        v.company_id as vehicle_company_id,
        e.device_id,
        d.imei as device_imei,
        d.manufacturer_id,
        m.manufacturer_name,
        e.event_id,
        et.event_name,
        COALESCE(et.properties::text, '') as event_properties,
        COALESCE(e.user_id, 0) as user_id,
        COALESCE(u.username, '') as user_username,
        COALESCE(u.email, '') as user_email,
        COALESCE(u.full_name, '') as user_full_name,
        COALESCE(u.role, '') as user_role,
        c.company_name,
        ST_Y(e.geom::geometry) as latitude,
        ST_X(e.geom::geometry) as longitude,
        COALESCE(e.altitude, 0) as altitude,
        COALESCE(e.speed, 0) as speed,
        COALESCE(e.angle, 0) as angle,
        COALESCE(e.satellites, 0) as satellites,
        COALESCE(e.hdop, 0) as hdop,
        COALESCE(e.pdop, 0) as pdop,
        COALESCE(e.total_odometer, 0) as total_odometer,
        COALESCE(e.location_desc, '') as location_desc,
        COALESCE(e.ip, '') as ip,
        COALESCE(e.reference_id, '') as reference_id
    FROM event_record e
    INNER JOIN vehicle v ON e.vehicle_id = v.vehicle_id
    INNER JOIN device d ON e.device_id = d.device_id
    INNER JOIN manufacturer m ON d.manufacturer_id = m.manufacturer_id
    INNER JOIN event_type et ON e.event_id = et.event_id
    INNER JOIN company c ON v.company_id = c.company_id
    LEFT JOIN "user" u ON e.user_id = u.user_id
    WHERE e.time_stamp_event > '{last_sync_time.isoformat()}'
      AND e.deleted_at IS NULL
    ORDER BY e.time_stamp_event ASC
    LIMIT 100000) as events
    """
    
    try:
        df = spark.read \
            .format("jdbc") \
            .option("url", jdbc_url) \
            .option("dbtable", query) \
            .option("user", PG_CONFIG['user']) \
            .option("password", PG_CONFIG['password']) \
            .option("driver", "org.postgresql.Driver") \
            .option("fetchsize", "10000") \
            .load()
        
        count = df.count()
        logger.info(f"📦 Extraídos {count} eventos de PostgreSQL")
        
        if count > 0:
            logger.info("📊 Schema de datos:")
            df.printSchema()
            logger.info("🔍 Muestra de datos:")
            df.show(5, truncate=False)
        
        return df
        
    except Exception as e:
        logger.error(f"❌ Error extrayendo datos: {e}")
        raise

# ==================== TRANSFORMACIÓN ====================
def transform_for_druid(df):
    """Transformar DataFrame para formato Druid"""
    logger.info("🔄 Transformando datos para Druid...")
    
    # Convertir timestamps a ISO string
    df_transformed = df.withColumn(
        "time_stamp_event",
        from_unixtime(unix_timestamp(col("time_stamp_event")), "yyyy-MM-dd'T'HH:mm:ss.SSSXXX")
    )
    
    # Asegurar tipos correctos
    df_transformed = df_transformed.select(
        col("record_id").cast("string"),
        col("time_stamp_event").cast("string"),
        col("vehicle_id").cast("long"),
        col("vehicle_plate").cast("string"),
        col("vehicle_company_id").cast("long"),
        col("device_id").cast("long"),
        col("device_imei").cast("string"),
        col("manufacturer_id").cast("long"),
        col("manufacturer_name").cast("string"),
        col("event_id").cast("long"),
        col("event_name").cast("string"),
        col("event_properties").cast("string"),
        col("user_id").cast("long"),
        col("user_username").cast("string"),
        col("user_email").cast("string"),
        col("user_full_name").cast("string"),
        col("user_role").cast("string"),
        col("company_name").cast("string"),
        col("latitude").cast("double"),
        col("longitude").cast("double"),
        col("altitude").cast("double"),
        col("speed").cast("double"),
        col("angle").cast("double"),
        col("satellites").cast("long"),
        col("hdop").cast("double"),
        col("pdop").cast("double"),
        col("total_odometer").cast("double"),
        col("location_desc").cast("string"),
        col("ip").cast("string"),
        col("reference_id").cast("string")
    )
    
    logger.info("✅ Transformación completada")
    return df_transformed

# ==================== EXPORTAR A NDJSON ====================
def export_to_ndjson(df):
    """Exportar DataFrame a NDJSON para Druid"""
    ensure_temp_dir()
    timestamp = int(time.time())
    json_file = os.path.join(TEMP_DIR, f'gps_events_{timestamp}.json')
    
    logger.info(f"💾 Exportando a NDJSON: {json_file}")
    
    # Convertir a JSON (una línea por registro)
    df.coalesce(1) \
        .write \
        .mode("overwrite") \
        .json(json_file + ".tmp")
    
    # Spark crea un directorio, necesitamos consolidar en un archivo
    import glob
    import shutil
    
    # Buscar el archivo part generado por Spark
    part_files = glob.glob(os.path.join(json_file + ".tmp", "part-*.json"))
    
    if part_files:
        # Mover el archivo part al nombre final
        shutil.move(part_files[0], json_file)
        # Limpiar directorio temporal
        shutil.rmtree(json_file + ".tmp")
        logger.info(f"✅ NDJSON creado: {json_file}")
        return json_file
    else:
        logger.error("❌ No se generó archivo JSON")
        return None

# ==================== INGESTIÓN DRUID ====================
def create_druid_spec(data_content):
    """Crear spec de ingestión Druid"""
    return {
        "type": "index_parallel",
        "spec": {
            "dataSchema": {
                "dataSource": DRUID_CONFIG['datasource'],
                "timestampSpec": {
                    "column": "time_stamp_event",
                    "format": "iso"
                },
                "dimensionsSpec": {
                    "dimensions": [
                        "record_id",
                        {"name": "vehicle_id", "type": "long"},
                        "vehicle_plate",
                        {"name": "vehicle_company_id", "type": "long"},
                        {"name": "device_id", "type": "long"},
                        "device_imei",
                        {"name": "manufacturer_id", "type": "long"},
                        "manufacturer_name",
                        {"name": "event_id", "type": "long"},
                        "event_name",
                        "event_properties",
                        {"name": "user_id", "type": "long"},
                        "user_username",
                        "user_email",
                        "user_full_name",
                        "user_role",
                        "company_name",
                        "location_desc",
                        "ip",
                        "reference_id"
                    ]
                },
                "metricsSpec": [
                    {"type": "count", "name": "count"},
                    {"type": "doubleSum", "name": "sum_speed", "fieldName": "speed"},
                    {"type": "doubleMax", "name": "max_speed", "fieldName": "speed"},
                    {"type": "doubleMin", "name": "min_speed", "fieldName": "speed"},
                    {"type": "doubleSum", "name": "sum_distance", "fieldName": "total_odometer"},
                    {"type": "longSum", "name": "total_satellites", "fieldName": "satellites"}
                ],
                "granularitySpec": {
                    "type": "uniform",
                    "segmentGranularity": "DAY",
                    "queryGranularity": "MINUTE",
                    "rollup": False
                }
            },
            "ioConfig": {
                "type": "index_parallel",
                "inputSource": {
                    "type": "inline",
                    "data": data_content
                },
                "inputFormat": {
                    "type": "json"
                }
            },
            "tuningConfig": {
                "type": "index_parallel",
                "partitionsSpec": {
                    "type": "dynamic"
                },
                "maxRowsInMemory": 100000,
                "maxNumConcurrentSubTasks": 2
            }
        }
    }

def submit_to_druid(json_file_path):
    """Enviar tarea de ingestión a Druid"""
    try:
        logger.info("📖 Leyendo datos NDJSON...")
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = f.read()
        
        spec = create_druid_spec(data)
        
        url = f"{DRUID_CONFIG['router_url']}/druid/indexer/v1/task"
        headers = {'Content-Type': 'application/json'}
        
        logger.info("📤 Enviando tarea a Druid...")
        response = requests.post(url, json=spec, headers=headers, timeout=30)
        
        if response.status_code == 200:
            task_id = response.json().get('task')
            logger.info(f"✅ Tarea creada: {task_id}")
            return task_id
        else:
            logger.error(f"❌ Error HTTP {response.status_code}: {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"❌ Error enviando a Druid: {e}")
        raise

def monitor_task(task_id):
    """Monitorear estado de tarea Druid"""
    logger.info("⏳ Monitoreando tarea...")
    
    for i in range(60):  # 10 minutos máximo
        try:
            url = f"{DRUID_CONFIG['router_url']}/druid/indexer/v1/task/{task_id}/status"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                status_data = response.json().get('status', {})
                status = status_data.get('status')
                
                if status == "SUCCESS":
                    logger.info("✅ Ingestión exitosa!")
                    return True
                elif status == "FAILED":
                    logger.error("❌ Ingestión falló")
                    logger.error(f"Detalles: {json.dumps(status_data, indent=2)}")
                    return False
                elif status == "RUNNING":
                    logger.info(f"⏳ Ejecutando... ({i*10}s)")
                else:
                    logger.info(f"⏳ Estado: {status}")
            
            time.sleep(10)
            
        except Exception as e:
            logger.warning(f"⚠️  Error verificando estado: {e}")
            time.sleep(10)
    
    logger.warning("⚠️  Timeout esperando resultado")
    return False

# ==================== PIPELINE PRINCIPAL ====================
def run_sync_pipeline():
    """Ejecutar pipeline completo de sincronización"""
    spark = None
    
    try:
        # 1. Inicializar Spark
        spark = create_spark_session()
        
        # 2. Obtener checkpoint
        last_sync = get_last_sync_time()
        
        # 3. Extraer de PostgreSQL
        df = extract_from_postgres(spark, last_sync)
        
        if df.count() == 0:
            logger.info("✅ No hay datos nuevos para sincronizar")
            return 0
        
        # 4. Obtener máximo timestamp para checkpoint
        max_timestamp_row = df.agg({"time_stamp_event": "max"}).collect()[0]
        max_timestamp = max_timestamp_row[0]
        
        # 5. Transformar datos
        df_transformed = transform_for_druid(df)
        
        # 6. Exportar a NDJSON
        json_file = export_to_ndjson(df_transformed)
        
        if not json_file:
            logger.error("❌ Error exportando datos")
            return 0
        
        # 7. Enviar a Druid
        task_id = submit_to_druid(json_file)
        
        if not task_id:
            logger.error("❌ Error creando tarea en Druid")
            return 0
        
        # 8. Monitorear tarea
        success = monitor_task(task_id)
        
        if success and max_timestamp:
            # Guardar checkpoint
            save_last_sync_time(max_timestamp)
        
        record_count = df.count()
        return record_count if success else 0
        
    except Exception as e:
        logger.error(f"❌ Error en pipeline: {e}")
        raise
        
    finally:
        if spark:
            spark.stop()
            logger.info("🛑 Spark Session cerrada")

# ==================== MAIN ====================
if __name__ == "__main__":
    logger.info("=" * 70)
    logger.info("🚀 SINCRONIZACIÓN PostgreSQL → Druid (PySpark)")
    logger.info("=" * 70)
    
    try:
        records = run_sync_pipeline()
        logger.info("=" * 70)
        logger.info(f"✅ COMPLETADO: {records} registros sincronizados")
        logger.info("=" * 70)
    except Exception as e:
        logger.error("=" * 70)
        logger.error(f"❌ FALLÓ: {e}")
        logger.error("=" * 70)
        exit(1)