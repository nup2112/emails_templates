from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import APIKeyHeader
from typing import List, Optional, Union
from pydantic import BaseModel, EmailStr
import os
from datetime import datetime

from models import (
    Company, EmailAddress, Notification, Alert
)
from service import EmailService
from emails.templates import (
    WelcomeEmail, PasswordResetEmail, NotificationEmail, AlertEmail
)

app = FastAPI(title="Email System API", version="1.0.0")

# Configuración de seguridad
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME)

# Modelos Pydantic para la API
class CompanyBase(BaseModel):
    name: str
    address: str
    support_email: str
    website: str
    social_media: dict = {}
    logo_url: Optional[str] = None

class EmailAddressBase(BaseModel):
    email: EmailStr
    name: Optional[str] = None

class MultiEmailAddressBase(BaseModel):
    emails: List[EmailStr]
    names: Optional[List[str]] = None
    
    def to_email_addresses(self) -> List[EmailAddress]:
        """Convierte el modelo a una lista de objetos EmailAddress"""
        result = []
        for i, email in enumerate(self.emails):
            name = None
            if self.names and i < len(self.names):
                name = self.names[i]
            result.append(EmailAddress(email=email, name=name))
        return result

class OrderItemBase(BaseModel):
    name: str
    quantity: int
    price: float
    sku: Optional[str] = None

class OrderBase(BaseModel):
    number: str
    items: List[OrderItemBase]
    shipping_address: str
    delivery_estimate: str

class NewsletterArticleBase(BaseModel):
    title: str
    image_url: str
    excerpt: str
    url: str
    author: Optional[str] = None
    reading_time: Optional[int] = None

class NotificationBase(BaseModel):
    title: str
    message: str
    type: str
    icon: Optional[str] = None
    action_url: Optional[str] = None
    action_text: Optional[str] = None
    additional_info: Optional[str] = None

class AlertBase(BaseModel):
    title: str
    message: str
    type: str = "info"
    steps: Optional[List[str]] = None
    action_url: Optional[str] = None
    action_text: Optional[str] = None
    contact_support: bool = True

# Configuración del servicio de email
def get_email_service():
    api_key = os.getenv("RESEND_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="RESEND_API_KEY no configurada")
    
    default_from = EmailAddress(
        email=os.getenv("DEFAULT_FROM_EMAIL", "no-reply@example.com"),
        name=os.getenv("DEFAULT_FROM_NAME", "Email System")
    )
    
    return EmailService(api_key=api_key, default_from=default_from)

# Middleware de autenticación
async def verify_api_key(api_key: str = Depends(api_key_header)):
    if api_key != os.getenv("API_KEY"):
        raise HTTPException(
            status_code=403,
            detail="API key inválida"
        )
    return api_key

# Rutas de la API

@app.post("/api/emails/batch")
async def send_batch_emails(
    request_data: dict,  # Recibe todos los datos en un solo objeto
    api_key: str = Depends(verify_api_key)
):
    """
    Envía emails personalizados a múltiples destinatarios en un solo llamado.
    """
    try:
        # Extraer datos del cuerpo
        email_type = request_data.get("email_type")
        company_data = request_data.get("company")
        recipients_data = request_data.get("recipients", [])
        query_data = request_data.get("query", {})
        alert_data = request_data.get("alert")
        
        # Validar datos
        if not email_type:
            raise HTTPException(status_code=400, detail="email_type es requerido")
        if not company_data:
            raise HTTPException(status_code=400, detail="company es requerido")
        if not recipients_data:
            raise HTTPException(status_code=400, detail="recipients es requerido")
        
        # Convertir datos de diccionario a objetos
        company = Company(
            name=company_data.get("name", ""),
            address=company_data.get("address", ""),
            support_email=EmailAddress(
                email=company_data.get("support_email", ""),
                name=company_data.get("name", "")
            ),
            website=company_data.get("website", ""),
            social_media=company_data.get("social_media", {}),
            logo_url=company_data.get("logo_url")
        )
        
        # Obtener el servicio de email
        service = get_email_service()
        
        # Validar que haya destinatarios
        if not recipients_data:
            raise HTTPException(status_code=400, detail="No se proporcionaron destinatarios")
        
        # Obtener el primer destinatario como referencia para la plantilla
        first_recipient = recipients_data[0]
        primary_user = EmailAddress(
            email=first_recipient.get("email", ""),
            name=first_recipient.get("name")
        )
        
        # Crear la instancia de email según el tipo
        if email_type == "welcome":
            if not query_data or 'dashboard_url' not in query_data:
                raise HTTPException(status_code=400, detail="dashboard_url es requerido")
                
            email_obj = WelcomeEmail(
                company=company,
                user=primary_user,
                dashboard_url=query_data.get("dashboard_url")
            )
            subject = f"¡Bienvenido a {company.name}!"
            
        elif email_type == "password-reset":
            if not query_data or 'reset_url' not in query_data:
                raise HTTPException(status_code=400, detail="reset_url es requerido")
                
            email_obj = PasswordResetEmail(
                company=company,
                user=primary_user,
                reset_url=query_data.get("reset_url"),
                expires_in=query_data.get("expires_in", 24)
            )
            subject = "Restablecimiento de contraseña"
            
        elif email_type == "notification":
            if not query_data:
                raise HTTPException(status_code=400, detail="Se requieren datos para la notificación")
                
            notification_obj = Notification(
                title=query_data.get("title", ""),
                message=query_data.get("message", ""),
                type=query_data.get("type", "info"),
                icon=query_data.get("icon"),
                action_url=query_data.get("action_url"),
                action_text=query_data.get("action_text"),
                additional_info=query_data.get("additional_info")
            )
            
            email_obj = NotificationEmail(
                company=company,
                user=primary_user,
                notification=notification_obj,
                preferences_url=query_data.get("preferences_url", "")
            )
            subject = notification_obj.title
            
        elif email_type == "alert":
            if not alert_data:
                raise HTTPException(status_code=400, detail="Se requieren datos para la alerta")
                
            alert_obj = Alert(
                title=alert_data.get("title", ""),
                message=alert_data.get("message", ""),
                type=alert_data.get("type", "info"),
                steps=alert_data.get("steps"),
                action_url=alert_data.get("action_url"),
                action_text=alert_data.get("action_text"),
                contact_support=alert_data.get("contact_support", True)
            )
            
            email_obj = AlertEmail(
                company=company,
                user=primary_user,
                alert=alert_obj
            )
            subject = alert_data.get("title", "Alerta")
            
        else:
            raise HTTPException(status_code=400, detail=f"Tipo de email no válido: {email_type}")
        
        # Procesar cada destinatario para preparar la lista para send_batch
        processed_recipients = []
        
        for recipient in recipients_data:
            if "email" not in recipient:
                continue
            
            processed_recipient = {
                "email": recipient.get("email"),
                "name": recipient.get("name")
            }
            processed_recipients.append(processed_recipient)
        
        # Enviar los emails personalizados en lote
        results = service.send_batch(
            email=email_obj,
            recipients=processed_recipients,
            subject=subject
        )
        
        # Contar éxitos y errores
        success_count = sum(1 for r in results if isinstance(r, dict) and "id" in r)
        error_count = len(results) - success_count
        
        return {
            "status": "success", 
            "sent": success_count,
            "failed": error_count,
            "total": len(results)
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/emails/welcome")
async def send_welcome_email(
    company: CompanyBase,
    user: Union[EmailAddressBase, MultiEmailAddressBase],  # Acepta ambos tipos
    query: dict,
    api_key: str = Depends(verify_api_key)
):
    try:
        service = get_email_service()
        company_obj = Company(**company.model_dump())
        
        # Procesar el o los destinatarios
        if isinstance(user, MultiEmailAddressBase):
            recipients = user.to_email_addresses()
            # Usamos el primer usuario para la plantilla
            primary_user = recipients[0]
        else:
            recipients = [EmailAddress(**user.model_dump())]
            primary_user = recipients[0]
        
        email = WelcomeEmail(
            company=company_obj,
            user=primary_user,  # Usamos el primer usuario para la plantilla
            dashboard_url=query.get('dashboard_url')
        )
        
        result = service.send(
            email=email,
            to=recipients,  # Enviar a todos los destinatarios
            subject=f"¡Bienvenido a {company.name}!"
        )
        
        return {"status": "success", "message_id": result.get("id")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/emails/password-reset")
async def send_password_reset(
    company: CompanyBase,
    user: Union[EmailAddressBase, MultiEmailAddressBase],
    query: dict,
    api_key: str = Depends(verify_api_key)
):
    try:
        service = get_email_service()
        company_obj = Company(**company.model_dump())
        
        # Procesar el o los destinatarios
        if isinstance(user, MultiEmailAddressBase):
            recipients = user.to_email_addresses()
            # Usamos el primer usuario para la plantilla
            primary_user = recipients[0]
        else:
            recipients = [EmailAddress(**user.model_dump())]
            primary_user = recipients[0]
        
        email = PasswordResetEmail(
            company=company_obj,
            user=primary_user,
            reset_url=query.get('reset_url'),
            expires_in=query.get('expires_in', 24)
        )
        
        result = service.send(
            email=email,
            to=recipients,
            subject="Restablecimiento de contraseña"
        )
        
        return {"status": "success", "message_id": result.get("id")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/emails/notification")
async def send_notification(
    company: CompanyBase,
    user: Union[EmailAddressBase, MultiEmailAddressBase],
    query: dict,
    api_key: str = Depends(verify_api_key)
):
    try:
        service = get_email_service()
        company_obj = Company(**company.model_dump())
        
        # Procesar el o los destinatarios
        if isinstance(user, MultiEmailAddressBase):
            recipients = user.to_email_addresses()
            # Usamos el primer usuario para la plantilla
            primary_user = recipients[0]
        else:
            recipients = [EmailAddress(**user.model_dump())]
            primary_user = recipients[0]
        
        notification_obj = Notification(
            title=query.get('title'),
            message=query.get('message'),
            type=query.get('type'),
            icon=query.get('icon'),
            action_url=query.get('action_url'),
            action_text=query.get('action_text'),
            additional_info=query.get('additional_info')
        )
        
        email = NotificationEmail(
            company=company_obj,
            user=primary_user,
            notification=notification_obj,
            preferences_url=query.get('preferences_url')
        )
        
        result = service.send(
            email=email,
            to=recipients,
            subject=notification_obj.title
        )
        
        return {"status": "success", "message_id": result.get("id")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/emails/alert")
async def send_alert(
    company: CompanyBase,
    user: Union[EmailAddressBase, MultiEmailAddressBase],
    alert: AlertBase,
    api_key: str = Depends(verify_api_key)
):
    try:
        service = get_email_service()
        company_obj = Company(**company.model_dump())
        alert_obj = Alert(**alert.model_dump())
        
        # Procesar el o los destinatarios
        if isinstance(user, MultiEmailAddressBase):
            recipients = user.to_email_addresses()
            # Usamos el primer usuario para la plantilla
            primary_user = recipients[0]
        else:
            recipients = [EmailAddress(**user.model_dump())]
            primary_user = recipients[0]
        
        email = AlertEmail(
            company=company_obj,
            user=primary_user,
            alert=alert_obj
        )
        
        result = service.send(
            email=email,
            to=recipients,
            subject=alert.title
        )
        
        return {"status": "success", "message_id": result.get("id")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)