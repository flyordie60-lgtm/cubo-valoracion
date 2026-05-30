import os
import base64
import json
import re
import httpx
import anthropic
from dotenv import load_dotenv

load_dotenv()

PROMPT_ES = """Eres un asistente experto en contabilidad colombiana. Analiza esta imagen de una factura o documento contable y extrae la siguiente información en formato JSON estricto.

Devuelve ÚNICAMENTE el JSON sin texto adicional, con esta estructura exacta:
{
  "supplier": "nombre del proveedor o empresa emisora (string o null)",
  "invoice_number": "número de factura (string o null)",
  "invoice_date": "fecha de la factura en formato DD/MM/YYYY (string o null)",
  "total_amount": valor numérico total sin puntos ni comas (number o null),
  "currency": "moneda, por defecto COP (string)",
  "items": [
    {
      "description": "descripción del ítem (string o null)",
      "quantity": cantidad numérica (number o null),
      "unit": "unidad de medida: m², m, m³, kg, lt, unidad, caja, rollo, saco, galón, etc. (string o null)",
      "unit_price": precio unitario numérico (number o null),
      "total": total del ítem numérico (number o null)
    }
  ],
  "notes": "notas adicionales relevantes (string o null)"
}

Reglas importantes:
- Todos los valores monetarios deben ser números (no strings), sin símbolos de moneda ni separadores de miles.
- Si un campo no se encuentra en la imagen, usa null.
- El array items puede estar vacío [] si no hay líneas de detalle visibles.
- Para la fecha, intenta identificarla aunque esté en diferentes formatos.
- Si la moneda es pesos colombianos, usa "COP".
"""


async def extract_invoice_data(image_url: str) -> dict:
    """Download image from URL, send to Claude vision, return extracted invoice data."""
    # Download image
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(image_url)
        response.raise_for_status()
        image_bytes = response.content
        content_type = response.headers.get("content-type", "image/jpeg")
        # Normalize content type
        if "png" in content_type:
            media_type = "image/png"
        elif "webp" in content_type:
            media_type = "image/webp"
        elif "gif" in content_type:
            media_type = "image/gif"
        else:
            media_type = "image/jpeg"

    image_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY no está configurada")

    client = anthropic.Anthropic(api_key=api_key)

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": PROMPT_ES,
                    },
                ],
            }
        ],
    )

    raw_text = message.content[0].text.strip()

    # Extract JSON from the response
    json_match = re.search(r"\{.*\}", raw_text, re.DOTALL)
    if json_match:
        json_str = json_match.group()
    else:
        json_str = raw_text

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError:
        # Return a best-effort empty structure
        data = {
            "supplier": None,
            "invoice_number": None,
            "invoice_date": None,
            "total_amount": None,
            "currency": "COP",
            "items": [],
            "notes": f"No se pudo parsear la respuesta: {raw_text[:200]}",
        }

    # Ensure required keys exist
    data.setdefault("supplier", None)
    data.setdefault("invoice_number", None)
    data.setdefault("invoice_date", None)
    data.setdefault("total_amount", None)
    data.setdefault("currency", "COP")
    data.setdefault("items", [])
    data.setdefault("notes", None)
    data["raw_text"] = raw_text

    return data
