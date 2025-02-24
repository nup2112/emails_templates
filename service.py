from pathlib import Path
from typing import List, Optional, Union, Dict, Any
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
        to: Union[EmailAddress, List[EmailAddress]],
        subject: str,
        from_email: Optional[EmailAddress] = None,
        cc: Optional[List[EmailAddress]] = None,
        bcc: Optional[List[EmailAddress]] = None,
        personalize: bool = False
    ) -> Union[dict, List[dict]]:
        """
        Envía un email utilizando Resend.
        
        Args:
            email: Instancia de BaseEmail con los datos del email
            to: Destinatario principal o lista de destinatarios
            subject: Asunto del email
            from_email: Remitente (opcional, usa default_from si no se especifica)
            cc: Lista de destinatarios en copia
            bcc: Lista de destinatarios en copia oculta
            personalize: Si es True, se generará un email personalizado para cada destinatario
            
        Returns:
            dict o List[dict]: Respuesta(s) de la API de Resend
        """
        email.validate()
        
        if not from_email:
            from_email = self.default_from
            
        # Convertir a lista si es un solo destinatario
        if not isinstance(to, list):
            to = [to]
            
        # Si no se requiere personalización, enviar email tradicional
        if not personalize:
            template = self.template_env.get_template(email.template_name)
            html_content = template.render(**email.get_template_data())
            
            params = {
                "from": str(from_email),
                "to": [str(addr) for addr in to],
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
            
        # Si se requiere personalización, enviar emails separados a cada destinatario
        results = []
        
        for recipient in to:
            # Modificar los datos de la plantilla para este destinatario
            template_data = email.get_template_data()
            
            # Actualizar el usuario en los datos de la plantilla con este destinatario
            if 'user' in template_data:
                template_data['user'] = {
                    'name': recipient.name or template_data['user'].get('name', 'Usuario'),
                    'email': recipient.email
                }
                
            # Renderizar la plantilla con los datos personalizados
            template = self.template_env.get_template(email.template_name)
            html_content = template.render(**template_data)
            
            # Preparar los parámetros para esta persona
            params = {
                "from": str(from_email),
                "to": str(recipient),
                "subject": subject,
                "html": html_content
            }
            
            # Enviar el email personalizado
            if self.testing:
                results.append(params)
            else:
                result = resend.Emails.send(params)
                results.append(result)
                
        return results
    
    def send_batch(
        self,
        email: BaseEmail,
        recipients: List[Dict[str, Any]],
        subject: str,
        from_email: Optional[EmailAddress] = None
    ) -> List[dict]:
        """
        Envía emails personalizados a múltiples destinatarios en un lote.
        
        Args:
            email: Instancia de BaseEmail con la plantilla base
            recipients: Lista de diccionarios con datos de los destinatarios
                        Cada dict debe tener al menos 'email' y opcionalmente 'name'
                        Puede tener datos adicionales para personalizar el contenido
            subject: Asunto del email
            from_email: Remitente (opcional, usa default_from si no se especifica)
            
        Returns:
            List[dict]: Lista de respuestas de la API de Resend
        """
        email.validate()
        
        if not from_email:
            from_email = self.default_from
        
        # Validar que haya destinatarios
        if not recipients:
            raise ValueError("No se proporcionaron destinatarios")
        
        # Enviar emails personalizados a cada destinatario
        results = []
        
        for recipient_data in recipients:
            # Validar que el destinatario tenga email
            if 'email' not in recipient_data:
                continue
                
            # Crear objeto EmailAddress para este destinatario
            recipient = EmailAddress(
                email=recipient_data['email'],
                name=recipient_data.get('name', '')
            )
            
            # Obtener los datos base de la plantilla
            template_data = email.get_template_data()
            
            # Crear una copia de los datos de usuario para no modificar el original
            if 'user' in template_data:
                # Crear una copia del usuario
                user_data = dict(template_data['user'])
                # Actualizar con los datos de este destinatario
                user_data['name'] = recipient.name or user_data.get('name', 'Usuario')
                user_data['email'] = recipient.email
                # Reemplazar en los datos de la plantilla
                template_data['user'] = user_data
            
            # Renderizar la plantilla con los datos personalizados
            template = self.template_env.get_template(email.template_name)
            html_content = template.render(**template_data)
            
            # Preparar los parámetros para esta persona
            params = {
                "from": str(from_email),
                "to": str(recipient),
                "subject": subject,
                "html": html_content
            }
            
            # Enviar el email personalizado
            if self.testing:
                results.append(params)
            else:
                try:
                    result = resend.Emails.send(params)
                    results.append(result)
                except Exception as e:
                    # Registrar el error pero continuar con los demás destinatarios
                    print(f"Error enviando a {recipient.email}: {str(e)}")
                    results.append({"error": str(e), "email": recipient.email})
                
        return results