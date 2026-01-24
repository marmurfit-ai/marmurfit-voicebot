import os, requests
from flask import Flask, request, Response

app = Flask(__name__)

LEADS_WEBHOOK_URL = os.getenv("LEADS_WEBHOOK_URL", "")

@app.route("/")
def health():
    return "OK - MARMURFIT Voice Bot MVP"

# Twilio voice webhook
@app.route("/voice", methods=["POST"])
def voice():
    from twilio.twiml.voice_response import VoiceResponse, Gather
    vr = VoiceResponse()
    g = Gather(input="speech", action="/collect", language="ro-RO", speech_timeout="auto")
    g.say("Buna! Ai sunat la MARMURFIT. Pentru calitate, apelul poate fi inregistrat. "
          "Nu facem masuratori la domiciliu; lucram pe dimensiunile tale si recomandam "
          "toleranta de aproximativ doi centimetri la capete si in fata, pentru ca treptele "
          "ies in exterior fata de contratrepte. Spune materialul si suprafata in metri patrati "
          "sau, pentru glafuri, latimea in centimetri si lungimea in metri liniari.")
    vr.append(g)
    vr.redirect("/voice")
    return Response(str(vr), mimetype="text/xml")

@app.route("/collect", methods=["POST"])
def collect():
    user_text = (request.form.get("SpeechResult") or "").lower()

    # detectie ultra-simpla
    materials = {
        "gri": 350, "marmura alba": 350, "dungi gri": 350, "bej": 350,
        "gri antracit": 350, "steel black": 650, "negru galaxy": 750, "negru absolut": 750
    }
    material = next((m for m in materials if m in user_text), None)

    import re
    nums = [n.replace(",", ".") for n in re.findall(r"[0-9]+[.,]?[0-9]*", user_text)]
    area_m2 = None
    if "cm" in user_text and "ml" in user_text and len(nums) >= 2:
        lat_cm = float(nums[0]); lng_ml = float(nums[1])
        area_m2 = (lat_cm/100.0) * lng_ml
    elif ("m2" in user_text) or ("metri patrati" in user_text) or ("metri pătrați" in user_text):
        if nums: area_m2 = float(nums[0])

    est = None
    if material and area_m2 is not None:
        est = round(area_m2 * materials[material])
        # push lead simplu
        try:
            if LEADS_WEBHOOK_URL:
                requests.post(LEADS_WEBHOOK_URL, json={
                    "sursa":"apel",
                    "material": material,
                    "suprafata_m2": area_m2,
                    "estimare_ron": est,
                    "observatii":"Lead draft automat (MVP)."
                }, timeout=10)
        except Exception as e:
            print("Lead push error:", e)

    from twilio.twiml.voice_response import VoiceResponse
    vr = VoiceResponse()
    if est is None:
        g = vr.gather(input="speech", action="/collect", language="ro-RO", speech_timeout="auto")
        g.say("Ca sa estimez corect, spune materialul si suprafata in metri patrati "
              "sau, la glafuri, latimea in centimetri si lungimea in metri liniari.")
    else:
        vr.say(f"Estimarea orientativa este aproximativ {int(est)} lei, fara transport si operatii speciale. "
               "Lucram exclusiv cu avans minim 50 la suta. Multumim!")
        vr.hangup()
    return Response(str(vr), mimetype="text/xml")

# rulare locala (fallback; cu gunicorn nu e folosit)
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
