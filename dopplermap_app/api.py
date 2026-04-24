import frappe
import requests
import json

# =====================================================================
# 1. CONEXIÓN SEGURA CON GOOGLE GEMINI (BACKEND)
# =====================================================================
@frappe.whitelist()
def generar_reporte_gemini(prompt_text):
    """
    Recibe el prompt desde React, busca las credenciales en la base de datos,
    se comunica con Google de forma segura y devuelve el reporte médico.
    """
    try:
        # 1. Obtener la configuración centralizada del DocType que creamos
        config = frappe.get_doc("Configuracion Gemini")
        api_key = config.api_key
        
        # Parámetros dinámicos desde el DocType
        modelo = config.modelo_predeterminado if config.modelo_predeterminado else "gemini-2.5-flash"
        temperatura = config.temperatura if config.temperatura else 0.3
        
        if not api_key:
            frappe.throw("Error: No hay API Key configurada en 'Configuracion Gemini'.")

        # 2. Configurar el Endpoint de Google
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}
        
        # 3. Ensamblar el Payload estricto para Gemini
        payload = {
            "systemInstruction": {
                "parts": [{
                    "text": "Actúa como un ecografista vascular senior. Tu único propósito es redactar un informe médico clínico, estructurado y preciso a partir de una matriz de datos JSON."
                }]
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt_text}]
                }
            ],
            "generationConfig": {
                "temperature": float(temperatura)
            }
        }

        # 4. Petición HTTP segura desde el servidor (no desde el iPad)
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status() 
        
        data = response.json()
        
        # 5. Extraer la respuesta de texto
        if 'candidates' in data and len(data['candidates']) > 0:
            return data['candidates'][0]['content']['parts'][0]['text']
        else:
            return "Error: La IA no devolvió un resultado válido."
            
    except Exception as e:
        frappe.log_error(message=frappe.get_traceback(), title="Error en API Gemini")
        frappe.throw("Fallo de conexión con la IA. Revise los logs del sistema.")


# =====================================================================
# 2. GUARDADO DE DATOS EN EL DOCTYPE 'VASCULAR ENCOUNTER'
# =====================================================================
@frappe.whitelist()
def guardar_doppler_frontend(encounter_id, sistema, reporte_ia, matriz_datos):
    """
    Recibe la orden de 'Culminar Estudio' desde React y guarda la información
    en el encuentro médico correspondiente.
    """
    if not encounter_id:
        frappe.throw("No se proporcionó un ID de Encuentro.")

    try:
        # 1. Cargar el documento original de ERPNext
        doc = frappe.get_doc("Vascular Encounter", encounter_id)
        
        # 2. Mapear los datos a los campos de tu DocType
        # NOTA: Verifica que estos nombres de campos (fieldnames) coincidan con los tuyos
        doc.sistema_evaluado = sistema         
        doc.reporte_ecografico = reporte_ia    
        doc.datos_json_mapa = matriz_datos     
        
        # 3. Guardar cambios
        doc.save(ignore_permissions=False)
        frappe.db.commit() # Asegura la escritura en disco
        
        return "OK"
        
    except Exception as e:
        frappe.log_error(message=frappe.get_traceback(), title="Error al guardar Doppler")
        frappe.throw(f"Error al guardar en la Historia Clínica: {str(e)}")
