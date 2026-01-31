from flask import request, make_response

def make_texml(xml_str: str):
    r = make_response(xml_str)
    r.headers["Content-Type"] = "application/xml"
    return r

@app.route("/telnyx/voice", methods=["GET","POST"])
def telnyx_voice():
    base = request.url_root.rstrip("/")
    xml = f"""
<Response>
  <Gather input="speech" language="ro-RO" action="{base}/telnyx/collect" method="POST" speechTimeout="auto">
    <Say voice="Polly.Carmen">
      Buna! Ai sunat la MARMURFIT. Pentru calitate, apelul poate fi inregistrat.
      Nu facem masuratori la domiciliu; lucram pe dimensiunile tale si recomandam aproximativ doi centimetri toleranta
      la capete si in fata, pentru ca treptele ies in exterior fata de contratrepte.
      Spune materialul si suprafata in metri patrati, sau pentru glafuri, latimea in centimetri si lungimea in metri liniari.
    </Say>
  </Gather>
  <Say voice="Polly.Carmen">Nu am auzit clar. Reincerc.</Say>
  <Redirect method="POST">{base}/telnyx/voice</Redirect>
</Response>
""".strip()
    return make_texml(xml)

@app.route("/telnyx/collect", methods=["GET","POST"])
def telnyx_collect():
    user_text = (
        request.form.get("SpeechResult")
        or request.form.get("speechResult")
        or request.form.get("Speech")
        or request.form.get("speech")
        or ""
    ).lower()

    material, area_m2, est = parse_area_and_material(user_text)

    push_lead({
        "sursa": "apel-telnyx",
        "material": material or "",
        "suprafata_m2": area_m2 or "",
        "estimare_ron": est or "",
        "observatii": "Lead draft automat Telnyx (MVP)."
    })

    base = request.url_root.rstrip("/")
    if est is None:
        return make_texml(f"""
<Response>
  <Gather input="speech" language="ro-RO" action="{base}/telnyx/collect" method="POST" speechTimeout="auto">
    <Say voice="Polly.Carmen">
      Ca sa estimez, spune materialul si suprafata in metri patrati
      sau, pentru glafuri, latimea in centimetri si lungimea in metri liniari.
    </Say>
  </Gather>
  <Say voice="Polly.Carmen">Nu am auzit clar. Reincerc.</Say>
  <Redirect method="POST">{base}/telnyx/voice</Redirect>
</Response>
""".strip())

    return make_texml(f"""
<Response>
  <Say voice="Polly.Carmen">
    Estimarea orientativa este aproximativ {est} lei, fara transport si operatii speciale.
    Lucram exclusiv cu avans minim 50 la suta. Multumim!
  </Say>
  <Hangup/>
</Response>
""".strip())
