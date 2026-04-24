import frappe
import requests
import json

# =====================================================================
# 1. CONEXIÓN SEGURA CON GOOGLE GEMINI (BACKEND)
# =====================================================================
@frappe.whitelist()
def generar_reporte_gemini(prompt_text):
    try:
        # 1. Obtener configuración
        config = frappe.get_doc("Configuracion Gemini")
        api_key = config.api_key
        frappe.log_error(f"API Key leída: {api_key[:10]}... (longitud: {len(api_key)})", "Gemini Debug")        
        modelo = config.modelo_predeterminado or "gemini-2.5-flash"
        # Asegurar que temperatura sea float
        temperatura = float(config.temperatura) if config.temperatura else 0.3

        if not api_key:
            frappe.throw("Error: No hay API Key configurada en 'Configuracion Gemini'.")

        # 2. Construir payload MÍNIMO para probar (funciona seguro)
        payload = {
            "contents": [{"parts": [{"text": prompt_text}]}]
        }

        # 3. Opcional: añadir systemInstruction y generationConfig de forma controlada
        # Puedes ir agregando uno a uno para identificar el error
        payload["systemInstruction"] = {
            "parts": [{
                "text": "Actúa como un ecografista vascular senior. Tu único propósito es redactar un informe médico clínico, estructurado y preciso a partir de una matriz de datos JSON."
            }]
        }
        payload["generationConfig"] = {
            "temperature": temperatura
        }

        # 4. Logger para depuración (verás el payload en Error Log de Frappe)
        frappe.log_error(f"Payload enviado a Gemini: {json.dumps(payload, indent=2)}", "Gemini Payload")

        # 5. Petición
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}
        response = requests.post(url, headers=headers, json=payload, timeout=30)

        # 6. Si hay error, registrar la respuesta completa y lanzar excepción
        if response.status_code != 200:
            error_msg = f"Error {response.status_code}: {response.text}"
            frappe.log_error(error_msg, "Gemini Error")
            frappe.throw(f"Google Gemini respondió con error: {error_msg}")

        data = response.json()

        # 7. Extraer texto
        candidates = data.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            if parts:
                return parts[0].get("text", "No se encontró texto en la respuesta.")
        return "No se pudo generar el informe."

    except Exception as e:
        frappe.log_error(message=frappe.get_traceback(), title="Error en API Gemini")
        frappe.throw(f"Error interno: {str(e)}")


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
