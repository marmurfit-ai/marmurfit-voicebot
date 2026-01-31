import os
import re
import requests
from flask import Flask, request, Response, make_response
from twilio.twiml.voice_response import VoiceResponse, Gather

app = Flask(__name__)

LEADS_WEBHOOK_URL = os.getenv("LEADS_WEBHOOK_URL", "")
VOICE_RO = "Polly.Carmen"

MATERIALS = {
    "gri": 350, "marmura alba": 350, "dungi gri": 350, "bej": 350,
    "gri antracit": 350, "steel black": 650, "negru galaxy": 750, "negru absolut": 750,
}

def push_lead(payload: dict):
    if not LEADS_WEBHOOK_URL: return
    try: requests.post(LEADS_WEBHOOK_URL, json=payload, timeout=10)
    except Exception as e: print("LEADS push error:", e)

def parse_area_and_material(text: str):
    t = (text or "").lower()
    material = next((m for m in MATERIALS if m in t), None)
    nums = [n.replace(",", ".") for n in re.findall(r"[0-9]+[.,]?[0-9]*", t)]
    area_m2 = None
    if "cm" in t and "ml" in t and len(nums) >= 2:
        lat_cm = float(nums[0]); lng_ml = float(nums[1]); area_m2 = (lat_cm/100.0)*lng_ml
    elif ("m2" in t) or ("metri patrati" in t) or ("metri pătrați" in t):
        if nums: area_m2 = float(nums[0])
    est = int(round(area_m2 * MATERIALS[material])) if (material and area_m2 is not None) else None
    return material, area_m2, est

def make_texml(xml_str: str):
    r = make_response(xml_str); r.headers["Content-Type"] = "application/xml"; return r

@app.route("/")
def health(): return "OK - MARMURFIT Voice Bot MVP"

@app.route("/selftest", methods=["GET"])
def selftest():
    payload = {"sursa":"selftest-backend","nume":"Test","telefon":"","localitate":"",
               "tip_lucrare":"glafuri","material":"gri","finisaj":"","grosime_cm":"2",
               "suprafata_m2":1,"latime_cm":"","lungime_ml":"","estimare_ron":350,
               "status":"nou","observatii":"trigger din /selftest"}
    try: status = requests.post(LEADS_WEBHOOK_URL, json=payload, timeout=10).status_code
    except Exception as e: status = f"ERR:{e}"
    return f"SELFTEST -> Sheets status: {status}"

# ===== TWILIO (opțional) =====
@app.route("/voice", methods=["GET","POST"])
def voice():
    vr = VoiceResponse()
    g = Gather(input="speech", action="/collect", language="ro-RO", speech_timeout="auto")
    g.say("Bună! Ai sunat la MARMURFIT. Pentru calitate, apelul poate fi înregistrat. "
          "Nu facem măsurători la domiciliu; lucrăm pe dimensiunile tale și recomandăm toleranță de ~ doi centimetri "
          "la capete și în față, pentru că treptele ies în exterior față de contratrepte. "
          "Spune materialul și suprafața în metri pătrați, sau pentru glafuri, lățimea în centimetri și lungimea în metri liniari.",
          language="ro-RO", voice=VOICE_RO)
    vr.append(g); vr.redirect("/voice")
    return Response(str(vr), mimetype="text/xml")

@app.route("/collect", methods=["POST"])
def collect():
    user_text = (request.form.get("SpeechResult") or "").lower()
    material, area_m2, est = parse_area_and_material(user_text)
    push_lead({"sursa":"apel","material":material or "","suprafata_m2":area_m2 or "","estimare_ron":est or "","observatii":"Lead draft automat (Twilio)."})
    vr = VoiceResponse()
    if est is None:
        g = vr.gather(input="speech", action="/collect", language="ro-RO", speech_timeout="auto")
        g.say("Ca să estimez, spune materialul și suprafața în metri pătrați sau, pentru glafuri, lățimea în centimetri și lungimea în metri liniari.",
              language="ro-RO", voice=VOICE_RO)
        vr.append(g); vr.redirect("/voice")
    else:
        vr.say(f"Estimarea orientativă este aproximativ {int(est)} lei, fără transport și operații speciale. "
               "Lucrăm exclusiv cu avans minim cincizeci la sută. Mulțumim!", language="ro-RO", voice=VOICE_RO)
        vr.hangup()
    return Response(str(vr), mimetype="text/xml")

# ===== TELNYX (PROD) =====
@app.route("/telnyx/ping", methods=["GET","POST"])
def telnyx_ping():
    return make_texml(f'<Response><Say voice="{VOICE_RO}">Test Telnyx OK</Say><Hangup/></Response>')

@app.route("/telnyx/voice", methods=["GET","POST"])
def telnyx_voice():
    base = request.url_root.rstrip("/")
    return make_texml(f"""
<Response>
  <Gather input="speech" language="ro-RO" action="{base}/telnyx/collect" method="POST" speechTimeout="auto">
    <Say voice="{VOICE_RO}">
      Buna! Ai sunat la MARMURFIT. Pentru calitate, apelul poate fi inregistrat.
      Nu facem masuratori la domiciliu; lucram pe dimensiunile tale si recomandam ~ doi centimetri toleranta
      la capete si in fata, pentru ca treptele ies in exterior fata de contratrepte.
      Spune materialul si suprafata in metri patrati, sau pentru glafuri, latimea in centimetri si lungimea in metri liniari.
    </Say>
  </Gather>
  <Say voice="{VOICE_RO}">Nu am auzit clar. Reincerc.</Say>
  <Redirect method="POST">{base}/telnyx/voice</Redirect>
</Response>
""".strip())

@app.route("/telnyx/collect", methods=["GET","POST"])
def telnyx_collect():
    user_text = (
        request.form.get("SpeechResult") or request.form.get("speechResult")
        or request.form.get("Speech") or request.form.get("speech") or ""
    ).lower()
    material, area_m2, est = parse_area_and_material(user_text)
    push_lead({"sursa":"apel-telnyx","material":material or "","suprafata_m2":area_m2 or "","estimare_ron":est or "","observatii":"Lead draft automat Telnyx (MVP)."})
    base = request.url_root.rstrip("/")
    if est is None:
        return make_texml(f"""
<Response>
  <Gather input="speech" language="ro-RO" action="{base}/telnyx/collect" method="POST" speechTimeout="auto">
    <Say voice="{VOICE_RO}">
      Ca sa estimez, spune materialul si suprafata in metri patrati
      sau, pentru glafuri, latimea in centimetri si lungimea in metri liniari.
    </Say>
  </Gather>
  <Say voice="{VOICE_RO}">Nu am auzit clar. Reincerc.</Say>
  <Redirect method="POST">{base}/telnyx/voice</Redirect>
</Response>
""".strip())
    return make_texml(f"""
<Response>
  <Say voice="{VOICE_RO}">
    Estimarea orientativa este aproximativ {est} lei, fara transport si operatii speciale.
    Lucram exclusiv cu avans minim 50 la suta. Multumim!
  </Say>
  <Hangup/>
</Response>
""".strip())

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
