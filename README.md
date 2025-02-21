# Sistema de Plantillas de Email 📧

Un sistema robusto y flexible para el envío de emails transaccionales y marketing, construido con Python y Jinja2, integrado con el servicio de Resend.

## 🌟 Características

- **Plantillas Responsivas**: Diseños adaptables y modernos para todos los clientes de correo
- **Múltiples Tipos de Email**:
  - Emails de Bienvenida
  - Confirmaciones de Pedido
  - Newsletters
  - Restablecimiento de Contraseña
  - Notificaciones
  - Alertas

- **Diseño Modular**: Arquitectura basada en componentes reutilizables
- **Validación Integrada**: Verificación automática de datos y direcciones de email
- **Personalización**: Soporte completo para la marca de tu empresa
- **Integración con Resend**: API de envío de emails moderna y confiable

## 📋 Requisitos

- Python 3.7+
- Resend API Key
- Jinja2
- Dataclasses (incluido en Python 3.7+)

## 🚀 Instalación

1. Clona el repositorio:
```bash
git clone [url-del-repositorio]
cd sistema-emails
```

2. Instala las dependencias:
```bash
pip install -r requirements.txt
```

3. Configura las variables de entorno:
```bash
export RESEND_API_KEY='tu-api-key'
```

## 💡 Uso

### Configuración Básica

```python
from models import EmailAddress, Company
from service import EmailService

# Configura la información de tu empresa
company = Company(
    name="Tu Empresa",
    address="Tu Dirección",
    support_email=EmailAddress("soporte@tuempresa.com"),
    website="https://tuempresa.com",
    logo_url="https://tuempresa.com/logo.png"
)

# Inicializa el servicio de email
email_service = EmailService(
    api_key="tu-api-key-de-resend",
    default_from=EmailAddress("no-reply@tuempresa.com", "Tu Empresa")
)
```

### Envío de Emails

#### Email de Bienvenida
```python
from templates import WelcomeEmail

welcome_email = WelcomeEmail(
    company=company,
    user=EmailAddress("usuario@ejemplo.com", "Nuevo Usuario"),
    dashboard_url="https://tuempresa.com/dashboard"
)

email_service.send(
    email=welcome_email,
    to=EmailAddress("usuario@ejemplo.com", "Nuevo Usuario"),
    subject="¡Bienvenido a Tu Empresa!"
)
```

#### Confirmación de Pedido
```python
from templates import OrderConfirmationEmail
from models import Order, OrderItem

order = Order(
    number="ORD-123",
    items=[
        OrderItem(name="Producto 1", quantity=2, price=29.99),
        OrderItem(name="Producto 2", quantity=1, price=49.99)
    ],
    shipping_address="Calle Principal 123",
    delivery_estimate="2-3 días hábiles"
)

confirmation_email = OrderConfirmationEmail(
    company=company,
    customer=EmailAddress("cliente@ejemplo.com", "Cliente"),
    order=order
)

email_service.send(
    email=confirmation_email,
    to=EmailAddress("cliente@ejemplo.com", "Cliente"),
    subject="Confirmación de tu pedido #ORD-123"
)
```

## 📝 Plantillas Disponibles

1. **welcome.html**: Email de bienvenida para nuevos usuarios
2. **order_confirmation.html**: Confirmación de pedidos
3. **newsletter.html**: Boletines informativos
4. **password_reset.html**: Restablecimiento de contraseña
5. **notification.html**: Notificaciones generales
6. **alert.html**: Alertas y advertencias

## 🎨 Personalización

Todas las plantillas pueden ser personalizadas modificando:

- Colores y estilos en `base.html`
- Contenido y estructura en las plantillas individuales
- Variables de la marca en la configuración de Company

## 🛡️ Validación

El sistema incluye validaciones automáticas para:

- Direcciones de email válidas
- Datos requeridos en las plantillas
- Cantidades y precios en órdenes
- Estructura de datos consistente

## 📚 Estructura del Proyecto

```
sistema-emails/
├── emails/
│   ├── __init__.py
│   ├── base.py
│   ├── models.py
│   ├── service.py
│   └── templates.py
├── templates/
│   ├── alert.html
│   ├── base.html
│   ├── newsletter.html
│   ├── notification.html
│   ├── order_confirmation.html
│   ├── password_reset.html
│   └── welcome.html
├── requirements.txt
└── README.md
```

## 🤝 Contribución

Las contribuciones son bienvenidas. Por favor, sigue estos pasos:

1. Fork el repositorio
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📄 Licencia

Este proyecto está licenciado bajo la Licencia MIT - ver el archivo [LICENSE.md](LICENSE.md) para más detalles.

## 🙋‍♂️ Soporte

Si tienes alguna pregunta o necesitas ayuda, no dudes en:

- Abrir un issue en el repositorio
- Contactar al equipo de soporte: soporte@tuempresa.com
- Consultar la documentación completa en: docs.tuempresa.com