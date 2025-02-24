from emails.base import BaseEmail
from models import EmailAddress, Notification, Alert, Company
from typing import List

class WelcomeEmail(BaseEmail):
    """Email de bienvenida para nuevos usuarios."""
    template_name = "welcome.html"
    
    def __init__(self, company: Company, user: EmailAddress, dashboard_url: str):
        super().__init__(company)
        self.user = user
        self.dashboard_url = dashboard_url
    
    def get_template_data(self) -> dict:
        data = super().get_template_data()
        data.update({
            "user": {
                "name": self.user.name,
                "email": self.user.email
            },
            "dashboard_url": self.dashboard_url
        })
        return data
    
class PasswordResetEmail(BaseEmail):
    """Email para restablecimiento de contraseña."""
    template_name = "password_reset.html"
    
    def __init__(
        self,
        company: Company,
        user: EmailAddress,
        reset_url: str,
        expires_in: int = 24
    ):
        super().__init__(company)
        self.user = user
        self.reset_url = reset_url
        self.expires_in = expires_in
    
    def get_template_data(self) -> dict:
        data = super().get_template_data()
        data.update({
            "user": {
                "name": self.user.name,
                "email": self.user.email
            },
            "reset_url": self.reset_url,
            "expires_in": self.expires_in
        })
        return data

class NotificationEmail(BaseEmail):
    """Email para notificaciones generales."""
    template_name = "notification.html"
    
    def __init__(
        self,
        company: Company,
        user: EmailAddress,
        notification: Notification,
        preferences_url: str
    ):
        super().__init__(company)
        self.user = user
        self.notification = notification
        self.preferences_url = preferences_url
    
    def get_template_data(self) -> dict:
        data = super().get_template_data()
        data.update({
            "user": {
                "name": self.user.name,
                "email": self.user.email
            },
            "notification": {
                "title": self.notification.title,
                "message": self.notification.message,
                "type": self.notification.type,
                "icon": self.notification.icon,
                "action_url": self.notification.action_url,
                "action_text": self.notification.action_text,
                "additional_info": self.notification.additional_info
            },
            "preferences_url": self.preferences_url
        })
        return data

class AlertEmail(BaseEmail):
    """Email para alertas y advertencias."""
    template_name = "alert.html"
    
    def __init__(
        self,
        company: Company,
        user: EmailAddress,
        alert: Alert
    ):
        super().__init__(company)
        self.user = user
        self.alert = alert
    
    def get_template_data(self) -> dict:
        data = super().get_template_data()
        data.update({
            "user": {
                "name": self.user.name,
                "email": self.user.email
            },
            "alert": {
                "title": self.alert.title,
                "message": self.alert.message,
                "type": self.alert.type,
                "steps": self.alert.steps,
                "action_url": self.alert.action_url,
                "action_text": self.alert.action_text,
                "contact_support": self.alert.contact_support
            }
        })
        return data