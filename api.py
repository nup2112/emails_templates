from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import APIKeyHeader
from typing import List, Optional
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

@app.post("/api/emails/welcome")
async def send_welcome_email(
    company: CompanyBase,
    user: EmailAddressBase,
    query: dict,
    api_key: str = Depends(verify_api_key)
):
    try:
        service = get_email_service()
        company_obj = Company(**company.model_dump())
        user_obj = EmailAddress(**user.model_dump())
        
        email = WelcomeEmail(
            company=company_obj,
            user=user_obj,
            dashboard_url=query.get('dashboard_url')
        )
        
        result = service.send(
            email=email,
            to=user_obj,
            subject=f"¡Bienvenido a {company.name}!"
        )
        
        return {"status": "success", "message_id": result.get("id")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/emails/password-reset")
async def send_password_reset(
    company: CompanyBase,
    user: EmailAddressBase,
    query: dict,
    api_key: str = Depends(verify_api_key)
):
    try:
        service = get_email_service()
        company_obj = Company(**company.model_dump())
        user_obj = EmailAddress(**user.model_dump())
        
        email = PasswordResetEmail(
            company=company_obj,
            user=user_obj,
            reset_url=query.get('reset_url'),
            expires_in=query.get('expires_in', 24)
        )
        
        result = service.send(
            email=email,
            to=user_obj,
            subject="Restablecimiento de contraseña"
        )
        
        return {"status": "success", "message_id": result.get("id")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/emails/notification")
async def send_notification(
    company: CompanyBase,
    user: EmailAddressBase,
    query: dict,
    api_key: str = Depends(verify_api_key)
):
    try:
        service = get_email_service()
        company_obj = Company(**company.model_dump())
        user_obj = EmailAddress(**user.model_dump())
        
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
            user=user_obj,
            notification=notification_obj,
            preferences_url=query.get('preferences_url')
        )
        
        result = service.send(
            email=email,
            to=user_obj,
            subject=notification_obj.title
        )
        
        return {"status": "success", "message_id": result.get("id")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/emails/alert")
async def send_alert(
    company: CompanyBase,
    user: EmailAddressBase,
    alert: AlertBase,
    api_key: str = Depends(verify_api_key)
):
    try:
        service = get_email_service()
        company_obj = Company(**company.model_dump())
        user_obj = EmailAddress(**user.model_dump())
        alert_obj = Alert(**alert.model_dump())
        
        email = AlertEmail(
            company=company_obj,
            user=user_obj,
            alert=alert_obj
        )
        
        result = service.send(
            email=email,
            to=user_obj,
            subject=alert.title
        )
        
        return {"status": "success", "message_id": result.get("id")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)