# MARMURFIT Voice Bot – Starter (A–Z pentru Începători)

Acest pachet te pornește cu botul care răspunde la telefon.

## Conținut
- `app.py` – aplicația (Flask) care răspunde la apel și calculează o estimare simplă
- `requirements.txt` – dependențe
- `.env.example` – variabile de mediu (copie în `.env` și completezi)
- `marmurfit_kb.json` – materiale, prețuri, politici (deja generat)
- `marmurfit_system_prompt.txt` – instrucțiuni bot
- `assets/marmurfit_whatsapp_templates_ro_en.txt` – șabloane WhatsApp
- `docs/Google_Apps_Script_Lead_Webhook.txt` – cod pentru Google Sheets webhook
- `docs/Twilio_Studio_Flow_Skeleton.json` – schelet IVR (opțional)

## Pasul 1 – Google Sheets (CRM light)
1. Importă Excelul „Leads” în Google Sheets (nume: **MARMURFIT Leads**).
2. `Extensions > Apps Script` → lipești codul din `docs/Google_Apps_Script_Lead_Webhook.txt`.
3. Înlocuiești `SPREADSHEET_ID` cu ID-ul din URL.
4. `Deploy > New deployment > Web app > Anyone` → copiază **URL** (LEADS_WEBHOOK_URL).

## Pasul 2 – Twilio (număr)
1. Cont Twilio → `Buy a Number` (România, Voice).
2. Setezi numărul: `A CALL COMES IN = Webhook` către `https://{SERVER}/voice` (după ce urci aplicația).

## Pasul 3 – Urcă aplicația (Render)
1. Creezi repo GitHub cu aceste fișiere.
2. Render.com → New Web Service → conectezi repo.
3. Python 3.11. Start command: `python app.py`.
4. Setezi `LEADS_WEBHOOK_URL` în Environment Variables cu cel din Pasul 1.
5. Render îți dă un URL public (ex. `https://marmurfit-voice.onrender.com/`).

## Pasul 4 – Leagă Twilio de server
- La numărul Twilio pui Webhook `.../voice` cu URL-ul Render.
- Suni numărul, răspunde botul, dai dimensiuni, verifici că apare un rând în Sheet.

## (Opțional) WhatsApp
- Activezi WhatsApp Business în Twilio.
- Încarci șabloanele din `assets/...txt`.
- Adăugăm trimitere automată de mesaje în `app.py` (pas ulterior).

## Test rapid
- Intro cu GDPR.
- Botul cere dimensiuni, amintește toleranța ~2 cm.
- „gri, 1 m2” → ~350 lei.
- „glaf 20 cm pe 5 ml” → 1 m2 → ~350 lei (sau 650/750 la materialele premium).
- Lead draft apare în Google Sheets.

Generat: 2025-10-26T10:11:55.188416Z
