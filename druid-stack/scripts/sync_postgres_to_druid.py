"""
Sincronización PostgreSQL -> Druid
Lee datos de PostgreSQL y los ingesta en Druid para analytics
"""
import psycopg2
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
    'host': '127.0.0.1',  # Localhost desde Windows
    'port': 5432,
    'database': 'proyecto_mis_datos',
    'user': 'postgres',
    'password': 'admin123'
}

# Druid
DRUID_ROUTER_URL = 'http://localhost:8888'
DRUID_DATASOURCE = 'gps_events'

# Directorio temporal
TEMP_DIR = os.path.join(os.path.dirname(__file__), 'temp')

# ==================== QUERY DESNORMALIZADO ====================
QUERY_EVENTS = """
SELECT 
    er.record_id,
    er.time_stamp_event,
    er.vehicle_id,
    v.plate as vehicle_plate,
    v.company_id as vehicle_company_id,
    er.device_id,
    d.imei as device_imei,
    d.manufacturer_id,
    m.manufacturer_name,
    er.event_id,
    et.event_name,
    COALESCE(er.user_id, 0) as user_id,
    COALESCE(u.username, '') as user_username,
    COALESCE(u.email, '') as user_email,
    COALESCE(u.full_name, '') as user_full_name,
    COALESCE(u.role, '') as user_role,
    c.company_name,
    ST_Y(er.geom::geometry) as latitude,
    ST_X(er.geom::geometry) as longitude,
    COALESCE(er.altitude, 0) as altitude,
    COALESCE(er.speed, 0) as speed,
    COALESCE(er.angle, 0) as angle,
    COALESCE(er.satellites, 0) as satellites,
    COALESCE(er.hdop, 0) as hdop,
    COALESCE(er.pdop, 0) as pdop,
    COALESCE(er.total_odometer, 0) as total_odometer,
    COALESCE(er.location_desc, '') as location_desc,
    COALESCE(er.ip, '') as ip,
    COALESCE(er.reference_id, '') as reference_id
FROM event_record er
INNER JOIN vehicle v ON er.vehicle_id = v.vehicle_id
INNER JOIN device d ON er.device_id = d.device_id
INNER JOIN manufacturer m ON d.manufacturer_id = m.manufacturer_id
INNER JOIN event_type et ON er.event_id = et.event_id
INNER JOIN company c ON v.company_id = c.company_id
LEFT JOIN "user" u ON er.user_id = u.user_id
WHERE er.time_stamp_event > %s
  AND er.deleted_at IS NULL
ORDER BY er.time_stamp_event ASC
LIMIT 10000;
"""

def ensure_temp_dir():
    """Crear directorio temporal si no existe"""
    if not os.path.exists(TEMP_DIR):
        os.makedirs(TEMP_DIR)
        logger.info(f"📁 Directorio temporal creado: {TEMP_DIR}")

def get_last_sync_time():
    """Obtener timestamp de última sincronización desde archivo"""
    sync_file = os.path.join(TEMP_DIR, 'last_sync.txt')
    
    try:
        if os.path.exists(sync_file):
            with open(sync_file, 'r') as f:
                timestamp_str = f.read().strip()
                last_sync = datetime.fromisoformat(timestamp_str)
                logger.info(f"📅 Última sincronización: {last_sync}")
                return last_sync
    except Exception as e:
        logger.warning(f"⚠️  No se pudo leer última sync: {e}")
    
    # Por defecto últimas 24 horas
    default_time = datetime.now() - timedelta(hours=24)
    logger.info(f"📅 Sincronizando desde: {default_time}")
    return default_time

def save_last_sync_time(timestamp):
    """Guardar timestamp de última sincronización"""
    sync_file = os.path.join(TEMP_DIR, 'last_sync.txt')
    try:
        with open(sync_file, 'w') as f:
            f.write(timestamp.isoformat())
        logger.info(f"💾 Guardado timestamp: {timestamp}")
    except Exception as e:
        logger.warning(f"⚠️  No se pudo guardar timestamp: {e}")

def export_postgres_to_json(last_sync_time):
    """Exportar datos de PostgreSQL a JSON"""
    try:
        logger.info("🔌 Conectando a PostgreSQL...")
        conn = psycopg2.connect(**PG_CONFIG)
        cursor = conn.cursor()
        
        logger.info(f"🔍 Buscando eventos posteriores a: {last_sync_time}")
        cursor.execute(QUERY_EVENTS, (last_sync_time,))
        rows = cursor.fetchall()
        
        if not rows:
            logger.info("✅ No hay eventos nuevos para sincronizar")
            conn.close()
            return None, 0, None
        
        logger.info(f"📦 Encontrados {len(rows)} eventos")
        
        # Obtener el timestamp más reciente
        max_timestamp = max(row[1] for row in rows if row[1])
        
        # Convertir a JSON (formato NDJSON para Druid)
        events = []
        for row in rows:
            event = {
                "record_id": str(row[0]),
                "time_stamp_event": row[1].isoformat() if row[1] else None,
                "vehicle_id": row[2],
                "vehicle_plate": row[3],
                "vehicle_company_id": row[4],
                "device_id": row[5],
                "device_imei": row[6],
                "manufacturer_id": row[7],
                "manufacturer_name": row[8],
                "event_id": row[9],
                "event_name": row[10],
                "user_id": row[11],
                "user_username": row[12],
                "user_email": row[13],
                "user_full_name": row[14],
                "user_role": row[15],
                "company_name": row[16],
                "latitude": float(row[17]) if row[17] is not None else 0.0,
                "longitude": float(row[18]) if row[18] is not None else 0.0,
                "altitude": float(row[19]),
                "speed": float(row[20]),
                "angle": float(row[21]),
                "satellites": int(row[22]),
                "hdop": float(row[23]),
                "pdop": float(row[24]),
                "total_odometer": float(row[25]),
                "location_desc": row[26],
                "ip": row[27],
                "reference_id": row[28]
            }
            events.append(event)
        
        # Guardar en archivo NDJSON
        ensure_temp_dir()
        timestamp = int(time.time())
        json_file = os.path.join(TEMP_DIR, f'gps_events_{timestamp}.json')
        
        with open(json_file, 'w', encoding='utf-8') as f:
            for event in events:
                f.write(json.dumps(event) + '\n')
        
        logger.info(f"💾 Datos exportados a: {json_file}")
        
        conn.close()
        return json_file, len(events), max_timestamp
        
    except Exception as e:
        logger.error(f"❌ Error exportando datos: {e}")
        raise

def create_druid_ingestion_spec(data_content):
    """Crear especificación de ingestion para Druid"""
    return {
        "type": "index_parallel",
        "spec": {
            "dataSchema": {
                "dataSource": DRUID_DATASOURCE,
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
                    {"type": "doubleSum", "name": "total_distance", "fieldName": "total_odometer"},
                    {"type": "doubleMax", "name": "max_speed", "fieldName": "speed"},
                    {"type": "doubleMin", "name": "min_speed", "fieldName": "speed"},
                    {"type": "doubleSum", "name": "sum_speed", "fieldName": "speed"},
                    {"type": "longSum", "name": "total_satellites", "fieldName": "satellites"},
                    {"type": "doubleSum", "name": "sum_latitude", "fieldName": "latitude"},
                    {"type": "doubleSum", "name": "sum_longitude", "fieldName": "longitude"}
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

def submit_ingestion_task(json_file_path):
    """Enviar tarea de ingestion a Druid"""
    try:
        # Leer datos
        logger.info("📖 Leyendo archivo JSON...")
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = f.read()
        
        # Crear spec con datos inline
        spec = create_druid_ingestion_spec(data)
        
        url = f"{DRUID_ROUTER_URL}/druid/indexer/v1/task"
        headers = {'Content-Type': 'application/json'}
        
        logger.info("📤 Enviando tarea de ingestion a Druid...")
        response = requests.post(url, json=spec, headers=headers, timeout=30)
        
        if response.status_code == 200:
            task_id = response.json().get('task')
            logger.info(f"✅ Tarea creada: {task_id}")
            return task_id
        else:
            logger.error(f"❌ Error HTTP {response.status_code}")
            logger.error(f"Respuesta: {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"❌ Error enviando tarea: {e}")
        raise

def check_task_status(task_id):
    """Verificar estado de la tarea"""
    try:
        url = f"{DRUID_ROUTER_URL}/druid/indexer/v1/task/{task_id}/status"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            status_data = response.json().get('status', {})
            return status_data.get('status'), status_data
        return None, None
        
    except Exception as e:
        logger.error(f"❌ Error verificando estado: {e}")
        return None, None

def sync_postgres_to_druid():
    """Sincronizar PostgreSQL -> Druid"""
    try:
        ensure_temp_dir()
        last_sync = get_last_sync_time()
        
        # Exportar a JSON
        json_file, record_count, max_timestamp = export_postgres_to_json(last_sync)
        
        if not json_file:
            return 0
        
        # Enviar a Druid
        task_id = submit_ingestion_task(json_file)
        
        if not task_id:
            return 0
        
        # Monitorear estado
        logger.info("⏳ Monitoreando tarea...")
        for i in range(60):  # 10 minutos máximo
            status, status_data = check_task_status(task_id)
            
            if status == "SUCCESS":
                logger.info("✅ Ingestion exitosa!")
                # Guardar timestamp para próxima sincronización
                if max_timestamp:
                    save_last_sync_time(max_timestamp)
                return record_count
            elif status == "FAILED":
                logger.error("❌ Ingestion falló")
                if status_data:
                    logger.error(f"Detalles: {json.dumps(status_data, indent=2)}")
                return 0
            elif status == "RUNNING":
                logger.info(f"⏳ Ejecutando... ({i*10}s)")
            else:
                logger.info(f"⏳ Estado: {status}")
                
            time.sleep(10)
        
        logger.warning("⚠️  Timeout esperando resultado")
        return record_count
        
    except Exception as e:
        logger.error(f"❌ Error en sincronización: {e}")
        raise

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("🚀 SINCRONIZACIÓN PostgreSQL → Druid")
    logger.info("=" * 60)
    
    try:
        records = sync_postgres_to_druid()
        logger.info("=" * 60)
        logger.info(f"✅ ÉXITO: {records} registros sincronizados")
        logger.info("=" * 60)
    except Exception as e:
        logger.error("=" * 60)
        logger.error(f"❌ FALLÓ: {e}")
        logger.error("=" * 60)
        exit(1)