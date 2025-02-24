from dataclasses import dataclass, field
from typing import List, Optional, Dict
from datetime import datetime

@dataclass
class EmailAddress:
    """Representa una dirección de correo electrónico con nombre opcional."""
    email: str
    name: Optional[str] = None

    def __str__(self) -> str:
        return f"{self.name} <{self.email}>" if self.name else self.email

    def __post_init__(self):
        if not isinstance(self.email, str) or '@' not in self.email:
            raise ValueError("Dirección de email inválida")

@dataclass
class Company:
    """Información de la empresa para uso en las plantillas de email."""
    name: str
    address: str
    support_email: EmailAddress
    website: str
    social_media: Dict[str, str] = field(default_factory=dict)
    logo_url: Optional[str] = None

@dataclass
class Notification:
    """Representa una notificación para enviar por email."""
    title: str
    message: str
    type: str
    icon: Optional[str] = None
    action_url: Optional[str] = None
    action_text: Optional[str] = None
    additional_info: Optional[str] = None

@dataclass
class Alert:
    """Representa una alerta para enviar por email."""
    title: str
    message: str
    type: str = "info"  # 'info', 'warning', 'error'
    steps: Optional[List[str]] = None
    action_url: Optional[str] = None
    action_text: Optional[str] = None
    contact_support: bool = True