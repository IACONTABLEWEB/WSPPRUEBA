# -*- coding: utf-8 -*-
"""
Servidor del bot de WhatsApp (webhook Cloud API de Meta).
Config por variables de entorno en Render:
  WHATSAPP_TOKEN, PHONE_NUMBER_ID, VERIFY_TOKEN
"""

import os
import unicodedata
import requests
from flask import Flask, request

app = Flask(__name__)

WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN", "")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID", "")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "siro2026")
GRAPH_URL = "https://graph.facebook.com/v21.0"


# ====== DATOS DEL NEGOCIO (lo unico que cambias por cliente) ======
NEGOCIO = {
    "nombre": "Peluqueria Estilo",
    "saludo": "Hola! Soy el asistente de Peluqueria Estilo. En que te puedo ayudar? Puedo darte horarios, precios, ubicacion o tomarte un turno.",
    "horarios": "Atendemos de Lunes a Sabado de 9 a 20 hs. Los domingos cerramos.",
    "direccion": "Estamos en Av. Nazca 2500, Villa del Parque, CABA.",
    "precios": [
        ("Corte de pelo", "$8.000"),
        ("Corte + barba", "$11.000"),
        ("Color / tintura", "desde $18.000"),
        ("Brushing", "$7.000"),
    ],
    "turnos": "Genial! Para reservarte un turno decime tu nombre y que dia y horario preferis. Tambien podes llamarnos al 11-5555-5555.",
    "contacto": "Podes escribirnos por aca o venir directamente al local.",
    "faq": [
        (["estacionamiento", "cochera", "estacionar"], "Si, hay estacionamiento en la cuadra y una cochera a 50 metros."),
        (["tarjeta", "debito", "credito", "pago", "efectivo", "mercado pago"], "Aceptamos efectivo, debito, credito y Mercado Pago."),
    ],
    "fallback": "Buena pregunta. Esa consulta se la paso al equipo y en un ratito te responden. Mientras tanto, queres horarios, precios o un turno?",
}
# ==================================================================


def normalizar(t):
    t = t.lower()
    t = "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn")
    for ch in "?!.,":
        t = t.replace(ch, " ")
    return t


def contiene(txt, palabras):
    return any(p in txt for p in palabras)


def responder(mensaje):
    t = normalizar(mensaje)
    for palabras, resp in NEGOCIO["faq"]:
        if contiene(t, palabras):
            return resp
    if contiene(t, ["hola", "buenas", "buen dia", "buenas tardes", "buenas noches", "que tal"]):
        return NEGOCIO["saludo"]
    if contiene(t, ["hora", "horario", "abren", "abierto", "cierran", "cierra", "atienden", "abre", "cerrado", "dias"]):
        return NEGOCIO["horarios"]
    if contiene(t, ["precio", "cuanto", "sale", "cuesta", "cuestan", "valor", "tarifa", "cobran"]):
        lista = "\n".join("- " + s + ": " + p for s, p in NEGOCIO["precios"])
        return "Estos son nuestros precios:\n" + lista + "\n\nQueres que te tome un turno?"
    if contiene(t, ["donde", "direccion", "ubicacion", "ubicados", "llegar", "local", "quedan", "estan", "mapa", "zona"]):
        return NEGOCIO["direccion"]
    if contiene(t, ["turno", "reserva", "reservar", "cita", "agendar", "disponibilidad"]):
        return NEGOCIO["turnos"]
    if contiene(t, ["servicio", "servicios", "hacen", "ofrecen", "trabajos"]):
        lista = "\n".join("- " + s for s, _ in NEGOCIO["precios"])
        return "Ofrecemos:\n" + lista + "\n\nSobre cual queres el precio?"
    if contiene(t, ["telefono", "whatsapp", "contacto", "llamar", "numero", "mail", "email"]):
        return NEGOCIO["contacto"]
    if contiene(t, ["gracias", "genial", "perfecto", "dale", "ok", "buenisimo"]):
        return "De nada! Si necesitas algo mas, aca estoy las 24 horas."
    return NEGOCIO["fallback"]


def normalizar_destino(numero):
    # Argentina: WhatsApp entrega 549XXXXXXXXXX pero la API responde sin el 9.
    numero = numero.lstrip("+")
    if numero.startswith("549"):
        numero = "54" + numero[3:]
    return numero


def enviar_whatsapp(destino, texto):
    destino = normalizar_destino(destino)
    url = GRAPH_URL + "/" + PHONE_NUMBER_ID + "/messages"
    headers = {"Authorization": "Bearer " + WHATSAPP_TOKEN, "Content-Type": "application/json"}
    data = {"messaging_product": "whatsapp", "to": destino, "type": "text", "text": {"body": texto}}
    try:
        r = requests.post(url, headers=headers, json=data, timeout=15)
        print("Envio:", r.status_code, r.text[:200])
    except Exception as e:
        print("Error al enviar:", e)


@app.route("/webhook", methods=["GET"])
def verificar():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    return "Token invalido", 403


@app.route("/webhook", methods=["POST"])
def recibir():
    data = request.get_json(silent=True) or {}
    try:
        for entry in data.get("entry", []):
            for cambio in entry.get("changes", []):
                valor = cambio.get("value", {})
                for msg in valor.get("messages", []):
                    if msg.get("type") != "text":
                        continue
                    remitente = msg["from"]
                    texto = msg["text"]["body"]
                    print("Mensaje de", remitente, ":", texto)
                    enviar_whatsapp(remitente, responder(texto))
    except Exception as e:
        print("Error procesando:", e)
    return "OK", 200


@app.route("/", methods=["GET"])
def home():
    return "Bot de WhatsApp activo OK", 200


if __name__ == "__main__":
    puerto = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=puerto)
