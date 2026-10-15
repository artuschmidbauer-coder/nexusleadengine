# 🚀 Guía Maestra de Publicación y Caza de Bots (Bot Hunting)
**NexusLeadEngine.io — Estrategia de Captación Inmediata de Tráfico, Agencias y Bots**

Este documento contiene los copys exactos, tácticas de guerrilla comprobadas y enlaces de alta para conseguir los primeros 100 visitantes técnicos y las primeras ventas ($15 a $69 USD) con **$0 de presupuesto en publicidad**.

---

## 🎯 Eje 1: Caza de Bots (MCP & AI Agent Registries)

Los agentes de IA (Claude Desktop, Cursor, LangChain, AutoGen) necesitan herramientas externas para prospectar. Al registrarnos en los directorios de MCP, los bots nos descubren y consumen nuestra API de forma autónoma.

### 1. Smithery.ai (El mayor registro de servidores MCP para Claude y Cursor)
* **URL:** https://smithery.ai
* **Comando de registro / validación:**
  ```bash
  npx -y @smithery/cli@latest run mcp_server.py
  ```
* **Nombre:** `nexus-lead-engine`
* **Descripción:** `Real-time B2B lead intelligence, live website technical audit, and conversion leak detection for sales bots and agencies.`
* **Configuración del Servidor (para agregar en `claude_desktop_config.json`):**
  ```json
  {
    "mcpServers": {
      "nexus-lead-engine": {
        "command": "python",
        "args": ["/ruta/absoluta/a/mcp_server.py"],
        "env": {
          "NEXUS_API_URL": "https://nexusleadengine.io"
        }
      }
    }
  }
  ```

### 2. Glama.ai MCP Hub
* **URL:** https://glama.ai/mcp/servers
* **Tagline:** Autonomous B2B Lead Intelligence & Conversion Auditor
* **Repositorio GitHub:** `https://github.com/artuschmidbauer-coder/nexusleadengine`
* **Manifiesto:** `https://nexusleadengine.io/.well-known/mcp.json`

### 3. Pull Request en `punkpeye/awesome-mcp-servers` (30k+ estrellas en GitHub)
* **Repositorio:** https://github.com/punkpeye/awesome-mcp-servers
* **Línea a agregar en la categoría `Business & Marketing Tools`:**
  ```markdown
  - [NexusLeadEngine](https://github.com/artuschmidbauer-coder/nexusleadengine) - Autonomous B2B prospect audit engine that scans websites in real time for missing tracking pixels, booking widgets, and drafts outreach hooks.
  ```

### 4. Custom GPT en OpenAI Store ("B2B Lead Auditor & Hook Drafter")
1. Ve a **chatgpt.com/gpts/create**
2. Nombre: **Nexus Lead & Web Auditor**
3. Descripción: *Audits any company website in seconds, identifies conversion leaks, and drafts high-converting outreach hooks.*
4. En **Actions (Acciones)**, pega la URL de OpenAPI:
   👉 `https://nexusleadengine.io/openapi.json`
5. Activa el GPT como **Público**. Cada consulta realizada por usuarios a través de OpenAI consulta en vivo nuestra API.

---

## 📢 Eje 2: Comunidades Técnicas (Reddit & Skool)

En Reddit los posts corporativos son ignorados; lo que funciona es el **aporte de valor técnico con interactividad**.

### Post 1: La Dinámica Interactiva "Audito tu web o la de tu cliente"
* **Subreddits recomendados:** `r/SideProject`, `r/SaaS`, `r/agency`, `r/webdev`
* **Título (EN):**
  > Built an engine that scans local business websites for conversion leaks & auto-drafts cold outreach hooks (Live demo + free tool)
* **Cuerpo del Post (EN):**
  ```markdown
  Hey Reddit,

  Most cold B2B outreach fails because people send generic pitches like "Hey, we do SEO / web design."
  
  I built an engine called [NexusLeadEngine](https://nexusleadengine.io) that approaches prospecting from a technical audit angle. In 1 call, it inspects:
  1. If the website has a Meta / Google Pixel installed (if not, they are burning ad money or losing retargeting).
  2. If they have mobile WhatsApp / booking widgets (if not, mobile traffic bounce rate is huge).
  3. The estimated monthly revenue leak based on their niche.
  4. Auto-generates a personalized outreach message mentioning these exact points.

  You can test it with ANY website in real time (no signup required):
  👉 https://nexusleadengine.io

  Drop any local business URL in the comments (dental, contractor, solar, agency) and I'll run the audit report for you, or test it yourself!

  Also built a free n8n blueprint that pulls these audited leads on a schedule if anyone wants the JSON flow. Would love your brutal feedback on the audit signals!
  ```

---

### Post 2: Para Comunidades de Automatizadores (`r/n8n`, `r/Integromat`, Skool)
* **Subreddits:** `r/n8n`, `r/Integromat`, `r/Automate`
* **Título (EN):**
  > [Free Resource] n8n workflow that scrapes & audits local businesses (checks missing pixels, WhatsApp & drafts outreach)
* **Cuerpo del Post (EN):**
  ```markdown
  Hey everyone,

  Instead of paying $100+/mo for Apollo or Clay with expiring credits just to get email lists that bounce, I put together an n8n workflow designed for agencies pitching high-ticket local niches (dental, roofing, remodeling, solar).

  What the workflow does:
  - Triggers every weekday at 9:00 AM.
  - Queries the NexusLeadEngine API for qualified businesses with verified phone numbers.
  - Verifies whether their website is missing a Meta Pixel or WhatsApp contact button.
  - Formats a pre-drafted WhatsApp / Email message pointing out the conversion leak.
  - Ready to route straight into your CRM, Slack, or Google Sheets.

  You can download the official JSON blueprint directly here:
  📥 https://nexusleadengine.io/templates/n8n

  It comes with free trial credits so you can run it in your own n8n instance and see the payload immediately. Hope it helps someone automate their outbound this week!
  ```

* **Versión en Español para Skool / Facebook ("Make en Español", "n8n en Español"):**
  ```markdown
  🔥 [Recurso Gratis] Flujo de n8n para auditar prospectos locales y prospectar en automático

  Buenas a todos! Les comparto un flujo de n8n que armé para agencias que ofrecen desarrollo web, funnels o pauta publicitaria.

  En lugar de mandar mensajes fríos genéricos, el flujo analiza la web del cliente en vivo, detecta si no tiene instalado el Píxel de Meta o botón de WhatsApp, calcula la fuga de clientes y redacta el mensaje de apertura comercial exacto.

  Pueden descargar el JSON oficial listo para importar en 1 clic aquí:
  👉 https://nexusleadengine.io/templates/n8n

  Viene con créditos de prueba para que lo corran en su propio n8n y vean cómo entrega los datos en tiempo real. ¡Espero que les sirva!
  ```

---

## ⚡ Eje 3: Hacker News (Show HN)

* **URL:** https://news.ycombinator.com/submit
* **Título:**
  > Show HN: NexusLeadEngine – Real-time website conversion leak auditor & B2B lead API
* **Texto:**
  ```markdown
  Hi HN,

  I built NexusLeadEngine (https://nexusleadengine.io) to solve the quality and pricing issues with traditional prospecting platforms. Most B2B lead databases charge $49-$150/mo on rigid subscriptions and expire unused credits every 30 days.

  NexusLeadEngine is built with a pay-as-you-go model (credits never expire) and focuses on technical website audits rather than scraping raw email dumps. In a single call, it checks if a target business has active tracking pixels, mobile chat widgets, calculates estimated conversion drop-offs, and drafts a technical outreach hook.

  It also exposes native Model Context Protocol (MCP) endpoints for autonomous agents (https://nexusleadengine.io/.well-known/mcp.json) and an open API (https://nexusleadengine.io/openapi.json).

  You can audit any URL live on the homepage without an account. Would love your feedback on the architecture and scan accuracy.
  ```

---

## 📩 Eje 4: Campaña Outbound por Correo (`hola@nexusleadengine.io`)

Para contactar a las agencias minadas en [`prospecting_campaign_agencies.csv`](file:///Users/artu/Desktop/Nexus/prospecting_campaign_agencies.csv):

```bash
# 1. Ver el listado de agencias
./.venv/bin/python3 dispatch_outbound_emails.py --list

# 2. Previsualizar el mensaje exacto para la agencia 1
./.venv/bin/python3 dispatch_outbound_emails.py --preview 1

# 3. Abrir en Apple Mail / cliente de correo configurado con 1 clic:
./.venv/bin/python3 dispatch_outbound_emails.py --open-mail 1
./.venv/bin/python3 dispatch_outbound_emails.py --open-mail 2
./.venv/bin/python3 dispatch_outbound_emails.py --open-mail 3
```

---

## 📈 Eje 5: Medición Diaria en Vivo
Todas las visitas, clics en WhatsApp, auditorías y conversiones se registran de forma anónima en el dashboard:
👉 **https://nexusleadengine.io/dashboard**
