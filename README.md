# Sistema de Emails API

Un sistema completo de envío de emails basado en FastAPI con plantillas HTML responsivas y personalizadas.

## ✨ Características

- 🚀 API RESTful construida con FastAPI
- 📧 Múltiples tipos de emails (bienvenida, restablecimiento de contraseña, notificaciones, alertas)
- 🎨 Plantillas HTML responsivas con estilos modernos
- 🔄 Soporte para envío de emails en lote
- 🔒 Autenticación mediante API Key
- 🎯 Personalización de contenido por destinatario
- 📱 Diseño adaptable a dispositivos móviles
- 🌐 Integración con el servicio de Resend para envío confiable

## 📋 Requisitos

- Python 3.8+
- Cuenta en [Resend](https://resend.com) para el envío de emails

## 🛠️ Instalación

1. Clona el repositorio:

```bash
git clone https://github.com/tuusuario/email-system-api.git
cd email-system-api
```

2. Crea y activa un entorno virtual:

```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

3. Instala las dependencias:

```bash
pip install -r requirements.txt
```

## ⚙️ Configuración

1. Crea un archivo `.env` en la raíz del proyecto con las siguientes variables:

```
RESEND_API_KEY=tu_api_key_de_resend
API_KEY=tu_api_key_para_seguridad
DEFAULT_FROM_EMAIL=no-reply@tudominio.com
DEFAULT_FROM_NAME=Nombre de tu empresa
```

2. Personaliza las plantillas HTML en la carpeta `templates` según sea necesario.

## 🚀 Uso

### Iniciar el servidor

```bash
uvicorn api:app --reload
```

El servidor estará disponible en `http://localhost:8000`.

### Documentación interactiva

Accede a la documentación interactiva de la API en:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 📝 Ejemplos de uso

### Enviar un email de bienvenida

```python
import requests
import json

url = "http://localhost:8000/api/emails/welcome"
headers = {
    "X-API-Key": "tu_api_key",
    "Content-Type": "application/json"
}
payload = {
    "company": {
        "name": "Mi Empresa",
        "address": "Calle Principal 123",
        "support_email": "soporte@miempresa.com",
        "website": "https://miempresa.com",
        "social_media": {
            "facebook": "https://facebook.com/miempresa",
            "twitter": "https://twitter.com/miempresa"
        },
        "logo_url": "https://miempresa.com/logo.png"
    },
    "user": {
        "email": "usuario@ejemplo.com",
        "name": "Juan Pérez"
    },
    "query": {
        "dashboard_url": "https://miempresa.com/dashboard"
    }
}

response = requests.post(url, headers=headers, data=json.dumps(payload))
print(response.json())
```

### Enviar notificaciones a múltiples usuarios

```python
import requests
import json

url = "http://localhost:8000/api/emails/batch"
headers = {
    "X-API-Key": "tu_api_key",
    "Content-Type": "application/json"
}
payload = {
    "email_type": "notification",
    "company": {
        "name": "Mi Empresa",
        "address": "Calle Principal 123",
        "support_email": "soporte@miempresa.com",
        "website": "https://miempresa.com",
        "logo_url": "https://miempresa.com/logo.png"
    },
    "recipients": [
        {"email": "usuario1@ejemplo.com", "name": "Usuario Uno"},
        {"email": "usuario2@ejemplo.com", "name": "Usuario Dos"},
        {"email": "usuario3@ejemplo.com", "name": "Usuario Tres"}
    ],
    "query": {
        "title": "Nueva actualización disponible",
        "message": "Hemos lanzado nuevas funciones en nuestra plataforma.",
        "type": "info",
        "action_url": "https://miempresa.com/novedades",
        "action_text": "Ver novedades",
        "preferences_url": "https://miempresa.com/preferencias"
    }
}

response = requests.post(url, headers=headers, data=json.dumps(payload))
print(response.json())
```

## 📡 Endpoints de la API

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/emails/batch` | Envía emails personalizados a múltiples destinatarios en un lote |
| POST | `/api/emails/welcome` | Envía un email de bienvenida |
| POST | `/api/emails/password-reset` | Envía un email de restablecimiento de contraseña |
| POST | `/api/emails/notification` | Envía un email de notificación |
| POST | `/api/emails/alert` | Envía un email de alerta |

## 📁 Estructura del proyecto

```
email-system-api/
├── api.py                 # Aplicación FastAPI principal
├── models.py              # Modelos de datos
├── service.py             # Servicio de emails
├── main.py                # GUI de prueba
├── emails/
│   ├── __init__.py 
│   ├── base.py            # Clase base para emails
│   ├── validation.py      # Utilidades de validación
│   └── templates.py       # Clases para cada tipo de email
├── templates/
│   ├── base.html          # Plantilla base HTML
│   ├── welcome.html       # Plantilla de bienvenida
│   ├── password_reset.html # Plantilla de reset de contraseña
│   ├── notification.html  # Plantilla de notificaciones
│   └── alert.html         # Plantilla de alertas
└── requirements.txt       # Dependencias del proyecto
```

## 🔧 Personalización

### Añadir una nueva plantilla de email

1. Crea un nuevo archivo HTML en la carpeta `templates/`
2. Extiende la plantilla base: `{% extends "base.html" %}`
3. Crea una nueva clase en `emails/templates.py` que extienda `BaseEmail`
4. Añade un nuevo endpoint en `api.py` para el nuevo tipo de email

## 📄 Licencia

Este proyecto está licenciado bajo la Licencia MIT - ver el archivo LICENSE para más detalles.
