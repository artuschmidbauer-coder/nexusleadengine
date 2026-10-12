# NexusLeadEngine.io ⚡
### Motor Autónomo de Inteligencia y Comercialización de Leads B2B (Agent-to-Agent / M2M)

- **Dominio Oficial:** [nexusleadengine.io](https://nexusleadengine.io)
- **Email de Contacto:** `hola@nexusleadengine.io`
- **Pasarela Rápida PayPal:** [paypal.me/NexusLeadEngine](https://www.paypal.com/paypalme/NexusLeadEngine)

---

## 🎯 Visión Unificada
**NexusLeadEngine.io** convierte la prospección de clientes de alto ticket en un servicio puramente programático (Lead-as-an-API). Sus clientes son sistemas automatizados (bots de WhatsApp, flujos de Make.com, n8n y agentes de GoHighLevel) que compran y consumen oportunidades calificadas en tiempo real sin requerir reuniones ni fricción humana.

---

## 💰 Precios Ultra Económicos ("No-Brainer Pricing")

Precios diseñados para que los bots y agencias compren por impulso sin tener que consultar:

| Paquete | Leads Calificados | Precio Total | Precio / Lead | Caso de Uso | Enlace de Pago Directo |
|---|---|---|---|---|---|
| **Pack Micro** | 15 leads | **$9 USD** | $0.60 | Prueba en 30s sin pensarlo | [Pagar $9 USD](https://www.paypal.com/paypalme/NexusLeadEngine/9USD) |
| **Pack Starter** | 60 leads | **$29 USD** | $0.48 | Flujos semanales en Make/n8n | [Pagar $29 USD](https://www.paypal.com/paypalme/NexusLeadEngine/29USD) |
| **Pack Pro** | 200 leads | **$69 USD** | $0.34 | Bots y agencias activas | [Pagar $69 USD](https://www.paypal.com/paypalme/NexusLeadEngine/69USD) |
| **Pack Scale** | 600 leads | **$149 USD** | $0.24 | Máximo volumen (-60% descuento) | [Pagar $149 USD](https://www.paypal.com/paypalme/NexusLeadEngine/149USD) |

---

## 🚀 Cómo Ejecutar el Proyecto

```bash
cd /Users/artu/.gemini/antigravity/scratch/lead_stream_engine

# 1. Correr la demostración en terminal:
./.venv/bin/python3 run_demo.py

# 2. Iniciar el servidor API y la Landing Page:
./start_server.sh
```

- **Landing Page en Vivo:** `http://localhost:8000/`
- **Documentación Interactiva Swagger:** `http://localhost:8000/docs`

---

## 📡 Endpoints Principales

| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/` | Landing Page moderna lista para producción. |
| `GET` | `/v1/billing/packages` | Consulta los paquetes de precios ultra económicos. |
| `POST` | `/v1/billing/paypal-activate` | Activa créditos y genera la API Key tras pagar en PayPal.me. |
| `POST` | `/v1/billing/create-checkout` | Genera sesión de pago directo. |
| `GET` | `/v1/billing/balance` | Consulta saldo y consumo por API Key. |
| `POST` | `/v1/webhooks/subscribe` | Registra el bot receptor para streaming en tiempo real. |
| `POST` | `/v1/leads/trigger-scan` | Dispara prospección y deduce 1 crédito por lead calificado. |
