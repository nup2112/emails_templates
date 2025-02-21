import sys
import json
import requests
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QTextEdit, QComboBox,
    QTabWidget, QFormLayout, QMessageBox, QGroupBox, QSpinBox
)
from PyQt5.QtCore import Qt

class EmailTesterGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sistema de Emails - Tester")
        self.setMinimumSize(800, 600)
        
        # Configuración inicial
        self.api_url = "http://localhost:8000/api"
        
        # Widget principal
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # Configuración API
        config_group = QGroupBox("Configuración API")
        config_layout = QFormLayout()
        
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.Password)
        config_layout.addRow("API Key:", self.api_key_input)
        
        config_group.setLayout(config_layout)
        layout.addWidget(config_group)
        
        # Pestañas para diferentes tipos de email
        tabs = QTabWidget()
        
        # Pestaña de Email de Bienvenida
        welcome_tab = self.create_welcome_tab()
        tabs.addTab(welcome_tab, "Bienvenida")
        
        # Pestaña de Confirmación de Orden
        order_tab = self.create_order_tab()
        tabs.addTab(order_tab, "Pedido")
        
        # Pestaña de Newsletter
        newsletter_tab = self.create_newsletter_tab()
        tabs.addTab(newsletter_tab, "Newsletter")
        
        # Pestaña de Reset de Contraseña
        password_tab = self.create_password_reset_tab()
        tabs.addTab(password_tab, "Reset Contraseña")
        
        # Pestaña de Notificación
        notification_tab = self.create_notification_tab()
        tabs.addTab(notification_tab, "Notificación")
        
        # Pestaña de Alerta
        alert_tab = self.create_alert_tab()
        tabs.addTab(alert_tab, "Alerta")
        
        layout.addWidget(tabs)
    
    def create_company_group(self):
        group = QGroupBox("Información de la Empresa")
        layout = QFormLayout()
        
        self.company_name = QLineEdit("Mi Empresa")
        self.company_address = QLineEdit("Calle Principal 123")
        self.company_email = QLineEdit("soporte@miempresa.com")
        self.company_website = QLineEdit("https://miempresa.com")
        self.company_logo = QLineEdit("https://miempresa.com/logo.png")
        
        layout.addRow("Nombre:", self.company_name)
        layout.addRow("Dirección:", self.company_address)
        layout.addRow("Email:", self.company_email)
        layout.addRow("Website:", self.company_website)
        layout.addRow("Logo URL:", self.company_logo)
        
        group.setLayout(layout)
        return group
    
    def create_welcome_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        layout.addWidget(self.create_company_group())
        
        # Información del usuario
        user_group = QGroupBox("Información del Usuario")
        user_layout = QFormLayout()
        
        self.welcome_user_name = QLineEdit()
        self.welcome_user_email = QLineEdit()
        self.welcome_dashboard_url = QLineEdit("https://miempresa.com/dashboard")
        
        user_layout.addRow("Nombre:", self.welcome_user_name)
        user_layout.addRow("Email:", self.welcome_user_email)
        user_layout.addRow("Dashboard URL:", self.welcome_dashboard_url)
        
        user_group.setLayout(user_layout)
        layout.addWidget(user_group)
        
        # Botón de envío
        send_button = QPushButton("Enviar Email de Bienvenida")
        send_button.clicked.connect(self.send_welcome_email)
        layout.addWidget(send_button)
        
        layout.addStretch()
        return tab
    
    def create_order_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        layout.addWidget(self.create_company_group())
        
        # Información del cliente
        customer_group = QGroupBox("Información del Cliente")
        customer_layout = QFormLayout()
        
        self.order_customer_name = QLineEdit()
        self.order_customer_email = QLineEdit()
        
        customer_layout.addRow("Nombre:", self.order_customer_name)
        customer_layout.addRow("Email:", self.order_customer_email)
        
        customer_group.setLayout(customer_layout)
        layout.addWidget(customer_group)
        
        # Información del pedido
        order_group = QGroupBox("Información del Pedido")
        order_layout = QFormLayout()
        
        self.order_number = QLineEdit("ORD-001")
        self.order_items = QTextEdit()
        self.order_items.setPlaceholderText("""[
    {"name": "Producto 1", "quantity": 2, "price": 29.99},
    {"name": "Producto 2", "quantity": 1, "price": 49.99}
]""")
        self.shipping_address = QLineEdit("Calle Cliente 456")
        self.delivery_estimate = QLineEdit("2-3 días hábiles")
        
        order_layout.addRow("Número:", self.order_number)
        order_layout.addRow("Items (JSON):", self.order_items)
        order_layout.addRow("Dirección:", self.shipping_address)
        order_layout.addRow("Estimación:", self.delivery_estimate)
        
        order_group.setLayout(order_layout)
        layout.addWidget(order_group)
        
        # Botón de envío
        send_button = QPushButton("Enviar Confirmación de Pedido")
        send_button.clicked.connect(self.send_order_confirmation)
        layout.addWidget(send_button)
        
        layout.addStretch()
        return tab
    
    def create_newsletter_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        layout.addWidget(self.create_company_group())
        
        # Información del suscriptor
        subscriber_group = QGroupBox("Información del Suscriptor")
        subscriber_layout = QFormLayout()
        
        self.newsletter_subscriber_name = QLineEdit()
        self.newsletter_subscriber_email = QLineEdit()
        
        subscriber_layout.addRow("Nombre:", self.newsletter_subscriber_name)
        subscriber_layout.addRow("Email:", self.newsletter_subscriber_email)
        
        subscriber_group.setLayout(subscriber_layout)
        layout.addWidget(subscriber_group)
        
        # Contenido del newsletter
        content_group = QGroupBox("Contenido del Newsletter")
        content_layout = QFormLayout()
        
        self.newsletter_title = QLineEdit("Newsletter Mensual")
        self.newsletter_intro = QTextEdit()
        self.newsletter_articles = QTextEdit()
        self.newsletter_articles.setPlaceholderText("""[
    {
        "title": "Artículo 1",
        "image_url": "https://ejemplo.com/imagen1.jpg",
        "excerpt": "Resumen del artículo 1",
        "url": "https://ejemplo.com/articulo1",
        "author": "Autor 1",
        "reading_time": 5
    }
]""")
        
        content_layout.addRow("Título:", self.newsletter_title)
        content_layout.addRow("Introducción:", self.newsletter_intro)
        content_layout.addRow("Artículos (JSON):", self.newsletter_articles)
        
        content_group.setLayout(content_layout)
        layout.addWidget(content_group)
        
        # URLs
        urls_group = QGroupBox("URLs")
        urls_layout = QFormLayout()
        
        self.unsubscribe_url = QLineEdit("https://miempresa.com/unsubscribe")
        self.preference_url = QLineEdit("https://miempresa.com/preferences")
        
        urls_layout.addRow("Unsubscribe:", self.unsubscribe_url)
        urls_layout.addRow("Preferencias:", self.preference_url)
        
        urls_group.setLayout(urls_layout)
        layout.addWidget(urls_group)
        
        # Botón de envío
        send_button = QPushButton("Enviar Newsletter")
        send_button.clicked.connect(self.send_newsletter)
        layout.addWidget(send_button)
        
        layout.addStretch()
        return tab
    
    def create_password_reset_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        layout.addWidget(self.create_company_group())
        
        # Información del usuario
        user_group = QGroupBox("Información del Usuario")
        user_layout = QFormLayout()
        
        self.reset_user_name = QLineEdit()
        self.reset_user_email = QLineEdit()
        self.reset_url = QLineEdit("https://miempresa.com/reset-password")
        self.expires_in = QSpinBox()
        self.expires_in.setValue(24)
        self.expires_in.setRange(1, 72)
        
        user_layout.addRow("Nombre:", self.reset_user_name)
        user_layout.addRow("Email:", self.reset_user_email)
        user_layout.addRow("Reset URL:", self.reset_url)
        user_layout.addRow("Expira en (horas):", self.expires_in)
        
        user_group.setLayout(user_layout)
        layout.addWidget(user_group)
        
        # Botón de envío
        send_button = QPushButton("Enviar Reset de Contraseña")
        send_button.clicked.connect(self.send_password_reset)
        layout.addWidget(send_button)
        
        layout.addStretch()
        return tab
    
    def create_notification_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        layout.addWidget(self.create_company_group())
        
        # Información del usuario
        user_group = QGroupBox("Información del Usuario")
        user_layout = QFormLayout()
        
        self.notification_user_name = QLineEdit()
        self.notification_user_email = QLineEdit()
        
        user_layout.addRow("Nombre:", self.notification_user_name)
        user_layout.addRow("Email:", self.notification_user_email)
        
        user_group.setLayout(user_layout)
        layout.addWidget(user_group)
        
        # Contenido de la notificación
        notification_group = QGroupBox("Contenido de la Notificación")
        notification_layout = QFormLayout()
        
        self.notification_title = QLineEdit()
        self.notification_message = QTextEdit()
        self.notification_type = QComboBox()
        self.notification_type.addItems(["success", "warning", "error"])
        self.notification_icon = QLineEdit()
        self.notification_action_url = QLineEdit()
        self.notification_action_text = QLineEdit()
        self.notification_additional_info = QTextEdit()
        self.notification_preferences_url = QLineEdit("https://miempresa.com/preferences")
        
        notification_layout.addRow("Título:", self.notification_title)
        notification_layout.addRow("Mensaje:", self.notification_message)
        notification_layout.addRow("Tipo:", self.notification_type)
        notification_layout.addRow("Icono URL:", self.notification_icon)
        notification_layout.addRow("Action URL:", self.notification_action_url)
        notification_layout.addRow("Action Text:", self.notification_action_text)
        notification_layout.addRow("Info Adicional:", self.notification_additional_info)
        notification_layout.addRow("Preferences URL:", self.notification_preferences_url)
        
        notification_group.setLayout(notification_layout)
        layout.addWidget(notification_group)
        
        # Botón de envío
        send_button = QPushButton("Enviar Notificación")
        send_button.clicked.connect(self.send_notification)
        layout.addWidget(send_button)
        
        layout.addStretch()
        return tab
    
    def create_alert_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        layout.addWidget(self.create_company_group())
        
        # Información del usuario
        user_group = QGroupBox("Información del Usuario")
        user_layout = QFormLayout()
        
        self.alert_user_name = QLineEdit()
        self.alert_user_email = QLineEdit()
        
        user_layout.addRow("Nombre:", self.alert_user_name)
        user_layout.addRow("Email:", self.alert_user_email)
        
        user_group.setLayout(user_layout)
        layout.addWidget(user_group)
        
        # Contenido de la alerta
        alert_group = QGroupBox("Contenido de la Alerta")
        alert_layout = QFormLayout()
        
        self.alert_title = QLineEdit()
        self.alert_message = QTextEdit()
        self.alert_type = QComboBox()
        self.alert_type.addItems(["info", "warning", "error"])
        self.alert_steps = QTextEdit()
        self.alert_steps.setPlaceholderText("Un paso por línea")
        self.alert_action_url = QLineEdit()
        self.alert_action_text = QLineEdit()
        
        alert_layout.addRow("Título:", self.alert_title)
        alert_layout.addRow("Mensaje:", self.alert_message)
        alert_layout.addRow("Tipo:", self.alert_type)
        alert_layout.addRow("Pasos:", self.alert_steps)
        alert_layout.addRow("Action URL:", self.alert_action_url)
        alert_layout.addRow("Action Text:", self.alert_action_text)
        
        alert_group.setLayout(alert_layout)
        layout.addWidget(alert_group)
        
        # Botón de envío
        send_button = QPushButton("Enviar Alerta")
        send_button.clicked.connect(self.send_alert)
        layout.addWidget(send_button)
        
        layout.addStretch()
        return tab

    def get_company_data(self):
        """Obtiene los datos de la empresa de los campos del formulario"""
        return {
            "name": self.company_name.text(),
            "address": self.company_address.text(),
            "support_email": self.company_email.text(),
            "website": self.company_website.text(),
            "logo_url": self.company_logo.text(),
            "social_media": {}
        }

    def make_api_request(self, endpoint, data):
        """Realiza una petición a la API con los headers correctos"""
        # Validar API key
        if not self.api_key_input.text():
            QMessageBox.warning(self, "Error", "La API key es requerida")
            return
            
        headers = {
            "X-API-Key": self.api_key_input.text(),
            "Content-Type": "application/json"
        }
        
        try:
            print(f"Realizando petición a: {self.api_url}/emails/{endpoint}")
            response = requests.post(
                f"{self.api_url}/emails/{endpoint}",
                json=data,
                headers=headers
            )
            
            # Imprimir respuesta para debug
            print(f"Código de respuesta: {response.status_code}")
            print(f"Respuesta: {response.text}")
            
            if response.status_code == 200:
                QMessageBox.information(
                    self,
                    "Éxito",
                    f"Email enviado correctamente. ID: {response.json().get('message_id')}"
                )
            else:
                error_detail = "Error desconocido"
                try:
                    error_data = response.json()
                    error_detail = error_data.get('detail', str(error_data))
                except:
                    error_detail = response.text
                    
                QMessageBox.warning(
                    self,
                    "Error",
                    f"Error al enviar el email (código {response.status_code}): {error_detail}"
                )
        except requests.exceptions.ConnectionError:
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudo conectar con la API en {self.api_url}. ¿Está el servidor corriendo?"
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Error inesperado: {str(e)}"
            )

    def send_welcome_email(self):
        """Envía un email de bienvenida"""
        # Validar campos requeridos
        if not self.welcome_user_email.text():
            QMessageBox.warning(self, "Error", "El email del usuario es requerido")
            return
            
        if not self.welcome_dashboard_url.text():
            QMessageBox.warning(self, "Error", "La URL del dashboard es requerida")
            return

        # Validar campos de la empresa
        company_data = self.get_company_data()
        if not company_data["name"] or not company_data["support_email"]:
            QMessageBox.warning(self, "Error", "El nombre de la empresa y email de soporte son requeridos")
            return

        data = {
            "company": company_data,
            "user": {
                "name": self.welcome_user_name.text() or None,
                "email": self.welcome_user_email.text()
            },
            "query": {
                "dashboard_url": self.welcome_dashboard_url.text()
            }
        }
        
        # Imprimir datos para debug
        print("Enviando datos:", json.dumps(data, indent=2))
        
        self.make_api_request("welcome", data)

    def send_order_confirmation(self):
        """Envía una confirmación de pedido"""
        try:
            items = json.loads(self.order_items.toPlainText())
        except json.JSONDecodeError:
            QMessageBox.warning(self, "Error", "El formato JSON de los items no es válido")
            return
        
        data = {
            "company": self.get_company_data(),
            "customer": {
                "name": self.order_customer_name.text(),
                "email": self.order_customer_email.text()
            },
            "order": {
                "number": self.order_number.text(),
                "items": items,
                "shipping_address": self.shipping_address.text(),
                "delivery_estimate": self.delivery_estimate.text()
            }
        }
        self.make_api_request("order-confirmation", data)

    def send_newsletter(self):
        """Envía un newsletter"""
        # Validar campos requeridos
        if not self.newsletter_subscriber_email.text():
            QMessageBox.warning(self, "Error", "El email del suscriptor es requerido")
            return
            
        try:
            articles = json.loads(self.newsletter_articles.toPlainText())
        except json.JSONDecodeError:
            QMessageBox.warning(self, "Error", "El formato JSON de los artículos no es válido")
            return
        
        data = {
            "company": self.get_company_data(),
            "subscriber": {
                "name": self.newsletter_subscriber_name.text() or None,
                "email": self.newsletter_subscriber_email.text()
            },
            "query": {
                "title": self.newsletter_title.text(),
                "intro": self.newsletter_intro.toPlainText(),
                "articles": articles,
                "unsubscribe_url": self.unsubscribe_url.text(),
                "preference_url": self.preference_url.text()
            }
        }
        
        # Imprimir datos para debug
        print("Enviando datos:", json.dumps(data, indent=2))
        
        self.make_api_request("newsletter", data)

    def send_password_reset(self):
        """Envía un email de reset de contraseña"""
        # Validar campos requeridos
        if not self.reset_user_email.text():
            QMessageBox.warning(self, "Error", "El email del usuario es requerido")
            return
            
        if not self.reset_url.text():
            QMessageBox.warning(self, "Error", "La URL de reset es requerida")
            return

        data = {
            "company": self.get_company_data(),
            "user": {
                "name": self.reset_user_name.text() or None,
                "email": self.reset_user_email.text()
            },
            "query": {
                "reset_url": self.reset_url.text(),
                "expires_in": self.expires_in.value()
            }
        }
        
        # Imprimir datos para debug
        print("Enviando datos:", json.dumps(data, indent=2))
        
        self.make_api_request("password-reset", data)

    def send_notification(self):
        """Envía una notificación"""
        # Validar campos requeridos
        if not self.notification_user_email.text():
            QMessageBox.warning(self, "Error", "El email del usuario es requerido")
            return

        data = {
            "company": self.get_company_data(),
            "user": {
                "name": self.notification_user_name.text() or None,
                "email": self.notification_user_email.text()
            },
            "query": {
                "title": self.notification_title.text(),
                "message": self.notification_message.toPlainText(),
                "type": self.notification_type.currentText(),
                "icon": self.notification_icon.text() or None,
                "action_url": self.notification_action_url.text() or None,
                "action_text": self.notification_action_text.text() or None,
                "additional_info": self.notification_additional_info.toPlainText() or None,
                "preferences_url": self.notification_preferences_url.text()
            }
        }
        
        # Imprimir datos para debug
        print("Enviando datos:", json.dumps(data, indent=2))
        
        self.make_api_request("notification", data)

    def send_alert(self):
        """Envía una alerta"""
        steps = [
            step.strip() 
            for step in self.alert_steps.toPlainText().split("\n") 
            if step.strip()
        ]
        
        data = {
            "company": self.get_company_data(),
            "user": {
                "name": self.alert_user_name.text(),
                "email": self.alert_user_email.text()
            },
            "alert": {
                "title": self.alert_title.text(),
                "message": self.alert_message.toPlainText(),
                "type": self.alert_type.currentText(),
                "steps": steps if steps else None,
                "action_url": self.alert_action_url.text() or None,
                "action_text": self.alert_action_text.text() or None,
                "contact_support": True
            }
        }
        self.make_api_request("alert", data)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = EmailTesterGUI()
    window.show()
    sys.exit(app.exec_())