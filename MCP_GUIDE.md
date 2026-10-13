# NexusLeadEngine • Guía del Servidor MCP (Model Context Protocol)

El protocolo **MCP (Model Context Protocol)** permite a cualquier cliente de Inteligencia Artificial moderna (**Claude Desktop, Cursor, Windsurf, Zed, o enjambres de agentes en LangChain y CrewAI**) conectarse de forma nativa a **NexusLeadEngine.io** como una herramienta instalada en su sistema.

---

## 🛠️ Herramientas disponibles para la IA

| Nombre de la Herramienta | Descripción |
| :--- | :--- |
| `nexus_sample_lead` | Extrae un lead de muestra auditado en vivo (`US`, `GB` o `ES`) con señales técnicas y hook pre-redactado. |
| `nexus_scan_leads` | Escanea y califica prospectos de alto ticket en tiempo real en cualquier ciudad y nicho. |
| `nexus_check_balance` | Consulta el saldo de créditos disponible en la cuenta de la API key. |
| `nexus_m2m_buy_pack` | **Agentic Commerce M2M:** Genera orden de compra cripto directa en NOWPayments para que la billetera del bot compre créditos. |

---

## 💻 Instalación en Claude Desktop

1. Abre tu archivo de configuración de Claude Desktop:
   - **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

2. Agrega la entrada de `nexusleadengine` dentro de `mcpServers`:

```json
{
  "mcpServers": {
    "nexusleadengine": {
      "command": "python3",
      "args": ["/ruta/absoluta/a/nexusleadengine/mcp_server.py"],
      "env": {
        "NEXUS_API_URL": "https://nexusleadengine.io",
        "NEXUS_API_KEY": "tu_api_key_aquí"
      }
    }
  }
}
```

3. Reinicia Claude Desktop. Verás aparecer el icono del martillo 🔨 con las herramientas de NexusLeadEngine listas para usar.

---

## 🤖 Ejemplos de Prompts para la IA

- *"Claude, usa NexusLeadEngine para buscar 5 clínicas de implantes dentales en Miami y evalúa qué errores técnicos tienen en sus páginas web."*
- *"Revisa el saldo de créditos de mi cuenta de NexusLeadEngine."*
- *"Si no tenemos créditos, inicia la compra de un pack de $15 USD con USDT en la red TRC20."*

---

## 🚀 Agentes Autónomos (Python / LangChain / CrewAI)

Puedes lanzar el servidor directamente en subprocesos o consumirlo mediante stdio:

```python
import subprocess, json

proc = subprocess.Popen(["python3", "mcp_server.py"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)

# Consultar herramientas disponibles
proc.stdin.write(json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}) + "\n")
proc.stdin.flush()
response = json.loads(proc.stdout.readline())
print(response)
```
