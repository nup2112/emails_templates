import sys
import json
import requests
import tempfile
import os
import webbrowser
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QTextEdit, QComboBox,
    QTabWidget, QFormLayout, QMessageBox, QGroupBox, QSpinBox,
    QSplitter, QDialog, QCheckBox, QTextBrowser, QFileDialog
)
from PyQt5.QtCore import Qt
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape

class EmailPreviewDialog(QDialog):
    def __init__(self, html_content, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Vista Previa del Email")
        self.resize(800, 600)
        self.html_content = html_content
        
        layout = QVBoxLayout(self)
        
        # Usando QTextBrowser como alternativa a QWebEngineView
        self.text_browser = QTextBrowser()
        self.text_browser.setHtml(html_content)
        self.text_browser.setOpenExternalLinks(True)
        
        layout.addWidget(self.text_browser)
        
        # Botones
        button_layout = QHBoxLayout()
        
        # Añadir opción para abrir en navegador
        open_browser_button = QPushButton("Abrir en Navegador")
        open_browser_button.clicked.connect(self.open_in_browser)
        button_layout.addWidget(open_browser_button)
        
        # Añadir opción para guardar HTML
        save_button = QPushButton("Guardar HTML")
        save_button.clicked.connect(self.save_html)
        button_layout.addWidget(save_button)
        
        button_layout.addStretch()
        
        close_button = QPushButton("Cerrar")
        close_button.clicked.connect(self.accept)
        button_layout.addWidget(close_button)
        
        layout.addLayout(button_layout)
    
    def open_in_browser(self):
        try:
            # Crear un archivo temporal para visualizar en el navegador
            # Especificar encoding='utf-8' para manejar caracteres Unicode
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.html', encoding='utf-8') as f:
                f.write(self.html_content)
                temp_name = f.name
            
            # Abrir el archivo en el navegador
            webbrowser.open('file://' + temp_name)
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudo abrir en el navegador: {str(e)}"
            )
    
    def save_html(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Guardar HTML", "", "Archivos HTML (*.html *.htm)"
        )
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.html_content)
                QMessageBox.information(self, "Éxito", f"HTML guardado en: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo guardar el archivo: {str(e)}")

class EmailTesterGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sistema de Emails - Tester")
        self.setMinimumSize(1000, 700)
        
        # Inicialización de atributos
        self.api_url = "http://localhost:8000/api"
        self.templates_dir_input = None  # Inicializado aquí para evitar errores
        self.template_env = None
        
        # Widget principal
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # Configuración API y Templates
        config_group = self.create_config_group()
        layout.addWidget(config_group)
        
        # Ahora que templates_dir_input existe, podemos configurar el motor de plantillas
        self.setup_template_engine()
        
        # Pestañas para diferentes tipos de email
        self.tabs = QTabWidget()
        
        # Pestaña de Email de Bienvenida
        welcome_tab = self.create_welcome_tab()
        self.tabs.addTab(welcome_tab, "Bienvenida")
        
        # Pestaña de Reset de Contraseña
        password_tab = self.create_password_reset_tab()
        self.tabs.addTab(password_tab, "Reset Contraseña")
        
        # Pestaña de Notificación
        notification_tab = self.create_notification_tab()
        self.tabs.addTab(notification_tab, "Notificación")
        
        # Pestaña de Alerta
        alert_tab = self.create_alert_tab()
        self.tabs.addTab(alert_tab, "Alerta")
        
        layout.addWidget(self.tabs)
    
    def create_config_group(self):
        """Crea el grupo de configuración API y directorio de plantillas"""
        config_group = QGroupBox("Configuración")
        config_layout = QFormLayout()
        
        # API Key
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.Password)
        config_layout.addRow("API Key:", self.api_key_input)
        
        # Directorio de plantillas
        self.templates_dir_input = QLineEdit()
        self.templates_dir_input.setReadOnly(True)
        browse_button = QPushButton("Explorar...")
        browse_button.clicked.connect(self.browse_templates_dir)
        
        templates_layout = QHBoxLayout()
        templates_layout.addWidget(self.templates_dir_input)
        templates_layout.addWidget(browse_button)
        
        config_layout.addRow("Directorio de Plantillas:", templates_layout)
        
        config_group.setLayout(config_layout)
        return config_group
    
    def browse_templates_dir(self):
        directory = QFileDialog.getExistingDirectory(
            self, "Seleccionar Directorio de Plantillas"
        )
        if directory:
            self.templates_dir_input.setText(directory)
            self.setup_template_engine(directory)
    
    def setup_template_engine(self, custom_dir=None):
        """Configura el motor de plantillas Jinja2"""
        # No hacer nada si templates_dir_input no existe aún
        if not hasattr(self, 'templates_dir_input') or self.templates_dir_input is None:
            return
            
        if custom_dir:
            templates_dir = Path(custom_dir)
        else:
            # Intenta encontrar templates en diferentes ubicaciones
            templates_dir = None
            possible_paths = [
                Path("./templates"),
                Path("../templates"),
                Path(__file__).parent / "templates"
            ]
            
            for path in possible_paths:
                if path.exists():
                    templates_dir = path
                    self.templates_dir_input.setText(str(templates_dir))
                    break
            
            # Si no se encuentra ningún directorio, usar el directorio actual
            if templates_dir is None:
                templates_dir = Path(".")
                self.templates_dir_input.setText(str(templates_dir))
                print("Advertencia: No se encontró un directorio de plantillas válido.")
        
        try:
            self.template_env = Environment(
                loader=FileSystemLoader(templates_dir),
                autoescape=select_autoescape(['html', 'xml']),
                trim_blocks=True,
                lstrip_blocks=True
            )
            print(f"Motor de plantillas configurado con el directorio: {templates_dir}")
        except Exception as e:
            print(f"Error al configurar el motor de plantillas: {str(e)}")
            if custom_dir:  # Solo mostrar mensaje si fue solicitado por el usuario
                QMessageBox.warning(
                    self,
                    "Advertencia",
                    f"No se pudo configurar el motor de plantillas: {str(e)}"
                )
        
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
        
        self.welcome_user_name = QLineEdit("Usuario de Prueba")
        self.welcome_user_email = QLineEdit("usuario@ejemplo.com")
        self.welcome_dashboard_url = QLineEdit("https://miempresa.com/dashboard")
        
        user_layout.addRow("Nombre:", self.welcome_user_name)
        user_layout.addRow("Email:", self.welcome_user_email)
        user_layout.addRow("Dashboard URL:", self.welcome_dashboard_url)
        
        user_group.setLayout(user_layout)
        layout.addWidget(user_group)
        
        # Botones
        button_layout = QHBoxLayout()
        
        preview_button = QPushButton("Vista Previa")
        preview_button.clicked.connect(lambda: self.preview_email("welcome"))
        button_layout.addWidget(preview_button)
        
        send_button = QPushButton("Enviar Email de Bienvenida")
        send_button.clicked.connect(self.send_welcome_email)
        button_layout.addWidget(send_button)
        
        layout.addLayout(button_layout)
        
        layout.addStretch()
        return tab
        
    def create_password_reset_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        layout.addWidget(self.create_company_group())
        
        # Información del usuario
        user_group = QGroupBox("Información del Usuario")
        user_layout = QFormLayout()
        
        self.reset_user_name = QLineEdit("Usuario de Prueba")
        self.reset_user_email = QLineEdit("usuario@ejemplo.com")
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
        
        # Botones
        button_layout = QHBoxLayout()
        
        preview_button = QPushButton("Vista Previa")
        preview_button.clicked.connect(lambda: self.preview_email("password_reset"))
        button_layout.addWidget(preview_button)
        
        send_button = QPushButton("Enviar Reset de Contraseña")
        send_button.clicked.connect(self.send_password_reset)
        button_layout.addWidget(send_button)
        
        layout.addLayout(button_layout)
        
        layout.addStretch()
        return tab
    
    def create_notification_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        layout.addWidget(self.create_company_group())
        
        # Información del usuario
        user_group = QGroupBox("Información del Usuario")
        user_layout = QFormLayout()
        
        self.notification_user_name = QLineEdit("Usuario de Prueba")
        self.notification_user_email = QLineEdit("usuario@ejemplo.com")
        
        user_layout.addRow("Nombre:", self.notification_user_name)
        user_layout.addRow("Email:", self.notification_user_email)
        
        user_group.setLayout(user_layout)
        layout.addWidget(user_group)
        
        # Contenido de la notificación
        notification_group = QGroupBox("Contenido de la Notificación")
        notification_layout = QFormLayout()
        
        self.notification_title = QLineEdit("Notificación Importante")
        self.notification_message = QTextEdit("Este es un mensaje de notificación de prueba.")
        self.notification_type = QComboBox()
        self.notification_type.addItems(["success", "warning", "error"])
        self.notification_icon = QLineEdit("https://miempresa.com/icons/notification.png")
        self.notification_action_url = QLineEdit("https://miempresa.com/action")
        self.notification_action_text = QLineEdit("Ver Detalles")
        self.notification_additional_info = QTextEdit("Información adicional sobre esta notificación.")
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
        
        # Botones
        button_layout = QHBoxLayout()
        
        preview_button = QPushButton("Vista Previa")
        preview_button.clicked.connect(lambda: self.preview_email("notification"))
        button_layout.addWidget(preview_button)
        
        send_button = QPushButton("Enviar Notificación")
        send_button.clicked.connect(self.send_notification)
        button_layout.addWidget(send_button)
        
        layout.addLayout(button_layout)
        
        layout.addStretch()
        return tab
    
    def create_alert_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        layout.addWidget(self.create_company_group())
        
        # Información del usuario
        user_group = QGroupBox("Información del Usuario")
        user_layout = QFormLayout()
        
        self.alert_user_name = QLineEdit("Usuario de Prueba")
        self.alert_user_email = QLineEdit("usuario@ejemplo.com")
        
        user_layout.addRow("Nombre:", self.alert_user_name)
        user_layout.addRow("Email:", self.alert_user_email)
        
        user_group.setLayout(user_layout)
        layout.addWidget(user_group)
        
        # Contenido de la alerta
        alert_group = QGroupBox("Contenido de la Alerta")
        alert_layout = QFormLayout()
        
        self.alert_title = QLineEdit("Alerta de Seguridad")
        self.alert_message = QTextEdit("Este es un mensaje de alerta de prueba.")
        self.alert_type = QComboBox()
        self.alert_type.addItems(["info", "warning", "error"])
        self.alert_steps = QTextEdit("Paso 1: Verificar conexión\nPaso 2: Actualizar contraseña\nPaso 3: Cerrar sesiones")
        self.alert_steps.setPlaceholderText("Un paso por línea")
        self.alert_action_url = QLineEdit("https://miempresa.com/action")
        self.alert_action_text = QLineEdit("Resolver Ahora")
        self.alert_contact_support = QCheckBox("Incluir información de soporte")
        self.alert_contact_support.setChecked(True)
        
        alert_layout.addRow("Título:", self.alert_title)
        alert_layout.addRow("Mensaje:", self.alert_message)
        alert_layout.addRow("Tipo:", self.alert_type)
        alert_layout.addRow("Pasos:", self.alert_steps)
        alert_layout.addRow("Action URL:", self.alert_action_url)
        alert_layout.addRow("Action Text:", self.alert_action_text)
        alert_layout.addRow("", self.alert_contact_support)
        
        alert_group.setLayout(alert_layout)
        layout.addWidget(alert_group)
        
        # Botones
        button_layout = QHBoxLayout()
        
        preview_button = QPushButton("Vista Previa")
        preview_button.clicked.connect(lambda: self.preview_email("alert"))
        button_layout.addWidget(preview_button)
        
        send_button = QPushButton("Enviar Alerta")
        send_button.clicked.connect(self.send_alert)
        button_layout.addWidget(send_button)
        
        layout.addLayout(button_layout)
        
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
            "social_media": {
                "facebook": "https://facebook.com/miempresa",
                "twitter": "https://twitter.com/miempresa",
                "instagram": "https://instagram.com/miempresa"
            }
        }

    def preview_email(self, email_type):
        """Genera una vista previa del email según el tipo seleccionado"""
        try:
            if not self.template_env:
                QMessageBox.warning(
                    self,
                    "Error",
                    "No se ha configurado el motor de plantillas. Por favor, seleccione el directorio de plantillas."
                )
                return
                
            template_name = f"{email_type}.html"
            try:
                template = self.template_env.get_template(template_name)
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"No se pudo cargar la plantilla '{template_name}': {str(e)}\n"
                    f"Verifique que el archivo existe en el directorio de plantillas: {self.templates_dir_input.text()}"
                )
                return
            
            # Preparar los datos según el tipo de email
            if email_type == "welcome":
                data = {
                    "company": self.get_company_data(),
                    "user": {
                        "name": self.welcome_user_name.text(),
                        "email": self.welcome_user_email.text()
                    },
                    "dashboard_url": self.welcome_dashboard_url.text(),
                    "year": 2025
                }
            elif email_type == "password_reset":
                data = {
                    "company": self.get_company_data(),
                    "user": {
                        "name": self.reset_user_name.text(),
                        "email": self.reset_user_email.text()
                    },
                    "reset_url": self.reset_url.text(),
                    "expires_in": self.expires_in.value(),
                    "year": 2025
                }
            elif email_type == "notification":
                data = {
                    "company": self.get_company_data(),
                    "user": {
                        "name": self.notification_user_name.text(),
                        "email": self.notification_user_email.text()
                    },
                    "notification": {
                        "title": self.notification_title.text(),
                        "message": self.notification_message.toPlainText(),
                        "type": self.notification_type.currentText(),
                        "icon": self.notification_icon.text(),
                        "action_url": self.notification_action_url.text(),
                        "action_text": self.notification_action_text.text(),
                        "additional_info": self.notification_additional_info.toPlainText()
                    },
                    "preferences_url": self.notification_preferences_url.text(),
                    "year": 2025
                }
            elif email_type == "alert":
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
                        "steps": steps,
                        "action_url": self.alert_action_url.text(),
                        "action_text": self.alert_action_text.text(),
                        "contact_support": self.alert_contact_support.isChecked()
                    },
                    "year": 2025
                }
            
            # Renderizar la plantilla
            html_content = template.render(**data)
            
            # Mostrar el diálogo de vista previa
            preview_dialog = EmailPreviewDialog(html_content, self)
            preview_dialog.exec_()
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error en la Vista Previa",
                f"No se pudo generar la vista previa: {str(e)}"
            )

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
                "contact_support": self.alert_contact_support.isChecked()
            }
        }
        self.make_api_request("alert", data)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = EmailTesterGUI()
    window.show()
    sys.exit(app.exec_())