-- ================================================
-- KEYSPACE: gps_tracking
-- ================================================
CREATE KEYSPACE IF NOT EXISTS gps_tracking
WITH replication = {
    'class': 'SimpleStrategy',
    'replication_factor': 3
};

USE gps_tracking;

-- ================================================
-- TABLA PRINCIPAL: event_record
-- DESNORMALIZADA: Todos los datos de evento + joins
-- ================================================
CREATE TABLE IF NOT EXISTS event_record (
    vehicle_id int,
    time_stamp_event timestamp,
    record_id bigint,
    
    -- Datos del evento
    created_at timestamp,
    updated_at timestamp,
    deleted_at timestamp,
    ip text,
    location_desc text,
    altitude decimal,
    angle decimal,
    satellites smallint,
    speed decimal,
    hdop decimal,
    pdop decimal,
    total_odometer decimal,
    reference_id text,
    
    -- Coordenadas (desnormalizado de PostGIS)
    latitude double,
    longitude double,
    
    -- Información desnormalizada de VEHICLE
    vehicle_plate text,
    vehicle_company_id int,
    
    -- Información desnormalizada de DEVICE
    device_id int,
    device_imei text,
    device_manufacturer_id int,
    
    -- Información desnormalizada de EVENT_TYPE
    event_id int,
    event_name text,
    event_properties text,
    
    -- Información desnormalizada de USER
    user_id int,
    user_username text,
    user_email text,
    user_full_name text,
    user_role text,
    
    -- Información desnormalizada de COMPANY
    company_name text,
    
    -- Información desnormalizada de MANUFACTURER
    manufacturer_name text,
    
    PRIMARY KEY ((vehicle_id), time_stamp_event, record_id)
) WITH CLUSTERING ORDER BY (time_stamp_event DESC, record_id DESC)
  AND compaction = {
      'class': 'TimeWindowCompactionStrategy',
      'compaction_window_size': '1',
      'compaction_window_unit': 'DAYS'
  }
  AND default_time_to_live = 7776000
  AND gc_grace_seconds = 86400
  AND comment = 'Eventos GPS desnormalizados ordenados por vehículo y timestamp';

-- Índices secundarios para búsquedas alternativas
CREATE INDEX IF NOT EXISTS idx_device ON event_record (device_id);
CREATE INDEX IF NOT EXISTS idx_event ON event_record (event_id);
CREATE INDEX IF NOT EXISTS idx_user ON event_record (user_id);
CREATE INDEX IF NOT EXISTS idx_company ON event_record (vehicle_company_id);
CREATE INDEX IF NOT EXISTS idx_vehicle_plate ON event_record (vehicle_plate);

-- ================================================
-- TABLA: event_by_device
-- Para consultas por dispositivo
-- ================================================
CREATE TABLE IF NOT EXISTS event_by_device (
    device_id int,
    time_stamp_event timestamp,
    record_id bigint,
    vehicle_id int,
    vehicle_plate text,
    event_name text,
    latitude double,
    longitude double,
    speed decimal,
    company_name text,
    PRIMARY KEY ((device_id), time_stamp_event, record_id)
) WITH CLUSTERING ORDER BY (time_stamp_event DESC, record_id DESC)
  AND comment = 'Eventos ordenados por dispositivo';

-- ================================================
-- TABLA: event_by_company
-- Para consultas por empresa
-- ================================================
CREATE TABLE IF NOT EXISTS event_by_company (
    vehicle_company_id int,
    time_stamp_event timestamp,
    record_id bigint,
    vehicle_id int,
    vehicle_plate text,
    device_imei text,
    event_name text,
    latitude double,
    longitude double,
    speed decimal,
    user_username text,
    PRIMARY KEY ((vehicle_company_id), time_stamp_event, record_id)
) WITH CLUSTERING ORDER BY (time_stamp_event DESC, record_id DESC)
  AND comment = 'Eventos ordenados por empresa';

-- ================================================
-- TABLA: event_summary_by_vehicle_day
-- Resumen diario por vehículo
-- ================================================
CREATE TABLE IF NOT EXISTS event_summary_by_vehicle_day (
    vehicle_id int,
    date date,
    vehicle_plate text,
    company_name text,
    total_events bigint,
    total_distance decimal,
    avg_speed decimal,
    max_speed decimal,
    min_speed decimal,
    total_odometer_start decimal,
    total_odometer_end decimal,
    PRIMARY KEY ((vehicle_id), date)
) WITH CLUSTERING ORDER BY (date DESC)
  AND comment = 'Resumen diario de eventos por vehículo';

-- ================================================
-- TABLAS DE CATÁLOGO (Desnormalizadas para joins)
-- ================================================

CREATE TABLE IF NOT EXISTS vehicle (
    vehicle_id int PRIMARY KEY,
    plate text,
    company_id int,
    company_name text
);

CREATE TABLE IF NOT EXISTS device (
    device_id int PRIMARY KEY,
    imei text,
    manufacturer_id int,
    manufacturer_name text
);

CREATE TABLE IF NOT EXISTS company (
    company_id int PRIMARY KEY,
    company_name text
);

CREATE TABLE IF NOT EXISTS user_info (
    user_id int PRIMARY KEY,
    username text,
    email text,
    full_name text,
    role text,
    company_id int,
    company_name text,
    is_active boolean
);

CREATE TABLE IF NOT EXISTS manufacturer (
    manufacturer_id int PRIMARY KEY,
    manufacturer_name text
);

CREATE TABLE IF NOT EXISTS event_type (
    event_id int PRIMARY KEY,
    event_name text,
    properties text
);