from abc import ABC, abstractmethod
from datetime import datetime
from models import Company

class BaseEmail(ABC):
    """Clase base abstracta para todos los tipos de email."""
    template_name: str
    
    def __init__(self, company: Company):
        self.company = company
        self.year = datetime.now().year
    
    @abstractmethod
    def get_template_data(self) -> dict:
        """Retorna los datos base para todas las plantillas."""
        return {
            "company": {
                "name": self.company.name,
                "address": self.company.address,
                "website": self.company.website,
                "support_email": str(self.company.support_email),
                "social_media": self.company.social_media,
                "logo_url": self.company.logo_url
            },
            "year": self.year
        }

    def validate(self) -> None:
        """Valida que todos los datos requeridos estén presentes."""
        if not self.template_name:
            raise ValueError("template_name es requerido")