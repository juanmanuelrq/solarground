-- Crear tabla para polígonos
CREATE TABLE IF NOT EXISTS polygons (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name TEXT,
    coordinates JSONB NOT NULL,
    properties JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índice para búsquedas rápidas por fecha
CREATE INDEX idx_polygons_created_at ON polygons(created_at);

-- Función para actualizar updated_at automáticamente
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger para actualizar updated_at
CREATE TRIGGER update_polygons_updated_at 
    BEFORE UPDATE ON polygons 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Habilitar RLS (Row Level Security) si necesitas control de acceso
-- ALTER TABLE polygons ENABLE ROW LEVEL SECURITY;

-- Política para permitir todas las operaciones (ajusta según tus necesidades)
-- CREATE POLICY "Enable all operations for polygons" ON polygons FOR ALL USING (true);



CREATE TABLE "fc_energia_solar" (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  polygons_id uuid,
  date_day date,
  geometry jsonb,
  latitude float8,
  longitude float8,
  area_panel float8,
  surface_tilt float8,
  surface_azimuth float8,
  ghi float8,
  dhi float8,
  dni float8,
  dni_extra float8,
  temp_air float8,
  poa_direct float8,
  poa_diffuse float8,
  poa_global float8,
  iam float8,
  effective_irradiance float8,
  temp_cell float8,
  i_mp float8,
  v_mp float8,
  p_mp float8,
  energy_kwh float8,
  energy_mwh float8
);
