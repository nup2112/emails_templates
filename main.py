import sys
import json
import requests
import tempfile
import webbrowser
import threading
import time
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QLineEdit, QTextEdit, QComboBox, QSpinBox,
    QTabWidget, QFormLayout, QMessageBox, QGroupBox, QSplitter, QDialog, 
    QCheckBox, QTextBrowser, QFileDialog, QListWidget, QListWidgetItem,
    QStackedWidget, QToolBar, QAction, QSizePolicy, QScrollArea, QFrame
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, QSize, QUrl
from PyQt5.QtGui import QIcon, QPixmap, QFont, QColor, QPalette
from jinja2 import Environment, FileSystemLoader, select_autoescape
from emails.validation import validate_email, validate_emails

class RenderPreviewWorker(QThread):
    """Worker thread para renderizar la vista previa sin bloquear la UI"""
    preview_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, template_env, template_name, template_data):
        super().__init__()
        self.template_env = template_env
        self.template_name = template_name
        self.template_data = template_data
        
    def run(self):
        try:
            if not self.template_env:
                self.error_occurred.emit("El motor de plantillas no está configurado.")
                return
            
            template = self.template_env.get_template(self.template_name)
            html_content = template.render(**self.template_data)
            self.preview_ready.emit(html_content)
        except Exception as e:
            self.error_occurred.emit(f"Error al renderizar vista previa: {str(e)}")


class EmailPreviewDialog(QDialog):
    def __init__(self, html_content, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Vista Previa del Email")
        self.resize(800, 600)
        self.html_content = html_content
        
        layout = QVBoxLayout(self)
        
        # Usando QTextBrowser como visor HTML
        self.text_browser = QTextBrowser()
        self.text_browser.setHtml(html_content)
        self.text_browser.setOpenExternalLinks(True)
        
        layout.addWidget(self.text_browser)
        
        # Botones de acción
        button_layout = QHBoxLayout()
        
        # Botón para abrir en navegador
        open_browser_button = QPushButton("Abrir en Navegador")
        open_browser_button.clicked.connect(self.open_in_browser)
        open_browser_button.setIcon(QIcon.fromTheme("web-browser"))
        button_layout.addWidget(open_browser_button)
        
        # Botón para guardar HTML
        save_button = QPushButton("Guardar HTML")
        save_button.clicked.connect(self.save_html)
        save_button.setIcon(QIcon.fromTheme("document-save"))
        button_layout.addWidget(save_button)
        
        button_layout.addStretch()
        
        close_button = QPushButton("Cerrar")
        close_button.clicked.connect(self.accept)
        close_button.setIcon(QIcon.fromTheme("window-close"))
        button_layout.addWidget(close_button)
        
        layout.addLayout(button_layout)
    
    def open_in_browser(self):
        try:
            # Crear archivo temporal para visualizar en navegador
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.html', encoding='utf-8') as f:
                f.write(self.html_content)
                temp_name = f.name
            
            # Abrir archivo en navegador
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


class SidebarItem(QWidget):
    """Widget personalizado para cada ítem de la barra lateral"""
    def __init__(self, icon_name, text, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        
        self.icon_label = QLabel()
        # Aquí podrías cargar iconos personalizados
        # self.icon_label.setPixmap(QPixmap(f"icons/{icon_name}.png").scaled(24, 24, Qt.KeepAspectRatio))
        layout.addWidget(self.icon_label)
        
        self.text_label = QLabel(text)
        self.text_label.setStyleSheet("font-size: 14px;")
        layout.addWidget(self.text_label)
        
        layout.addStretch()


class ImprovedEmailTesterGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sistema de Emails - Tester Mejorado")
        self.setMinimumSize(1200, 800)
        
        # Inicialización de atributos
        self.api_url = "http://localhost:8000/api"
        self.api_key = ""
        self.templates_dir_input = None
        self.template_env = None
        self.current_preview_timer = None
        self.html_preview = None
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Crear la barra lateral
        self.create_sidebar(main_layout)
        
        # Contenedor principal para los formularios y la vista previa
        self.main_container = QWidget()
        main_container_layout = QVBoxLayout(self.main_container)
        main_container_layout.setContentsMargins(0, 0, 0, 0)
        
        # Crear toolbar para configuración
        self.create_toolbar(main_container_layout)
        
        # Splitter para dividir el formulario y la vista previa
        self.main_splitter = QSplitter(Qt.Horizontal)
        
        # Contenedor para el formulario (izquierda)
        self.form_container = QWidget()
        self.form_layout = QVBoxLayout(self.form_container)
        
        # Contenedor para la vista previa (derecha)
        self.preview_container = QWidget()
        preview_layout = QVBoxLayout(self.preview_container)
        
        # Título para la vista previa
        preview_header = QWidget()
        preview_header_layout = QHBoxLayout(preview_header)
        preview_header_layout.setContentsMargins(10, 5, 10, 5)
        
        preview_title = QLabel("Vista Previa del Email")
        preview_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        preview_header_layout.addWidget(preview_title)
        
        preview_header_layout.addStretch()
        
        # Botones para la vista previa
        self.preview_in_browser_btn = QPushButton("Abrir en Navegador")
        self.preview_in_browser_btn.clicked.connect(self.open_preview_in_browser)
        preview_header_layout.addWidget(self.preview_in_browser_btn)
        
        self.save_preview_btn = QPushButton("Guardar HTML")
        self.save_preview_btn.clicked.connect(self.save_preview_html)
        preview_header_layout.addWidget(self.save_preview_btn)
        
        preview_layout.addWidget(preview_header)
        
        # Visor de HTML
        self.html_preview = QTextBrowser()
        self.html_preview.setOpenExternalLinks(True)
        
        # Scroll area para la vista previa
        preview_scroll = QScrollArea()
        preview_scroll.setWidget(self.html_preview)
        preview_scroll.setWidgetResizable(True)
        preview_layout.addWidget(preview_scroll)
        
        # Añadir los contenedores al splitter
        self.main_splitter.addWidget(self.form_container)
        self.main_splitter.addWidget(self.preview_container)
        self.main_splitter.setSizes([400, 800])  # Tamaños iniciales
        
        main_container_layout.addWidget(self.main_splitter)
        
        # Añadir el contenedor principal al layout
        main_layout.addWidget(self.main_container)
        
        # Configurar el motor de plantillas
        self.setup_template_engine()
        
        # Crear los formularios para cada tipo de email
        self.create_company_form()  # Formulario común de empresa
        self.create_all_email_forms()
        
        # Seleccionar el primer tipo de email por defecto
        if self.sidebar_list.count() > 0:
            self.sidebar_list.setCurrentRow(0)
            
    def create_toolbar(self, layout):
        """Crea una barra de herramientas para la configuración"""
        toolbar_container = QWidget()
        toolbar_container.setStyleSheet("""
            background-color: white;
            border-bottom: 1px solid #e0e0e0;
            max-height: 60px;
        """)
        toolbar_layout = QHBoxLayout(toolbar_container)
        toolbar_layout.setContentsMargins(15, 12, 15, 12)
        
        # API Key
        api_key_label = QLabel("API Key:")
        api_key_label.setStyleSheet("font-weight: bold;")
        toolbar_layout.addWidget(api_key_label)
        
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.api_key_input.setMaximumWidth(500)
        self.api_key_input.setPlaceholderText("Ingrese su API key")
        toolbar_layout.addWidget(self.api_key_input)
        
        # Separador
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setFixedWidth(2)
        separator.setStyleSheet("background-color: #e0e0e0;")
        toolbar_layout.addWidget(separator)
        
        # Directorio de plantillas
        templates_dir_label = QLabel("Plantillas:")
        templates_dir_label.setStyleSheet("font-weight: bold;")
        toolbar_layout.addWidget(templates_dir_label)
        
        self.templates_dir_input = QLineEdit()
        self.templates_dir_input.setReadOnly(True)
        self.templates_dir_input.setPlaceholderText("Seleccione el directorio de plantillas")
        toolbar_layout.addWidget(self.templates_dir_input)
        
        browse_button = QPushButton("Explorar")
        browse_button.setStyleSheet("""
            QPushButton {
                background-color: #f5f5f5;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """)
        browse_button.clicked.connect(self.browse_templates_dir)
        toolbar_layout.addWidget(browse_button)
        
        layout.addWidget(toolbar_container)
        
        # Línea separadora
        separator_line = QFrame()
        separator_line.setFrameShape(QFrame.HLine)
        separator_line.setFrameShadow(QFrame.Sunken)
        separator_line.setFixedHeight(1)
        separator_line.setStyleSheet("background-color: #e0e0e0;")
        layout.addWidget(separator_line)
            
    def create_sidebar(self, layout):
        """Crea la barra lateral con los tipos de emails"""
        # Contenedor para la barra lateral
        sidebar_container = QWidget()
        sidebar_container.setMaximumWidth(250)
        sidebar_container.setMinimumWidth(200)
        sidebar_container.setStyleSheet("""
            background-color: #2e2e36;
            border-top-left-radius: 0px;
            border-bottom-left-radius: 0px;
        """)
        
        sidebar_layout = QVBoxLayout(sidebar_container)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)
        
        # Título de la barra lateral
        sidebar_header = QLabel("Email System")
        sidebar_header.setAlignment(Qt.AlignCenter)
        sidebar_header.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            padding: 20px 15px;
            color: white;
            background-color: #232329;
        """)
        sidebar_layout.addWidget(sidebar_header)
        
        # Subtítulo
        sidebar_subtitle = QLabel("TIPOS DE EMAIL")
        sidebar_subtitle.setAlignment(Qt.AlignLeft)
        sidebar_subtitle.setStyleSheet("""
            font-size: 12px;
            font-weight: bold;
            padding: 15px 20px 10px 20px;
            color: #9e9e9e;
            background-color: transparent;
        """)
        sidebar_layout.addWidget(sidebar_subtitle)
        
        # Lista de tipos de email
        self.sidebar_list = QListWidget()
        self.sidebar_list.setStyleSheet("""
            QListWidget {
                border: none;
                outline: none;
                background-color: transparent;
            }
        """)
        
        # Añadir los tipos de email con iconos
        email_types = [
            ("welcome", "Bienvenida", "👋"),
            ("password_reset", "Reset Contraseña", "🔒"),
            ("notification", "Notificación", "🔔"),
            ("alert", "Alerta", "⚠️"),
            ("batch", "Envío en Lote", "📧")
        ]
        
        for email_type, display_name, icon in email_types:
            item = QListWidgetItem()
            item.setData(Qt.UserRole, email_type)
            item.setText(f"{icon}  {display_name}")
            self.sidebar_list.addItem(item)
        
        # Conectar la señal de selección
        self.sidebar_list.currentItemChanged.connect(self.on_sidebar_item_changed)
        
        sidebar_layout.addWidget(self.sidebar_list)
        
        # Añadir espacio
        sidebar_layout.addStretch()
        
        # Footer
        sidebar_footer = QLabel("© 2025 Email System")
        sidebar_footer.setAlignment(Qt.AlignCenter)
        sidebar_footer.setStyleSheet("""
            font-size: 12px;
            padding: 15px;
            color: #9e9e9e;
            background-color: #232329;
        """)
        sidebar_layout.addWidget(sidebar_footer)
        
        # Añadir la barra lateral al layout principal
        layout.addWidget(sidebar_container)
        
    def on_sidebar_item_changed(self, current, previous):
        """Maneja el cambio de selección en la barra lateral"""
        if not current:
            return
            
        # Obtener el tipo de email seleccionado
        email_type = current.data(Qt.UserRole)
        
        # Mostrar el formulario correspondiente
        self.show_email_form(email_type)
        
        # Actualizar título de la vista previa según el tipo seleccionado
        preview_title = f"Vista Previa: {current.text()}"
        
    def show_email_form(self, email_type):
        """Muestra el formulario correspondiente al tipo de email seleccionado"""
        # Limpiar el contenedor de formularios
        for i in reversed(range(self.form_layout.count())):
            widget = self.form_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        
        # Añadir el formulario de empresa (común a todos)
        self.form_layout.addWidget(self.company_form)
        
        # Añadir el formulario específico
        if email_type == "welcome":
            self.form_layout.addWidget(self.welcome_form)
            self.current_email_type = "welcome"
        elif email_type == "password_reset":
            self.form_layout.addWidget(self.password_reset_form)
            self.current_email_type = "password_reset"
        elif email_type == "notification":
            self.form_layout.addWidget(self.notification_form)
            self.current_email_type = "notification"
        elif email_type == "alert":
            self.form_layout.addWidget(self.alert_form)
            self.current_email_type = "alert"
        elif email_type == "batch":
            self.form_layout.addWidget(self.batch_form)
            self.current_email_type = "batch"
            
        # Botones de acción
        action_buttons = QWidget()
        action_layout = QHBoxLayout(action_buttons)
        
        # Añadir espacio
        action_layout.addStretch()
        
        # Botón para enviar email
        if email_type == "welcome":
            send_btn = QPushButton("Enviar Email de Bienvenida")
            send_btn.clicked.connect(self.send_welcome_email)
        elif email_type == "password_reset":
            send_btn = QPushButton("Enviar Reset de Contraseña")
            send_btn.clicked.connect(self.send_password_reset)
        elif email_type == "notification":
            send_btn = QPushButton("Enviar Notificación")
            send_btn.clicked.connect(self.send_notification)
        elif email_type == "alert":
            send_btn = QPushButton("Enviar Alerta")
            send_btn.clicked.connect(self.send_alert)
        elif email_type == "batch":
            send_btn = QPushButton("Enviar Lote de Emails")
            send_btn.clicked.connect(self.send_batch_email)
            
        send_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        action_layout.addWidget(send_btn)
        
        self.form_layout.addWidget(action_buttons)
        
        # Generar vista previa automáticamente
        QTimer.singleShot(500, self.update_preview)
        
    def create_company_form(self):
        """Crea el formulario para la información de la empresa"""
        self.company_form = QGroupBox("Información de la Empresa")
        form_layout = QFormLayout(self.company_form)
        
        self.company_name = QLineEdit("Mi Empresa")
        self.company_address = QLineEdit("Calle Principal 123")
        self.company_email = QLineEdit("soporte@miempresa.com")
        self.company_website = QLineEdit("https://miempresa.com")
        self.company_logo = QLineEdit("https://miempresa.com/logo.png")
        
        form_layout.addRow("Nombre:", self.company_name)
        form_layout.addRow("Dirección:", self.company_address)
        form_layout.addRow("Email:", self.company_email)
        form_layout.addRow("Website:", self.company_website)
        form_layout.addRow("Logo URL:", self.company_logo)
        
        # Conectar señales de cambio para actualizar la vista previa
        self.company_name.textChanged.connect(self.schedule_preview_update)
        self.company_address.textChanged.connect(self.schedule_preview_update)
        self.company_email.textChanged.connect(self.schedule_preview_update)
        self.company_website.textChanged.connect(self.schedule_preview_update)
        self.company_logo.textChanged.connect(self.schedule_preview_update)
        
    def create_all_email_forms(self):
        """Crea todos los formularios para los diferentes tipos de email"""
        self.create_welcome_form()
        self.create_password_reset_form()
        self.create_notification_form()
        self.create_alert_form()
        self.create_batch_form()
    
    def create_welcome_form(self):
        """Crea el formulario para el email de bienvenida"""
        self.welcome_form = QWidget()
        layout = QVBoxLayout(self.welcome_form)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Información del usuario
        user_group = QGroupBox("Información del Usuario")
        user_layout = QFormLayout(user_group)
        
        self.welcome_user_name = QLineEdit("Usuario de Prueba")
        self.welcome_user_name.textChanged.connect(self.schedule_preview_update)
        
        # Crear campo de emails con contador
        email_container, self.welcome_user_email = self.create_email_recipients_field()
        self.welcome_user_email.setText("usuario@ejemplo.com")
        self.welcome_user_email.textChanged.connect(self.schedule_preview_update)
        
        # Botón para gestionar destinatarios
        manage_recipients_button = QPushButton("Gestionar Destinatarios")
        manage_recipients_button.clicked.connect(lambda: self.manage_recipients("welcome"))
        
        # Layout para campo de email y botón
        email_layout = QHBoxLayout()
        email_layout.addWidget(email_container)
        email_layout.addWidget(manage_recipients_button)
        
        self.welcome_dashboard_url = QLineEdit("https://miempresa.com/dashboard")
        self.welcome_dashboard_url.textChanged.connect(self.schedule_preview_update)
        
        user_layout.addRow("Nombre por defecto:", self.welcome_user_name)
        user_layout.addRow("Email(s):", email_layout)
        user_layout.addRow("Dashboard URL:", self.welcome_dashboard_url)
        
        layout.addWidget(user_group)
    
    def create_password_reset_form(self):
        """Crea el formulario para el email de restablecimiento de contraseña"""
        self.password_reset_form = QWidget()
        layout = QVBoxLayout(self.password_reset_form)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Información del usuario
        user_group = QGroupBox("Información del Usuario")
        user_layout = QFormLayout(user_group)
        
        self.reset_user_name = QLineEdit("Usuario de Prueba")
        self.reset_user_name.textChanged.connect(self.schedule_preview_update)
        
        # Crear campo de emails con contador
        email_container, self.reset_user_email = self.create_email_recipients_field()
        self.reset_user_email.setText("usuario@ejemplo.com")
        self.reset_user_email.textChanged.connect(self.schedule_preview_update)
        
        # Botón para gestionar destinatarios
        manage_recipients_button = QPushButton("Gestionar Destinatarios")
        manage_recipients_button.clicked.connect(lambda: self.manage_recipients("password_reset"))
        
        # Layout para campo de email y botón
        email_layout = QHBoxLayout()
        email_layout.addWidget(email_container)
        email_layout.addWidget(manage_recipients_button)
        
        self.reset_url = QLineEdit("https://miempresa.com/reset-password")
        self.reset_url.textChanged.connect(self.schedule_preview_update)
        
        self.expires_in = QSpinBox()
        self.expires_in.setValue(24)
        self.expires_in.setRange(1, 72)
        self.expires_in.valueChanged.connect(self.schedule_preview_update)
        
        user_layout.addRow("Nombre por defecto:", self.reset_user_name)
        user_layout.addRow("Email(s):", email_layout)
        user_layout.addRow("Reset URL:", self.reset_url)
        user_layout.addRow("Expira en (horas):", self.expires_in)
        
        layout.addWidget(user_group)
    
    def create_notification_form(self):
        """Crea el formulario para el email de notificación"""
        self.notification_form = QWidget()
        layout = QVBoxLayout(self.notification_form)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Información del usuario
        user_group = QGroupBox("Información del Usuario")
        user_layout = QFormLayout(user_group)
        
        self.notification_user_name = QLineEdit("Usuario de Prueba")
        self.notification_user_name.textChanged.connect(self.schedule_preview_update)
        
        # Crear campo de emails con contador
        email_container, self.notification_user_email = self.create_email_recipients_field()
        self.notification_user_email.setText("usuario@ejemplo.com")
        self.notification_user_email.textChanged.connect(self.schedule_preview_update)
        
        # Botón para gestionar destinatarios
        manage_recipients_button = QPushButton("Gestionar Destinatarios")
        manage_recipients_button.clicked.connect(lambda: self.manage_recipients("notification"))
        
        # Layout para campo de email y botón
        email_layout = QHBoxLayout()
        email_layout.addWidget(email_container)
        email_layout.addWidget(manage_recipients_button)
        
        user_layout.addRow("Nombre por defecto:", self.notification_user_name)
        user_layout.addRow("Email(s):", email_layout)
        
        layout.addWidget(user_group)
        
        # Contenido de la notificación
        notification_group = QGroupBox("Contenido de la Notificación")
        notification_layout = QFormLayout(notification_group)
        
        self.notification_title = QLineEdit("Notificación Importante")
        self.notification_title.textChanged.connect(self.schedule_preview_update)
        
        self.notification_message = QTextEdit("Este es un mensaje de notificación de prueba.")
        self.notification_message.textChanged.connect(self.schedule_preview_update)
        
        self.notification_type = QComboBox()
        self.notification_type.addItems(["success", "warning", "error", "info"])
        self.notification_type.currentIndexChanged.connect(self.schedule_preview_update)
        
        self.notification_icon = QLineEdit("https://miempresa.com/icons/notification.png")
        self.notification_icon.textChanged.connect(self.schedule_preview_update)
        
        self.notification_action_url = QLineEdit("https://miempresa.com/action")
        self.notification_action_url.textChanged.connect(self.schedule_preview_update)
        
        self.notification_action_text = QLineEdit("Ver Detalles")
        self.notification_action_text.textChanged.connect(self.schedule_preview_update)
        
        self.notification_additional_info = QTextEdit("Información adicional sobre esta notificación.")
        self.notification_additional_info.textChanged.connect(self.schedule_preview_update)
        
        self.notification_preferences_url = QLineEdit("https://miempresa.com/preferences")
        self.notification_preferences_url.textChanged.connect(self.schedule_preview_update)
        
        notification_layout.addRow("Título:", self.notification_title)
        notification_layout.addRow("Mensaje:", self.notification_message)
        notification_layout.addRow("Tipo:", self.notification_type)
        notification_layout.addRow("Icono URL:", self.notification_icon)
        notification_layout.addRow("Action URL:", self.notification_action_url)
        notification_layout.addRow("Action Text:", self.notification_action_text)
        notification_layout.addRow("Info Adicional:", self.notification_additional_info)
        notification_layout.addRow("Preferences URL:", self.notification_preferences_url)
        
        layout.addWidget(notification_group)
    
    def create_alert_form(self):
        """Crea el formulario para el email de alerta"""
        self.alert_form = QWidget()
        layout = QVBoxLayout(self.alert_form)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Información del usuario
        user_group = QGroupBox("Información del Usuario")
        user_layout = QFormLayout(user_group)
        
        self.alert_user_name = QLineEdit("Usuario de Prueba")
        self.alert_user_name.textChanged.connect(self.schedule_preview_update)
        
        # Crear campo de emails con contador
        email_container, self.alert_user_email = self.create_email_recipients_field()
        self.alert_user_email.setText("usuario@ejemplo.com")
        self.alert_user_email.textChanged.connect(self.schedule_preview_update)
        
        # Botón para gestionar destinatarios
        manage_recipients_button = QPushButton("Gestionar Destinatarios")
        manage_recipients_button.clicked.connect(lambda: self.manage_recipients("alert"))
        
        # Layout para campo de email y botón
        email_layout = QHBoxLayout()
        email_layout.addWidget(email_container)
        email_layout.addWidget(manage_recipients_button)
        
        user_layout.addRow("Nombre por defecto:", self.alert_user_name)
        user_layout.addRow("Email(s):", email_layout)
        
        layout.addWidget(user_group)
        
        # Contenido de la alerta
        alert_group = QGroupBox("Contenido de la Alerta")
        alert_layout = QFormLayout(alert_group)
        
        self.alert_title = QLineEdit("Alerta de Seguridad")
        self.alert_title.textChanged.connect(self.schedule_preview_update)
        
        self.alert_message = QTextEdit("Este es un mensaje de alerta de prueba.")
        self.alert_message.textChanged.connect(self.schedule_preview_update)
        
        self.alert_type = QComboBox()
        self.alert_type.addItems(["info", "warning", "error"])
        self.alert_type.currentIndexChanged.connect(self.schedule_preview_update)
        
        self.alert_steps = QTextEdit("Paso 1: Verificar conexión\nPaso 2: Actualizar contraseña\nPaso 3: Cerrar sesiones")
        self.alert_steps.setPlaceholderText("Un paso por línea")
        self.alert_steps.textChanged.connect(self.schedule_preview_update)
        
        self.alert_action_url = QLineEdit("https://miempresa.com/action")
        self.alert_action_url.textChanged.connect(self.schedule_preview_update)
        
        self.alert_action_text = QLineEdit("Resolver Ahora")
        self.alert_action_text.textChanged.connect(self.schedule_preview_update)
        
        self.alert_contact_support = QCheckBox("Incluir información de soporte")
        self.alert_contact_support.setChecked(True)
        self.alert_contact_support.stateChanged.connect(self.schedule_preview_update)
        
        alert_layout.addRow("Título:", self.alert_title)
        alert_layout.addRow("Mensaje:", self.alert_message)
        alert_layout.addRow("Tipo:", self.alert_type)
        alert_layout.addRow("Pasos:", self.alert_steps)
        alert_layout.addRow("Action URL:", self.alert_action_url)
        alert_layout.addRow("Action Text:", self.alert_action_text)
        alert_layout.addRow("", self.alert_contact_support)
        
        layout.addWidget(alert_group)
    
    def create_batch_form(self):
        """Crea el formulario para el envío en lote"""
        self.batch_form = QWidget()
        layout = QVBoxLayout(self.batch_form)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Tipo de email a enviar
        type_group = QGroupBox("Tipo de Email a Enviar")
        type_layout = QFormLayout(type_group)
        
        self.batch_email_type = QComboBox()
        self.batch_email_type.addItems(["welcome", "password-reset", "notification", "alert"])
        self.batch_email_type.currentIndexChanged.connect(self.update_batch_form)
        
        type_layout.addRow("Tipo:", self.batch_email_type)
        
        layout.addWidget(type_group)
        
        # Destinatarios
        recipients_group = QGroupBox("Destinatarios")
        recipients_layout = QVBoxLayout(recipients_group)
        
        # Editor de texto para los destinatarios
        self.batch_recipients_text = QTextEdit()
        self.batch_recipients_text.setPlaceholderText("usuario1@ejemplo.com, Nombre 1\nusuario2@ejemplo.com, Nombre 2\n...")
        
        recipients_layout.addWidget(self.batch_recipients_text)
        
        # Botones para gestionar los destinatarios
        recipients_buttons = QHBoxLayout()
        
        add_recipients_btn = QPushButton("Añadir Destinatarios")
        add_recipients_btn.clicked.connect(self.manage_batch_recipients)
        recipients_buttons.addWidget(add_recipients_btn)
        
        clear_recipients_btn = QPushButton("Limpiar")
        clear_recipients_btn.clicked.connect(lambda: self.batch_recipients_text.clear())
        recipients_buttons.addWidget(clear_recipients_btn)
        
        recipients_layout.addLayout(recipients_buttons)
        
        layout.addWidget(recipients_group)
        
        # Parámetros adicionales (depende del tipo de email)
        self.batch_params_container = QWidget()
        self.batch_params_layout = QVBoxLayout(self.batch_params_container)
        layout.addWidget(self.batch_params_container)
        
        # Actualizar los parámetros según el tipo seleccionado
        self.update_batch_form()
    
    def update_batch_form(self):
        """Actualiza el formulario de batch según el tipo de email seleccionado"""
        # Limpiar el contenedor de parámetros
        for i in reversed(range(self.batch_params_layout.count())):
            widget = self.batch_params_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        
        # Obtener el tipo de email seleccionado
        email_type = self.batch_email_type.currentText()
        
        if email_type == "welcome":
            # Parámetros para email de bienvenida
            params_group = QGroupBox("Parámetros de Bienvenida")
            params_layout = QFormLayout(params_group)
            
            self.batch_dashboard_url = QLineEdit("https://miempresa.com/dashboard")
            params_layout.addRow("Dashboard URL:", self.batch_dashboard_url)
            
            self.batch_params_layout.addWidget(params_group)
            
        elif email_type == "password-reset":
            # Parámetros para reset de contraseña
            params_group = QGroupBox("Parámetros de Reset")
            params_layout = QFormLayout(params_group)
            
            self.batch_reset_url = QLineEdit("https://miempresa.com/reset-password")
            params_layout.addRow("Reset URL:", self.batch_reset_url)
            
            self.batch_expires_in = QSpinBox()
            self.batch_expires_in.setValue(24)
            self.batch_expires_in.setRange(1, 72)
            params_layout.addRow("Expira en (horas):", self.batch_expires_in)
            
            self.batch_params_layout.addWidget(params_group)
            
        elif email_type == "notification":
            # Parámetros para notificación
            params_group = QGroupBox("Parámetros de Notificación")
            params_layout = QFormLayout(params_group)
            
            self.batch_notification_title = QLineEdit("Notificación Importante")
            params_layout.addRow("Título:", self.batch_notification_title)
            
            self.batch_notification_message = QTextEdit("Este es un mensaje de notificación de prueba.")
            params_layout.addRow("Mensaje:", self.batch_notification_message)
            
            self.batch_notification_type = QComboBox()
            self.batch_notification_type.addItems(["success", "warning", "error", "info"])
            params_layout.addRow("Tipo:", self.batch_notification_type)
            
            self.batch_notification_icon = QLineEdit("https://miempresa.com/icons/notification.png")
            params_layout.addRow("Icono URL:", self.batch_notification_icon)
            
            self.batch_notification_action_url = QLineEdit("https://miempresa.com/action")
            params_layout.addRow("Action URL:", self.batch_notification_action_url)
            
            self.batch_notification_action_text = QLineEdit("Ver Detalles")
            params_layout.addRow("Action Text:", self.batch_notification_action_text)
            
            self.batch_notification_additional_info = QTextEdit("Información adicional sobre esta notificación.")
            params_layout.addRow("Info Adicional:", self.batch_notification_additional_info)
            
            self.batch_notification_preferences_url = QLineEdit("https://miempresa.com/preferences")
            params_layout.addRow("Preferences URL:", self.batch_notification_preferences_url)
            
            self.batch_params_layout.addWidget(params_group)
            
        elif email_type == "alert":
            # Parámetros para alerta
            params_group = QGroupBox("Parámetros de Alerta")
            params_layout = QFormLayout(params_group)
            
            self.batch_alert_title = QLineEdit("Alerta de Seguridad")
            params_layout.addRow("Título:", self.batch_alert_title)
            
            self.batch_alert_message = QTextEdit("Este es un mensaje de alerta de prueba.")
            params_layout.addRow("Mensaje:", self.batch_alert_message)
            
            self.batch_alert_type = QComboBox()
            self.batch_alert_type.addItems(["info", "warning", "error"])
            params_layout.addRow("Tipo:", self.batch_alert_type)
            
            self.batch_alert_steps = QTextEdit("Paso 1: Verificar conexión\nPaso 2: Actualizar contraseña\nPaso 3: Cerrar sesiones")
            self.batch_alert_steps.setPlaceholderText("Un paso por línea")
            params_layout.addRow("Pasos:", self.batch_alert_steps)
            
            self.batch_alert_action_url = QLineEdit("https://miempresa.com/action")
            params_layout.addRow("Action URL:", self.batch_alert_action_url)
            
            self.batch_alert_action_text = QLineEdit("Resolver Ahora")
            params_layout.addRow("Action Text:", self.batch_alert_action_text)
            
            self.batch_alert_contact_support = QCheckBox("Incluir información de soporte")
            self.batch_alert_contact_support.setChecked(True)
            params_layout.addRow("", self.batch_alert_contact_support)
            
            self.batch_params_layout.addWidget(params_group)
    
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
    
    def schedule_preview_update(self):
        """Programa una actualización de la vista previa después de un retraso"""
        # Cancelar el temporizador anterior si existe
        if self.current_preview_timer:
            self.current_preview_timer.stop()
        
        # Crear nuevo temporizador para actualizar después de 500ms
        self.current_preview_timer = QTimer()
        self.current_preview_timer.setSingleShot(True)
        self.current_preview_timer.timeout.connect(self.update_preview)
        self.current_preview_timer.start(500)
    
    def update_preview(self):
        """Actualiza la vista previa del email"""
        try:
            if not hasattr(self, 'current_email_type') or not self.current_email_type:
                return
                
            if not self.template_env:
                self.html_preview.setHtml("<p>Error: El motor de plantillas no está configurado.</p>")
                return
            
            # Determinar la plantilla según el tipo de email actual
            if self.current_email_type == "welcome":
                template_name = "welcome.html"
                template_data = self.get_welcome_template_data()
            elif self.current_email_type == "password_reset":
                template_name = "password_reset.html"
                template_data = self.get_password_reset_template_data()
            elif self.current_email_type == "notification":
                template_name = "notification.html"
                template_data = self.get_notification_template_data()
            elif self.current_email_type == "alert":
                template_name = "alert.html"
                template_data = self.get_alert_template_data()
            elif self.current_email_type == "batch":
                # Para batch, usamos el tipo seleccionado
                email_type = self.batch_email_type.currentText()
                if email_type == "welcome":
                    template_name = "welcome.html"
                    template_data = self.get_batch_welcome_template_data()
                elif email_type == "password-reset":
                    template_name = "password_reset.html"
                    template_data = self.get_batch_password_reset_template_data()
                elif email_type == "notification":
                    template_name = "notification.html"
                    template_data = self.get_batch_notification_template_data()
                elif email_type == "alert":
                    template_name = "alert.html"
                    template_data = self.get_batch_alert_template_data()
                else:
                    self.html_preview.setHtml("<p>Error: Tipo de email no válido.</p>")
                    return
            else:
                self.html_preview.setHtml("<p>Error: Tipo de email no válido.</p>")
                return
            
            # Iniciar el worker de renderizado
            self.render_worker = RenderPreviewWorker(self.template_env, template_name, template_data)
            self.render_worker.preview_ready.connect(self.set_preview_html)
            self.render_worker.error_occurred.connect(self.show_preview_error)
            self.render_worker.start()
            
        except Exception as e:
            self.html_preview.setHtml(f"<p>Error al renderizar vista previa: {str(e)}</p>")
    
    def set_preview_html(self, html_content):
        """Establece el contenido HTML en la vista previa"""
        self.preview_html_content = html_content  # Guardar para uso posterior
        self.html_preview.setHtml(html_content)
    
    def show_preview_error(self, error_message):
        """Muestra un error en la vista previa"""
        self.html_preview.setHtml(f"<p>Error: {error_message}</p>")
    
    def open_preview_in_browser(self):
        """Abre la vista previa actual en el navegador"""
        if not hasattr(self, 'preview_html_content') or not self.preview_html_content:
            QMessageBox.warning(self, "Error", "No hay vista previa disponible.")
            return
            
        try:
            # Crear archivo temporal
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.html', encoding='utf-8') as f:
                f.write(self.preview_html_content)
                temp_name = f.name
            
            # Abrir en navegador
            webbrowser.open('file://' + temp_name)
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudo abrir en el navegador: {str(e)}"
            )
    
    def save_preview_html(self):
        """Guarda la vista previa actual como archivo HTML"""
        if not hasattr(self, 'preview_html_content') or not self.preview_html_content:
            QMessageBox.warning(self, "Error", "No hay vista previa disponible.")
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Guardar HTML", "", "Archivos HTML (*.html *.htm)"
        )
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.preview_html_content)
                QMessageBox.information(self, "Éxito", f"HTML guardado en: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo guardar el archivo: {str(e)}")
    
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
    
    def get_welcome_template_data(self):
        """Obtiene los datos para la plantilla de bienvenida"""
        # Obtener el primer email y nombre
        email = self.welcome_user_email.toPlainText().split('\n')[0].strip()
        name = self.welcome_user_name.text() or "Usuario"
        
        return {
            "company": self.get_company_data(),
            "user": {
                "name": name,
                "email": email
            },
            "dashboard_url": self.welcome_dashboard_url.text(),
            "year": 2025
        }
    
    def get_password_reset_template_data(self):
        """Obtiene los datos para la plantilla de reset de contraseña"""
        # Obtener el primer email y nombre
        email = self.reset_user_email.toPlainText().split('\n')[0].strip()
        name = self.reset_user_name.text() or "Usuario"
        
        return {
            "company": self.get_company_data(),
            "user": {
                "name": name,
                "email": email
            },
            "reset_url": self.reset_url.text(),
            "expires_in": self.expires_in.value(),
            "year": 2025
        }
    
    def get_notification_template_data(self):
        """Obtiene los datos para la plantilla de notificación"""
        # Obtener el primer email y nombre
        email = self.notification_user_email.toPlainText().split('\n')[0].strip()
        name = self.notification_user_name.text() or "Usuario"
        
        return {
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
    
    def get_alert_template_data(self):
        """Obtiene los datos para la plantilla de alerta"""
        # Obtener el primer email y nombre
        email = self.alert_user_email.toPlainText().split('\n')[0].strip()
        name = self.alert_user_name.text() or "Usuario"
        
        # Obtener los pasos
        steps = [
            step.strip() 
            for step in self.alert_steps.toPlainText().split("\n") 
            if step.strip()
        ]
        
        return {
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
    
    def get_batch_welcome_template_data(self):
        """Obtiene los datos para la plantilla de bienvenida en lote"""
        # Usar el primer destinatario para la vista previa
        recipients = self.get_batch_recipients()
        if recipients:
            email, name = recipients[0]
        else:
            email = "usuario@ejemplo.com"
            name = "Usuario de Prueba"
        
        return {
            "company": self.get_company_data(),
            "user": {
                "name": name,
                "email": email
            },
            "dashboard_url": self.batch_dashboard_url.text(),
            "year": 2025
        }
    
    def get_batch_password_reset_template_data(self):
        """Obtiene los datos para la plantilla de reset en lote"""
        # Usar el primer destinatario para la vista previa
        recipients = self.get_batch_recipients()
        if recipients:
            email, name = recipients[0]
        else:
            email = "usuario@ejemplo.com"
            name = "Usuario de Prueba"
        
        return {
            "company": self.get_company_data(),
            "user": {
                "name": name,
                "email": email
            },
            "reset_url": self.batch_reset_url.text(),
            "expires_in": self.batch_expires_in.value(),
            "year": 2025
        }
    
    def get_batch_notification_template_data(self):
        """Obtiene los datos para la plantilla de notificación en lote"""
        # Usar el primer destinatario para la vista previa
        recipients = self.get_batch_recipients()
        if recipients:
            email, name = recipients[0]
        else:
            email = "usuario@ejemplo.com"
            name = "Usuario de Prueba"
        
        return {
            "company": self.get_company_data(),
            "user": {
                "name": name,
                "email": email
            },
            "notification": {
                "title": self.batch_notification_title.text(),
                "message": self.batch_notification_message.toPlainText(),
                "type": self.batch_notification_type.currentText(),
                "icon": self.batch_notification_icon.text(),
                "action_url": self.batch_notification_action_url.text(),
                "action_text": self.batch_notification_action_text.text(),
                "additional_info": self.batch_notification_additional_info.toPlainText()
            },
            "preferences_url": self.batch_notification_preferences_url.text(),
            "year": 2025
        }
    
    def get_batch_alert_template_data(self):
        """Obtiene los datos para la plantilla de alerta en lote"""
        # Usar el primer destinatario para la vista previa
        recipients = self.get_batch_recipients()
        if recipients:
            email, name = recipients[0]
        else:
            email = "usuario@ejemplo.com"
            name = "Usuario de Prueba"
        
        # Obtener los pasos
        steps = [
            step.strip() 
            for step in self.batch_alert_steps.toPlainText().split("\n") 
            if step.strip()
        ]
        
        return {
            "company": self.get_company_data(),
            "user": {
                "name": name,
                "email": email
            },
            "alert": {
                "title": self.batch_alert_title.text(),
                "message": self.batch_alert_message.toPlainText(),
                "type": self.batch_alert_type.currentText(),
                "steps": steps,
                "action_url": self.batch_alert_action_url.text(),
                "action_text": self.batch_alert_action_text.text(),
                "contact_support": self.batch_alert_contact_support.isChecked()
            },
            "year": 2025
        }
    
    def get_batch_recipients(self):
        """Obtiene la lista de destinatarios para el envío en lote"""
        text = self.batch_recipients_text.toPlainText()
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
                
            # Actualizar la vista previa
            self.update_preview()
    
    def manage_batch_recipients(self):
        """Gestiona los destinatarios para el envío en lote"""
        # Obtener destinatarios actuales
        recipients = self.get_batch_recipients()
        emails = [email for email, _ in recipients]
        names = [name for _, name in recipients]
        
        # Crear y mostrar el diálogo
        dialog = EmailRecipientsDialog(self, emails, names)
        if dialog.exec_() == QDialog.Accepted:
            # Obtener los destinatarios del diálogo
            recipients = dialog.get_recipients()
            
            # Actualizar el campo de texto
            text_lines = []
            for email, name in recipients:
                text_lines.append(f"{email}, {name}" if name else email)
            
            self.batch_recipients_text.setText("\n".join(text_lines))
            
            # Actualizar la vista previa
            self.update_preview()
            
    def browse_templates_dir(self):
        directory = QFileDialog.getExistingDirectory(
            self, "Seleccionar Directorio de Plantillas"
        )
        if directory:
            self.templates_dir_input.setText(directory)
            self.setup_template_engine(directory)
            
            # Actualizar la vista previa con el nuevo motor de plantillas
            self.update_preview()
    
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
    
    def send_api_request(self, endpoint, data):
        """Envía una petición a la API de emails"""
        # Validar API key
        api_key = self.api_key_input.text()
        if not api_key:
            QMessageBox.warning(self, "Error", "La API key es requerida")
            return None
            
        headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }
        
        try:
            url = f"{self.api_url}/emails/{endpoint}"
            print(f"Enviando petición a: {url}")
            print(f"Datos: {json.dumps(data, indent=2)}")
            
            response = requests.post(
                url,
                json=data,
                headers=headers
            )
            
            # Imprimir respuesta para debug
            print(f"Código de respuesta: {response.status_code}")
            print(f"Respuesta: {response.text}")
            
            if response.status_code == 200:
                return response.json()
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
                return None
                
        except requests.exceptions.ConnectionError:
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudo conectar con la API en {self.api_url}. ¿Está el servidor corriendo?"
            )
            return None
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Error inesperado: {str(e)}"
            )
            return None
    
    def send_welcome_email(self):
        """Envía el email de bienvenida"""
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
        
        # Datos para la petición
        company_data = self.get_company_data()
        
        # Si hay múltiples destinatarios, usar MultiEmailAddressBase
        if len(valid_emails) > 1:
            # Preparar datos de usuarios
            emails_list = []
            names_list = []
            
            for i, email in enumerate(valid_emails):
                emails_list.append(email)
                
                # Buscar el nombre correspondiente en el índice original
                original_idx = emails.index(email)
                if original_idx < len(names) and names[original_idx]:
                    names_list.append(names[original_idx])
                else:
                    names_list.append(self.welcome_user_name.text())
            
            user_data = {
                "emails": emails_list,
                "names": names_list
            }
        else:
            # Un solo destinatario, usar EmailAddressBase
            user_data = {
                "email": valid_emails[0],
                "name": names[0] if names and len(names) > 0 else self.welcome_user_name.text()
            }
        
        # Parámetros de consulta
        query_data = {
            "dashboard_url": self.welcome_dashboard_url.text()
        }
        
        # Enviar la petición
        result = self.send_api_request("welcome", {
            "company": company_data,
            "user": user_data,
            "query": query_data
        })
        
        if result:
            QMessageBox.information(
                self,
                "Éxito",
                f"El email de bienvenida se ha enviado correctamente."
            )
    
    def send_password_reset(self):
        """Envía el email de restablecimiento de contraseña"""
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
        
        # Datos para la petición
        company_data = self.get_company_data()
        
        # Si hay múltiples destinatarios, usar MultiEmailAddressBase
        if len(valid_emails) > 1:
            # Preparar datos de usuarios
            emails_list = []
            names_list = []
            
            for i, email in enumerate(valid_emails):
                emails_list.append(email)
                
                # Buscar el nombre correspondiente en el índice original
                original_idx = emails.index(email)
                if original_idx < len(names) and names[original_idx]:
                    names_list.append(names[original_idx])
                else:
                    names_list.append(self.reset_user_name.text())
            
            user_data = {
                "emails": emails_list,
                "names": names_list
            }
        else:
            # Un solo destinatario, usar EmailAddressBase
            user_data = {
                "email": valid_emails[0],
                "name": names[0] if names and len(names) > 0 else self.reset_user_name.text()
            }
        
        # Parámetros de consulta
        query_data = {
            "reset_url": self.reset_url.text(),
            "expires_in": self.expires_in.value()
        }
        
        # Enviar la petición
        result = self.send_api_request("password-reset", {
            "company": company_data,
            "user": user_data,
            "query": query_data
        })
        
        if result:
            QMessageBox.information(
                self,
                "Éxito",
                f"El email de restablecimiento de contraseña se ha enviado correctamente."
            )
    
    def send_notification(self):
        """Envía el email de notificación"""
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
        
        # Validar campos requeridos
        if not self.notification_title.text() or not self.notification_message.toPlainText():
            QMessageBox.warning(self, "Error", "El título y mensaje de la notificación son requeridos")
            return
        
        # Datos para la petición
        company_data = self.get_company_data()
        
        # Si hay múltiples destinatarios, usar MultiEmailAddressBase
        if len(valid_emails) > 1:
            # Preparar datos de usuarios
            emails_list = []
            names_list = []
            
            for i, email in enumerate(valid_emails):
                emails_list.append(email)
                
                # Buscar el nombre correspondiente en el índice original
                original_idx = emails.index(email)
                if original_idx < len(names) and names[original_idx]:
                    names_list.append(names[original_idx])
                else:
                    names_list.append(self.notification_user_name.text())
            
            user_data = {
                "emails": emails_list,
                "names": names_list
            }
        else:
            # Un solo destinatario, usar EmailAddressBase
            user_data = {
                "email": valid_emails[0],
                "name": names[0] if names and len(names) > 0 else self.notification_user_name.text()
            }
        
        # Parámetros de consulta
        query_data = {
            "title": self.notification_title.text(),
            "message": self.notification_message.toPlainText(),
            "type": self.notification_type.currentText(),
            "icon": self.notification_icon.text() or None,
            "action_url": self.notification_action_url.text() or None,
            "action_text": self.notification_action_text.text() or None,
            "additional_info": self.notification_additional_info.toPlainText() or None,
            "preferences_url": self.notification_preferences_url.text()
        }
        
        # Enviar la petición
        result = self.send_api_request("notification", {
            "company": company_data,
            "user": user_data,
            "query": query_data
        })
        
        if result:
            QMessageBox.information(
                self,
                "Éxito",
                f"El email de notificación se ha enviado correctamente."
            )
    
    def send_alert(self):
        """Envía el email de alerta"""
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
        
        # Validar campos requeridos
        if not self.alert_title.text() or not self.alert_message.toPlainText():
            QMessageBox.warning(self, "Error", "El título y mensaje de la alerta son requeridos")
            return
        
        # Obtener pasos
        steps = [
            step.strip() 
            for step in self.alert_steps.toPlainText().split("\n") 
            if step.strip()
        ]
        
        # Datos para la petición
        company_data = self.get_company_data()
        
        # Si hay múltiples destinatarios, usar MultiEmailAddressBase
        if len(valid_emails) > 1:
            # Preparar datos de usuarios
            emails_list = []
            names_list = []
            
            for i, email in enumerate(valid_emails):
                emails_list.append(email)
                
                # Buscar el nombre correspondiente en el índice original
                original_idx = emails.index(email)
                if original_idx < len(names) and names[original_idx]:
                    names_list.append(names[original_idx])
                else:
                    names_list.append(self.alert_user_name.text())
            
            user_data = {
                "emails": emails_list,
                "names": names_list
            }
        else:
            # Un solo destinatario, usar EmailAddressBase
            user_data = {
                "email": valid_emails[0],
                "name": names[0] if names and len(names) > 0 else self.alert_user_name.text()
            }
        
        # Datos de la alerta
        alert_data = {
            "title": self.alert_title.text(),
            "message": self.alert_message.toPlainText(),
            "type": self.alert_type.currentText(),
            "steps": steps if steps else None,
            "action_url": self.alert_action_url.text() or None,
            "action_text": self.alert_action_text.text() or None,
            "contact_support": self.alert_contact_support.isChecked()
        }
        
        # Enviar la petición
        result = self.send_api_request("alert", {
            "company": company_data,
            "user": user_data,
            "alert": alert_data
        })
        
        if result:
            QMessageBox.information(
                self,
                "Éxito",
                f"El email de alerta se ha enviado correctamente."
            )
    
    def send_batch_email(self):
        """Envía emails en lote usando el endpoint batch"""
        # Obtener tipo de email
        email_type = self.batch_email_type.currentText()
        
        # Obtener destinatarios
        recipients = self.get_batch_recipients()
        if not recipients:
            QMessageBox.warning(self, "Error", "Debe agregar al menos un destinatario")
            return
        
        # Validar emails
        emails = [email for email, _ in recipients]
        valid_emails, invalid_emails = validate_emails(emails)
        
        if not valid_emails:
            QMessageBox.warning(self, "Error", "No se encontraron emails válidos")
            return
        
        if invalid_emails:
            invalid_indices = [emails.index(email) for email in invalid_emails]
            
            # Filtrar los destinatarios inválidos
            invalid_recipients = [recipients[i] for i in invalid_indices]
            invalid_str = "\n".join([f"{email}, {name}" for email, name in invalid_recipients])
            
            msg = "Se encontraron emails inválidos:\n\n"
            msg += invalid_str
            msg += "\n\n¿Desea continuar con los emails válidos?"
            
            reply = QMessageBox.question(
                self, "Emails inválidos", msg,
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            
            if reply == QMessageBox.No:
                return
            
            # Filtrar solo los destinatarios válidos
            valid_indices = [i for i in range(len(emails)) if emails[i] in valid_emails]
            recipients = [recipients[i] for i in valid_indices]
        
        # Preparar datos para la API
        company_data = self.get_company_data()
        
        # Convertir a formato de destinatarios para el endpoint batch
        recipients_data = []
        for email, name in recipients:
            recipients_data.append({
                "email": email,
                "name": name
            })
        
        # Parámetros específicos según el tipo de email
        if email_type == "welcome":
            # Validar campos requeridos
            if not self.batch_dashboard_url.text():
                QMessageBox.warning(self, "Error", "La URL del dashboard es requerida")
                return
                
            query_data = {
                "dashboard_url": self.batch_dashboard_url.text()
            }
            alert_data = None
            
        elif email_type == "password-reset":
            # Validar campos requeridos
            if not self.batch_reset_url.text():
                QMessageBox.warning(self, "Error", "La URL de reset es requerida")
                return
                
            query_data = {
                "reset_url": self.batch_reset_url.text(),
                "expires_in": self.batch_expires_in.value()
            }
            alert_data = None
            
        elif email_type == "notification":
            # Validar campos requeridos
            if not self.batch_notification_title.text() or not self.batch_notification_message.toPlainText():
                QMessageBox.warning(self, "Error", "El título y mensaje de la notificación son requeridos")
                return
                
            query_data = {
                "title": self.batch_notification_title.text(),
                "message": self.batch_notification_message.toPlainText(),
                "type": self.batch_notification_type.currentText(),
                "icon": self.batch_notification_icon.text() or None,
                "action_url": self.batch_notification_action_url.text() or None,
                "action_text": self.batch_notification_action_text.text() or None,
                "additional_info": self.batch_notification_additional_info.toPlainText() or None,
                "preferences_url": self.batch_notification_preferences_url.text()
            }
            alert_data = None
            
        elif email_type == "alert":
            # Validar campos requeridos
            if not self.batch_alert_title.text() or not self.batch_alert_message.toPlainText():
                QMessageBox.warning(self, "Error", "El título y mensaje de la alerta son requeridos")
                return
                
            # Obtener pasos
            steps = [
                step.strip() 
                for step in self.batch_alert_steps.toPlainText().split("\n") 
                if step.strip()
            ]
            
            # Para alertas, usamos el campo específico alert_data
            query_data = {}
            alert_data = {
                "title": self.batch_alert_title.text(),
                "message": self.batch_alert_message.toPlainText(),
                "type": self.batch_alert_type.currentText(),
                "steps": steps if steps else None,
                "action_url": self.batch_alert_action_url.text() or None,
                "action_text": self.batch_alert_action_text.text() or None,
                "contact_support": self.batch_alert_contact_support.isChecked()
            }
        else:
            QMessageBox.warning(self, "Error", f"Tipo de email no válido: {email_type}")
            return
        
        # Datos para la petición
        batch_data = {
            "email_type": email_type,
            "company": company_data,
            "recipients": recipients_data,
            "query": query_data
        }
        
        # Añadir alert_data si es necesario
        if alert_data:
            batch_data["alert"] = alert_data
        
        # Enviar la petición
        result = self.send_api_request("batch", batch_data)
        
        if result:
            QMessageBox.information(
                self,
                "Éxito",
                f"Se enviaron {result.get('sent', 0)} emails correctamente.\n" +
                (f"Fallaron {result.get('failed', 0)} envíos." if result.get('failed', 0) > 0 else "")
            )

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Establecer estilo base
    app.setStyle("Fusion")
    
    # Paleta de colores moderna
    palette = QPalette()
    
    # Colores principales con enfoque moderno
    primary_color = QColor(156, 39, 176)      # Morado principal (más brillante)
    secondary_color = QColor(103, 58, 183)    # Violeta secundario
    background_color = QColor(250, 250, 252)  # Fondo general muy claro
    surface_color = QColor(255, 255, 255)     # Superficies (como tarjetas)
    text_primary = QColor(33, 33, 33)         # Texto principal
    text_secondary = QColor(117, 117, 117)    # Texto secundario
    divider_color = QColor(238, 238, 238)     # Divisores
    error_color = QColor(244, 67, 54)         # Error
    
    # Configurar paleta
    palette.setColor(QPalette.Window, background_color)
    palette.setColor(QPalette.WindowText, text_primary)
    palette.setColor(QPalette.Base, surface_color)
    palette.setColor(QPalette.AlternateBase, QColor(245, 245, 250))
    palette.setColor(QPalette.ToolTipBase, surface_color)
    palette.setColor(QPalette.ToolTipText, text_primary)
    palette.setColor(QPalette.Text, text_primary)
    palette.setColor(QPalette.Button, surface_color)
    palette.setColor(QPalette.ButtonText, text_primary)
    palette.setColor(QPalette.BrightText, surface_color)
    palette.setColor(QPalette.Highlight, primary_color)
    palette.setColor(QPalette.HighlightedText, surface_color)
    palette.setColor(QPalette.Disabled, QPalette.Text, text_secondary)
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, text_secondary)
    
    app.setPalette(palette)
    
    # Establecer estilo moderno con CSS
    app.setStyleSheet("""
        /* Estilo general */
        QMainWindow, QDialog {
            background-color: #fafafc;
        }
        
        /* Barra lateral */
        QListWidget {
            background-color: #2e2e36;
            border: none;
            border-radius: 0px;
            font-size: 14px;
            padding: 8px 0px;
        }
        
        QListWidget::item {
            color: #e0e0e0;
            padding: 12px 16px;
            margin: 4px 8px;
            border-radius: 6px;
        }
        
        QListWidget::item:selected {
            background-color: #9c27b0;
            color: white;
        }
        
        QListWidget::item:hover:!selected {
            background-color: #3a3a44;
        }
        
        /* Encabezados y etiquetas */
        QLabel {
            color: #212121;
            font-size: 13px;
        }
        
        QGroupBox {
            font-size: 14px;
            font-weight: bold;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            margin-top: 16px;
            padding-top: 16px;
            background-color: white;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 10px;
            color: #9c27b0;
            background-color: transparent;
        }
        
        /* Campos de entrada */
        QLineEdit, QTextEdit, QComboBox, QSpinBox {
            border: 1px solid #e0e0e0;
            border-radius: 6px;
            padding: 8px;
            background-color: white;
            selection-background-color: #9c27b0;
            selection-color: white;
            min-height: 20px;
        }
        
        QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus {
            border: 2px solid #9c27b0;
            padding: 7px;
        }
        
        QComboBox::drop-down {
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 20px;
            border-left-width: 0px;
            border-top-right-radius: 6px;
            border-bottom-right-radius: 6px;
        }
        
        QComboBox::down-arrow {
            image: url(:/icons/down-arrow.png);
            width: 12px;
            height: 12px;
        }
        
        QComboBox QAbstractItemView {
            border: 1px solid #e0e0e0;
            border-radius: 6px;
            background: white;
            selection-background-color: #9c27b0;
        }
        
        /* Botones */
        QPushButton {
            background-color: #f5f5f5;
            color: #212121;
            border: none;
            border-radius: 6px;
            padding: 10px 16px;
            font-weight: bold;
            min-width: 80px;
        }
        
        QPushButton:hover {
            background-color: #e0e0e0;
        }
        
        QPushButton:pressed {
            background-color: #d0d0d0;
        }
        
        QPushButton#primaryButton {
            background-color: #9c27b0;
            color: white;
        }
        
        QPushButton#primaryButton:hover {
            background-color: #8e24aa;
        }
        
        QPushButton#primaryButton:pressed {
            background-color: #7b1fa2;
        }
        
        /* Checkbox y Radio Button */
        QCheckBox, QRadioButton {
            spacing: 8px;
        }
        
        QCheckBox::indicator, QRadioButton::indicator {
            width: 18px;
            height: 18px;
        }
        
        QCheckBox::indicator:checked, QRadioButton::indicator:checked {
            background-color: #9c27b0;
            border: 2px solid #9c27b0;
            border-radius: 3px;
        }
        
        QCheckBox::indicator:unchecked, QRadioButton::indicator:unchecked {
            background-color: #fff;
            border: 2px solid #aaa;
            border-radius: 3px;
        }
        
        /* Vista previa */
        QTextBrowser {
            background-color: white;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 4px;
        }
        
        /* Scrollbars */
        QScrollBar:vertical {
            border: none;
            background: #f5f5f5;
            width: 10px;
            margin: 0px;
        }
        
        QScrollBar::handle:vertical {
            background: #9c27b0;
            min-height: 20px;
            border-radius: 5px;
        }
        
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px;
        }
        
        QScrollBar:horizontal {
            border: none;
            background: #f5f5f5;
            height: 10px;
            margin: 0px;
        }
        
        QScrollBar::handle:horizontal {
            background: #9c27b0;
            min-width: 20px;
            border-radius: 5px;
        }
        
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
            width: 0px;
        }
        
        /* Splitter */
        QSplitter::handle {
            background-color: #e0e0e0;
        }
        
        QSplitter::handle:horizontal {
            width: 2px;
        }
        
        QSplitter::handle:vertical {
            height: 2px;
        }
        
        /* Toolbar y separadores */
        QToolBar {
            background-color: white;
            border-bottom: 1px solid #e0e0e0;
            spacing: 6px;
            padding: 3px;
        }
        
        QFrame[frameShape="4"], /* QFrame::HLine */
        QFrame[frameShape="5"] /* QFrame::VLine */
        {
            background-color: #e0e0e0;
        }
    """)
    
    window = ImprovedEmailTesterGUI()
    window.show()
    
    sys.exit(app.exec_())
    
    window = ImprovedEmailTesterGUI()
    window.show()
    
    sys.exit(app.exec_())