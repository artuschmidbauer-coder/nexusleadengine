# Nexus Lead Engine ⚡
### Plataforma B2B de Inteligencia Técnica, Auditoría de Conversión y Monetización de Leads

- **Sitio Web Oficial:** [https://nexusleadengine.io](https://nexusleadengine.io)
- **Repositorio GitHub:** [artuschmidbauer-coder/nexusleadengine](https://github.com/artuschmidbauer-coder/nexusleadengine)
- **Email Corporativo:** `hola@nexusleadengine.io` / `auracomercial387@gmail.com`
- **Ubicación del Proyecto Local:** `/Users/artu/Desktop/Nexus`

---

## 🎯 Visión y Modelo del Negocio

**Nexus Lead Engine** es una plataforma automatizada que ayuda a agencias de marketing, consultores y empresas de software a conseguir clientes B2B calificados mediante:
1. **Auditoría Técnica en Tiempo Real:** Detección automática de fugas de conversión en sitios web (falta de Pixel de Meta/Google, lentitud, falta de widget de reserva).
2. **Generación de Mensajes de Prospección (Outreach Hooks):** Redacción hiper-personalizada en inglés nativo (para EE.UU. y Reino Unido) y español (para España y Latinoamérica).
3. **API & Servidor MCP:** Consumo programático directo para automatizadores de Make.com, n8n, GoHighLevel y agentes autónomos.
4. **Pasarelas de Pago Multi-canal:**
   - **Polar.sh** (Merchant of Record / Stripe Connect Express): Facturación internacional y cobro con tarjeta 100% legal hacia Argentina.
   - **NOWPayments / Binance Pay:** Cobros directos en criptomonedas (USDT/USDC/BTC) acreditados en billetera.

---

## 📚 Documentación Central del Proyecto

Toda la estrategia, auditorías y manuales del proyecto se encuentran centralizados en [`docs/`](docs/):

* 📊 **[Auditoría Técnica y Proyecciones de Negocio](docs/auditoria_y_proyecciones.md):** Dictamen de seguridad (SSRF, Auth Bypass mitigados), legalidad (CAN-SPAM, RGPD, MoR) y proyecciones a 3, 6 y 12 meses.
* 📋 **[Manual Operativo de la Empresa](docs/manual_operativo.md):** Estructura de gobernanza financiera para el CFO (regla 70% ganancia / 20% fondo IA con aprobación / 10% reserva) y cartera de prospectos.
* 📦 **[Propuesta de Paquetes Comerciales](docs/propuesta_paquetes.md):** Escalera de valor ($290 USD Starter, $590 USD Growth, $1,500 USD Enterprise).
* ⚖️ **[Dictamen Fundacional del Consejo](docs/dictamen_consejo.md):** Elección del modelo de negocio de costo $0 inicial con consenso multi-IA.
* 🚀 **[Kit de Lanzamiento para Comunidades (n8n / Reddit)](LAUNCH_KIT.md):** Plantillas de publicación listas para atraer tráfico orgánico.
* 🔌 **[Guía del Servidor MCP](MCP_GUIDE.md):** Protocolo para conectar la API de Nexus a Cursor, Windsurf o Claude Desktop.

---

## 💰 Catálogo de Precios (Packs de Créditos)

| Paquete | Leads / Auditorías | Precio USD | Costo por Lead | Enfoque |
|---|---|---|---|---|
| **Pack Micro** | 15 leads | **$9 USD** | $0.60 | Prueba inmediata en 30s |
| **Pack Starter** | 60 leads | **$29 USD** | $0.48 | Flujos semanales en Make/n8n |
| **Pack Pro** | 200 leads | **$69 USD** | $0.34 | Agencias activas |
| **Pack Scale** | 600 leads | **$149 USD** | $0.24 | Máximo volumen (-60% descuento) |

---

## 🚀 Comandos Rápidos de Desarrollo y Pruebas

Ejecuta todos los comandos desde la raíz de este directorio (`/Users/artu/Desktop/Nexus`):

### 1. Iniciar el Servidor API y la Landing Page
```bash
./start_server.sh
```
* **Landing Page:** [http://localhost:8000](http://localhost:8000)
* **Documentación Interactiva Swagger:** [http://localhost:8000/docs](http://localhost:8000/docs)
* **Dashboard Administrativo:** [http://localhost:8000/static/dashboard.html](http://localhost:8000/static/dashboard.html)

### 2. Ejecutar la Suite de Pruebas Automatizadas
```bash
# Probar endpoints de API y autenticación:
./.venv/bin/python3 test_api.py

# Probar flujo de pagos y webhooks:
./.venv/bin/python3 test_payments.py
./.venv/bin/python3 test_polar.py
./.venv/bin/python3 test_nowpayments.py
```

### 3. Iniciar el Servidor MCP Local
```bash
./.venv/bin/python3 mcp_server.py
```

---

## 🏗️ Infraestructura y Despliegue en Producción

* **Hosting:** Render (`render.yaml` y `Procfile` incluidos).
* **Contenedor:** `Dockerfile` basado en Python 3.14 / Debian Bookworm.
* **Dominio & DNS:** Gestionado con Porkbun y certificado SSL automático en Render.
* **Control de Versiones:** Git sincronizado con la rama `main` de GitHub.

> [!TIP]
> **Flujo de Trabajo:** De ahora en más, todo el desarrollo, modificaciones del frontend y nuevos módulos se trabajan directamente en esta carpeta (`/Users/artu/Desktop/Nexus`) para mantener el proyecto 100% cohesionado y con control de versiones.
