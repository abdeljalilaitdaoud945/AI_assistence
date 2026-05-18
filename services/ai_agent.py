import os
import json
import asyncio
from dotenv import load_dotenv
from groq import Groq
from fastmcp import Client
from fastmcp.client.transports import PythonStdioTransport

load_dotenv()

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))


async def _discover_and_ask(message: str, history: list) -> str:
    mcp_client = Client(PythonStdioTransport("mcp_server.py"))

    async with mcp_client:
        mcp_tools = await mcp_client.session.list_tools()

        groq_tools = []

        for tool in mcp_tools.tools:
            schema = tool.inputSchema.copy() if tool.inputSchema else {
                "type": "object",
                "properties": {},
                "required": []
            }

            schema.pop("$schema", None)
            schema.pop("additionalProperties", None)
            schema.pop("title", None)

            if "type" not in schema:
                schema["type"] = "object"

            if "properties" not in schema:
                schema["properties"] = {}

            if "required" not in schema:
                schema["required"] = []

            groq_tools.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description or f"Outil MCP : {tool.name}",
                    "parameters": schema,
                }
            })

        from datetime import date
        today = date.today().isoformat()

        messages = [
            {
                "role": "system",
                "content": (
                    "Tu es un assistant de gestion pour un directeur d'entreprise marocain. "
                    "Tu gères ses réunions, mails, actions et PV. "
                    "Réponds toujours en français. "
                    f"Aujourd'hui on est le {today}. "
                    "IMPORTANT: Pour supprimer un événement, tu dois toujours obtenir son ID réel avant suppression. "
                    "Si l'utilisateur donne une date précise, par exemple '1 mai', 'demain', 'lundi', tu dois appeler mcp_get_events avec la date exacte au format YYYY-MM-DD. "
                    "Ne pas utiliser mcp_list_upcoming pour une date passée ou une date précise. "
                    "mcp_list_upcoming sert uniquement quand l'utilisateur parle des prochains événements sans date précise. "
                    "Si aujourd'hui est après la date mentionnée, considère quand même la date comme valide dans l'année courante. "
                    "Exemple: si aujourd'hui est 2026-05-07 et l'utilisateur dit '1 mai', tu dois chercher 2026-05-01. "
                    "Ensuite seulement, appelle mcp_delete_event avec l'ID réel trouvé. "
                    "Ne jamais inventer un ID. "
                    "Ne jamais imbriquer les appels d'outils."
                ),
            },
            *history,
            {"role": "user", "content": message},
        ]

        for _ in range(10):
            response = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                tools=groq_tools,
                tool_choice="auto",
            )

            msg = response.choices[0].message

            if not msg.tool_calls:
                return msg.content or ""

            messages.append(msg)

            for tool_call in msg.tool_calls:
                func_name = tool_call.function.name

                try:
                    func_args = json.loads(tool_call.function.arguments or "{}")
                except json.JSONDecodeError:
                    func_args = {}

                result = await mcp_client.session.call_tool(func_name, func_args)
                result_text = result.content[0].text if result.content else "OK"

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result_text,
                })

        return "Erreur : trop d'appels d'outils."


_history = []


def ask_agent(message: str) -> str:
    global _history

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        result = loop.run_until_complete(_discover_and_ask(message, _history))

        loop.close()

        _history.append({"role": "user", "content": message})
        _history.append({"role": "assistant", "content": result})

        return result

    except Exception as e:
        return f"Erreur : {e}"