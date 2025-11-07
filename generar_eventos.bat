@echo off
SET PGPASSWORD=admin123
cd /d "C:\Program Files\PostgreSQL\18\bin"
psql -U postgres -d proyecto_mis_datos -c "SELECT generate_random_events(100);" >> "C:\logs\eventos_gps.log" 2>&1
SET PGPASSWORD=