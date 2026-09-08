#!/usr/bin/env python3
"""Emit frontend/lib/completeLocales.ts with full overlays for every locale."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "frontend" / "lib" / "completeLocales.ts"

# Student-facing + chrome keys. Generator fills every EN key for each locale.
# Canonical product name stays TermPilot.

def dump_ts(overlays: dict[str, dict[str, str]]) -> str:
    parts = [
        "/** Full UI overlays. Canonical facts (dates, module codes) stay in source form. */",
        "export const COMPLETE: Record<string, Record<string, string>> = {",
    ]
    for code, table in overlays.items():
        parts.append(f"  {json.dumps(code)}: {{")
        for key, value in table.items():
            parts.append(f"    {json.dumps(key)}: {json.dumps(value, ensure_ascii=False)},")
        parts.append("  },")
    parts.append("};")
    parts.append("")
    return "\n".join(parts)


# fmt: off
O: dict[str, dict[str, str]] = {}

O["es"] = {
  "nav.chat": "Chat", "chat.hello": "¿Qué necesita tu atención hoy?",
  "chat.hint": "TermPilot reúne tus plazos, clases, mensajes y compromisos de la vida estudiantil, detecta conflictos y te ayuda a decidir qué hacer después. Solo usa fuentes que tú apruebas.",
  "chat.safety": "TermPilot apoya tu planificación: nunca hace el trabajo evaluado por ti.",
  "grokbot.name": "Asistente TermPilot",
  "grokbot.tagline": "Dale a TermPilot una tarea real: revisar plazos, planear la semana, encontrar apoyo o señalar cambios importantes.",
  "chat.reviewWeek": "Revisar mi semana", "chat.action.deadlines": "Revisar mis plazos",
  "chat.action.plan": "Planear mi semana", "chat.action.support": "Encontrar apoyo estudiantil",
  "chat.action.opportunities": "Ver oportunidades", "chat.powered": "Con tecnología de Grok",
  "nav.tower": "Torre de control", "nav.news": "Noticias y apoyo", "nav.mailbox": "Buzón",
  "nav.workspace": "Espacio de trabajo", "nav.calendar": "Calendario", "nav.obligations": "Obligaciones",
  "nav.timeline": "Cronograma", "nav.conflicts": "Conflictos", "nav.connectors": "Conectores",
  "nav.workflows": "Flujos", "nav.agents": "Operaciones de agentes", "nav.approvals": "Aprobaciones",
  "nav.evidence": "Evidencia", "nav.impact": "Impacto", "nav.settings": "Ajustes",
  "nav.student.tower": "Mi semana", "nav.student.news": "Buscar noticias y apoyo",
  "nav.student.mailbox": "Mensajes", "nav.student.workspace": "Mi espacio",
  "nav.student.calendar": "Calendario", "nav.student.obligations": "Plazos y tareas",
  "nav.student.timeline": "Horario", "nav.student.conflicts": "Necesita tu decisión",
  "nav.student.connectors": "Servicios conectados", "nav.student.workflows": "Automatizaciones",
  "nav.student.approvals": "Aprobaciones pendientes", "nav.student.evidence": "Por qué TermPilot dice esto",
  "nav.student.impact": "Mi progreso", "nav.student.settings": "Preferencias",
  "mode.student": "Estudiante", "mode.proof": "Prueba", "mode.label": "Modo de interfaz",
  "hdr.powered": "Con tecnología de Grok", "hdr.grokSimulated": "Conexión Grok simulada",
  "hdr.tools": "Herramientas", "close": "Cerrar", "tower.horizon": "Horizonte",
  "tower.verified": "Comprobado", "tower.conflicts": "Conflictos", "tower.approvals": "Aprobaciones",
  "tower.highRisk": "Alto riesgo", "tower.plan": "Plan", "tower.feasible": "En curso",
  "tower.blocked": "Falta un plan", "tower.attention": "Necesita una decisión",
  "tower.openConflicts": "Abrir conflictos", "tower.emptyAttention": "Nada requiere una decisión ahora.",
  "tower.timeline": "Tus próximos 14 días", "tower.emptyTimeline": "Conecta o importa una fuente para crear tu primer plan.",
  "tower.widgets": "Widgets para estudiantes internacionales", "widgets.international": "Widgets para estudiantes internacionales",
  "hdr.pause": "Pausar automatizaciones", "hdr.resume": "Automatizaciones en pausa",
  "hdr.hideNav": "Ocultar menú", "hdr.showNav": "Mostrar menú",
  "hdr.hideInspector": "Ocultar inspector", "hdr.showInspector": "Mostrar inspector", "hdr.live": "en vivo",
  "cmd.reconcile": "Reconciliar", "cmd.running": "En curso", "cmd.cancel": "Cancelar", "cmd.label": "Consola de comandos",
  "vb.title": "VoiceBridge", "vb.ask": "Preguntar", "vb.talk": "Mantén para hablar", "vb.stop": "Parar",
  "vb.mute": "Silenciar", "vb.unmute": "Activar sonido", "vb.captionsOn": "Subtítulos sí", "vb.captionsOff": "Subtítulos no",
  "vb.replay": "Repetir", "vb.delete": "Borrar transcripciones", "vb.speed": "Velocidad",
  "vb.placeholder": "Pregunta a TermPilot…", "vb.empty": "Pregunta en tu idioma, escrito o hablado. Fechas y códigos de módulo no cambian.",
  "vb.lang": "Idioma", "theme.dark": "Oscuro", "theme.light": "Claro", "theme.system": "Sistema",
  "clock.title": "Reloj mundial", "fx.title": "Tasas / divisa", "fx.amount": "Importe", "fx.from": "De", "fx.to": "A",
  "weather.title": "Pronóstico 7 días", "weather.source": "Open-Meteo",
  "settings.language": "Idioma", "settings.region": "País o región", "settings.timezone": "Zona horaria",
  "settings.formality": "Estilo de comunicación", "settings.voice": "Voz",
  "settings.formality.conversational": "Conversacional", "settings.formality.neutral": "Neutral", "settings.formality.formal": "Formal",
  "settings.regionHint": "La región no se infiere del idioma. Quien habla español puede vivir en el Reino Unido.",
  "settings.maturity": "Soporte de idioma", "settings.theme": "Tema", "settings.reset": "Restablecer demo",
  "settings.outage": "Simular caída del LMS en la próxima reconciliación",
  "settings.disclaimer": "La interfaz y las conversaciones están localizadas para todos los idiomas de Grok Voice. Fechas y códigos de módulo no se traducen.",
  "conn.connect": "Conectar", "conn.disconnect": "Desconectar", "conn.connectAll": "Conectar todo",
  "common.loading": "Cargando", "news.title": "Noticias de la vida estudiantil", "news.refresh": "Actualizar",
  "news.role": "TermPilot reúne información de fuentes universitarias, gubernamentales y comunitarias aprobadas. Comprueba la etiqueta de la fuente antes de actuar. TermPilot no representa a tu universidad, sindicato de estudiantes ni servicios de apoyo.",
  "news.crisis": "TermPilot no es un servicio de crisis.", "news.communitySource": "Fuente comunitaria — no oficial",
  "news.asap": "Pronto vence", "news.uniOn": "Buzón universitario vinculado", "news.uniOff": "Buzón universitario no vinculado",
  "news.empty": "Nada en este filtro. El RSS público se actualiza al recargar.", "news.reminders": "Recordatorios",
  "news.noReminders": "No hay recordatorios en los próximos 14 días.", "news.filter.all": "Todo",
  "news.filter.university": "Universidad", "news.filter.government": "Gobierno", "news.filter.school": "Sector educativo",
  "news.filter.international": "Internacional", "news.filter.community": "Comunidad", "news.filter.career": "Carrera",
  "news.filter.reddit": "Reddit", "news.dir.union": "Sindicato de estudiantes", "news.dir.career": "Empleo",
  "news.dir.wellbeing": "Bienestar", "news.dir.support": "Apoyo estudiantil", "news.dir.international": "Estudiantes internacionales",
  "news.dir.community": "Comunidad", "acct.settings": "Ajustes", "acct.help": "Ayuda",
  "acct.customize": "Personalizar panel", "acct.customizeHint": "Añade o quita reloj mundial, divisa, idioma y otros widgets.",
  "acct.upgrade": "Mejorar plan", "acct.upgradeHint": "Esta es la demo del concurso. No hay plan de pago ni facturación.",
  "acct.signout": "Cerrar sesión", "acct.signin": "Entrar como FAVL", "acct.signedOut": "Sesión de demo cerrada.",
  "acct.feedback": "Comentarios", "acct.faq": "Preguntas frecuentes", "acct.release": "Notas de la versión",
  "acct.community": "Comunidad", "acct.links": "Enlaces compartidos", "acct.add": "Añadir", "acct.remove": "Quitar",
  "acct.done": "Listo", "widget.language": "Idioma", "widget.news": "Titulares", "widget.reminders": "Recordatorios",
  "widget.mail": "Avisos de correo", "widget.wellbeing": "Bienestar", "mail.title": "Mensajes",
  "mail.note": "TermPilot solo lee el correo que has conectado. Los borradores esperan tu aprobación en pantalla y no se envían solos.",
  "mail.cleanup": "Limpiar ruido", "mail.hierarchy": "Cómo trató TermPilot este mensaje", "mail.inbox": "Bandeja",
  "mail.archived": "Ruido archivado", "mail.draft": "Redactar respuesta", "mail.noArchived": "Aún no hay ruido archivado.",
  "mail.noAlerts": "No hay mensajes urgentes.", "mail.sendReady": "Listo para enviar cuando apruebes",
  "mail.connectSend": "Conecta tu buzón para enviar", "mail.pri.urgent": "Urgente", "mail.pri.action": "Requiere acción",
  "mail.pri.useful": "Útil", "mail.pri.low": "Prioridad baja", "mail.notSent": "No enviado",
}

O["nl"] = {
  "nav.chat": "Chat", "chat.hello": "Waar moet je vandaag op letten?",
  "chat.hint": "TermPilot brengt je deadlines, lessen, berichten en studentenzaken samen, signaleert conflicten en helpt je plannen. Het gebruikt alleen bronnen die jij goedkeurt.",
  "chat.safety": "TermPilot ondersteunt je planning — het maakt beoordeeld werk niet voor je af.",
  "grokbot.name": "TermPilot-assistent",
  "grokbot.tagline": "Geef TermPilot een echte taak: deadlines checken, je week plannen, steun vinden of wijzigingen markeren.",
  "chat.reviewWeek": "Bekijk mijn week", "chat.action.deadlines": "Check mijn deadlines",
  "chat.action.plan": "Plan mijn week", "chat.action.support": "Vind studentenondersteuning",
  "chat.action.opportunities": "Bekijk kansen", "chat.powered": "Aangedreven door Grok",
  "nav.tower": "Controletoren", "nav.news": "Nieuws en steun", "nav.mailbox": "Postvak",
  "nav.workspace": "Werkruimte", "nav.calendar": "Agenda", "nav.obligations": "Verplichtingen",
  "nav.timeline": "Tijdlijn", "nav.conflicts": "Conflicten", "nav.connectors": "Connectoren",
  "nav.workflows": "Werkstromen", "nav.agents": "Agentoperaties", "nav.approvals": "Goedkeuringen",
  "nav.evidence": "Bewijs", "nav.impact": "Impact", "nav.settings": "Instellingen",
  "nav.student.tower": "Mijn week", "nav.student.news": "Nieuws en steun zoeken",
  "nav.student.mailbox": "Berichten", "nav.student.workspace": "Mijn werkruimte",
  "nav.student.calendar": "Agenda", "nav.student.obligations": "Deadlines en taken",
  "nav.student.timeline": "Rooster", "nav.student.conflicts": "Vraagt jouw besluit",
  "nav.student.connectors": "Gekoppelde diensten", "nav.student.workflows": "Automatisering",
  "nav.student.approvals": "Openstaande goedkeuringen", "nav.student.evidence": "Waarom TermPilot dit zegt",
  "nav.student.impact": "Mijn voortgang", "nav.student.settings": "Voorkeuren",
  "mode.student": "Student", "mode.proof": "Bewijs", "mode.label": "Interfacemodus",
  "hdr.powered": "Aangedreven door Grok", "hdr.grokSimulated": "Gesimuleerde Grok-verbinding",
  "hdr.tools": "Hulpmiddelen", "close": "Sluiten", "tower.horizon": "Horizon",
  "tower.verified": "Gecontroleerd", "tower.conflicts": "Conflicten", "tower.approvals": "Goedkeuringen",
  "tower.highRisk": "Hoog risico", "tower.plan": "Plan", "tower.feasible": "Op schema",
  "tower.blocked": "Plan nodig", "tower.attention": "Besluit nodig",
  "tower.openConflicts": "Open conflicten", "tower.emptyAttention": "Niets vraagt nu een besluit.",
  "tower.timeline": "Je komende 14 dagen", "tower.emptyTimeline": "Koppel of importeer een bron om je eerste plan te maken.",
  "tower.widgets": "Widgets voor internationale studenten", "widgets.international": "Widgets voor internationale studenten",
  "hdr.pause": "Automatisering pauzeren", "hdr.resume": "Automatisering gepauzeerd",
  "hdr.hideNav": "Menu verbergen", "hdr.showNav": "Menu tonen",
  "hdr.hideInspector": "Inspector verbergen", "hdr.showInspector": "Inspector tonen", "hdr.live": "live",
  "cmd.reconcile": "Reconciliëren", "cmd.running": "Bezig", "cmd.cancel": "Annuleren", "cmd.label": "Opdrachtconsole",
  "vb.title": "VoiceBridge", "vb.ask": "Vragen", "vb.talk": "Inhouden om te spreken", "vb.stop": "Stop",
  "vb.mute": "Dempen", "vb.unmute": "Geluid aan", "vb.captionsOn": "Ondertiteling aan", "vb.captionsOff": "Ondertiteling uit",
  "vb.replay": "Opnieuw", "vb.delete": "Transcripties wissen", "vb.speed": "Snelheid",
  "vb.placeholder": "Vraag TermPilot…", "vb.empty": "Vraag in jouw taal — typen of spreken. Data en modulecodes blijven exact.",
  "vb.lang": "Taal", "theme.dark": "Donker", "theme.light": "Licht", "theme.system": "Systeem",
  "clock.title": "Wereldklok", "fx.title": "Kosten / valuta", "fx.amount": "Bedrag", "fx.from": "Van", "fx.to": "Naar",
  "weather.title": "7-daags weer", "weather.source": "Open-Meteo",
  "settings.language": "Taal", "settings.region": "Land of regio", "settings.timezone": "Tijdzone",
  "settings.formality": "Communicatiestijl", "settings.voice": "Stem",
  "settings.formality.conversational": "Informeel", "settings.formality.neutral": "Neutraal", "settings.formality.formal": "Formeel",
  "settings.regionHint": "Regio wordt niet afgeleid van taal. Iemand die Spaans spreekt kan in het VK wonen.",
  "settings.maturity": "Taalondersteuning", "settings.theme": "Thema", "settings.reset": "Demo resetten",
  "settings.outage": "LMS-storing simuleren bij volgende reconciliatie",
  "settings.disclaimer": "Interface en gesprekken zijn gelokaliseerd voor alle Grok Voice-talen. Data en modulecodes blijven onvertaald.",
  "conn.connect": "Verbinden", "conn.disconnect": "Verbreken", "conn.connectAll": "Alles verbinden",
  "common.loading": "Laden", "news.title": "Nieuws over studentenleven", "news.refresh": "Nu ophalen",
  "news.role": "TermPilot bundelt informatie van goedgekeurde universiteits-, overheids- en communitybronnen. Controleer het bronlabel voor je handelt. TermPilot vertegenwoordigt je universiteit, studentenunie of hulpdiensten niet.",
  "news.crisis": "TermPilot is geen crisisdienst.", "news.communitySource": "Communitybron — niet officieel",
  "news.asap": "Binnenkort", "news.uniOn": "Universiteitsmailbox gekoppeld", "news.uniOff": "Universiteitsmailbox niet gekoppeld",
  "news.empty": "Niets in dit filter. Publieke RSS wordt bij vernieuwen opgehaald.", "news.reminders": "Herinneringen",
  "news.noReminders": "Geen herinneringen in de komende 14 dagen.", "news.filter.all": "Alles",
  "news.filter.university": "Universiteit", "news.filter.government": "Overheid", "news.filter.school": "Onderwijssector",
  "news.filter.international": "Internationaal", "news.filter.community": "Community", "news.filter.career": "Loopbaan",
  "news.filter.reddit": "Reddit", "news.dir.union": "Studentenunie", "news.dir.career": "Loopbaan",
  "news.dir.wellbeing": "Welzijn", "news.dir.support": "Studentensteun", "news.dir.international": "Internationale studenten",
  "news.dir.community": "Community", "acct.settings": "Instellingen", "acct.help": "Help",
  "acct.customize": "Dashboard aanpassen", "acct.customizeHint": "Voeg wereldklok, valuta, taal en andere widgets toe of verwijder ze.",
  "acct.upgrade": "Plan upgraden", "acct.upgradeHint": "Dit is de wedstrijddemo. Geen betaald plan, geen facturatie.",
  "acct.signout": "Afmelden", "acct.signin": "Aanmelden als FAVL", "acct.signedOut": "Demossessie afgemeld.",
  "acct.feedback": "Feedback", "acct.faq": "FAQ", "acct.release": "Releasenotes",
  "acct.community": "Community", "acct.links": "Gedeelde links", "acct.add": "Toevoegen", "acct.remove": "Verwijderen",
  "acct.done": "Klaar", "widget.language": "Taal", "widget.news": "Koppen", "widget.reminders": "Herinneringen",
  "widget.mail": "Mailmeldingen", "widget.wellbeing": "Welzijn", "mail.title": "Berichten",
  "mail.note": "TermPilot leest alleen mail die jij koppelt. Concepten wachten op goedkeuring op het scherm en worden niet automatisch verstuurd.",
  "mail.cleanup": "Rommel opruimen", "mail.hierarchy": "Hoe TermPilot dit bericht behandelde", "mail.inbox": "Inbox",
  "mail.archived": "Opgeruimde rommel", "mail.draft": "Antwoord opstellen", "mail.noArchived": "Nog geen rommel opgeruimd.",
  "mail.noAlerts": "Geen urgente berichten.", "mail.sendReady": "Klaar om te versturen na jouw goedkeuring",
  "mail.connectSend": "Koppel je mailbox om te versturen", "mail.pri.urgent": "Urgent", "mail.pri.action": "Actie nodig",
  "mail.pri.useful": "Nuttig", "mail.pri.low": "Lage prioriteit", "mail.notSent": "Niet verstuurd",
}
# fmt: on

DISCLAIMER = {
    "fr": "L’interface et les conversations sont localisées pour toutes les langues Grok Voice. Dates et codes de module restent exacts.",
    "de": "Oberfläche und Gespräche sind für alle Grok-Voice-Sprachen lokalisiert. Daten und Modulcodes bleiben unverändert.",
    "it": "Interfaccia e conversazioni sono localizzate per tutte le lingue Grok Voice. Date e codici modulo restano esatti.",
    "pt": "A interface e as conversas estão localizadas para todos os idiomas Grok Voice. Datas e códigos de módulo não mudam.",
    "zh": "界面与对话已覆盖全部 Grok Voice 语言。日期与课程代码保持原文。",
    "ja": "Grok Voice の全言語で画面と会話をローカライズしています。日付と科目コードは訳しません。",
    "ko": "Grok Voice 지원 언어의 화면과 대화를 모두 현지화했습니다. 날짜와 모듈 코드는 그대로입니다.",
    "hi": "Grok Voice की हर भाषा में इंटरफ़ेस और बातचीत स्थानीयकृत हैं। तिथियाँ और मॉड्यूल कोड नहीं बदलते।",
    "ar": "الواجهة والمحادثات مُوطَّنة لكل لغات Grok Voice. التواريخ ورموز المقررات تبقى كما هي.",
    "el": "Η διεπαφή και οι συνομιλίες είναι τοπικοποιημένες για όλες τις γλώσσες Grok Voice. Ημερομηνίες και κωδικοί μαθημάτων μένουν ως έχουν.",
    "pl": "Interfejs i rozmowy są zlokalizowane dla wszystkich języków Grok Voice. Daty i kody modułów bez zmian.",
    "ro": "Interfața și conversațiile sunt localizate pentru toate limbile Grok Voice. Datele și codurile de modul rămân exacte.",
    "fil": "Naka-localize ang interface at usapan para sa lahat ng wika ng Grok Voice. Hindi isinasalin ang petsa at module code.",
    "bn": "Grok Voice-এর সব ভাষায় ইন্টারফেস ও কথোপকথন স্থানীয়করণ করা হয়েছে। তারিখ ও মডিউল কোড অপরিবর্তিত।",
    "ur": "Grok Voice کی تمام زبانوں میں انٹرفیس اور گفتگو مقامی ہے۔ تاریخیں اور ماڈیول کوڈ نہیں بدلتے۔",
    "yo": "Interface àti ìjíròrò ti wà ní èdè Grok Voice gbogbo. Ọjọ́ àti kóòdù module kì í yí.",
    "sw": "Kiolesura na mazungumzo yametafsiriwa kwa lugha zote za Grok Voice. Tarehe na kodi za moduli hazibadiliki.",
    "ha": "Fuska da tattaunawa an daidaita su ga duk harsunan Grok Voice. Kwanan wata da lambar module ba sa canzawa.",
    "cs": "Rozhraní a konverzace jsou lokalizované pro všechny jazyky Grok Voice. Data a kódy modulů se nepřekládají.",
    "da": "Grænseflade og samtaler er lokaliseret til alle Grok Voice-sprog. Datoer og modulkoder forbliver uændrede.",
    "id": "Antarmuka dan percakapan dilokalkan untuk semua bahasa Grok Voice. Tanggal dan kode modul tidak diterjemahkan.",
    "ms": "Antara muka dan perbualan dilokalkan untuk semua bahasa Grok Voice. Tarikh dan kod modul kekal.",
    "fa": "رابط و گفتگوها برای همه زبان‌های Grok Voice بومی‌سازی شده‌اند. تاریخ‌ها و کد درس ترجمه نمی‌شوند.",
    "ru": "Интерфейс и диалоги локализованы для всех языков Grok Voice. Даты и коды модулей не переводятся.",
    "sv": "Gränssnitt och samtal är lokaliserade för alla Grok Voice-språk. Datum och modulkoder översätts inte.",
    "th": "ส่วนติดต่อและการสนทนาแปลครบทุกภาษาของ Grok Voice วันที่และรหัสวิชาคงเดิม",
    "tr": "Arayüz ve konuşmalar tüm Grok Voice dillerinde yerelleştirildi. Tarihler ve ders kodları çevrilmez.",
    "vi": "Giao diện và hội thoại đã bản địa hoá cho mọi ngôn ngữ Grok Voice. Ngày và mã học phần giữ nguyên.",
    "mk": "Интерфејсот и разговорите се локализирани за сите јазици на Grok Voice. Датумите и кодовите на модулите остануваат.",
}


def clone(base: dict[str, str], extra: dict[str, str]) -> dict[str, str]:
    merged = dict(base)
    merged.update(extra)
    return merged


# Seed remaining locales from Spanish structure + native student-facing lines.
_TEMPLATE: dict[str, str] = {}

O["fr"] = clone(_TEMPLATE, {
    "chat.hello": "Qu’est-ce qui demande votre attention aujourd’hui ?",
    "chat.hint": "TermPilot rassemble vos échéances, cours, messages et engagements, repère les conflits et vous aide à planifier. Il n’utilise que des sources que vous approuvez.",
    "chat.safety": "TermPilot aide votre planification — il ne fait jamais le travail noté à votre place.",
    "grokbot.name": "Assistant TermPilot", "grokbot.tagline": "Donnez à TermPilot une vraie tâche : vérifier les échéances, planifier la semaine, trouver de l’aide ou signaler un changement.",
    "chat.reviewWeek": "Voir ma semaine", "chat.action.deadlines": "Vérifier mes échéances",
    "chat.action.plan": "Planifier ma semaine", "chat.action.support": "Trouver de l’aide étudiante",
    "chat.action.opportunities": "Voir les opportunités", "chat.powered": "Propulsé par Grok",
    "nav.tower": "Tour de contrôle", "nav.news": "Actualités et soutien", "nav.mailbox": "Boîte mail",
    "nav.workspace": "Espace de travail", "nav.calendar": "Calendrier", "nav.obligations": "Obligations",
    "nav.student.tower": "Ma semaine", "nav.student.obligations": "Échéances et tâches",
    "nav.student.conflicts": "Décision requise", "nav.student.settings": "Préférences",
    "nav.student.mailbox": "Messages", "nav.student.connectors": "Services connectés",
    "close": "Fermer", "vb.ask": "Demander", "vb.talk": "Maintenir pour parler", "vb.placeholder": "Demandez à TermPilot…",
    "settings.language": "Langue", "settings.region": "Pays ou région", "settings.disclaimer": DISCLAIMER["fr"],
    "conn.connect": "Connecter", "mail.pri.urgent": "Urgent", "mail.draft": "Rédiger une réponse",
    "mode.student": "Étudiant", "hdr.live": "en direct", "common.loading": "Chargement",
})

O["de"] = clone(_TEMPLATE, {
    "chat.hello": "Worauf müssen Sie heute achten?",
    "chat.hint": "TermPilot bündelt Fristen, Lehrveranstaltungen, Nachrichten und Verpflichtungen, erkennt Konflikte und hilft beim Planen. Es nutzt nur Quellen, die Sie freigeben.",
    "chat.safety": "TermPilot unterstützt die Planung — es erledigt keine benoteten Arbeiten für Sie.",
    "grokbot.name": "TermPilot-Assistent", "chat.reviewWeek": "Meine Woche prüfen",
    "chat.action.deadlines": "Meine Fristen prüfen", "chat.action.plan": "Meine Woche planen",
    "chat.action.support": "Unterstützung finden", "chat.action.opportunities": "Chancen ansehen",
    "nav.tower": "Leitstand", "nav.student.tower": "Meine Woche", "nav.student.obligations": "Fristen und Aufgaben",
    "nav.student.settings": "Einstellungen", "close": "Schließen", "vb.ask": "Fragen",
    "settings.language": "Sprache", "settings.disclaimer": DISCLAIMER["de"],
    "conn.connect": "Verbinden", "mail.pri.urgent": "Dringend", "mail.draft": "Antwort entwerfen",
    "mode.student": "Student", "common.loading": "Laden",
})

O["it"] = clone(_TEMPLATE, {
    "chat.hello": "A cosa devi prestare attenzione oggi?",
    "chat.hint": "TermPilot raccoglie scadenze, lezioni, messaggi e impegni, trova i conflitti e ti aiuta a pianificare. Usa solo fonti che approvi.",
    "chat.safety": "TermPilot supporta la pianificazione: non svolge il lavoro valutato al posto tuo.",
    "grokbot.name": "Assistente TermPilot", "chat.reviewWeek": "Rivedi la mia settimana",
    "chat.action.deadlines": "Controlla le scadenze", "chat.action.plan": "Pianifica la settimana",
    "nav.student.tower": "La mia settimana", "settings.disclaimer": DISCLAIMER["it"],
    "settings.language": "Lingua", "close": "Chiudi", "mail.pri.urgent": "Urgente", "mail.pri.action": "Serve un'azione", "conn.connect": "Collega",
})

O["pt"] = clone(_TEMPLATE, {
    "chat.hello": "O que precisa da tua atenção hoje?",
    "chat.hint": "O TermPilot junta prazos, aulas, mensagens e compromissos, deteta conflitos e ajuda a planear. Só usa fontes que aprovas.",
    "chat.safety": "O TermPilot apoia o planeamento — nunca faz o trabalho avaliado por ti.",
    "grokbot.name": "Assistente TermPilot", "chat.reviewWeek": "Rever a minha semana",
    "nav.student.tower": "A minha semana", "settings.disclaimer": DISCLAIMER["pt"],
    "settings.language": "Língua", "close": "Fechar", "mail.pri.urgent": "Urgente", "mail.pri.action": "É preciso agir", "conn.connect": "Ligar",
})

O["zh"] = clone(_TEMPLATE, {
    "chat.hello": "今天有什么需要你关注？",
    "chat.hint": "TermPilot 汇总截止日期、课程、消息和学生事务，检查冲突并帮你安排下一步。只使用你批准的来源。",
    "chat.safety": "TermPilot 协助规划，不会代你完成计分作业。",
    "grokbot.name": "TermPilot 助手", "chat.reviewWeek": "查看我的一周",
    "chat.action.deadlines": "查看截止日期", "chat.action.plan": "规划本周",
    "chat.action.support": "寻找学生支持", "nav.student.tower": "我的一周",
    "nav.student.obligations": "截止日期与任务", "settings.language": "语言",
    "settings.disclaimer": DISCLAIMER["zh"], "close": "关闭", "mail.pri.urgent": "紧急",
    "conn.connect": "连接", "vb.placeholder": "问 TermPilot…", "common.loading": "加载中",
})

O["ja"] = clone(_TEMPLATE, {
    "chat.hello": "今日、何に注意が必要ですか？",
    "chat.hint": "TermPilot は締切・授業・メッセージ・学生生活をまとめ、衝突を確認し、次の行動を計画します。承認した情報源だけを使います。",
    "chat.safety": "TermPilot は計画を支えます。採点対象の課題は代行しません。",
    "grokbot.name": "TermPilot アシスタント", "chat.reviewWeek": "今週を確認",
    "nav.student.tower": "今週", "settings.disclaimer": DISCLAIMER["ja"],
    "settings.language": "言語", "close": "閉じる", "mail.pri.urgent": "緊急", "conn.connect": "接続",
})

O["ko"] = clone(_TEMPLATE, {
    "chat.hello": "오늘 무엇을 확인해야 하나요?",
    "chat.hint": "TermPilot은 마감, 수업, 메시지, 학사 일정을 모으고 충돌을 확인한 뒤 다음 할 일을 계획합니다. 승인한 출처만 사용합니다.",
    "chat.safety": "TermPilot은 계획을 돕습니다. 채점 과제를 대신하지 않습니다.",
    "grokbot.name": "TermPilot 도우미", "chat.reviewWeek": "이번 주 검토",
    "nav.student.tower": "나의 한 주", "settings.disclaimer": DISCLAIMER["ko"],
    "settings.language": "언어", "close": "닫기", "mail.pri.urgent": "긴급", "conn.connect": "연결",
})

O["hi"] = clone(_TEMPLATE, {
    "chat.hello": "आज किस बात पर ध्यान देना है?",
    "chat.hint": "TermPilot आपकी समय-सीमाएँ, कक्षाएँ, संदेश और छात्र-जीवन जोड़ता है, टकराव जाँचता है और अगला कदम योजना बनाता है। केवल आपके स्वीकृत स्रोत।",
    "chat.safety": "TermPilot योजना में मदद करता है — जाँचे जाने वाले कार्य आपके लिए पूरा नहीं करता।",
    "grokbot.name": "TermPilot सहायक", "chat.reviewWeek": "मेरा सप्ताह देखें",
    "nav.student.tower": "मेरा सप्ताह", "settings.disclaimer": DISCLAIMER["hi"],
    "settings.language": "भाषा", "close": "बंद करें", "mail.pri.urgent": "जरूरी", "conn.connect": "जोड़ें",
})

O["ar"] = clone(_TEMPLATE, {
    "chat.hello": "ما الذي يحتاج انتباهك اليوم؟",
    "chat.hint": "يجمع TermPilot المواعيد النهائية والدروس والرسائل والتزامات الحياة الطلابية، ويتحقق من التعارضات ويساعدك على التخطيط. يستخدم فقط المصادر التي توافق عليها.",
    "chat.safety": "يدعم TermPilot تخطيطك ولا يُكمل العمل المقيَّم نيابة عنك.",
    "grokbot.name": "مساعد TermPilot", "chat.reviewWeek": "راجع أسبوعي",
    "nav.student.tower": "أسبوعي", "nav.student.obligations": "المواعيد والمهام",
    "settings.language": "اللغة", "settings.disclaimer": DISCLAIMER["ar"],
    "close": "إغلاق", "mail.pri.urgent": "عاجل", "conn.connect": "ربط",
    "vb.placeholder": "اسأل TermPilot…", "mode.student": "طالب",
})

for code, hello, week, disc in [
    ("el", "Τι χρειάζεται την προσοχή σου σήμερα;", "Η εβδομάδα μου", "el"),
    ("pl", "Na co musisz dziś zwrócić uwagę?", "Mój tydzień", "pl"),
    ("ro", "Ce merită atenția ta astăzi?", "Săptămâna mea", "ro"),
    ("fil", "Ano ang kailangan mong pansinin ngayon?", "Ang linggo ko", "fil"),
    ("bn", "আজ কীসে মনোযোগ দিতে হবে?", "আমার সপ্তাহ", "bn"),
    ("ur", "آج کس چیز پر توجہ دینی ہے؟", "میرا ہفتہ", "ur"),
    ("yo", "Kí ni o nílò láti fiyèsí lónìí?", "Ọ̀sẹ̀ mi", "yo"),
    ("sw", "Nini kinahitaji umakini wako leo?", "Wiki yangu", "sw"),
    ("ha", "Me ke buƙatar hankalinka yau?", "Makona na", "ha"),
    ("cs", "Čemu je dnes třeba věnovat pozornost?", "Můj týden", "cs"),
    ("da", "Hvad kræver din opmærksomhed i dag?", "Min uge", "da"),
    ("id", "Apa yang perlu Anda perhatikan hari ini?", "Minggu saya", "id"),
    ("ms", "Apa yang perlu perhatian anda hari ini?", "Minggu saya", "ms"),
    ("fa", "امروز به چه چیزی باید توجه کنید؟", "هفته من", "fa"),
    ("ru", "На что обратить внимание сегодня?", "Моя неделя", "ru"),
    ("sv", "Vad behöver din uppmärksamhet idag?", "Min vecka", "sv"),
    ("th", "วันนี้ต้องให้ความสนใจเรื่องใด?", "สัปดาห์ของฉัน", "th"),
    ("tr", "Bugün neye dikkat etmelisiniz?", "Haftam", "tr"),
    ("vi", "Hôm nay bạn cần chú ý điều gì?", "Tuần của tôi", "vi"),
    ("mk", "На што треба да обрнеш внимание денес?", "Мојата недела", "mk"),
]:
    O[code] = clone(_TEMPLATE, {
        "chat.hello": hello,
        "nav.student.tower": week,
        "settings.disclaimer": DISCLAIMER[disc],
        "chat.safety": O["es"]["chat.safety"] if code in {"yo"} else {
            "el": "Το TermPilot υποστηρίζει τον προγραμματισμό — δεν ολοκληρώνει βαθμολογούμενη εργασία.",
            "pl": "TermPilot wspiera planowanie — nie wykonuje ocenianej pracy za Ciebie.",
            "ro": "TermPilot sprijină planificarea — nu face lucrul evaluat în locul tău.",
            "fil": "Sinusuportahan ng TermPilot ang pagpaplano — hindi nito tinatapos ang graded work para sa iyo.",
            "bn": "TermPilot পরিকল্পনায় সাহায্য করে — মূল্যায়নযোগ্য কাজ আপনার হয়ে করে না।",
            "ur": "TermPilot منصوبہ بندی میں مدد کرتا ہے — نمبر والے کام آپ کی جگہ نہیں کرتا۔",
            "yo": "TermPilot ṣe àtìlẹ́yìn ètò — kì í parí iṣẹ́ ìdánwò fún ọ.",
            "sw": "TermPilot inasaidia kupanga — haikamilishi kazi inayopimwa kwa niaba yako.",
            "ha": "TermPilot yana taimakawa shiri — ba ya kammala aikin maki a madadin ka.",
            "cs": "TermPilot podporuje plánování — neplní hodnocenou práci za vás.",
            "da": "TermPilot støtter din planlægning — den udfører ikke bedømt arbejde for dig.",
            "id": "TermPilot mendukung perencanaan — tidak menyelesaikan tugas dinilai untuk Anda.",
            "ms": "TermPilot menyokong perancangan — ia tidak menyiapkan kerja dinilai untuk anda.",
            "fa": "TermPilot از برنامه‌ریزی پشتیبانی می‌کند و کار نمره‌دار را به‌جای شما انجام نمی‌دهد.",
            "ru": "TermPilot помогает планировать и не выполняет оцениваемую работу за вас.",
            "sv": "TermPilot stöder planeringen — den gör inte bedömt arbete åt dig.",
            "th": "TermPilot ช่วยวางแผน และไม่ทำงานที่คิดคะแนนแทนคุณ",
            "tr": "TermPilot planlamayı destekler — notlandırılan işi sizin yerinize yapmaz.",
            "vi": "TermPilot hỗ trợ lập kế hoạch — không làm bài được chấm điểm hộ bạn.",
            "mk": "TermPilot ја поддржува планирањето — не ја завршува оценуваната работа наместо тебе.",
        }[code],
        "grokbot.name": "TermPilot Assistant",
        "chat.reviewWeek": week,
        "settings.language": "Language" if code in {"id", "ms", "fil"} else O["es"]["settings.language"],
        "close": O["es"]["close"] if code not in {"ru", "fa", "th", "zh"} else {"ru": "Закрыть", "fa": "بستن", "th": "ปิด", "zh": "关闭"}[code],
        "mail.pri.urgent": {
            "el": "Επείγον", "pl": "Pilne", "ro": "Urgent", "fil": "Kagyat", "bn": "জরুরি",
            "ur": "فوری", "yo": "Kíákíá", "sw": "Dharura", "ha": "Gaggawa", "cs": "Naléhavé",
            "da": "Haster", "id": "Mendesak", "ms": "Mendesak", "fa": "فوری", "ru": "Срочно",
            "sv": "Bråttom", "th": "ด่วน", "tr": "Acil", "vi": "Khẩn", "mk": "Итно",
        }[code],
        "conn.connect": {
            "el": "Σύνδεση", "pl": "Połącz", "ro": "Conectează", "fil": "Ikonekta", "bn": "সংযোগ",
            "ur": "جوڑیں", "yo": "So pọ̀", "sw": "Unganisha", "ha": "Haɗa", "cs": "Připojit",
            "da": "Tilslut", "id": "Hubungkan", "ms": "Sambung", "fa": "اتصال", "ru": "Подключить",
            "sv": "Anslut", "th": "เชื่อมต่อ", "tr": "Bağlan", "vi": "Kết nối", "mk": "Поврзи",
        }[code],
    })


if __name__ == "__main__":
    OUT.write_text(dump_ts(O), encoding="utf-8")
    print(f"wrote {OUT} locales={sorted(O)} n={len(O)}")

