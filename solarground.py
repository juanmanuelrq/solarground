
import pvlib
import pandas as pd
import geopandas as gpd
from supabase import create_client, Client

import os
from dotenv import load_dotenv
load_dotenv()

# Configuración de Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")

# Crear cliente
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Autenticación con usuario y contraseña
email = os.getenv("SUPABASE_USER")  # Reemplaza con el correo del usuario
password = os.getenv("SUPABASE_PASSWORD")  # Reemplaza con la contraseña

auth_response = supabase.auth.sign_in_with_password({
    "email": email,
    "password": password
})

# Verificar si la autenticación fue exitosa
if auth_response.user:
    print("Autenticación exitosa:", auth_response.user.email)
else:
    print("Error de autenticación:", auth_response)


agg_calcs={'latitude': 'mean',             # Latitud promedio, grados
  'longitude': 'mean',            # Longitud promedio, grados
  'area_panel': 'mean',           # Área promedio de un panel solar, m²
  'surface_tilt': 'mean',         # Inclinación de superficie promedio, grados
  'surface_azimuth': 'mean',      # Azimut de superficie promedio, grados
  'ghi': 'sum',                   # Suma de la irradiación global horizontal, W/m²
  'dhi': 'sum',                   # Suma de la irradiación difusa horizontal, W/m²
  'dni': 'sum',                   # Suma de la irradiación normal directa, W/m²
  'dni_extra': 'sum',             # Suma de la irradiación extraterrestre, W/m²
  'temp_air': 'mean',             # Temperatura del aire promedio, °C
  'poa_direct': 'sum',            # Suma de la irradiancia directa en el plano del arreglo, W/m²
  'poa_diffuse': 'sum',           # Suma de la irradiancia difusa en el plano del arreglo, W/m²
  'poa_global': 'sum',            # Suma de la irradiancia global en el plano del arreglo, W/m²
  'iam': 'mean',                  # Coeficiente de ángulo de incidencia medio, sin unidad
  'effective_irradiance': 'sum',  # Suma de la irradiancia efectiva en el plano del arreglo, W/m²
  'temp_cell': 'mean',            # Temperatura promedio de la célula del panel, °C
  'i_mp': 'sum',                  # Suma de la corriente en el punto de máxima potencia, A
  'v_mp': 'sum',                  # Suma del voltaje en el punto de máxima potencia, V
  'p_mp': 'sum',                  # Suma de la potencia en el punto de máxima potencia, W
  'energy_kwh': 'sum',            # Suma de la energía generada, kWh
  'energy_mwh': 'sum',            # Suma de la energía generada, MWh
}


CECMODS = pvlib.pvsystem.retrieve_sam('CECMod')
INVERTERS = pvlib.pvsystem.retrieve_sam('CECInverter')

CECMOD_POLY = CECMODS['Canadian_Solar_Inc__CS6X_300P']
CECMOD_MONO = CECMODS['Canadian_Solar_Inc__CS6X_300M']

# here's a trick, transpose the database, and search the index using
# strings
INVERTERS.T[INVERTERS.T.index.str.startswith('SMA_America__STP')]

# that was almost too easy, let's use the 60-kW Sunny TriPower, it's a good inverter.
INVERTER_60K = INVERTERS['SMA_America__STP_60_US_10__480V_']


def solar_calculations(latitude, longitude,YEAR,surface_albedo):
    #data, months, inputs, meta = pvlib.iotools.get_pvgis_tmy(latitude, longitude)
    data, meta = pvlib.iotools.get_pvgis_tmy(latitude, longitude)
    STARTDATE = '%d-01-01T00:00:00' % YEAR
    ENDDATE = '%d-12-31T23:59:59' % YEAR
    #TIMES = pd.date_range(start=STARTDATE, end=ENDDATE, freq='H')
    TIMES = pd.date_range(start=STARTDATE, periods=len(data), freq='H')
    # get solar position
    data.index = TIMES
    
    sp = pvlib.solarposition.get_solarposition(
          TIMES, latitude, longitude)
    solar_zenith = sp.apparent_zenith.values
    solar_azimuth = sp.azimuth.values
    
    # get tracker positions
    tracker = pvlib.tracking.singleaxis(solar_zenith, solar_azimuth)
    surface_tilt = tracker['surface_tilt']
    surface_azimuth = tracker['surface_azimuth']
    aoi = tracker['aoi']
    
    # get irradiance
    dni = data['dni'].values
    ghi = data['ghi'].values
    dhi = data['dhi'].values
    
    temp_air = data['temp_air'].values
    dni_extra = pvlib.irradiance.get_extra_radiation(TIMES).values
    
    # we use the Hay Davies transposition model
    poa_sky_diffuse = pvlib.irradiance.get_sky_diffuse(
          surface_tilt, surface_azimuth, solar_zenith, solar_azimuth,
          dni, ghi, dhi, dni_extra=dni_extra, model='haydavies')
    poa_ground_diffuse = pvlib.irradiance.get_ground_diffuse(
          surface_tilt, ghi, albedo=surface_albedo)
    poa = pvlib.irradiance.poa_components(
          aoi, dni, poa_sky_diffuse, poa_ground_diffuse)
    poa_direct = poa['poa_direct']
    poa_diffuse = poa['poa_diffuse']
    poa_global = poa['poa_global']
    iam = pvlib.iam.ashrae(aoi)
    effective_irradiance = poa_direct*iam + poa_diffuse
    
    # module temperature
    temp_cell = pvlib.temperature.pvsyst_cell(poa_global, temp_air)
    
    # finally this is the magic
    cecparams = pvlib.pvsystem.calcparams_cec(
          effective_irradiance, temp_cell,
          CECMOD_MONO.alpha_sc, CECMOD_MONO.a_ref,
          CECMOD_MONO.I_L_ref, CECMOD_MONO.I_o_ref,
          CECMOD_MONO.R_sh_ref, CECMOD_MONO.R_s, CECMOD_MONO.Adjust)
    mpp = pvlib.pvsystem.max_power_point(*cecparams, method='newton')
    mpp = pd.DataFrame(mpp, index=TIMES)
    
    
    mpp['ghi']=ghi
    mpp['dhi']=dhi
    mpp['dni']=dni
    
    mpp['surface_tilt']=surface_tilt
    mpp['surface_azimuth']=surface_azimuth
    mpp['dni_extra']=dni_extra
    mpp['temp_air']=temp_air
    mpp['poa_direct']=poa_direct
    mpp['poa_diffuse']=poa_diffuse
    mpp['poa_global']=poa_global
    mpp['iam']=iam
    mpp['effective_irradiance']=effective_irradiance
    mpp['temp_cell']=temp_cell
    
    return mpp


surface_albedo = 0.25 #Albedo de la superficie
YEAR = 2023 #Año de simulación
area_disp = 0.8  #m2 de panel por m2 de terreno disponible
efficiency = 0.18  #Eficiencia del panel

def solar_agg(polygon_id):

      result = supabase.table('polygons').select('*').eq('id', polygon_id).execute()

      polygon = result.data[0]

      coordinates = polygon['coordinates']

      # Lista original en formato [lon, lat]
      #coords_lon_lat = [[-75.5782, 6.2783], [-75.5770, 6.2790], [-75.5760, 6.2780]]
      #en la base de datos las coordenadas están en [lng, lat]
      coords_lon_lat = coordinates

      # Convertir a [lat, lon]
      coords_lat_lon = [[lat, lon] for lon, lat in coords_lon_lat]

      geojson = {
      "type": "FeatureCollection",
      "features": [{"type": "Feature",
      "properties": {},
      "geometry": {"type": "Polygon",
      "coordinates": [coords_lat_lon]}}]
      }
      gdf = gpd.GeoDataFrame.from_features(geojson["features"])
            
      # Asignar CRS WGS 84
      gdf.set_crs(epsg=4326, inplace=True)
      #gdf = gdf.to_crs(epsg=3857)  # Por ejemplo, a Web Mercator
      #gdf['centroid'] = gdf.geometry.centroid
      
      gdf=gdf.to_crs(epsg=3395)  #EPSG 3395 utiliza metros
      
      gdf['area_panel'] = gdf.geometry.area

      gdf = gdf.to_crs(epsg=4326)
      gdf['centroid'] = gdf.geometry.centroid  # recalcular en lat/lon
      
      df_list = []

      for index, row in gdf.iterrows():
    
            latitude, longitude, area_panel,geometry = row['centroid'].y, row['centroid'].x, row['area_panel'], row['geometry']
              
            df_sol=solar_calculations(latitude, longitude,YEAR,surface_albedo)

            df_sol['latitude']=latitude
            df_sol['longitude']=longitude
            df_sol['area_panel']=area_panel
            df_sol['energy_kwh']=(df_sol['p_mp']*area_panel*area_disp*efficiency)/1000
            df_sol['energy_mwh']=df_sol['energy_kwh']/1000
            df_sol['geometry']=geometry
            #print(df_sol.ghi.sum())

            df_list.append(df_sol)

            # Concatenar todos los DataFrames en uno solo
            final_df = pd.concat(df_list)

            df=final_df.reset_index().rename(columns={'index': 'date'})

            #AGRUPAR DATOS
            df['date'] = pd.to_datetime(df['date'])  # Asegurar que es datetime
            df['geometry'] = df['geometry'].astype(str)

            # Agrupar por mes y calcular la energía generada
            df_day= df.groupby([df['date'].dt.to_period('D'),df['geometry']]).agg(agg_calcs).reset_index()

            # Agrupar por mes y calcular la energía generada
            df_month = df.groupby([df['date'].dt.to_period('M'),df['geometry']]).agg(agg_calcs).reset_index()

            df_month['dias_por_mes'] = df.groupby([df['date'].dt.to_period('M'), df['geometry']]).size().values
            df_month['ghi_kwh_dia']=(df_month['ghi']/df_month['dias_por_mes'])/1000

            df_year = df.groupby([df['date'].dt.to_period('Y'),df['geometry']]).agg(agg_calcs).reset_index()
            df_year['ghi_kwh_dia']=(df_year['ghi']/365)/1000

            df_day['date'] = df_day['date'].astype(str)
            df_day = df_day.rename(columns={'date': 'date_day'})
            df_day['polygons_id'] = polygon_id



      json_records = df_day.to_dict(orient='records')

      if auth_response.user:
            print("Autenticación exitosa:", auth_response.user.email)

            # Insertar datos en la tabla
            result = supabase.table('fc_energia_solar').insert(json_records).execute()
            print("Resultado de la inserción:", result)
      else:
            print("Error de autenticación:", auth_response)

      return df_day, df_month, df_year


def update_fc_energia_solar():

      response = supabase.table('polygons_without_solar').select('*').execute()

      # Acceder a los datos
      for item in response.data:
            print(item['id'])
            solar_agg(item['id'])
            
      return "Proceso completado"

