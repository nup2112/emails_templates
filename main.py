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
from emails.validation import validate_email, validate_emails

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

class EmailRecipientsDialog(QDialog):
    """Diálogo para gestionar múltiples destinatarios con nombres personalizados"""
    def __init__(self, parent=None, emails=None, names=None):
        super().__init__(parent)
        self.setWindowTitle("Gestionar Destinatarios")
        self.resize(500, 400)
        
        layout = QVBoxLayout(self)
        
        # Instrucciones
        instructions = QLabel("Ingrese un email y nombre por línea, separados por coma o punto y coma.\nEjemplo: juan@ejemplo.com, Juan Pérez")
        layout.addWidget(instructions)
        
        # Campo de texto para ingresar destinatarios
        self.recipients_text = QTextEdit()
        self.recipients_text.setPlaceholderText("email1@ejemplo.com, Nombre 1\nemail2@ejemplo.com, Nombre 2")
        
        # Si se proporcionan emails, llenar el campo
        if emails:
            text_lines = []
            for i, email in enumerate(emails):
                name = ""
                if names and i < len(names) and names[i]:
                    name = names[i]
                text_lines.append(f"{email}, {name}" if name else email)
            self.recipients_text.setText("\n".join(text_lines))
        
        layout.addWidget(self.recipients_text)
        
        # Contador de destinatarios
        self.counter = QLabel("0 destinatarios")
        self.counter.setStyleSheet("color: gray;")
        layout.addWidget(self.counter)
        
        # Actualizar contador cuando cambia el texto
        def update_counter():
            text = self.recipients_text.toPlainText()
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            self.counter.setText(f"{len(lines)} destinatario{'s' if len(lines) != 1 else ''}")
        
        self.recipients_text.textChanged.connect(update_counter)
        update_counter()  # Actualizar al inicio
        
        # Botones
        button_layout = QHBoxLayout()
        
        cancel_button = QPushButton("Cancelar")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        button_layout.addStretch()
        
        save_button = QPushButton("Guardar")
        save_button.clicked.connect(self.accept)
        save_button.setDefault(True)
        button_layout.addWidget(save_button)
        
        layout.addLayout(button_layout)
    
    def get_recipients(self):
        """Retorna una lista de tuplas (email, nombre)"""
        text = self.recipients_text.toPlainText()
        recipients = []
        
        for line in text.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            # Intentar separar por coma o punto y coma
            if ',' in line:
                parts = line.split(',', 1)
            elif ';' in line:
                parts = line.split(';', 1)
            else:
                # Solo email sin nombre
                parts = [line, ""]
            
            email = parts[0].strip()
            name = parts[1].strip() if len(parts) > 1 else ""
            
            if email:
                recipients.append((email, name))
        
        return recipients                

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

    def manage_recipients(self, tab_type):
        """Abre un diálogo para gestionar destinatarios con nombres personalizados"""
        # Obtener el campo de email según la pestaña
        if tab_type == "welcome":
            email_field = self.welcome_user_email
        elif tab_type == "password_reset":
            email_field = self.reset_user_email
        elif tab_type == "notification":
            email_field = self.notification_user_email
        elif tab_type == "alert":
            email_field = self.alert_user_email
        else:
            return
        
        # Obtener emails actuales
        emails_text = email_field.toPlainText()
        emails = [email.strip() for email in emails_text.split('\n') if email.strip()]
        
        # Obtener nombres personalizados si existen (atributo personalizado)
        names = getattr(email_field, 'recipient_names', [])
        
        # Crear y mostrar el diálogo
        dialog = EmailRecipientsDialog(self, emails, names)
        if dialog.exec_() == QDialog.Accepted:
            # Obtener los destinatarios del diálogo
            recipients = dialog.get_recipients()
            
            # Actualizar el campo de email
            email_field.setText("\n".join([email for email, _ in recipients]))
            
            # Guardar los nombres para uso posterior
            email_field.recipient_names = [name for _, name in recipients]
            
            # Actualizar contador si existe
            if hasattr(email_field, 'counter'):
                email_field.counter.setText(f"{len(recipients)} destinatario{'s' if len(recipients) != 1 else ''}")

    def create_email_recipients_field(self, placeholder="Ingrese un email por línea"):
        """Crea un campo para ingresar múltiples destinatarios con contador"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Campo de texto para ingresar emails
        field = QTextEdit()
        field.setPlaceholderText(placeholder)
        field.setMaximumHeight(80)  # Limitar altura
        
        # Etiqueta para mostrar contador de destinatarios
        counter = QLabel("0 destinatarios")
        counter.setStyleSheet("color: gray; font-size: 10px;")
        
        # Actualizar contador cuando cambia el texto
        def update_counter():
            text = field.toPlainText()
            emails = [email.strip() for email in text.split('\n') if email.strip()]
            counter.setText(f"{len(emails)} destinatario{'s' if len(emails) != 1 else ''}")
        
        field.textChanged.connect(update_counter)
        
        # Almacenar el contador como atributo del campo para acceder después
        field.counter = counter
        
        layout.addWidget(field)
        layout.addWidget(counter)
        
        return container, field
    
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
        
        # Crear campo de emails con contador
        email_container, self.welcome_user_email = self.create_email_recipients_field()
        self.welcome_user_email.setText("usuario@ejemplo.com")
        
        # Botón para gestionar destinatarios
        manage_recipients_button = QPushButton("Gestionar Destinatarios")
        manage_recipients_button.clicked.connect(lambda: self.manage_recipients("welcome"))
        
        # Layout para campo de email y botón
        email_layout = QHBoxLayout()
        email_layout.addWidget(email_container)
        email_layout.addWidget(manage_recipients_button)
        
        self.welcome_dashboard_url = QLineEdit("https://miempresa.com/dashboard")
        
        user_layout.addRow("Nombre por defecto:", self.welcome_user_name)
        user_layout.addRow("Email(s):", email_layout)
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
        
        # Crear campo de emails con contador
        email_container, self.reset_user_email = self.create_email_recipients_field()
        self.reset_user_email.setText("usuario@ejemplo.com")
        
        # Botón para gestionar destinatarios
        manage_recipients_button = QPushButton("Gestionar Destinatarios")
        manage_recipients_button.clicked.connect(lambda: self.manage_recipients("password_reset"))
        
        # Layout para campo de email y botón
        email_layout = QHBoxLayout()
        email_layout.addWidget(email_container)
        email_layout.addWidget(manage_recipients_button)
        
        self.reset_url = QLineEdit("https://miempresa.com/reset-password")
        self.expires_in = QSpinBox()
        self.expires_in.setValue(24)
        self.expires_in.setRange(1, 72)
        
        user_layout.addRow("Nombre por defecto:", self.reset_user_name)
        user_layout.addRow("Email(s):", email_layout)
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
        
        # Crear campo de emails con contador
        email_container, self.notification_user_email = self.create_email_recipients_field()
        self.notification_user_email.setText("usuario@ejemplo.com")
        
        # Botón para gestionar destinatarios
        manage_recipients_button = QPushButton("Gestionar Destinatarios")
        manage_recipients_button.clicked.connect(lambda: self.manage_recipients("notification"))
        
        # Layout para campo de email y botón
        email_layout = QHBoxLayout()
        email_layout.addWidget(email_container)
        email_layout.addWidget(manage_recipients_button)
        
        user_layout.addRow("Nombre por defecto:", self.notification_user_name)
        user_layout.addRow("Email(s):", email_layout)
        
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
        
        # Crear campo de emails con contador
        email_container, self.alert_user_email = self.create_email_recipients_field()
        self.alert_user_email.setText("usuario@ejemplo.com")
        
        # Botón para gestionar destinatarios
        manage_recipients_button = QPushButton("Gestionar Destinatarios")
        manage_recipients_button.clicked.connect(lambda: self.manage_recipients("alert"))
        
        # Layout para campo de email y botón
        email_layout = QHBoxLayout()
        email_layout.addWidget(email_container)
        email_layout.addWidget(manage_recipients_button)
        
        user_layout.addRow("Nombre por defecto:", self.alert_user_name)
        user_layout.addRow("Email(s):", email_layout)
        
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
            
            # Obtener el campo de email y nombre según el tipo de email
            if email_type == "welcome":
                email_field = self.welcome_user_email
                name_field = self.welcome_user_name
            elif email_type == "password_reset":
                email_field = self.reset_user_email
                name_field = self.reset_user_name
            elif email_type == "notification":
                email_field = self.notification_user_email
                name_field = self.notification_user_name
            elif email_type == "alert":
                email_field = self.alert_user_email
                name_field = self.alert_user_name
            
            # Procesar los emails (uno por línea)
            emails_text = email_field.toPlainText()
            emails = [email.strip() for email in emails_text.split('\n') if email.strip()]
            
            if not emails:
                QMessageBox.warning(self, "Error", "No hay emails disponibles para la vista previa")
                return
            
            # Obtener nombres personalizados si existen
            names = getattr(email_field, 'recipient_names', [])
            
            # Validar emails
            valid_emails, invalid_emails = validate_emails(emails)
            
            if not valid_emails:
                QMessageBox.warning(self, "Error", "No se encontraron emails válidos para la vista previa")
                return
            
            # Usar el primer email válido para la vista previa
            preview_email_idx = 0
            for i, email in enumerate(emails):
                if email in valid_emails:
                    preview_email_idx = i
                    break
            
            email = valid_emails[0]
            
            # Obtener el nombre correspondiente
            if preview_email_idx < len(names) and names[preview_email_idx]:
                name = names[preview_email_idx]
            else:
                name = name_field.text() or "Usuario"
            
            # Preparar los datos según el tipo de email
            if email_type == "welcome":
                data = {
                    "company": self.get_company_data(),
                    "user": {
                        "name": name,
                        "email": email
                    },
                    "dashboard_url": self.welcome_dashboard_url.text(),
                    "year": 2025
                }
            elif email_type == "password_reset":
                data = {
                    "company": self.get_company_data(),
                    "user": {
                        "name": name,
                        "email": email
                    },
                    "reset_url": self.reset_url.text(),
                    "expires_in": self.expires_in.value(),
                    "year": 2025
                }
            elif email_type == "notification":
                data = {
                    "company": self.get_company_data(),
                    "user": {
                        "name": name,
                        "email": email
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
                        "name": name,
                        "email": email
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
            
            # Crear un mensaje informativo sobre los destinatarios
            if len(valid_emails) > 1:
                recipient_info = f"Vista previa para: {name} <{email}>"
                recipient_info += f"\n\nEste email se enviará a {len(valid_emails)} destinatarios:"
                
                for i, valid_email in enumerate(valid_emails, 1):
                    idx = emails.index(valid_email)
                    recipient_name = names[idx] if idx < len(names) and names[idx] else name_field.text() or "Usuario"
                    recipient_info += f"\n{i}. {recipient_name} <{valid_email}>"
                
                if invalid_emails:
                    recipient_info += f"\n\nSe encontraron {len(invalid_emails)} emails inválidos que serán ignorados."
            else:
                recipient_info = f"Vista previa para el destinatario: {name} <{email}>"
            
            # Mostrar el diálogo de vista previa con información adicional
            preview_dialog = EmailPreviewDialog(html_content, self)
            preview_dialog.setWindowTitle(f"Vista Previa - {len(valid_emails)} destinatario(s)")
            
            # Añadir un widget para mostrar información de destinatarios
            info_label = QLabel(recipient_info)
            info_label.setStyleSheet("background-color: #f0f8ff; padding: 10px; border-radius: 5px;")
            info_label.setWordWrap(True)
            
            # Insertar el widget en el layout del diálogo antes del navegador
            preview_dialog.layout().insertWidget(0, info_label)
            
            preview_dialog.exec_()
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error en la Vista Previa",
                f"No se pudo generar la vista previa: {str(e)}"
            )

    def make_batch_request(self, data):
        """Realiza una petición al endpoint de envío en lote"""
        # Validar API key
        if not self.api_key_input.text():
            QMessageBox.warning(self, "Error", "La API key es requerida")
            return
            
        headers = {
            "X-API-Key": self.api_key_input.text(),
            "Content-Type": "application/json"
        }
        
        # Verificar que los datos de la compañía sean correctos
        company_data = data.get("company", {})
        if not company_data.get("name") or not company_data.get("support_email"):
            QMessageBox.warning(self, "Error", "El nombre de la empresa y email de soporte son requeridos")
            return
        
        # Si hay muchos destinatarios, mostrar una barra de progreso
        recipients = data.get("recipients", [])
        if len(recipients) > 5:
            from PyQt5.QtWidgets import QProgressDialog
            from PyQt5.QtCore import Qt
            
            progress = QProgressDialog("Enviando emails...", "Cancelar", 0, 0, self)
            progress.setWindowTitle("Procesando")
            progress.setWindowModality(Qt.WindowModal)
            progress.show()
        else:
            progress = None
        
        try:
            print(f"Realizando petición a: {self.api_url}/emails/batch")
            print(f"Datos: {json.dumps(data, indent=2)}")
            
            response = requests.post(
                f"{self.api_url}/emails/batch",
                json=data,
                headers=headers
            )
            
            # Cerrar la barra de progreso si existe
            if progress:
                progress.close()
            
            # Imprimir respuesta para debug
            print(f"Código de respuesta: {response.status_code}")
            print(f"Respuesta: {response.text}")
            
            if response.status_code == 200:
                result = response.json()
                message_type = ""
                
                if data.get("email_type") == "welcome":
                    message_type = "emails de bienvenida"
                elif data.get("email_type") == "password-reset":
                    message_type = "emails de restablecimiento"
                elif data.get("email_type") == "notification":
                    message_type = "notificaciones"
                elif data.get("email_type") == "alert":
                    message_type = "alertas"
                
                QMessageBox.information(
                    self,
                    "Éxito",
                    f"Se enviaron {result.get('sent')} {message_type} correctamente.\n" +
                    (f"Fallaron {result.get('failed')} envíos." if result.get('failed', 0) > 0 else "")
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
                    f"Error al enviar los emails (código {response.status_code}): {error_detail}"
                )
        except requests.exceptions.ConnectionError:
            if progress:
                progress.close()
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudo conectar con la API en {self.api_url}. ¿Está el servidor corriendo?"
            )
        except Exception as e:
            if progress:
                progress.close()
            QMessageBox.critical(
                self,
                "Error",
                f"Error inesperado: {str(e)}"
            )

    def send_welcome_email(self):
        """Envía emails de bienvenida personalizados en lote"""
        # Obtener emails
        emails_text = self.welcome_user_email.toPlainText()
        if not emails_text.strip():
            QMessageBox.warning(self, "Error", "El email del usuario es requerido")
            return
        
        # Procesar los emails (uno por línea)
        emails = [email.strip() for email in emails_text.split('\n') if email.strip()]
        if not emails:
            QMessageBox.warning(self, "Error", "No se encontraron emails")
            return
        
        # Obtener nombres personalizados si existen
        names = getattr(self.welcome_user_email, 'recipient_names', [])
        
        # Validar emails
        valid_emails, invalid_emails = validate_emails(emails)
        
        if not valid_emails:
            QMessageBox.warning(self, "Error", "No se encontraron emails válidos")
            return
        
        if invalid_emails:
            msg = "Se encontraron emails inválidos:\n\n"
            msg += "\n".join(invalid_emails)
            msg += "\n\n¿Desea continuar con los emails válidos?"
            
            reply = QMessageBox.question(
                self, "Emails inválidos", msg,
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            
            if reply == QMessageBox.No:
                return
        
        # Validar campos requeridos
        if not self.welcome_dashboard_url.text():
            QMessageBox.warning(self, "Error", "La URL del dashboard es requerida")
            return

        # Validar campos de la empresa
        company_data = self.get_company_data()
        if not company_data["name"] or not company_data["support_email"]:
            QMessageBox.warning(self, "Error", "El nombre de la empresa y email de soporte son requeridos")
            return
        
        # Preparar el listado de destinatarios
        recipients = []
        for i, email in enumerate(valid_emails):
            # Obtener el índice original para acceder al nombre correcto
            original_idx = emails.index(email)
            
            # Obtener el nombre correspondiente
            name = None
            if original_idx < len(names) and names[original_idx]:
                name = names[original_idx]
            else:
                name = self.welcome_user_name.text()
            
            # Añadir destinatario
            recipients.append({
                "email": email,
                "name": name
            })
        
        # Preparar datos para la API
        data = {
            "email_type": "welcome",
            "company": company_data,
            "recipients": recipients,
            "query": {
                "dashboard_url": self.welcome_dashboard_url.text()
            }
        }
        
        # Imprimir datos para debug
        print("Enviando datos:", json.dumps(data, indent=2))
        
        self.make_batch_request(data)

    def send_password_reset(self):
        """Envía emails de restablecimiento de contraseña personalizados en lote"""
        # Obtener emails
        emails_text = self.reset_user_email.toPlainText()
        if not emails_text.strip():
            QMessageBox.warning(self, "Error", "El email del usuario es requerido")
            return
        
        # Procesar los emails (uno por línea)
        emails = [email.strip() for email in emails_text.split('\n') if email.strip()]
        if not emails:
            QMessageBox.warning(self, "Error", "No se encontraron emails")
            return
        
        # Obtener nombres personalizados si existen
        names = getattr(self.reset_user_email, 'recipient_names', [])
        
        # Validar emails
        valid_emails, invalid_emails = validate_emails(emails)
        
        if not valid_emails:
            QMessageBox.warning(self, "Error", "No se encontraron emails válidos")
            return
        
        if invalid_emails:
            msg = "Se encontraron emails inválidos:\n\n"
            msg += "\n".join(invalid_emails)
            msg += "\n\n¿Desea continuar con los emails válidos?"
            
            reply = QMessageBox.question(
                self, "Emails inválidos", msg,
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            
            if reply == QMessageBox.No:
                return
        
        # Validar campos requeridos
        if not self.reset_url.text():
            QMessageBox.warning(self, "Error", "La URL de reset es requerida")
            return
        
        # Preparar el listado de destinatarios
        recipients = []
        for i, email in enumerate(valid_emails):
            # Obtener el índice original para acceder al nombre correcto
            original_idx = emails.index(email)
            
            # Obtener el nombre correspondiente
            name = None
            if original_idx < len(names) and names[original_idx]:
                name = names[original_idx]
            else:
                name = self.reset_user_name.text()
            
            # Añadir destinatario
            recipients.append({
                "email": email,
                "name": name
            })
        
        # Preparar datos para la API
        data = {
            "email_type": "password-reset",
            "company": self.get_company_data(),
            "recipients": recipients,
            "query": {
                "reset_url": self.reset_url.text(),
                "expires_in": self.expires_in.value()
            }
        }
        
        # Imprimir datos para debug
        print("Enviando datos:", json.dumps(data, indent=2))
        
        # Hacer la petición a la API
        self.make_batch_request(data)

    def send_notification(self):
        """Envía notificaciones personalizadas en lote"""
        # Obtener emails
        emails_text = self.notification_user_email.toPlainText()
        if not emails_text.strip():
            QMessageBox.warning(self, "Error", "El email del usuario es requerido")
            return
        
        # Procesar los emails (uno por línea)
        emails = [email.strip() for email in emails_text.split('\n') if email.strip()]
        if not emails:
            QMessageBox.warning(self, "Error", "No se encontraron emails")
            return
        
        # Obtener nombres personalizados si existen
        names = getattr(self.notification_user_email, 'recipient_names', [])
        
        # Validar emails
        valid_emails, invalid_emails = validate_emails(emails)
        
        if not valid_emails:
            QMessageBox.warning(self, "Error", "No se encontraron emails válidos")
            return
        
        if invalid_emails:
            msg = "Se encontraron emails inválidos:\n\n"
            msg += "\n".join(invalid_emails)
            msg += "\n\n¿Desea continuar con los emails válidos?"
            
            reply = QMessageBox.question(
                self, "Emails inválidos", msg,
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            
            if reply == QMessageBox.No:
                return
        
        # Preparar el listado de destinatarios
        recipients = []
        for i, email in enumerate(valid_emails):
            # Obtener el índice original para acceder al nombre correcto
            original_idx = emails.index(email)
            
            # Obtener el nombre correspondiente
            name = None
            if original_idx < len(names) and names[original_idx]:
                name = names[original_idx]
            else:
                name = self.notification_user_name.text()
            
            # Añadir destinatario
            recipients.append({
                "email": email,
                "name": name
            })
        
        # Preparar datos para la API
        data = {
            "email_type": "notification",
            "company": self.get_company_data(),
            "recipients": recipients,
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
        
        # Hacer la petición a la API
        self.make_batch_request(data)

    def send_alert(self):
        """Envía alertas personalizadas en lote"""
        # Obtener emails
        emails_text = self.alert_user_email.toPlainText()
        if not emails_text.strip():
            QMessageBox.warning(self, "Error", "El email del usuario es requerido")
            return
        
        # Procesar los emails (uno por línea)
        emails = [email.strip() for email in emails_text.split('\n') if email.strip()]
        if not emails:
            QMessageBox.warning(self, "Error", "No se encontraron emails")
            return
        
        # Obtener nombres personalizados si existen
        names = getattr(self.alert_user_email, 'recipient_names', [])
        
        # Validar emails
        valid_emails, invalid_emails = validate_emails(emails)
        
        if not valid_emails:
            QMessageBox.warning(self, "Error", "No se encontraron emails válidos")
            return
        
        if invalid_emails:
            msg = "Se encontraron emails inválidos:\n\n"
            msg += "\n".join(invalid_emails)
            msg += "\n\n¿Desea continuar con los emails válidos?"
            
            reply = QMessageBox.question(
                self, "Emails inválidos", msg,
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            
            if reply == QMessageBox.No:
                return
        
        # Obtener pasos
        steps = [
            step.strip() 
            for step in self.alert_steps.toPlainText().split("\n") 
            if step.strip()
        ]
        
        # Preparar el listado de destinatarios
        recipients = []
        for i, email in enumerate(valid_emails):
            # Obtener el índice original para acceder al nombre correcto
            original_idx = emails.index(email)
            
            # Obtener el nombre correspondiente
            name = None
            if original_idx < len(names) and names[original_idx]:
                name = names[original_idx]
            else:
                name = self.alert_user_name.text()
            
            # Añadir destinatario
            recipients.append({
                "email": email,
                "name": name
            })
        
        # Preparar datos de alerta
        alert_data = {
            "title": self.alert_title.text(),
            "message": self.alert_message.toPlainText(),
            "type": self.alert_type.currentText(),
            "steps": steps if steps else None,
            "action_url": self.alert_action_url.text() or None,
            "action_text": self.alert_action_text.text() or None,
            "contact_support": self.alert_contact_support.isChecked()
        }
        
        # Preparar datos para la API
        data = {
            "email_type": "alert",
            "company": self.get_company_data(),
            "recipients": recipients,
            "alert": alert_data
        }
        
        # Imprimir datos para debug
        print("Enviando datos:", json.dumps(data, indent=2))
        
        # Hacer la petición a la API
        self.make_batch_request(data)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = EmailTesterGUI()
    window.show()
    sys.exit(app.exec_())