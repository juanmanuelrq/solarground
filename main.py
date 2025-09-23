from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from supabase import create_client, Client
from dotenv import load_dotenv
import os
import json
from datetime import datetime
import uuid
import solarground

# Cargar variables de entorno
load_dotenv()

app = FastAPI(title="Mapa con Herramientas de Dibujo", version="1.0.0")

# Servir archivos estáticos
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configuración de Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")

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





# Funciones de validación manual
def validate_polygon_data(data):
    """Validación manual de los datos del polígono"""
    if not isinstance(data, dict):
        return False, "Los datos deben ser un objeto JSON"
    
    if 'coordinates' not in data:
        return False, "Faltan las coordenadas"
    
    coordinates = data['coordinates']
    if not isinstance(coordinates, list):
        return False, "Las coordenadas deben ser una lista"
    
    if len(coordinates) < 3:
        return False, "Un polígono necesita al menos 3 puntos"
    
    for coord in coordinates:
        if not isinstance(coord, list) or len(coord) != 2:
            return False, "Cada coordenada debe tener [lat, lng]"
        
        try:
            lat, lng = float(coord[0]), float(coord[1])
            if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
                return False, "Coordenadas fuera de rango válido"
        except (ValueError, TypeError):
            return False, "Las coordenadas deben ser números"
    
    return True, "OK"

@app.get("/", response_class=HTMLResponse)
async def get_map():
    """Servir la página HTML principal"""
    try:
        with open("static/index.html", "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        return HTMLResponse(
            content="<h1>Error: Archivo index.html no encontrado en static/</h1>",
            status_code=404
        )

@app.post("/polygons")
async def create_polygon(request: Request):
    """Crear un nuevo polígono en Supabase"""
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="JSON inválido")
    
    # Validación manual
    is_valid, error_msg = validate_polygon_data(data)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)
    
    try:
        # Preparar datos para insertar
        insert_data = {
            'coordinates': data['coordinates'],
            'properties': data.get('properties', {})
        }
        
        # Agregar nombre si existe
        if 'name' in data and data['name']:
            insert_data['name'] = data['name']
        
        result = supabase.table('polygons').insert(insert_data).execute()
        solarground.update_fc_energia_solar()


        if result.data:
            return result.data[0]
        else:
            raise HTTPException(status_code=400, detail="Error creando polígono")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error de base de datos: {str(e)}")

@app.get("/polygons")
async def get_polygons():
    """Obtener todos los polígonos de Supabase"""
    try:
        result = supabase.table('polygons').select('*').order('created_at', desc=True).execute()
        return result.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error de base de datos: {str(e)}")

@app.get("/polygons/{polygon_id}")
async def get_polygon(polygon_id: str):
    """Obtener un polígono específico de Supabase"""
    try:
        result = supabase.table('polygons').select('*').eq('id', polygon_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Polígono no encontrado")
        
        return result.data[0]
    except Exception as e:
        if "no encontrado" in str(e):
            raise e
        raise HTTPException(status_code=500, detail=f"Error de base de datos: {str(e)}")

@app.delete("/polygons/{polygon_id}")
async def delete_polygon(polygon_id: str):
    """Eliminar un polígono específico de Supabase"""
    try:
        result = supabase.table('polygons').delete().eq('id', polygon_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Polígono no encontrado")
        
        return {"message": f"Polígono {polygon_id} eliminado de Supabase"}
    except Exception as e:
        if "no encontrado" in str(e):
            raise e
        raise HTTPException(status_code=500, detail=f"Error de base de datos: {str(e)}")

@app.delete("/polygons/clear")
async def clear_all_polygons():
    """Eliminar todos los polígonos de Supabase"""
    try:
        result = supabase.table('polygons').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
        return {"message": f"{len(result.data) if result.data else 0} polígonos eliminados de Supabase"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error de base de datos: {str(e)}")

@app.put("/polygons/{polygon_id}")
async def update_polygon(polygon_id: str, request: Request):
    """Actualizar un polígono existente en Supabase"""
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="JSON inválido")
    
    try:
        # Construir datos de actualización
        update_data = {}
        
        if 'name' in data:
            update_data['name'] = data['name']
            
        if 'coordinates' in data:
            is_valid, error_msg = validate_polygon_data(data)
            if not is_valid:
                raise HTTPException(status_code=400, detail=error_msg)
            update_data['coordinates'] = data['coordinates']
            
        if 'properties' in data:
            update_data['properties'] = data['properties']
            
        if not update_data:
            raise HTTPException(status_code=400, detail="No hay datos para actualizar")
        
        result = supabase.table('polygons').update(update_data).eq('id', polygon_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Polígono no encontrado")
        
        return result.data[0]
    except Exception as e:
        if "no encontrado" in str(e) or "No hay datos" in str(e) or "JSON inválido" in str(e):
            raise e
        raise HTTPException(status_code=500, detail=f"Error de base de datos: {str(e)}")
    

@app.get("/create_solar_data/{polygon_id}")
async def create_solar_data(polygon_id: str):
    """Generar datos solares para un polígono específico"""
    
    print("polygon_id",polygon_id)
    # Obtener el polígono desde Supabase    

    json_records = solarground.solar_agg(polygon_id)

    try:        
        # Por simplicidad, retornamos un mensaje simulado
        return {"message": f"Datos solares generados para el polígono {json_records}"}
    
    except Exception as e:
        if "no encontrado" in str(e):
            raise e
        raise HTTPException(status_code=500, detail="Error de base de datos: {"+str(e)+str(result)+"}")



@app.get("/health")
async def health_check():
    """Endpoint para verificar la salud de la aplicación y conexión con Supabase"""
    try:
        # Probar conexión con Supabase
        result = supabase.table('polygons').select('id').limit(1).execute()
        return {
            "status": "healthy",
            "supabase": "connected",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Error de conexión con Supabase: {str(e)}")  
