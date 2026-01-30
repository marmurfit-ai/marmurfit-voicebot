import os, json, re, requests
from flask import Flask, request, Response

# ================================
# MARMURFIT Voice Bot - Full MVP
# ================================

app = Flask(__name__)

# --- KB + Prompt (existente în repo) ---
KB = json.load(open("marmurfit_kb.json", encoding="utf-8"))
SYSTEM_PROMPT = open("marmurfit_system_prompt.txt", encoding="utf-8").read()

# --- ENV ---
LEADS_WEBHOOK_URL = os.getenv("LEADS_WEBHOOK_URL", "").strip()

# =========================
# UTIL & BUSINESS HELPERS
# =========================
def get_price_per_m2(material_name: str):
    mname = (material_name or "").strip().lower()
    for m in KB.get("materials", []):
        if m["name"].lower() == mname:
            return m["price_per_m2"]
    return None

def estimate_from_area(material_name: str, area_m2: float):
    try:
        area = float(area_m2)
    except:
        return None
    price = get_price_per_m2(material_name)
    if price is None:
        return None
    return round(area * price)

def push_lead_to_sheet(payload: dict):
    if not LEADS_WEBHOOK_URL:
        print("LEADS_WEBHOOK_URL missing")
        return
    try:
        r = requests.post(LEADS_WEBHOOK_URL, json=payload, timeout=10)
        r.raise_for_status()
    except Exception as e:
        print("Lead push error:", e)

def find_material_in_text(t: str):
    t = (t or "").lower()
    for m in KB.get("materials", []):
        if m["name"].lower() in t:
            return m["name"]
    return None

def parse_area_from_text(t: str):
    """
    Returnează (area_m2, latime_cm, lungime_ml)
    Reguli:
      - Dacă textul conține "cm" și "ml" => glafuri: m2 = (lat_cm/100) * lung_ml
      - Altfel, dacă apare "m2" / "metri patrati" => ia primul număr ca m2
    """
    t_low = (t or "").lower()
    nums = [n.replace(",", ".") for n in re.findall(r"[0-9]+[.,]?[0-9]*", t_low)]
    area_m2, lat_cm, lng_ml = None, None, None

    if "cm" in t_low and ("ml" in t_low or "m liniar" in t_low or "metri liniari" in t_low) and len(nums) >= 2:
        lat_cm = float(nums[0]); lng_ml = float(nums[1])
        area_m2 = (lat_cm / 100.0) * lng_ml
    elif ("m2" in t_low) or ("metri patrati" in t_low) or ("metri pătrați" in t_low) or ("metru patrat" in t_low):
        if nums:
            area_m2 = float(nums[0])

    return area_m2, lat_cm, lng_ml

# ===========
# HEALTH
# ===========
@app.route("/")
def health():
    return "OK - MARMURFIT Voice Bot MVP"

# ===========
# SELFTEST
# ===========
@app.route("/selftest", methods=["GET"])
def selftest():
    payload = {
        "sursa": "selftest-backend",
        "nume": "Test",
        "telefon": "",
        "localitate": "",
        "tip_lucrare": "glafuri",
        "material": "gri",
        "finisaj": "",
        "grosime_cm": "2",
        "suprafata_m2": 1,
        "latime_cm": "",
        "lungime_ml": "",
        "estimare_ron": 350,
        "status": "nou",
        "observatii": "trigger din /selftest"
    }
    try:
        r = requests.post(LEADS_WEBHOOK_URL, json=payload, timeout=10)
        status = r.status_code
    except Exception as e:
        status = f"ERR:{e}"
    return f"SELFTEST -> Sheets status: {status}"

# =================
# TWILIO ROUTES
# =================
from twilio.twiml.voice_response import VoiceResponse

VOICE_RO = "Polly.Carmen"  # voce RO stabilă (evită "silent")

@app.route("/voice", methods=["GET","POST"])
def voice():
    vr = VoiceResponse()
    g = vr.gather(
        input="speech",
        action="/collect",
        language="ro-RO",
        speech_timeout="auto"
    )
    g.say(
        "Bună! Ai sunat la MARMURFIT. Pentru calitate, apelul poate fi înregistrat. "
        "Îți pot face o estimare orientativă. Nu facem măsurători la domiciliu; lucrăm pe dimensiunile tale "
        "și recomandăm toleranță de aproximativ doi centimetri la capete și în față, pentru că treptele ies "
        "în exterior față de contratrepte. Spune materialul și suprafața în metri pătrați sau, pentru glafuri, "
        "lățimea în centimetri și lungimea în metri liniari.",
        language="ro-RO",
        voice=VOICE_RO
    )
    vr.redirect("/voice")  # dacă nu vorbește
    return Response(str(vr), mimetype="text/xml")

@app.route("/collect", methods=["POST"])
def collect():
    user_text = request.form.get("SpeechResult", "") or ""
    caller = request.form.get("From", "")

    material = find_material_in_text(user_text)
    area_m2, lat_cm, lng_ml = parse_area_from_text(user_text)
    est = estimate_from_area(material, area_m2) if (material and area_m2 is not None) else None

    vr = VoiceResponse()
    if est is None:
        g = vr.gather(input="speech", action="/collect", language="ro-RO", speech_timeout="auto")
        if not material:
            g.say("Ce material dorești? Avem gri, marmură albă cu dungi gri, marmură bej, gri antracit, negru galaxy, negru absolut sau steel black.",
                  language="ro-RO", voice=VOICE_RO)
        else:
            g.say("Care este suprafața în metri pătrați sau, pentru glafuri, lățimea în centimetri și lungimea în metri liniari?",
                  language="ro-RO", voice=VOICE_RO)
        return Response(str(vr), mimetype="text/xml")

    push_lead_to_sheet({
        "sursa": "apel",
        "nume": "",
        "telefon": caller,
        "localitate": "",
        "tip_lucrare": "necunoscut",
        "material": material,
        "finisaj": "",
        "grosime_cm": "",
        "suprafata_m2": area_m2,
        "latime_cm": lat_cm or "",
        "lungime_ml": lng_ml or "",
        "estimare_ron": est,
        "status": "nou",
        "observatii": "Lead automat Twilio",
    })

    vr.say(
        f"Estimarea orientativă este aproximativ {int(est)} lei, fără transport și operații speciale. "
        "Lucrăm exclusiv cu avans minim cincizeci la sută. Mulțumim!",
        language="ro-RO", voice=VOICE_RO
    )
    vr.hangup()
    return Response(str(vr), mimetype="text/xml")

# =================
# TELNYX ROUTES
# =================
def make_texml(xml_str: str):
    return Response(xml_str, mimetype="application/xml")

@app.route("/telnyx/ping", methods=["POST"])
def telnyx_ping():
    return make_texml("<Response><Say>Test Telnyx OK</Say><Hangup/></Response>")

@app.route("/telnyx/voice", methods=["POST"])
def telnyx_voice():
    base = request.url_root.rstrip("/")  # ex: https://marmurfit-voicebot.onrender.com
    xml = f"""
<Response>
  <Gather input="speech" language="ro-RO" action="{base}/telnyx/collect" method="POST" speechTimeout="auto">
    <Say>
      Buna! Ai sunat la MARMURFIT. Pentru calitate, apelul poate fi inregistrat.
      Iti pot face o estimare orientativa. Nu facem masuratori la domiciliu; lucram pe dimensiunile tale
      si recomandam toleranta de aproximativ doi centimetri la capete si in fata, pentru ca treptele ies
      in exterior fata de contratrepte. Spune materialul si suprafata in metri patrati sau, la glafuri,
      latimea in centimetri si lungimea in metri liniari.
    </Say>
  </Gather>
  <Say>Nu am auzit nimic. Reincerc.</Say>
  <Redirect method="POST">{base}/telnyx/voice</Redirect>
</Response>
""".strip()
    return make_texml(xml)

@app.route("/telnyx/collect", methods=["POST"])
def telnyx_collect():
    user_text = request.form.get("SpeechResult", "") or ""
    caller = request.form.get("From", "")

    material = find_material_in_text(user_text)
    area_m2, lat_cm, lng_ml = parse_area_from_text(user_text)
    est = estimate_from_area(material, area_m2) if (material and area_m2 is not None) else None

    if est is None:
        base = request.url_root.rstrip("/")
        xml = f"""
<Response>
  <Gather input="speech" language="ro-RO" action="{base}/telnyx/collect" method="POST" speechTimeout="auto">
    <Say>Ca sa estimez corect, spune materialul si suprafata in metri patrati sau, la glafuri, latimea in centimetri si lungimea in metri liniari.</Say>
  </Gather>
  <Redirect method="POST">{base}/telnyx/voice</Redirect>
</Response>
""".strip()
        return make_texml(xml)

    push_lead_to_sheet({
        "sursa": "apel-telnyx",
        "nume": "",
        "telefon": caller,
        "localitate": "",
        "tip_lucrare": "necunoscut",
        "material": material,
        "finisaj": "",
        "grosime_cm": "",
        "suprafata_m2": area_m2,
        "latime_cm": lat_cm or "",
        "lungime_ml": lng_ml or "",
        "estimare_ron": est,
        "status": "nou",
        "observatii": "Lead automat Telnyx",
    })

    xml = f"""
<Response>
  <Say>Estimarea orientativa este aproximativ {int(est)} lei, fara transport si operatii speciale. Lucram cu avans minim cincizeci la suta. Multumim!</Say>
  <Hangup/>
</Response>
""".strip()
    return make_texml(xml)

# ===========
# MAIN
# ===========
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
