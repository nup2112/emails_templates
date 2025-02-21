from emails.base import BaseEmail
from models import EmailAddress, Order, NewsletterArticle, Notification, Alert, Company
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

class OrderConfirmationEmail(BaseEmail):
    """Email de confirmación de orden de compra."""
    template_name = "order_confirmation.html"
    
    def __init__(self, company: Company, customer: EmailAddress, order: Order):
        super().__init__(company)
        self.customer = customer
        self.order = order
    
    def get_template_data(self) -> dict:
        data = super().get_template_data()
        data.update({
            "customer": {
                "name": self.customer.name,
                "email": self.customer.email
            },
            "order_info": {
                "number": self.order.number,
                "products": [
                    {
                        "name": item.name,
                        "quantity": item.quantity,
                        "price": f"{item.price:.2f}",
                        "total": f"{item.total:.2f}",
                        "sku": item.sku
                    }
                    for item in self.order.items
                ],
                "total": f"{self.order.total:.2f}",
                "items_count": self.order.items_count,
                "shipping_address": self.order.shipping_address,
                "delivery_estimate": self.order.delivery_estimate,
                "created_at": self.order.created_at.strftime("%d/%m/%Y %H:%M")
            }
        })
        return data

class NewsletterEmail(BaseEmail):
    """Email de newsletter con artículos y contenido."""
    template_name = "newsletter.html"
    
    def __init__(
        self,
        company: Company,
        subscriber: EmailAddress,
        title: str,
        intro: str,
        articles: List[NewsletterArticle],
        unsubscribe_url: str,
        preference_url: str
    ):
        super().__init__(company)
        self.subscriber = subscriber
        self.title = title
        self.intro = intro
        self.articles = articles
        self.unsubscribe_url = unsubscribe_url
        self.preference_url = preference_url
    
    def get_template_data(self) -> dict:
        data = super().get_template_data()
        data.update({
            "subscriber": {
                "name": self.subscriber.name,
                "email": self.subscriber.email
            },
            "newsletter": {
                "title": self.title,
                "intro": self.intro,
                "articles": [
                    {
                        "title": article.title,
                        "image": article.image_url,
                        "excerpt": article.excerpt,
                        "url": article.url,
                        "author": article.author,
                        "reading_time": article.reading_time
                    }
                    for article in self.articles
                ]
            },
            "unsubscribe_url": self.unsubscribe_url,
            "preference_url": self.preference_url
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