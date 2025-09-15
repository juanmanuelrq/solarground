from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
import json

app = FastAPI(title="Mapa con Herramientas de Dibujo", version="1.0.0")

# Almacenamiento temporal de polígonos
polygons_storage = {}
polygon_counter = 0

@app.get("/", response_class=HTMLResponse)
async def get_map():
    """Retorna la página HTML con el mapa interactivo"""
    html_content = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Mapa con Herramientas de Dibujo</title>
        
        <!-- Leaflet CSS -->
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        
        <!-- Leaflet Draw CSS -->
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet.draw/1.0.4/leaflet.draw.css" />
        
        <style>
            body {
                margin: 0;
                padding: 20px;
                font-family: Arial, sans-serif;
            }
            
            #map {
                height: 600px;
                width: 100%;
                border: 2px solid #333;
                border-radius: 10px;
            }
            
            .controls {
                margin: 20px 0;
                padding: 15px;
                background-color: #f5f5f5;
                border-radius: 10px;
            }
            
            .btn {
                background-color: #007bff;
                color: white;
                border: none;
                padding: 10px 15px;
                margin: 5px;
                border-radius: 5px;
                cursor: pointer;
            }
            
            .btn:hover {
                background-color: #0056b3;
            }
            
            .btn-danger {
                background-color: #dc3545;
            }
            
            .btn-danger:hover {
                background-color: #c82333;
            }
            
            .info-panel {
                margin-top: 20px;
                padding: 15px;
                background-color: #e9ecef;
                border-radius: 10px;
            }
            
            .polygon-item {
                background-color: white;
                margin: 10px 0;
                padding: 10px;
                border-radius: 5px;
                border: 1px solid #ddd;
            }
        </style>
    </head>
    <body>
        <h1>🗺️ Mapa con Herramientas de Dibujo de Polígonos</h1>
        
        <div class="controls">
            <button class="btn" onclick="enablePolygonDrawing()">✏️ Dibujar Polígono</button>
            <button class="btn" onclick="toggleEditMode()">✂️ Editar Polígonos</button>
            <button class="btn btn-danger" onclick="clearAllPolygons()">🗑️ Limpiar Todo</button>
            <button class="btn" onclick="loadPolygons()">🔄 Cargar Polígonos</button>
        </div>
        
        <div id="map"></div>
        
        <div class="info-panel">
            <h3>📊 Polígonos Guardados</h3>
            <div id="polygonsList"></div>
        </div>

        <!-- Leaflet JS -->
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        
        <!-- Leaflet Draw JS -->
        <script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet.draw/1.0.4/leaflet.draw.js"></script>

        <script>
            // Inicializar el mapa centrado en Medellín, Colombia
            const map = L.map('map').setView([6.2442, -75.5812], 12);

            // Agregar capa de OpenStreetMap
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '© OpenStreetMap contributors'
            }).addTo(map);

            // Grupo de capas para los polígonos
            const drawnItems = new L.FeatureGroup();
            map.addLayer(drawnItems);

            // Configurar controles de dibujo
            const drawControl = new L.Control.Draw({
                position: 'topright',
                draw: {
                    polygon: {
                        allowIntersection: false,
                        drawError: {
                            color: '#e1e100',
                            message: '<strong>Error:</strong> Las líneas del polígono no pueden cruzarse!'
                        },
                        shapeOptions: {
                            color: '#97009c',
                            weight: 3,
                            fillOpacity: 0.3
                        }
                    },
                    polyline: false,
                    circle: false,
                    rectangle: false,
                    marker: false,
                    circlemarker: false
                },
                edit: {
                    featureGroup: drawnItems,
                    remove: true
                }
            });

            map.addControl(drawControl);

            // Evento cuando se crea un polígono
            map.on('draw:created', function (e) {
                const layer = e.layer;
                const coordinates = layer.getLatLngs()[0].map(latlng => [latlng.lat, latlng.lng]);
                
                // Agregar el polígono al mapa
                drawnItems.addLayer(layer);
                
                // Guardar el polígono en el servidor
                savePolygon(coordinates, {
                    color: layer.options.color || '#97009c',
                    created_at: new Date().toISOString()
                });
                
                // Agregar popup con información
                layer.bindPopup(`
                    <div>
                        <strong>Polígono</strong><br>
                        Puntos: ${coordinates.length}<br>
                        <button onclick="deletePolygonFromMap('${layer._leaflet_id}')">Eliminar</button>
                    </div>
                `);
            });

            // Evento cuando se edita un polígono
            map.on('draw:edited', function (e) {
                const layers = e.layers;
                layers.eachLayer(function (layer) {
                    const coordinates = layer.getLatLngs()[0].map(latlng => [latlng.lat, latlng.lng]);
                    console.log('Polígono editado:', coordinates);
                    // Aquí podrías actualizar el polígono en el servidor
                });
            });

            // Evento cuando se elimina un polígono
            map.on('draw:deleted', function (e) {
                console.log('Polígonos eliminados');
                updatePolygonsList();
            });

            // Funciones para los botones de control
            function enablePolygonDrawing() {
                alert('Usa las herramientas de dibujo en la esquina superior derecha del mapa');
            }

            function toggleEditMode() {
                alert('Usa las herramientas de edición en la esquina superior derecha del mapa');
            }

            function clearAllPolygons() {
                if (confirm('¿Estás seguro de que quieres eliminar todos los polígonos?')) {
                    drawnItems.clearLayers();
                    fetch('/polygons/clear', { method: 'DELETE' })
                        .then(response => response.json())
                        .then(data => {
                            console.log('Polígonos eliminados del servidor');
                            updatePolygonsList();
                        })
                        .catch(error => console.error('Error:', error));
                }
            }

            function loadPolygons() {
                fetch('/polygons')
                    .then(response => response.json())
                    .then(polygons => {
                        drawnItems.clearLayers();
                        
                        polygons.forEach(polygon => {
                            const latlngs = polygon.coordinates.map(coord => [coord[0], coord[1]]);
                            const polygonLayer = L.polygon(latlngs, {
                                color: polygon.properties.color || '#97009c',
                                weight: 3,
                                fillOpacity: 0.3
                            });
                            
                            polygonLayer.bindPopup(`
                                <div>
                                    <strong>Polígono ${polygon.id}</strong><br>
                                    Puntos: ${polygon.coordinates.length}<br>
                                    Creado: ${polygon.properties.created_at || 'N/A'}
                                </div>
                            `);
                            
                            drawnItems.addLayer(polygonLayer);
                        });
                        
                        updatePolygonsList();
                    })
                    .catch(error => console.error('Error cargando polígonos:', error));
            }

            // Función para guardar polígono en el servidor
            async function savePolygon(coordinates, properties) {
                try {
                    const response = await fetch('/polygons', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            coordinates: coordinates,
                            properties: properties
                        })
                    });
                    
                    if (response.ok) {
                        const result = await response.json();
                        console.log('Polígono guardado:', result);
                        updatePolygonsList();
                    } else {
                        console.error('Error guardando polígono');
                    }
                } catch (error) {
                    console.error('Error:', error);
                }
            }

            // Función para actualizar la lista de polígonos
            function updatePolygonsList() {
                fetch('/polygons')
                    .then(response => response.json())
                    .then(polygons => {
                        const listElement = document.getElementById('polygonsList');
                        if (polygons.length === 0) {
                            listElement.innerHTML = '<p>No hay polígonos guardados</p>';
                            return;
                        }
                        
                        listElement.innerHTML = polygons.map(polygon => `
                            <div class="polygon-item">
                                <strong>Polígono ${polygon.id}</strong> - 
                                ${polygon.coordinates.length} puntos
                                <br>
                                <small>Creado: ${polygon.properties.created_at || 'N/A'}</small>
                            </div>
                        `).join('');
                    })
                    .catch(error => console.error('Error:', error));
            }

            // Cargar polígonos al inicio
            loadPolygons();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

def validate_polygon_data(data):
    """Validación manual básica de los datos del polígono"""
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

@app.post("/polygons")
async def create_polygon(request: Request):
    """Crear un nuevo polígono sin Pydantic"""
    global polygon_counter
    
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="JSON inválido")
    
    # Validación manual
    is_valid, error_msg = validate_polygon_data(data)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)
    
    polygon_counter += 1
    polygon_id = f"polygon_{polygon_counter}"
    
    # Obtener propiedades o usar vacío
    properties = data.get('properties', {})
    
    polygons_storage[polygon_id] = {
        "id": polygon_id,
        "coordinates": data['coordinates'],
        "properties": properties
    }
    
    return {
        "id": polygon_id,
        "coordinates": data['coordinates'],
        "properties": properties
    }

@app.get("/polygons")
async def get_polygons():
    """Obtener todos los polígonos"""
    return list(polygons_storage.values())

@app.get("/polygons/{polygon_id}")
async def get_polygon(polygon_id: str):
    """Obtener un polígono específico"""
    if polygon_id not in polygons_storage:
        raise HTTPException(status_code=404, detail="Polígono no encontrado")
    
    return polygons_storage[polygon_id]

@app.delete("/polygons/{polygon_id}")
async def delete_polygon(polygon_id: str):
    """Eliminar un polígono específico"""
    if polygon_id not in polygons_storage:
        raise HTTPException(status_code=404, detail="Polígono no encontrado")
    
    del polygons_storage[polygon_id]
    return {"message": f"Polígono {polygon_id} eliminado"}

@app.delete("/polygons/clear")
async def clear_all_polygons():
    """Eliminar todos los polígonos"""
    global polygons_storage
    polygons_storage = {}
    return {"message": "Todos los polígonos han sido eliminados"}

@app.put("/polygons/{polygon_id}")
async def update_polygon(polygon_id: str, request: Request):
    """Actualizar un polígono existente"""
    if polygon_id not in polygons_storage:
        raise HTTPException(status_code=404, detail="Polígono no encontrado")
    
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="JSON inválido")
    
    # Validación manual
    is_valid, error_msg = validate_polygon_data(data)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)
    
    polygons_storage[polygon_id].update({
        "coordinates": data['coordinates'],
        "properties": data.get('properties', {})
    })
    
    return polygons_storage[polygon_id]

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
