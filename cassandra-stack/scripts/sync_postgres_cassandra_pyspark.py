#!/usr/bin/env python3
"""
Sincronización PostgreSQL → Cassandra usando PySpark
Compatible con tu estructura actual
Autor: Sistema GPS
Fecha: 2025-11-11
"""

import os
import logging
from datetime import datetime, timedelta
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, to_timestamp, lit
from pyspark.sql.types import *

# ==================== CONFIGURACIÓN ====================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# PostgreSQL
POSTGRES_CONFIG = {
    "host": "localhost",
    "port": "5432",
    "database": "proyecto_mis_datos",
    "user": "postgres",
    "password": "admin123"
}

# Cassandra
CASSANDRA_CONFIG = {
    "host": "127.0.0.1",
    "port": "9042",
    "keyspace": "gps_tracking",
    "table": "event_record"
}

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
POSTGRES_JDBC_JAR = os.path.join(BASE_DIR, "postgresql-42.7.1.jar")
CASSANDRA_CONNECTOR_JAR = os.path.join(BASE_DIR, "spark-cassandra-connector_2.12-3.5.0.jar")
CHECKPOINT_FILE = os.path.join(BASE_DIR, "checkpoint_cassandra.txt")

# Query PostgreSQL (tu vista existente)
POSTGRES_QUERY = """
(SELECT 
    er.record_id::text as record_id,
    er.time_stamp_event,
    er.created_at,
    er.updated_at,
    er.deleted_at,
    er.vehicle_id,
    v.plate as vehicle_plate,
    v.company_id as vehicle_company_id,
    er.device_id,
    d.imei as device_imei,
    d.manufacturer_id as device_manufacturer_id,
    m.manufacturer_name,
    er.event_id,
    et.event_name,
    et.properties as event_properties,
    er.user_id,
    u.username as user_username,
    u.email as user_email,
    u.full_name as user_full_name,
    u.role as user_role,
    c.company_name,
    ST_Y(er.geom::geometry) as latitude,
    ST_X(er.geom::geometry) as longitude,
    er.altitude,
    er.speed,
    er.angle,
    er.satellites,
    er.hdop,
    er.pdop,
    er.total_odometer,
    er.location_desc,
    er.ip,
    er.reference_id
FROM event_record er
INNER JOIN vehicle v ON er.vehicle_id = v.vehicle_id
INNER JOIN device d ON er.device_id = d.device_id
INNER JOIN manufacturer m ON d.manufacturer_id = m.manufacturer_id
INNER JOIN event_type et ON er.event_id = et.event_id
INNER JOIN company c ON v.company_id = c.company_id
LEFT JOIN "user" u ON er.user_id = u.user_id
WHERE er.deleted_at IS NULL
) AS gps_events
"""

# ==================== FUNCIONES ====================

def get_last_sync_timestamp():
    """Obtiene el último timestamp de sincronización"""
    try:
        if os.path.exists(CHECKPOINT_FILE):
            with open(CHECKPOINT_FILE, 'r') as f:
                timestamp_str = f.read().strip()
                return datetime.fromisoformat(timestamp_str)
        else:
            # Primera ejecución: CARGA COMPLETA
            # Cambia a timedelta(days=7) si solo quieres últimos 7 días
            logger.info("🔄 CARGA INICIAL: Sin checkpoint, cargando TODOS los datos")
            return None
    except Exception as e:
        logger.warning(f"⚠️ Error leyendo checkpoint: {e}")
        return None

def save_sync_timestamp(timestamp):
    """Guarda el timestamp de sincronización"""
    try:
        with open(CHECKPOINT_FILE, 'w') as f:
            f.write(timestamp.isoformat())
        logger.info(f"💾 Checkpoint guardado: {timestamp}")
    except Exception as e:
        logger.error(f"❌ Error guardando checkpoint: {e}")

def create_spark_session():
    """Crea Spark Session con conector de Cassandra"""
    try:
        logger.info("🚀 Inicializando Spark Session...")
        
        # Verificar que los JARs existen
        if not os.path.exists(POSTGRES_JDBC_JAR):
            raise FileNotFoundError(f"❌ No se encuentra: {POSTGRES_JDBC_JAR}")
        if not os.path.exists(CASSANDRA_CONNECTOR_JAR):
            raise FileNotFoundError(f"❌ No se encuentra: {CASSANDRA_CONNECTOR_JAR}")
        
        logger.info(f"✅ PostgreSQL JAR: {POSTGRES_JDBC_JAR}")
        logger.info(f"✅ Cassandra JAR: {CASSANDRA_CONNECTOR_JAR}")
        
        # Directorio temporal personalizado
        spark_temp_dir = os.path.abspath("./spark-warehouse")
        os.makedirs(spark_temp_dir, exist_ok=True)
        
        spark = SparkSession.builder \
            .appName("PostgreSQL_to_Cassandra_Sync") \
            .config("spark.jars", f"{POSTGRES_JDBC_JAR},{CASSANDRA_CONNECTOR_JAR}") \
            .config("spark.driver.extraClassPath", f"{POSTGRES_JDBC_JAR},{CASSANDRA_CONNECTOR_JAR}") \
            .config("spark.cassandra.connection.host", CASSANDRA_CONFIG["host"]) \
            .config("spark.cassandra.connection.port", CASSANDRA_CONFIG["port"]) \
            .config("spark.cassandra.auth.username", "cassandra") \
            .config("spark.cassandra.auth.password", "cassandra") \
            .config("spark.executor.memory", "2g") \
            .config("spark.driver.memory", "2g") \
            .config("spark.sql.warehouse.dir", spark_temp_dir) \
            .config("spark.local.dir", spark_temp_dir) \
            .config("spark.driver.host", "localhost") \
            .getOrCreate()
        
        logger.info("✅ Spark Session creada con conector Cassandra")
        return spark
        
    except Exception as e:
        logger.error(f"❌ Error creando Spark Session: {e}")
        raise

def extract_from_postgres(spark, last_sync=None):
    """Extrae datos de PostgreSQL"""
    try:
        logger.info("🔌 Conectando a PostgreSQL con Spark...")
        
        jdbc_url = f"jdbc:postgresql://{POSTGRES_CONFIG['host']}:{POSTGRES_CONFIG['port']}/{POSTGRES_CONFIG['database']}"
        
        # Construir query con filtro de fecha si existe checkpoint
        query = POSTGRES_QUERY
        if last_sync:
            # Agregar filtro WHERE antes del paréntesis final
            query = query.replace(
                "WHERE er.deleted_at IS NULL",
                f"WHERE er.deleted_at IS NULL AND er.time_stamp_event > '{last_sync.isoformat()}'"
            )
            logger.info(f"📅 Sincronizando desde: {last_sync}")
        else:
            logger.info("📅 🔄 CARGA COMPLETA: Sincronizando TODOS los datos históricos")
        
        df = spark.read \
            .format("jdbc") \
            .option("url", jdbc_url) \
            .option("dbtable", query) \
            .option("user", POSTGRES_CONFIG["user"]) \
            .option("password", POSTGRES_CONFIG["password"]) \
            .option("driver", "org.postgresql.Driver") \
            .option("fetchsize", "1000") \
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
        logger.error(f"❌ Error extrayendo de PostgreSQL: {e}")
        raise

def transform_for_cassandra(df):
    """Transforma el DataFrame para el schema de Cassandra"""
    try:
        logger.info("🔄 Transformando datos para Cassandra...")
        
        # Convertir record_id a bigint (Cassandra lo espera así)
        df_transformed = df.withColumn("record_id", col("record_id").cast("long"))
        
        # Asegurar que los decimales sean del tipo correcto
        decimal_columns = ["altitude", "speed", "angle", "hdop", "pdop", "total_odometer"]
        for col_name in decimal_columns:
            if col_name in df.columns:
                df_transformed = df_transformed.withColumn(col_name, col(col_name).cast("decimal(38,18)"))
        
        # Reordenar columnas según el orden de Cassandra
        columns_order = [
            "vehicle_id", "time_stamp_event", "record_id",
            "created_at", "updated_at", "deleted_at",
            "ip", "location_desc",
            "altitude", "angle", "satellites", "speed", "hdop", "pdop",
            "total_odometer", "reference_id",
            "latitude", "longitude",
            "vehicle_plate", "vehicle_company_id",
            "device_id", "device_imei", "device_manufacturer_id",
            "event_id", "event_name", "event_properties",
            "user_id", "user_username", "user_email", "user_full_name", "user_role",
            "company_name", "manufacturer_name"
        ]
        
        # Seleccionar solo las columnas que existen
        existing_columns = [c for c in columns_order if c in df_transformed.columns]
        df_transformed = df_transformed.select(existing_columns)
        
        logger.info("✅ Transformación completada")
        return df_transformed
        
    except Exception as e:
        logger.error(f"❌ Error transformando datos: {e}")
        raise

def load_to_cassandra(df):
    """Carga datos a Cassandra usando el conector de Spark"""
    try:
        logger.info("💾 Cargando datos a Cassandra...")
        
        df.write \
            .format("org.apache.spark.sql.cassandra") \
            .mode("append") \
            .option("keyspace", CASSANDRA_CONFIG["keyspace"]) \
            .option("table", CASSANDRA_CONFIG["table"]) \
            .option("spark.cassandra.output.consistency.level", "LOCAL_QUORUM") \
            .option("spark.cassandra.output.batch.size.rows", "100") \
            .option("spark.cassandra.output.concurrent.writes", "5") \
            .save()
        
        logger.info("✅ Datos cargados exitosamente a Cassandra")
        
    except Exception as e:
        logger.error(f"❌ Error cargando a Cassandra: {e}")
        raise

def main():
    """Función principal"""
    spark = None
    try:
        logger.info("=" * 70)
        logger.info("🚀 SINCRONIZACIÓN PostgreSQL → Cassandra (PySpark)")
        logger.info("=" * 70)
        
        # Crear Spark Session
        spark = create_spark_session()
        
        # Obtener última sincronización
        last_sync = get_last_sync_timestamp()
        
        # Extraer datos de PostgreSQL
        df_postgres = extract_from_postgres(spark, last_sync)
        
        if df_postgres.count() == 0:
            logger.info("✅ No hay nuevos registros para sincronizar")
            return 0
        
        # Transformar datos
        df_transformed = transform_for_cassandra(df_postgres)
        
        # Cargar a Cassandra
        load_to_cassandra(df_transformed)
        
        # Guardar checkpoint con el timestamp más reciente
        max_timestamp = df_transformed.agg({"time_stamp_event": "max"}).collect()[0][0]
        if max_timestamp:
            save_sync_timestamp(max_timestamp)
        
        record_count = df_transformed.count()
        
        logger.info("=" * 70)
        logger.info(f"✅ COMPLETADO: {record_count} registros sincronizados")
        logger.info("=" * 70)
        
        return record_count
        
    except Exception as e:
        logger.error(f"❌ Error en pipeline: {e}")
        logger.error("=" * 70)
        logger.error(f"❌ FALLÓ: {e}")
        logger.error("=" * 70)
        raise
        
    finally:
        if spark:
            spark.stop()
            logger.info("🛑 Spark Session cerrada")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        exit(1)