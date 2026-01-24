
import os, json, requests
from flask import Flask, request, Response
from twilio.twiml.voice_response import VoiceResponse, Gather

# =====================================
# MARMURFIT Voice Bot - Beginner Starter
# =====================================
# What this file does:
# - receives phone calls via Twilio (/voice route)
# - says the intro + asks the client for details
# - computes a very simple rough estimate
# - pushes a draft lead to Google Sheets (via LEADS_WEBHOOK_URL)
#
# NOTE: This is a very simple MVP to get started.
# Later you can add LLM intelligence and WhatsApp sending.
# =====================================

app = Flask(__name__)

# Load Knowledge Base and System Prompt
KB = json.load(open("marmurfit_kb.json", encoding="utf-8"))
SYSTEM_PROMPT = open("marmurfit_system_prompt.txt", encoding="utf-8").read()

LEADS_WEBHOOK_URL = os.getenv("LEADS_WEBHOOK_URL", "")  # set in .env on the server

def get_price_per_m2(material_name: str):
    """Returns price per m2 for the given material (or None if not found)."""
    material_name = (material_name or "").strip().lower()
    for m in KB.get("materials", []):
        if m["name"].lower() == material_name:
            return m["price_per_m2"]
    return None

def estimate_from_area(material_name: str, area_m2: float):
    """Computes rough estimate from area and material price."""
    try:
        area = float(area_m2)
    except:
        return None
    price = get_price_per_m2(material_name)
    if price is None:
        return None
    return round(area * price)

def push_lead_to_sheet(payload: dict):
    """Sends the lead to Google Sheets (Apps Script webhook)."""
    if not LEADS_WEBHOOK_URL:
        print("LEADS_WEBHOOK_URL missing - set it in .env")
        return
    try:
        r = requests.post(LEADS_WEBHOOK_URL, json=payload, timeout=10)
        r.raise_for_status()
    except Exception as e:
        print("Lead push error:", e)

@app.route("/voice", methods=["POST"])
def voice():
    """Entry point for incoming calls."""
    vr = VoiceResponse()
    g = Gather(input="speech", action="/collect", language="ro-RO", speech_timeout="auto")
    g.say("Buna! Ai sunat la MARMURFIT. Pentru calitate, apelul poate fi inregistrat. "
          "Iti pot face o estimare orientativa. Nu facem masuratori la domiciliu, "
          "lucram pe dimensiunile tale si recomandam toleranta de aproximativ doi centimetri "
          "la capete si in fata, pentru ca treptele ies in exterior fata de contratrepte. "
          "Spune-mi, te rog, materialul si suprafata in metri patrati, "
          "sau pentru glafuri latimea in centimetri si lungimea in metri liniari.")
    vr.append(g)
    vr.redirect("/voice")  # if no speech
    return Response(str(vr), mimetype="text/xml")

@app.route("/collect", methods=["POST"])
def collect():
    """Collect user answer and try to compute a rough estimate."""
    user_text = request.form.get("SpeechResult", "") or ""

    text_low = user_text.lower()

    # 1) find material in the KB by name
    material = None
    for m in KB.get("materials", []):
        if m["name"].lower() in text_low:
            material = m["name"]
            break

    # 2) extract numbers from text
    import re
    nums = re.findall(r"[0-9]+[.,]?[0-9]*", text_low)
    nums = [n.replace(",", ".") for n in nums]

    area_m2 = None
    latime_cm = None
    lungime_ml = None

    # If both "cm" and "ml" appear and we have at least 2 numbers, treat as width/length for sills
    if "cm" in text_low and "ml" in text_low and len(nums) >= 2:
        latime_cm = float(nums[0])
        lungime_ml = float(nums[1])
        area_m2 = (latime_cm / 100.0) * lungime_ml
    else:
        # If "m2" or "metri patrati" appears and we have a number, treat as total area
        if "m2" in text_low or "metri patrati" in text_low or "metri pătrați" in user_text:
            if nums:
                area_m2 = float(nums[0])

    if not material or area_m2 is None:
        vr = VoiceResponse()
        g = vr.gather(input="speech", action="/collect", language="ro-RO", speech_timeout="auto")
        if not material:
            g.say("Ce material doresti? Avem gri, marmura alba cu dungi gri, marmura bej, gri antracit, "
                  "negru galaxy, negru absolut sau steel black.")
        else:
            g.say("Care este suprafata in metri patrati sau, pentru glafuri, latimea in centimetri si lungimea in metri liniari?")
        return Response(str(vr), mimetype="text/xml")

    est = estimate_from_area(material, area_m2)
    vr = VoiceResponse()
    if est is None:
        g = vr.gather(input="speech", action="/collect", language="ro-RO", speech_timeout="auto")
        g.say("Ca sa estimez corect, am nevoie de materialul exact si suprafata totala in metri patrati "
              "sau latimea in centimetri plus lungimea in metri liniari. Imi spui, te rog?")
        return Response(str(vr), mimetype="text/xml")

    g = vr.gather(input="speech", action="/final", language="ro-RO", speech_timeout="auto")
    g.say(f"Estimarea orientativa este aproximativ {int(est)} lei, fara transport si operatii speciale. "
          "Lucram exclusiv cu avans minim 50 la suta. "
          "Iti trimit rezumatul pe WhatsApp? Spune da sau nu.")
    push_lead_to_sheet({
        "sursa": "apel",
        "tip_lucrare": "necunoscut",
        "material": material,
        "suprafata_m2": area_m2,
        "estimare_ron": est,
        "observatii": "Lead draft automat din apel (MVP)."
    })
    return Response(str(vr), mimetype="text/xml")

@app.route("/final", methods=["POST"])
def final():
    vr = VoiceResponse()
    vr.say("Multumesc! Trimit rezumatul. O zi excelenta din partea MARMURFIT!")
    vr.hangup()
    return Response(str(vr), mimetype="text/xml")

@app.route("/")
def health():
    return "OK - MARMURFIT Voice Bot MVP"
if __name__ == "__main__":
    import os
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
