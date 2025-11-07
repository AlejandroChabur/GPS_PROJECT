"""
Sincronización PostgreSQL -> Cassandra
Python 3.12 compatible: usando psycopg2 (más compatible con gevent)
"""
import os
import sys

# Configurar el event loop de Cassandra ANTES de importarlo
os.environ['CASSANDRA_DRIVER_EVENT_LOOP_FACTORY'] = 'cassandra.io.geventreactor.GeventConnection'

# Aplicar gevent monkey patch
from gevent import monkey
monkey.patch_all()

# Usar psycopg2 en lugar de psycopg3 (mejor compatibilidad con gevent)
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    USING_PSYCOPG2 = True
except ImportError:
    import psycopg
    USING_PSYCOPG2 = False

from cassandra.cluster import Cluster
from cassandra.policies import DCAwareRoundRobinPolicy
from datetime import datetime, timedelta
import logging
import traceback
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ==================== CONFIGURACIÓN ====================
PG_CONFIG = {
    'host': '127.0.0.1',
    'port': 5432,
    'dbname': 'proyecto_mis_datos',
    'user': 'postgres',
    'password': 'admin123'
}

CASSANDRA_HOSTS = ['127.0.0.1']
CASSANDRA_PORT = 9042
CASSANDRA_KEYSPACE = 'gps_tracking'

# ==================== QUERIES ====================
QUERY_EVENTS = """
SELECT 
    er.record_id, er.time_stamp_event, er.vehicle_id,
    v.plate, v.company_id,
    er.device_id, d.imei, d.manufacturer_id, m.manufacturer_name,
    er.event_id, et.event_name, et.properties,
    er.user_id, u.username, u.email, u.full_name, u.role,
    c.company_name,
    ST_Y(er.geom::geometry) as latitude,
    ST_X(er.geom::geometry) as longitude,
    er.altitude, er.speed, er.angle, er.satellites, er.hdop, er.pdop,
    er.total_odometer, er.location_desc, er.ip, er.reference_id,
    er.created_at, er.updated_at, er.deleted_at
FROM event_record er
INNER JOIN vehicle v ON er.vehicle_id = v.vehicle_id
INNER JOIN device d ON er.device_id = d.device_id
INNER JOIN manufacturer m ON d.manufacturer_id = m.manufacturer_id
INNER JOIN event_type et ON er.event_id = et.event_id
INNER JOIN company c ON v.company_id = c.company_id
LEFT JOIN "user" u ON er.user_id = u.user_id
WHERE er.time_stamp_event > %s AND er.deleted_at IS NULL
ORDER BY er.time_stamp_event DESC LIMIT 1000;
"""

INSERT_EVENT = """
INSERT INTO event_record (
    vehicle_id, time_stamp_event, record_id,
    vehicle_plate, vehicle_company_id,
    device_id, device_imei, device_manufacturer_id, manufacturer_name,
    event_id, event_name, event_properties,
    user_id, user_username, user_email, user_full_name, user_role,
    company_name, latitude, longitude, altitude, speed, angle,
    satellites, hdop, pdop, total_odometer,
    location_desc, ip, reference_id,
    created_at, updated_at, deleted_at
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
"""

def safe_str(value):
    """Convertir valores a string seguro"""
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return json.dumps(value)
    return str(value)

def get_last_sync_timestamp(session):
    try:
        result = session.execute("SELECT MAX(time_stamp_event) as last_sync FROM event_record LIMIT 1;")
        row = result.one()
        if row and row.last_sync:
            logger.info(f"📅 Último timestamp: {row.last_sync}")
            return row.last_sync
        logger.info("📅 No hay datos, sincronizando últimos 7 días")
        return datetime.now() - timedelta(days=7)
    except Exception as e:
        logger.warning(f"⚠️  Error: {e}")
        return datetime.now() - timedelta(hours=1)

def connect_postgres():
    """Conectar a PostgreSQL con la librería disponible"""
    if USING_PSYCOPG2:
        logger.info("🔌 Conectando a PostgreSQL con psycopg2...")
        conn = psycopg2.connect(
            host=PG_CONFIG['host'],
            port=PG_CONFIG['port'],
            dbname=PG_CONFIG['dbname'],
            user=PG_CONFIG['user'],
            password=PG_CONFIG['password']
        )
        logger.info("✅ PostgreSQL conectado (psycopg2)")
        return conn, conn.cursor()
    else:
        logger.info("🔌 Conectando a PostgreSQL con psycopg3...")
        conn_string = f"host={PG_CONFIG['host']} port={PG_CONFIG['port']} " \
                     f"dbname={PG_CONFIG['dbname']} user={PG_CONFIG['user']} " \
                     f"password={PG_CONFIG['password']} sslmode=disable"
        conn = psycopg.connect(conn_string)
        logger.info("✅ PostgreSQL conectado (psycopg3)")
        return conn, conn.cursor()

def sync_postgres_to_cassandra():
    pg_conn = None
    cassandra_session = None
    cluster = None
    
    try:
        logger.info("🔌 Conectando a Cassandra...")
        
        # Conectar Cassandra PRIMERO
        load_balancing_policy = DCAwareRoundRobinPolicy(local_dc='dc1')
        
        cluster = Cluster(
            CASSANDRA_HOSTS,
            port=CASSANDRA_PORT,
            load_balancing_policy=load_balancing_policy,
            protocol_version=5
        )
        
        cassandra_session = cluster.connect(CASSANDRA_KEYSPACE)
        logger.info("✅ Cassandra conectado")
        
        # Conectar PostgreSQL
        pg_conn, pg_cursor = connect_postgres()
        
        prepared = cassandra_session.prepare(INSERT_EVENT)
        last_sync = get_last_sync_timestamp(cassandra_session)
        logger.info(f"🔍 Buscando registros > {last_sync}")
        
        pg_cursor.execute(QUERY_EVENTS, (last_sync,))
        rows = pg_cursor.fetchall()
        
        if not rows:
            logger.info("✅ No hay nuevos registros")
            return 0
        
        logger.info(f"📦 {len(rows)} registros encontrados")
        
        inserted = 0
        errors = 0
        
        for row in rows:
            try:
                event_props = safe_str(row[11])
                
                cassandra_session.execute(prepared, (
                    row[2], row[1], row[0],
                    safe_str(row[3]), row[4],
                    row[5], safe_str(row[6]), row[7], safe_str(row[8]),
                    row[9], safe_str(row[10]), event_props,
                    row[12], safe_str(row[13]), safe_str(row[14]),
                    safe_str(row[15]), safe_str(row[16]),
                    safe_str(row[17]),
                    row[18], row[19], row[20], row[21], row[22],
                    row[23], row[24], row[25], row[26],
                    safe_str(row[27]), safe_str(row[28]), safe_str(row[29]),
                    row[30], row[31], row[32]
                ))
                inserted += 1
                
                if inserted % 100 == 0:
                    logger.info(f"⏳ {inserted}/{len(rows)} ({int(inserted/len(rows)*100)}%)")
                    
            except Exception as e:
                errors += 1
                if errors <= 3:
                    logger.error(f"❌ Error en registro {row[0]}: {e}")
                continue
        
        logger.info(f"🎉 Completado: {inserted} insertados, {errors} errores")
        return inserted
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        traceback.print_exc()
        raise
        
    finally:
        if pg_conn:
            pg_conn.close()
            logger.info("🔌 PostgreSQL cerrado")
        if cassandra_session:
            cassandra_session.shutdown()
        if cluster:
            cluster.shutdown()
            logger.info("🔌 Cassandra cerrado")

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("🚀 SINCRONIZACIÓN PostgreSQL → Cassandra (Python 3.12)")
    logger.info("=" * 60)
    
    try:
        records = sync_postgres_to_cassandra()
        logger.info("=" * 60)
        logger.info(f"✅ ÉXITO: {records} registros sincronizados")
        logger.info("=" * 60)
    except Exception as e:
        logger.error("=" * 60)
        logger.error(f"❌ FALLÓ: {e}")
        logger.error("=" * 60)
        exit(1)