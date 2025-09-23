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
  area_panel numeric(12,4),
  surface_tilt numeric(12,4),
  surface_azimuth numeric(12,4),
  ghi numeric(12,4),
  dhi numeric(12,4),
  dni numeric(12,4),
  dni_extra numeric(12,4),
  temp_air numeric(12,4),
  poa_direct numeric(12,4),
  poa_diffuse numeric(12,4),
  poa_global numeric(12,4),
  iam numeric(12,4),
  effective_irradiance numeric(12,4),
  temp_cell numeric(12,4),
  i_mp numeric(12,4),
  v_mp numeric(12,4),
  p_mp numeric(12,4),
  energy_kwh numeric(12,4),
  energy_mwh numeric(12,4)
);
