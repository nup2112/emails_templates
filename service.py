from pathlib import Path
from typing import List, Optional
import resend
from jinja2 import Environment, FileSystemLoader, select_autoescape
from models import EmailAddress
from emails.base import BaseEmail

class EmailService:
    """Servicio para envío de emails utilizando Resend."""
    def __init__(
        self,
        api_key: str,
        default_from: EmailAddress,
        templates_dir: Optional[str] = None,
        testing: bool = False
    ):
        self.api_key = api_key
        resend.api_key = api_key
        self.default_from = default_from
        self.testing = testing
        
        # Configurar directorio de templates
        if templates_dir is None:
            templates_dir = Path(__file__).parent / 'templates'
        else:
            templates_dir = Path(templates_dir)
            
        if not templates_dir.exists():
            raise ValueError(f"El directorio de templates no existe: {templates_dir}")
            
        self.template_env = Environment(
            loader=FileSystemLoader(templates_dir),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True
        )
    
    def send(
        self,
        email: BaseEmail,
        to: EmailAddress,
        subject: str,
        from_email: Optional[EmailAddress] = None,
        cc: Optional[List[EmailAddress]] = None,
        bcc: Optional[List[EmailAddress]] = None
    ) -> dict:
        """
        Envía un email utilizando Resend.
        
        Args:
            email: Instancia de BaseEmail con los datos del email
            to: Destinatario principal
            subject: Asunto del email
            from_email: Remitente (opcional, usa default_from si no se especifica)
            cc: Lista de destinatarios en copia
            bcc: Lista de destinatarios en copia oculta
            
        Returns:
            dict: Respuesta de la API de Resend
        """
        email.validate()
        
        if not from_email:
            from_email = self.default_from
            
        template = self.template_env.get_template(email.template_name)
        html_content = template.render(**email.get_template_data())
        
        params = {
            "from": str(from_email),
            "to": [str(to)],
            "subject": subject,
            "html": html_content
        }
        
        if cc:
            params["cc"] = [str(addr) for addr in cc]
        if bcc:
            params["bcc"] = [str(addr) for addr in bcc]
            
        if self.testing:
            return params
            
        return resend.Emails.send(params)