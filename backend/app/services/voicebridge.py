"""TermPilot VoiceBridge — localisation and accessibility over verified agents.

Canonical facts stay language-neutral. Speech never bypasses Guardian or approvals.
Raw audio is not stored. xAI STT/TTS is used when XAI_API_KEY is set; otherwise
the client may use browser speech APIs as a labelled local fallback.
"""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import AgentName, ApprovalState
from app.domain.ids import new_id
from app.domain.models import (
    ApprovalRequest,
    ConflictingClaim,
    Obligation,
    Plan,
    PlanBlock,
    SourceObservation,
    VoiceTurn,
)
from app.policies.gate import apply_student_policies
from app.policies.integrity import inspect_user_goal
from app.services import clock
from app.services.audit import record_audit
from app.services.grokbot import STUDENT_TOOLS, answer_with_policies, classify_tool, execute_tool
from app.services.identity import get_connection
from app.settings import get_settings

CONFIDENCE_THRESHOLD = 0.72

# Official Grok Voice STT language parameter codes (xAI Speech-to-Text docs).
GROK_VOICE_CODES = {
    "ar",
    "cs",
    "da",
    "nl",
    "en",
    "fil",
    "fr",
    "de",
    "hi",
    "id",
    "it",
    "ja",
    "ko",
    "mk",
    "ms",
    "fa",
    "pl",
    "pt",
    "ro",
    "ru",
    "es",
    "sv",
    "th",
    "tr",
    "vi",
}


def _lang(code: str, name: str) -> dict[str, Any]:
    grok = code in GROK_VOICE_CODES
    return {
        "code": code,
        "display_name": name,
        "speech_recognition": True,
        "speech_synthesis": True,
        "ui_translation": "complete",
        "conversation_translation": "complete",
        "evaluation_status": "grok_voice_available" if grok else "conversation_localised",
        "limitations": (
            "Canonical dates and module codes stay untranslated. Speech uses Grok Voice."
            if grok
            else (
                "Interface and conversations are localised. This code is outside the published "
                "Grok Voice STT list; speech uses Grok TTS when accepted, otherwise the browser."
            )
        ),
        "rtl": code in {"ar", "ur", "fa"},
        "grok_voice": grok,
    }


LANGUAGE_REGISTRY: list[dict[str, Any]] = [
    _lang("en", "English"),
    _lang("es", "Español"),
    _lang("nl", "Nederlands"),
    _lang("fr", "Français"),
    _lang("de", "Deutsch"),
    _lang("it", "Italiano"),
    _lang("pt", "Português"),
    _lang("zh", "中文"),
    _lang("ja", "日本語"),
    _lang("ko", "한국어"),
    _lang("hi", "हिन्दी"),
    _lang("ar", "العربية"),
    _lang("el", "Ελληνικά"),
    _lang("pl", "Polski"),
    _lang("ro", "Română"),
    _lang("fil", "Filipino"),
    _lang("bn", "বাংলা"),
    _lang("ur", "اردو"),
    _lang("yo", "Yorùbá"),
    _lang("sw", "Kiswahili"),
    _lang("ha", "Hausa"),
    _lang("cs", "Čeština"),
    _lang("da", "Dansk"),
    _lang("id", "Bahasa Indonesia"),
    _lang("ms", "Bahasa Melayu"),
    _lang("fa", "فارسی"),
    _lang("ru", "Русский"),
    _lang("sv", "Svenska"),
    _lang("th", "ไทย"),
    _lang("tr", "Türkçe"),
    _lang("vi", "Tiếng Việt"),
    _lang("mk", "Македонски"),
]

_NL_HINTS = {
    "wat",
    "deze",
    "week",
    "moet",
    "afmaken",
    "verplaats",
    "dinsdag",
    "woensdag",
    "ja",
    "nee",
    "schema",
    "deadline",
}
_ES_HINTS = {
    "que",
    "qué",
    "esta",
    "semana",
    "necesito",
    "terminar",
    "mueve",
    "martes",
    "miercoles",
    "miércoles",
    "si",
    "sí",
    "horario",
}

_STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "week_intro": "Here is what still needs finishing in the current 14-day horizon.",
        "conflict": "There is an unresolved deadline conflict. TermPilot will not guess.",
        "no_obligations": "No reconciled obligations yet. Ask me to reconcile the next 14 days.",
        "move_partial": "Wednesday has only {free} free minutes, but this task needs approximately {need} minutes. I can divide it into two sessions. Would you like to review that plan?",
        "move_ok": "Wednesday has enough free time for that block. No calendar change has been made. Review, approve or cancel in Approvals.",
        "approve_prompt": "I am proposing to create {n} study sessions in your Demo Calendar. No changes have been made. Would you like to review, approve or cancel?",
        "spoken_yes_blocked": "A spoken yes is not enough for this action. Confirm on screen.",
        "low_confidence": "I am not sure I heard that correctly. Please type the request or tap the transcript and edit it.",
        "unsupported": "That language is not in the Grok Voice set. I will continue in English and keep the factual fields unchanged.",
        "blocked": "I can organise work, not complete assessed homework or impersonate you.",
        "reconcile_done": "Reconciliation finished. Conflicts stay open until you decide.",
        "fallback": "I can help with this week's work, conflicts, the plan, or a calendar proposal. Nothing is changed until you approve it.",
        "switched": "Language set to {name}. Facts stay in their original form.",
    },
    "es": {
        "week_intro": "Esto es lo que aún hay que terminar en los próximos 14 días.",
        "conflict": "Hay un conflicto de fecha sin resolver. TermPilot no va a adivinar.",
        "no_obligations": "Aún no hay obligaciones reconciliadas. Pídeme reconciliar los próximos 14 días.",
        "move_partial": "El miércoles solo tiene {free} minutos libres, pero esta tarea necesita unos {need} minutos. Puedo dividirla en dos sesiones. ¿Quieres revisar ese plan?",
        "move_ok": "El miércoles tiene tiempo suficiente. No se ha cambiado el calendario. Revisa, aprueba o cancela en Approvals.",
        "approve_prompt": "Propongo crear {n} sesiones de estudio en tu Demo Calendar. No se ha cambiado nada. ¿Quieres revisar, aprobar o cancelar?",
        "spoken_yes_blocked": "Un «sí» hablado no basta para esta acción. Confirma en pantalla.",
        "low_confidence": "No estoy seguro de haberlo oído bien. Escribe la petición o edita la transcripción.",
        "unsupported": "Ese idioma no está en Grok Voice. Sigo en inglés y no cambio los datos canónicos.",
        "blocked": "Puedo organizar el trabajo; no completar tareas evaluadas ni impersonarte.",
        "reconcile_done": "Reconciliación terminada. Los conflictos siguen abiertos hasta que decidas.",
        "fallback": "Puedo ayudar con el trabajo de esta semana, conflictos, el plan o una propuesta de calendario. Nada cambia hasta que apruebes.",
        "switched": "Idioma fijado en {name}. Los hechos no se traducen.",
    },
    "nl": {
        "week_intro": "Dit moet je nog afronden in de komende 14 dagen.",
        "conflict": "Er is een onopgelost deadlineconflict. TermPilot gaat niet gokken.",
        "no_obligations": "Er zijn nog geen gereconcilieerde verplichtingen. Vraag me de komende 14 dagen te reconcilieren.",
        "move_partial": "Woensdag heeft maar {free} vrije minuten, maar deze taak vraagt ongeveer {need} minuten. Ik kan het in twee sessies splitsen. Wil je dat plan bekijken?",
        "move_ok": "Woensdag heeft genoeg ruimte. Er is niets in de agenda gewijzigd. Bekijk, keur goed of annuleer bij Approvals.",
        "approve_prompt": "Ik stel voor {n} studiesessies in je Demo Calendar te zetten. Er is niets gewijzigd. Wil je bekijken, goedkeuren of annuleren?",
        "spoken_yes_blocked": "Een gesproken ja is niet genoeg. Bevestig op het scherm.",
        "low_confidence": "Ik ben niet zeker van de transcriptie. Typ het verzoek of bewerk de tekst.",
        "unsupported": "Die taal zit niet in Grok Voice. Ik ga verder in het Engels; feiten blijven ongewijzigd.",
        "blocked": "Ik organiseer werk. Ik maak geen beoordeelde opdrachten en doe niet alsof ik jou ben.",
        "reconcile_done": "Reconciliatie is klaar. Conflicten blijven open tot jij beslist.",
        "fallback": "Ik help met werk van deze week, conflicten, het plan of een agenda-voorstel. Niets verandert zonder goedkeuring.",
        "switched": "Taal ingesteld op {name}. Feiten blijven in de oorspronkelijke vorm.",
    },
    "fr": {
        "week_intro": "Voici ce qu’il reste à terminer sur les 14 prochains jours.",
        "conflict": "Il y a un conflit de date non résolu. TermPilot ne va pas deviner.",
        "no_obligations": "Aucune obligation réconciliée. Demandez de réconcilier les 14 prochains jours.",
        "move_partial": "Mercredi n’a que {free} minutes libres, mais cette tâche demande environ {need} minutes. Je peux la couper en deux. Voulez-vous revoir ce plan ?",
        "move_ok": "Mercredi a assez de temps. Aucun changement calendrier. Vérifiez dans Approvals.",
        "approve_prompt": "Je propose de créer {n} sessions dans votre Demo Calendar. Rien n’a été modifié. Revoir, approuver ou annuler ?",
        "spoken_yes_blocked": "Un « oui » parlé ne suffit pas. Confirmez à l’écran.",
        "low_confidence": "Je n’ai pas bien entendu. Tapez ou corrigez la transcription.",
        "unsupported": "Langue hors registre. Je continue en anglais ; les faits restent inchangés.",
        "blocked": "J’organise le travail. Je ne fais pas les devoirs notés et je n’usurpe pas votre identité.",
        "reconcile_done": "Réconciliation terminée. Les conflits restent ouverts.",
        "fallback": "Je peux aider pour la semaine, les conflits, le plan ou le calendrier. Rien ne change sans approbation.",
        "switched": "Langue : {name}. Les faits restent dans leur forme d’origine.",
    },
    "de": {
        "week_intro": "Das steht in den nächsten 14 Tagen noch aus.",
        "conflict": "Es gibt einen ungelösten Fristkonflikt. TermPilot rät nicht.",
        "no_obligations": "Noch keine abgeglichenen Pflichten. Bitte die nächsten 14 Tage abgleichen.",
        "move_partial": "Mittwoch hat nur {free} freie Minuten, die Aufgabe braucht etwa {need}. Ich kann sie teilen. Plan prüfen?",
        "move_ok": "Mittwoch hat genug Zeit. Kalender unverändert. Unter Approvals prüfen.",
        "approve_prompt": "Ich schlage {n} Lernblöcke im Demo Calendar vor. Nichts wurde geändert. Prüfen, genehmigen oder abbrechen?",
        "spoken_yes_blocked": "Ein gesprochenes Ja reicht nicht. Bitte am Bildschirm bestätigen.",
        "low_confidence": "Ich habe das unsicher gehört. Bitte tippen oder Transkript ändern.",
        "unsupported": "Sprache nicht im Register. Weiter auf Englisch; Fakten unverändert.",
        "blocked": "Ich organisiere Arbeit. Ich schreibe keine benoteten Aufgaben und gebe mich nicht als Sie aus.",
        "reconcile_done": "Abgleich fertig. Konflikte bleiben offen.",
        "fallback": "Ich helfe bei Woche, Konflikten, Plan oder Kalender. Nichts ändert sich ohne Freigabe.",
        "switched": "Sprache: {name}. Fakten bleiben original.",
    },
    "it": {
        "week_intro": "Ecco cosa resta da finire nei prossimi 14 giorni.",
        "conflict": "C’è un conflitto di scadenza. TermPilot non indovina.",
        "no_obligations": "Nessun obbligo riconciliato. Chiedi di riconciliare i prossimi 14 giorni.",
        "move_partial": "Mercoledì ha solo {free} minuti liberi, il compito ne richiede circa {need}. Posso dividerlo. Vuoi rivedere il piano?",
        "move_ok": "Mercoledì ha tempo sufficiente. Calendario invariato.",
        "approve_prompt": "Propongo {n} sessioni nel Demo Calendar. Nessuna modifica fatta. Rivedere, approvare o annullare?",
        "spoken_yes_blocked": "Un «sì» parlato non basta. Conferma sullo schermo.",
        "low_confidence": "Non ho capito bene. Scrivi o modifica la trascrizione.",
        "unsupported": "Lingua non nel registro. Continuo in inglese.",
        "blocked": "Organizzo il lavoro. Non svolgo compiti valutati e non ti impersono.",
        "reconcile_done": "Riconciliazione completata.",
        "fallback": "Posso aiutare con la settimana, i conflitti, il piano o il calendario. Nulla cambia senza approvazione.",
        "switched": "Lingua: {name}. I fatti restano originali.",
    },
    "pt": {
        "week_intro": "Isto ainda precisa de ser concluído nos próximos 14 dias.",
        "conflict": "Há um conflito de prazo. O TermPilot não adivinha.",
        "no_obligations": "Ainda não há obrigações reconciliadas.",
        "move_partial": "Quarta tem só {free} minutos livres; a tarefa precisa de cerca de {need}. Posso dividir. Queres rever o plano?",
        "move_ok": "Quarta tem tempo suficiente. Calendário inalterado.",
        "approve_prompt": "Proponho criar {n} sessões no Demo Calendar. Nada foi alterado. Rever, aprovar ou cancelar?",
        "spoken_yes_blocked": "Um «sim» falado não chega. Confirma no ecrã.",
        "low_confidence": "Não ouvi bem. Escreve ou edita a transcrição.",
        "unsupported": "Língua fora do registo. Continuo em inglês.",
        "blocked": "Organizo trabalho. Não faço trabalhos avaliados nem impersono-te.",
        "reconcile_done": "Reconciliação concluída.",
        "fallback": "Posso ajudar com a semana, conflitos, plano ou calendário. Nada muda sem aprovação.",
        "switched": "Língua: {name}. Os factos mantêm-se.",
    },
    "zh": {
        "week_intro": "未来 14 天仍需完成的事项如下。",
        "conflict": "存在未解决的截止日期冲突。TermPilot 不会猜测。",
        "no_obligations": "尚无已核对事项。请先核对未来 14 天。",
        "move_partial": "周三仅有 {free} 分钟空闲，该任务约需 {need} 分钟。我可以拆成两段。是否查看该计划？",
        "move_ok": "周三时间足够。日历尚未更改。请在 Approvals 中审核。",
        "approve_prompt": "建议在 Demo Calendar 创建 {n} 个学习时段。尚未更改。查看、批准或取消？",
        "spoken_yes_blocked": "口头“是”不足够。请在屏幕上确认。",
        "low_confidence": "我不确定听清了。请输入或编辑转写。",
        "unsupported": "该语言不在登记表中。改用英语，事实字段不变。",
        "blocked": "我只组织学习，不代写计分作业，也不冒充你。",
        "reconcile_done": "核对完成。冲突仍待你决定。",
        "fallback": "我可以说明本周任务、冲突、计划或日历建议。未经批准不会改动。",
        "switched": "语言已设为 {name}。事实保持原样。",
    },
    "ja": {
        "week_intro": "今後14日で残っている作業です。",
        "conflict": "未解決の期限の食い違いがあります。TermPilot は推測しません。",
        "no_obligations": "まだ照合された課題がありません。",
        "move_partial": "水曜の空きは {free} 分ですが、この作業は約 {need} 分です。2つに分けられます。計画を確認しますか？",
        "move_ok": "水曜に十分な時間があります。カレンダーは未変更です。",
        "approve_prompt": "Demo Calendar に {n} 件の学習枠を提案します。未変更です。確認、承認、または取消しますか？",
        "spoken_yes_blocked": "音声の「はい」だけでは不十分です。画面で確認してください。",
        "low_confidence": "聞き取りに自信がありません。入力するか転写を直してください。",
        "unsupported": "未対応の言語です。英語で続け、事実は変えません。",
        "blocked": "学習の整理はします。採点対象の代行やなりすましはしません。",
        "reconcile_done": "照合が終わりました。",
        "fallback": "今週の課題、衝突、計画、カレンダー案を手伝えます。承認なしでは変更しません。",
        "switched": "言語を {name} にしました。事実はそのままです。",
    },
    "ko": {
        "week_intro": "앞으로 14일 동안 남은 일입니다.",
        "conflict": "기한 충돌이 있습니다. TermPilot은 추측하지 않습니다.",
        "no_obligations": "아직 대사된 과제가 없습니다.",
        "move_partial": "수요일은 {free}분만 비어 있고 이 작업은 약 {need}분이 필요합니다. 둘로 나눌 수 있습니다. 계획을 검토할까요?",
        "move_ok": "수요일에 시간이 충분합니다. 캘린더는 변경되지 않았습니다.",
        "approve_prompt": "Demo Calendar에 학습 블록 {n}개를 제안합니다. 아직 변경되지 않았습니다. 검토, 승인 또는 취소할까요?",
        "spoken_yes_blocked": "말한 '예'만으로는 부족합니다. 화면에서 확인하세요.",
        "low_confidence": "잘 듣지 못했습니다. 입력하거나 전사를 수정하세요.",
        "unsupported": "등록되지 않은 언어입니다. 영어로 이어가며 사실은 유지합니다.",
        "blocked": "학습을 정리합니다. 채점 과제를 대신하거나 사칭하지 않습니다.",
        "reconcile_done": "대사가 끝났습니다.",
        "fallback": "이번 주 과제, 충돌, 계획, 캘린더 제안을 도울 수 있습니다. 승인 전에는 바뀌지 않습니다.",
        "switched": "언어가 {name}(으)로 설정되었습니다. 사실은 그대로입니다.",
    },
    "hi": {
        "week_intro": "अगले 14 दिनों में यह काम बाकी है।",
        "conflict": "एक अनसुलझा समय-सीमा विरोध है। TermPilot अनुमान नहीं लगाएगा।",
        "no_obligations": "अभी कोई मिलाई गई जिम्मेदारी नहीं है।",
        "move_partial": "बुधवार पर केवल {free} मिनट खाली हैं, कार्य को लगभग {need} मिनट चाहिए। मैं दो सत्र कर सकता हूँ। योजना देखें?",
        "move_ok": "बुधवार पर समय पर्याप्त है। कैलेंडर नहीं बदला गया।",
        "approve_prompt": "Demo Calendar में {n} अध्ययन खंड प्रस्तावित हैं। कुछ नहीं बदला। समीक्षा, स्वीकृति या रद्द?",
        "spoken_yes_blocked": "बोला गया हाँ पर्याप्त नहीं। स्क्रीन पर पुष्टि करें।",
        "low_confidence": "सुनने में अनिश्चित हूँ। लिखें या ट्रांसक्रिप्ट सुधारें।",
        "unsupported": "यह भाषा सूची में नहीं। अंग्रेज़ी जारी; तथ्य वही रहेंगे।",
        "blocked": "मैं काम व्यवस्थित करता हूँ, जाँचे जाने वाले कार्य नहीं करता और आपका रूप नहीं धरता।",
        "reconcile_done": "मिलान पूरा।",
        "fallback": "इस सप्ताह, विरोध, योजना या कैलेंडर में मदद कर सकता हूँ। स्वीकृति के बिना कुछ नहीं बदलेगा।",
        "switched": "भाषा {name}। तथ्य मूल रूप में रहेंगे।",
    },
    "ar": {
        "week_intro": "هذا ما يجب إنهاؤه خلال 14 يوماً.",
        "conflict": "هناك تعارض في الموعد النهائي. TermPilot لن يخمن.",
        "no_obligations": "لا التزامات مُطابقة بعد.",
        "move_partial": "الأربعاء فيه {free} دقيقة فقط، والمهمة تحتاج حوالي {need}. يمكن تقسيمها. هل تراجع الخطة؟",
        "move_ok": "الأربعاء فيه وقت كاف. لم يُغيَّر التقويم.",
        "approve_prompt": "أقترح إنشاء {n} جلسات في Demo Calendar. لم يُغيَّر شيء. مراجعة أو موافقة أو إلغاء؟",
        "spoken_yes_blocked": "كلمة نعم صوتياً لا تكفي. أكّد على الشاشة.",
        "low_confidence": "لست متأكداً مما سمعت. اكتب أو عدّل النص.",
        "unsupported": "اللغة غير مسجّلة. أتابع بالإنجليزية دون تغيير الحقائق.",
        "blocked": "أنظّم العمل. لا أنجز واجبات مُقيَّمة ولا أنتحل شخصك.",
        "reconcile_done": "اكتملت المطابقة.",
        "fallback": "يمكنني المساعدة في الأسبوع والتعارضات والخطة والتقويم. لا تغيير بلا موافقة.",
        "switched": "اللغة: {name}. الحقائق تبقى كما هي.",
    },
    "el": {
        "week_intro": "Αυτό μένει για τις επόμενες 14 ημέρες.",
        "conflict": "Υπάρχει σύγκρουση προθεσμίας. Το TermPilot δεν μαντεύει.",
        "no_obligations": "Δεν υπάρχουν ακόμη συμφωνημένες υποχρεώσεις.",
        "move_partial": "Η Τετάρτη έχει μόνο {free} ελεύθερα λεπτά, η εργασία θέλει περίπου {need}. Μπορώ να τη χωρίσω. Να δούμε το πλάνο;",
        "move_ok": "Η Τετάρτη έχει χρόνο. Το ημερολόγιο δεν άλλαξε.",
        "approve_prompt": "Προτείνω {n} συνεδρίες στο Demo Calendar. Δεν έγινε αλλαγή. Έλεγχος, έγκριση ή ακύρωση;",
        "spoken_yes_blocked": "Το προφορικό ναι δεν αρκεί. Επιβεβαιώστε στην οθόνη.",
        "low_confidence": "Δεν άκουσα καθαρά. Πληκτρολογήστε ή διορθώστε.",
        "unsupported": "Η γλώσσα δεν είναι στο μητρώο. Συνεχίζω στα αγγλικά.",
        "blocked": "Οργανώνω εργασία. Δεν κάνω βαθμολογούμενες εργασίες ούτε σας μιμούμαι.",
        "reconcile_done": "Η συμφωνία ολοκληρώθηκε.",
        "fallback": "Βοηθώ με την εβδομάδα, συγκρούσεις, πλάνο ή ημερολόγιο. Τίποτα δεν αλλάζει χωρίς έγκριση.",
        "switched": "Γλώσσα: {name}. Τα γεγονότα μένουν ως έχουν.",
    },
    "pl": {
        "week_intro": "To zostało do zrobienia w ciągu 14 dni.",
        "conflict": "Jest nierozstrzygnięty konflikt terminu. TermPilot nie zgaduje.",
        "no_obligations": "Brak uzgodnionych obowiązków.",
        "move_partial": "Środa ma tylko {free} wolnych minut, zadanie potrzebuje ok. {need}. Mogę podzielić. Sprawdzić plan?",
        "move_ok": "Środa ma dość czasu. Kalendarz bez zmian.",
        "approve_prompt": "Proponuję {n} sesji w Demo Calendar. Nic nie zmieniono. Przejrzeć, zatwierdzić czy anulować?",
        "spoken_yes_blocked": "Wypowiedziane tak nie wystarczy. Potwierdź na ekranie.",
        "low_confidence": "Niepewna transkrypcja. Wpisz lub popraw.",
        "unsupported": "Język poza rejestrem. Kontynuuję po angielsku.",
        "blocked": "Organizuję pracę. Nie robię ocenianych zadań i nie podszywam się.",
        "reconcile_done": "Uzgodnienie zakończone.",
        "fallback": "Mogę pomóc z tygodniem, konfliktami, planem lub kalendarzem. Nic bez zgody.",
        "switched": "Język: {name}. Fakty bez zmian.",
    },
    "ro": {
        "week_intro": "Asta mai trebuie terminat în următoarele 14 zile.",
        "conflict": "Există un conflict de termen. TermPilot nu ghicește.",
        "no_obligations": "Încă nu există obligații reconciliate.",
        "move_partial": "Miercuri are doar {free} minute libere, sarcina cere circa {need}. Pot o împărți. Revizuim planul?",
        "move_ok": "Miercuri are timp suficient. Calendarul e neschimbat.",
        "approve_prompt": "Propun {n} sesiuni în Demo Calendar. Nimic nu s-a schimbat. Revizuire, aprobare sau anulare?",
        "spoken_yes_blocked": "Un da vorbit nu ajunge. Confirmă pe ecran.",
        "low_confidence": "Nu am auzit clar. Tastează sau editează transcrierea.",
        "unsupported": "Limba nu e în registru. Continui în engleză.",
        "blocked": "Organizez munca. Nu fac teme notate și nu te impersoniez.",
        "reconcile_done": "Reconcilierea s-a încheiat.",
        "fallback": "Pot ajuta cu săptămâna, conflicte, plan sau calendar. Nimic fără aprobare.",
        "switched": "Limba: {name}. Faptele rămân originale.",
    },
    "fil": {
        "week_intro": "Ito ang dapat tapusin sa susunod na 14 araw.",
        "conflict": "May hindi pa naresolbang conflict sa deadline. Hindi huhula ang TermPilot.",
        "no_obligations": "Wala pang naka-reconcile na obligation.",
        "move_partial": "May {free} libreng minuto lang ang Miyerkules; ~{need} ang kailangan. Puwedeng hatiin. I-review ang plano?",
        "move_ok": "Sapat ang oras sa Miyerkules. Hindi nabago ang calendar.",
        "approve_prompt": "Nagmumungkahi ng {n} study block sa Demo Calendar. Walang pagbabago. I-review, i-approve, o i-cancel?",
        "spoken_yes_blocked": "Hindi sapat ang sinabing oo. Kumpirmahin sa screen.",
        "low_confidence": "Hindi ako sigurado sa narinig. I-type o i-edit ang transcript.",
        "unsupported": "Wala sa registry ang wika. Magpapatuloy sa English.",
        "blocked": "Nag-aayos ako ng gawain. Hindi ko ginagawa ang graded work at hindi kita ginagaya.",
        "reconcile_done": "Tapos na ang reconcile.",
        "fallback": "Makakatulong ako sa linggo, conflict, plano, o calendar. Walang palit hangga't hindi approved.",
        "switched": "Wika: {name}. Hindi isinasalin ang mga katotohanan.",
    },
    "bn": {
        "week_intro": "আগামী ১৪ দিনে যা বাকি আছে।",
        "conflict": "সমাধানহীন সময়সীমা দ্বন্দ্ব আছে। TermPilot অনুমান করবে না।",
        "no_obligations": "এখনও মিলানো দায়িত্ব নেই।",
        "move_partial": "বুধবার মাত্র {free} মিনিট খালি, কাজটির প্রায় {need} মিনিট লাগে। দুই ভাগে ভাগ করা যায়। পরিকল্পনা দেখবেন?",
        "move_ok": "বুধবার যথেষ্ট সময় আছে। ক্যালেন্ডার বদলানো হয়নি।",
        "approve_prompt": "Demo Calendar-এ {n}টি স্টাডি ব্লক প্রস্তাব। কিছু বদলায়নি। পর্যালোচনা, অনুমোদন বা বাতিল?",
        "spoken_yes_blocked": "বলা ‘হ্যাঁ’ যথেষ্ট নয়। স্ক্রিনে নিশ্চিত করুন।",
        "low_confidence": "শুনতে নিশ্চিত নই। লিখুন বা ট্রান্সক্রিপ্ট সম্পাদনা করুন।",
        "unsupported": "ভাষা তালিকায় নেই। ইংরেজিতে চলবে; তথ্য অপরিবর্তিত।",
        "blocked": "আমি কাজ সাজাই, মূল্যায়নযোগ্য কাজ করি না, আপনার পরিচয় চুরি করি না।",
        "reconcile_done": "মিলানো শেষ।",
        "fallback": "সপ্তাহ, দ্বন্দ্ব, পরিকল্পনা বা ক্যালেন্ডারে সাহায্য করতে পারি। অনুমোদন ছাড়া কিছু বদলায় না।",
        "switched": "ভাষা {name}। তথ্য আসল থাকবে।",
    },
    "ur": {
        "week_intro": "اگلے 14 دن میں یہ کام باقی ہے۔",
        "conflict": "تاریخ کا تنازعہ ہے۔ TermPilot اندازہ نہیں لگائے گا۔",
        "no_obligations": "ابھی کوئی مطابقت شدہ ذمہ داری نہیں۔",
        "move_partial": "بدھ پر صرف {free} منٹ خالی ہیں، کام کو تقریباً {need} منٹ چاہیے۔ دو حصے ہو سکتے ہیں۔ منصوبہ دیکھیں؟",
        "move_ok": "بدھ پر وقت کافی ہے۔ کیلنڈر نہیں بدلا۔",
        "approve_prompt": "Demo Calendar میں {n} سیشن تجویز ہیں۔ کچھ نہیں بدلا۔ جائزہ، منظوری یا منسوخ؟",
        "spoken_yes_blocked": "بولا ہوا ہاں کافی نہیں۔ اسکرین پر تصدیق کریں۔",
        "low_confidence": "سننے میں یقین نہیں۔ لکھیں یا نقل درست کریں۔",
        "unsupported": "زبان فہرست میں نہیں۔ انگریزی جاری؛ حقائق وہی رہیں گے۔",
        "blocked": "میں کام ترتیب دیتا ہوں، نمبر والے کام نہیں کرتا اور آپ کا روپ نہیں دھارتا۔",
        "reconcile_done": "مطابقت مکمل۔",
        "fallback": "ہفتہ، تنازع، منصوبہ یا کیلنڈر میں مدد کر سکتا ہوں۔ منظوری کے بغیر کچھ نہیں بدلے گا۔",
        "switched": "زبان {name}۔ حقائق اصل رہیں گے۔",
    },
    "yo": {
        "week_intro": "Èyí ni ohun tó ṣẹ́kù fún ọjọ́ 14 tó ń bọ̀.",
        "conflict": "Ìforígbárí ọjọ́ ìparí wà. TermPilot kì í ṣe àsọtẹ́lẹ̀.",
        "no_obligations": "Kò sí ọranyan tí a ti ṣe ìṣọ̀kan.",
        "move_partial": "Ọjọ́rú ní ìṣẹ́jú {free} ṣìṣe; iṣẹ́ yìí nílò nǹkan bí {need}. Mo lè pín un. Ṣé o fẹ́ wo ètò náà?",
        "move_ok": "Ọjọ́rú ní àkókò tó tó. Kalẹ́ndà kò yí padà.",
        "approve_prompt": "Mo dábàá {n} àkókò ìkẹ́kọ̀ọ́ nínú Demo Calendar. Kò sí àyípadà. Ṣàyẹ̀wò, fọwọ́sí tàbí fagilé?",
        "spoken_yes_blocked": "Bẹ́ẹ̀ni lẹ́nu kò tó. Jẹ́rìí lórí ojú ìwòran.",
        "low_confidence": "Mi ò dá a lójú ohun tí mo gbọ́. Tẹ̀ ẹ́ tàbí ṣàtúnṣe.",
        "unsupported": "Èdè yìí kò sí nínú àkọsílẹ̀. Èdè Gẹ̀ẹ́sì ni, òtítọ́ kò yí.",
        "blocked": "Mo ṣètò iṣẹ́. Mi ò ṣe iṣẹ́ ìdánwò, mi ò sì fi ẹ̀ ṣe.",
        "reconcile_done": "Ìṣọ̀kan ti parí.",
        "fallback": "Mo lè ràn ọ́ lọ́wọ́ fún ọ̀sẹ̀, ìforígbárí, ètò tàbí kalẹ́ndà. Kò yí láìsí ìfọwọ́sí.",
        "switched": "Èdè: {name}. Òtítọ́ dúró bí ó ṣe wà.",
    },
    "sw": {
        "week_intro": "Hivi ndivyo vilivyobaki katika siku 14 zijazo.",
        "conflict": "Kuna mgongano wa tarehe. TermPilot hataabiri.",
        "no_obligations": "Bado hakuna wajibu uliopatanishwa.",
        "move_partial": "Jumatano ina dakika {free} tu, kazi inahitaji takriban {need}. Naweza kugawanya. Ukague mpango?",
        "move_ok": "Jumatano ina muda wa kutosha. Kalenda haijabadilika.",
        "approve_prompt": "Napendekeza vipindi {n} kwenye Demo Calendar. Hakuna kilichobadilika. Kagua, idhinisha au ghairi?",
        "spoken_yes_blocked": "Ndiyo ya sauti haitoshi. Thibitisha kwenye skrini.",
        "low_confidence": "Sijasikia vizuri. Andika au hariri nakala.",
        "unsupported": "Lugha haipo kwenye orodha. Ninaendelea kwa Kiingereza.",
        "blocked": "Ninaandaa kazi. Sifanyi kazi za alama wala kujifanya wewe.",
        "reconcile_done": "Upananishaji umekamilika.",
        "fallback": "Naweza kusaidia wiki, migongano, mpango au kalenda. Hakuna mabadiliko bila idhini.",
        "switched": "Lugha: {name}. Ukweli unabaki pale palipo.",
    },
    "ha": {
        "week_intro": "Ga abin da ya rage a cikin kwanaki 14 masu zuwa.",
        "conflict": "Akwai sabani na kwanan ƙarshe. TermPilot ba zai yi hasashe ba.",
        "no_obligations": "Babu hakki da aka daidaita tukuna.",
        "move_partial": "Laraba tana da mintuna {free} kawai, aikin yana buƙatar kusan {need}. Zan iya raba shi. A duba shirin?",
        "move_ok": "Laraba tana da isasshen lokaci. Ba a canza kalanda ba.",
        "approve_prompt": "Ina ba da shawarar zaman karatu {n} a Demo Calendar. Ba a canza komai ba. A duba, amince ko soke?",
        "spoken_yes_blocked": "I na magana bai isa ba. Tabbatar a allon.",
        "low_confidence": "Ban ji da kyau ba. Rubuta ko gyara rubutu.",
        "unsupported": "Harshen bai cikin rajista ba. Zan ci gaba da Turanci.",
        "blocked": "Ina tsara aiki. Ba na yin aikin maki kuma ba na yin kama da kai.",
        "reconcile_done": "Daidaitawa ta ƙare.",
        "fallback": "Zan iya taimakawa da mako, sabani, shiri ko kalanda. Babu canji ba tare da amincewa ba.",
        "switched": "Harshe: {name}. Gaskiya ta tsaya yadda take.",
    },
    "cs": {
        "week_intro": "Toto zbývá dokončit v příštích 14 dnech.",
        "conflict": "Existuje nevyřešený konflikt termínu. TermPilot nebude hádat.",
        "no_obligations": "Zatím žádné sladěné povinnosti.",
        "move_partial": "Středa má jen {free} volných minut, úkol potřebuje asi {need}. Mohu ho rozdělit. Zkontrolovat plán?",
        "move_ok": "Středa má dost času. Kalendář beze změny.",
        "approve_prompt": "Navrhuji {n} studijních bloků v Demo Calendar. Nic se nezměnilo. Zkontrolovat, schválit nebo zrušit?",
        "spoken_yes_blocked": "Vyřčené ano nestačí. Potvrďte na obrazovce.",
        "low_confidence": "Neslyšel jsem to jistě. Napište nebo upravte přepis.",
        "unsupported": "Tento jazyk není v Grok Voice. Pokračuji anglicky; fakta beze změny.",
        "blocked": "Organizuji práci. Neplním hodnocené úkoly a nikoho nenapodobuji.",
        "reconcile_done": "Sladění dokončeno.",
        "fallback": "Pomohu s týdnem, konflikty, plánem nebo kalendářem. Nic bez schválení.",
        "switched": "Jazyk: {name}. Fakta zůstávají původní.",
    },
    "da": {
        "week_intro": "Dette mangler i de næste 14 dage.",
        "conflict": "Der er en uløst fristkonflikt. TermPilot gætter ikke.",
        "no_obligations": "Ingen afstemte forpligtelser endnu.",
        "move_partial": "Onsdag har kun {free} ledige minutter; opgaven kræver ca. {need}. Jeg kan dele den. Se planen?",
        "move_ok": "Onsdag har tid nok. Kalenderen er uændret.",
        "approve_prompt": "Jeg foreslår {n} studieblokke i Demo Calendar. Intet er ændret. Gennemgå, godkend eller annullér?",
        "spoken_yes_blocked": "Et talt ja er ikke nok. Bekræft på skærmen.",
        "low_confidence": "Jeg hørte det usikkert. Skriv eller rediger transskriptionen.",
        "unsupported": "Sproget er ikke i Grok Voice. Jeg fortsætter på engelsk.",
        "blocked": "Jeg organiserer arbejde. Jeg laver ikke bedømt arbejde og udgiver mig ikke for at være dig.",
        "reconcile_done": "Afstemning færdig.",
        "fallback": "Jeg kan hjælpe med ugen, konflikter, planen eller kalenderen. Intet uden godkendelse.",
        "switched": "Sprog: {name}. Fakta forbliver originale.",
    },
    "id": {
        "week_intro": "Ini yang masih harus diselesaikan dalam 14 hari ke depan.",
        "conflict": "Ada konflik tenggat yang belum selesai. TermPilot tidak menebak.",
        "no_obligations": "Belum ada kewajiban yang direkonsiliasi.",
        "move_partial": "Rabu hanya punya {free} menit luang; tugas butuh sekitar {need}. Saya bisa membagi. Tinjau rencana?",
        "move_ok": "Rabu punya cukup waktu. Kalender belum diubah.",
        "approve_prompt": "Saya mengusulkan {n} sesi di Demo Calendar. Belum ada perubahan. Tinjau, setujui, atau batalkan?",
        "spoken_yes_blocked": "Ucapan ya tidak cukup. Konfirmasi di layar.",
        "low_confidence": "Saya tidak yakin mendengarnya. Ketik atau sunting transkrip.",
        "unsupported": "Bahasa ini tidak ada di Grok Voice. Saya lanjut dalam bahasa Inggris.",
        "blocked": "Saya mengatur pekerjaan. Saya tidak mengerjakan tugas dinilai atau menyamar sebagai Anda.",
        "reconcile_done": "Rekonsiliasi selesai.",
        "fallback": "Saya bisa membantu minggu ini, konflik, rencana, atau kalender. Tidak ada perubahan tanpa persetujuan.",
        "switched": "Bahasa: {name}. Fakta tetap asli.",
    },
    "ms": {
        "week_intro": "Ini yang masih perlu disiapkan dalam 14 hari akan datang.",
        "conflict": "Terdapat konflik tarikh akhir. TermPilot tidak meneka.",
        "no_obligations": "Belum ada kewajipan yang didamaikan.",
        "move_partial": "Rabu hanya ada {free} minit lapang; tugas perlu kira-kira {need}. Saya boleh bahagi. Semak rancangan?",
        "move_ok": "Rabu ada masa mencukupi. Kalendar tidak diubah.",
        "approve_prompt": "Saya cadangkan {n} sesi dalam Demo Calendar. Tiada perubahan. Semak, lulus atau batal?",
        "spoken_yes_blocked": "Ya yang ditutur tidak mencukupi. Sahkan di skrin.",
        "low_confidence": "Saya tidak pasti apa yang didengar. Taip atau sunting transkrip.",
        "unsupported": "Bahasa ini tiada dalam Grok Voice. Saya terus dalam bahasa Inggeris.",
        "blocked": "Saya menyusun kerja. Saya tidak menyiapkan kerja dinilai atau menyamar sebagai anda.",
        "reconcile_done": "Pendamaian selesai.",
        "fallback": "Saya boleh bantu minggu, konflik, rancangan atau kalendar. Tiada perubahan tanpa kelulusan.",
        "switched": "Bahasa: {name}. Fakta kekal asal.",
    },
    "fa": {
        "week_intro": "این کارها در ۱۴ روز آینده باقی است.",
        "conflict": "تعارض مهلت حل‌نشده وجود دارد. TermPilot حدس نمی‌زند.",
        "no_obligations": "هنوز تعهد تطبیق‌شده‌ای نیست.",
        "move_partial": "چهارشنبه فقط {free} دقیقه آزاد دارد؛ کار حدود {need} دقیقه می‌خواهد. می‌توانم تقسیم کنم. برنامه را ببینید؟",
        "move_ok": "چهارشنبه وقت کافی دارد. تقویم تغییر نکرده است.",
        "approve_prompt": "پیشنهاد {n} جلسه در Demo Calendar. هنوز تغییری نیست. بررسی، تأیید یا لغو؟",
        "spoken_yes_blocked": "بلهٔ گفتاری کافی نیست. روی صفحه تأیید کنید.",
        "low_confidence": "مطمئن نشنیدم. بنویسید یا رونوشت را ویرایش کنید.",
        "unsupported": "این زبان در Grok Voice نیست. به انگلیسی ادامه می‌دهم.",
        "blocked": "کار را سازمان می‌دهم. تکلیف نمره‌دار را انجام نمی‌دهم و جای شما را نمی‌گیرم.",
        "reconcile_done": "تطبیق تمام شد.",
        "fallback": "می‌توانم برای هفته، تعارض، برنامه یا تقویم کمک کنم. بدون تأیید چیزی عوض نمی‌شود.",
        "switched": "زبان: {name}. واقعیت‌ها اصلی می‌مانند.",
    },
    "ru": {
        "week_intro": "Вот что осталось сделать за следующие 14 дней.",
        "conflict": "Есть неразрешённый конфликт срока. TermPilot не будет угадывать.",
        "no_obligations": "Пока нет сверенных обязательств.",
        "move_partial": "В среду только {free} свободных минут, задаче нужно около {need}. Могу разделить. Просмотреть план?",
        "move_ok": "В среду достаточно времени. Календарь не изменён.",
        "approve_prompt": "Предлагаю {n} занятий в Demo Calendar. Ничего не изменено. Просмотреть, утвердить или отменить?",
        "spoken_yes_blocked": "Произнесённого «да» недостаточно. Подтвердите на экране.",
        "low_confidence": "Не уверен, что расслышал. Введите или правьте расшифровку.",
        "unsupported": "Этого языка нет в Grok Voice. Продолжаю на английском.",
        "blocked": "Я организую работу. Не выполняю оцениваемые задания и не выдаю себя за вас.",
        "reconcile_done": "Сверка завершена.",
        "fallback": "Могу помочь с неделей, конфликтами, планом или календарём. Без одобрения ничего не меняется.",
        "switched": "Язык: {name}. Факты остаются исходными.",
    },
    "sv": {
        "week_intro": "Detta återstår de kommande 14 dagarna.",
        "conflict": "Det finns en olöst deadlinekonflikt. TermPilot gissar inte.",
        "no_obligations": "Inga avstämda åtaganden ännu.",
        "move_partial": "Onsdag har bara {free} lediga minuter; uppgiften behöver ca {need}. Jag kan dela upp den. Granska planen?",
        "move_ok": "Onsdag har tillräckligt med tid. Kalendern är oförändrad.",
        "approve_prompt": "Jag föreslår {n} studiepass i Demo Calendar. Inget har ändrats. Granska, godkänn eller avbryt?",
        "spoken_yes_blocked": "Ett talat ja räcker inte. Bekräfta på skärmen.",
        "low_confidence": "Jag hörde osäkert. Skriv eller redigera transkriptionen.",
        "unsupported": "Språket finns inte i Grok Voice. Jag fortsätter på engelska.",
        "blocked": "Jag organiserar arbete. Jag gör inte bedömt arbete och utger mig inte för att vara du.",
        "reconcile_done": "Avstämningen är klar.",
        "fallback": "Jag kan hjälpa med veckan, konflikter, planen eller kalendern. Inget utan godkännande.",
        "switched": "Språk: {name}. Fakta förblir original.",
    },
    "th": {
        "week_intro": "งานที่เหลือใน 14 วันข้างหน้ามีดังนี้",
        "conflict": "มีกำหนดส่งที่ขัดกัน TermPilot จะไม่เดา",
        "no_obligations": "ยังไม่มีภาระที่กระทบยอด",
        "move_partial": "วันพุธว่างเพียง {free} นาที งานนี้ใช้ประมาณ {need} นาที แยกได้ สดูแผนไหม",
        "move_ok": "วันพุธมีเวลาพอ ปฏิทินยังไม่เปลี่ยน",
        "approve_prompt": "เสนอ {n} ช่วงเรียนใน Demo Calendar ยังไม่มีการเปลี่ยน ตรวจ อนุมัติ หรือยกเลิก?",
        "spoken_yes_blocked": "คำว่า ใช่ ที่พูดยังไม่พอ ยืนยันบนหน้าจอ",
        "low_confidence": "ฟังไม่ชัด พิมพ์หรือแก้บทถอดความ",
        "unsupported": "ภาษานี้ไม่อยู่ใน Grok Voice จะใช้ภาษาอังกฤษต่อ ข้อเท็จจริงไม่เปลี่ยน",
        "blocked": "ฉันจัดงาน ไม่ทำงานที่คิดคะแนนแทนคุณ และไม่ปลอมเป็นคุณ",
        "reconcile_done": "กระทบยอดเสร็จแล้ว",
        "fallback": "ช่วยเรื่องสัปดาห์ ความขัดแย้ง แผน หรือปฏิทินได้ ไม่เปลี่ยนโดยไม่ได้รับอนุมัติ",
        "switched": "ภาษา: {name} ข้อเท็จจริงคงเดิม",
    },
    "tr": {
        "week_intro": "Önümüzdeki 14 günde bitmesi gerekenler bunlar.",
        "conflict": "Çözülmemiş bir son tarih çatışması var. TermPilot tahmin etmez.",
        "no_obligations": "Henüz uzlaştırılmış yükümlülük yok.",
        "move_partial": "Çarşamba yalnızca {free} boş dakikaya sahip; iş yaklaşık {need} dakika. Bölebilirim. Planı inceler misiniz?",
        "move_ok": "Çarşamba yeterli zamanı var. Takvim değişmedi.",
        "approve_prompt": "Demo Calendar içinde {n} çalışma bloğu öneriyorum. Hiçbir şey değişmedi. İncele, onayla veya iptal et?",
        "spoken_yes_blocked": "Söylenen evet yetmez. Ekranda onaylayın.",
        "low_confidence": "Emin duyamadım. Yazın veya dökümü düzeltin.",
        "unsupported": "Bu dil Grok Voice’ta yok. İngilizceye devam ediyorum.",
        "blocked": "İşi düzenlerim. Notlandırılan ödevi yapmam ve sizin yerinize geçmem.",
        "reconcile_done": "Uzlaştırma bitti.",
        "fallback": "Hafta, çatışmalar, plan veya takvim için yardımcı olabilirim. Onaysız değişiklik yok.",
        "switched": "Dil: {name}. Olgular orijinal kalır.",
    },
    "vi": {
        "week_intro": "Đây là việc còn lại trong 14 ngày tới.",
        "conflict": "Có xung đột hạn chót chưa giải quyết. TermPilot không đoán.",
        "no_obligations": "Chưa có nghĩa vụ đã đối chiếu.",
        "move_partial": "Thứ Tư chỉ còn {free} phút trống; việc cần khoảng {need}. Tôi có thể tách. Xem kế hoạch?",
        "move_ok": "Thứ Tư đủ thời gian. Lịch chưa đổi.",
        "approve_prompt": "Tôi đề xuất {n} phiên trên Demo Calendar. Chưa thay đổi. Xem, duyệt hay hủy?",
        "spoken_yes_blocked": "Lời nói có chưa đủ. Xác nhận trên màn hình.",
        "low_confidence": "Tôi nghe chưa chắc. Hãy gõ hoặc sửa bản ghi.",
        "unsupported": "Ngôn ngữ này không có trong Grok Voice. Tôi tiếp tục bằng tiếng Anh.",
        "blocked": "Tôi sắp xếp việc. Không làm bài được chấm điểm hộ bạn và không giả danh bạn.",
        "reconcile_done": "Đối chiếu xong.",
        "fallback": "Tôi có thể giúp tuần này, xung đột, kế hoạch hoặc lịch. Không đổi nếu chưa duyệt.",
        "switched": "Ngôn ngữ: {name}. Sự kiện giữ nguyên.",
    },
    "mk": {
        "week_intro": "Ова останува за следните 14 дена.",
        "conflict": "Има нерешен конфликт на рок. TermPilot не погаѓа.",
        "no_obligations": "Сè уште нема усогласени обврски.",
        "move_partial": "Среда има само {free} слободни минути; задачата бара околу {need}. Можам да ја поделам. Да го видиме планот?",
        "move_ok": "Среда има доволно време. Календарот е непроменет.",
        "approve_prompt": "Предлагам {n} сесии во Demo Calendar. Ништо не е променето. Преглед, одобрување или откажување?",
        "spoken_yes_blocked": "Изговореното да не е доволно. Потврдете на екранот.",
        "low_confidence": "Не сум сигурен што слушнав. Напишете или поправете го записот.",
        "unsupported": "Овој јазик не е во Grok Voice. Продолжувам на англиски.",
        "blocked": "Организирам работа. Не завршувам оценувана работа и не се претставувам како вас.",
        "reconcile_done": "Усогласувањето е завршено.",
        "fallback": "Можам да помогнам со неделата, конфликти, план или календар. Ништо без одобрување.",
        "switched": "Јазик: {name}. Фактите остануваат изворни.",
    },
}


def registry() -> list[dict[str, Any]]:
    return LANGUAGE_REGISTRY


def detect_language(text: str, selected: str = "auto") -> tuple[str, bool]:
    known = {row["code"] for row in LANGUAGE_REGISTRY}
    if selected in known:
        return selected, False
    tokens = set(re.findall(r"[a-záéíóúüñäö]+", text.lower()))
    nl_hits = len(tokens & _NL_HINTS)
    es_hits = len(tokens & _ES_HINTS)
    if nl_hits >= 2 and nl_hits >= es_hits:
        return "nl", True
    if es_hits >= 2 and es_hits > nl_hits:
        return "es", True
    if tokens & {"qué", "miércoles", "semana"}:
        return "es", True
    if tokens & {"woensdag", "dinsdag", "afmaken"}:
        return "nl", True
    return "en", True


def _t(lang: str, key: str, **kwargs: Any) -> str:
    table = _STRINGS.get(lang) or _STRINGS["en"]
    template = table.get(key) or _STRINGS["en"][key]
    return template.format(**kwargs)


def classify_intent(text: str) -> str:
    lowered = text.lower()
    if inspect_user_goal(text).decision.value == "block":
        return "blocked"
    grok_tool = classify_tool(lowered)
    if grok_tool:
        return grok_tool
    if any(
        w in lowered
        for w in ("english", "español", "spanish", "nederlands", "dutch", "in dutch", "en español")
    ):
        return "switch_language"
    if any(w in lowered for w in ("reconcile", "reconcil", "14 days", "14 dagen", "próximos 14")):
        return "reconcile"
    if (
        re.search(r"\b(yes|ja|sí|approve|aprobar)\b", lowered)
        and len(lowered.split()) <= 3
        and "approval" not in lowered
    ):
        return "spoken_confirm"
    if any(
        w in lowered
        for w in ("move", "verplaats", "mueve", "wednesday", "woensdag", "miércoles", "miercoles")
    ):
        return "reschedule"
    if any(w in lowered for w in ("show calendar", "open calendar", "kalender", "calendario")):
        return "open_calendar"
    if any(w in lowered for w in ("show conflict", "open conflict")):
        return "open_conflicts"
    if any(w in lowered for w in ("show approval", "open approval")):
        return "open_approvals"
    if any(
        w in lowered
        for w in (
            "overwhelmed",
            "stressed",
            "anxious",
            "struggling",
            "tired",
            "can't cope",
            "too much",
        )
    ):
        return "support"
    if any(
        w in lowered
        for w in (
            "newsfeed",
            "news feed",
            "show news",
            "open news",
            "rss",
            "reddit",
            "government news",
            "student union",
            "student support",
            "international student",
            "wellbeing",
            "well-being",
            "careers",
            "career service",
        )
    ):
        return "open_news"
    if any(
        w in lowered
        for w in (
            "clean inbox",
            "clean my inbox",
            "clean my mail",
            "archive clutter",
            "declutter",
            "cleanup mail",
            "clean up my inbox",
        )
    ):
        return "mailbox_cleanup"
    if any(w in lowered for w in ("mail alert", "email alert", "urgent mail", "p0")):
        return "mailbox_alerts"
    if any(
        w in lowered
        for w in (
            "draft email",
            "draft an email",
            "draft a mail",
            "send email",
            "email my tutor",
            "write an email",
        )
    ):
        return "mailbox_draft"
    if any(w in lowered for w in ("check email", "inbox", "mailbox", "my mail")):
        return "email"
    if any(
        w in lowered
        for w in ("this week", "deze week", "esta semana", "finish", "afmaken", "terminar", "need")
    ):
        return "week"
    if any(w in lowered for w in ("conflict", "conflicto", "deadline")):
        return "conflict"
    return "ask"


async def handle_turn(
    session: AsyncSession,
    user_id: str,
    text: str,
    *,
    language: str = "auto",
    transcript_confidence: float = 1.0,
    source: str = "typed",
) -> dict[str, Any]:
    unsupported = False
    lang, auto = detect_language(text, language)
    known = {row["code"] for row in LANGUAGE_REGISTRY}
    if language not in {"auto"} | known:
        unsupported = True
        lang = "en"

    if transcript_confidence < CONFIDENCE_THRESHOLD and source == "voice":
        turn = await _store(
            session,
            user_id,
            lang,
            source,
            text,
            transcript_confidence,
            "clarify",
            _t(lang, "low_confidence"),
            {"action": "none"},
            True,
        )
        return _out(turn, auto, unsupported)

    text, policy = apply_student_policies(text)
    if policy.get("blocked"):
        turn = await _store(
            session,
            user_id,
            lang,
            source,
            text,
            transcript_confidence,
            "blocked",
            str(policy.get("summary") or _t(lang, "blocked")),
            policy,
            True,
        )
        return _out(turn, auto, unsupported)

    intent = classify_intent(text)
    facts: dict[str, Any] = {}
    requires_screen = False
    spoken = _t(lang, "fallback")
    # facts always defined before coaching merge.

    if intent == "blocked":
        spoken = _t(lang, "blocked")
        requires_screen = True
    elif intent == "switch_language":
        lowered = text.lower()
        if "neder" in lowered or "dutch" in lowered:
            lang = "nl"
        elif "espan" in lowered or "español" in lowered or "spanish" in lowered:
            lang = "es"
        else:
            lang = "en"
        name = next(r["display_name"] for r in LANGUAGE_REGISTRY if r["code"] == lang)
        spoken = _t(lang, "switched", name=name)
        facts = {"language": lang}
    elif intent == "week":
        spoken, facts = await _week_answer(session, user_id, lang)
    elif intent == "support":
        spoken, facts = await _week_answer(session, user_id, lang)
        spoken = (
            "That load is real — conflicting deadlines and a finite week would strain anyone. "
            "I will not guess how you feel medically. Here is the next concrete step.\n\n"
        ) + spoken
        facts["open_view"] = "conflicts" if facts.get("open_conflict") else "tower"
    elif intent == "email":
        spoken, facts = await _email_answer(session, user_id, lang)
    elif intent == "open_calendar":
        spoken, facts = await _week_answer(session, user_id, lang)
        facts["open_view"] = "calendar"
        spoken = spoken + "\nOpening the calendar panel."
    elif intent == "open_conflicts":
        spoken, facts = await _conflict_answer(session, user_id, lang)
        facts["open_view"] = "conflicts"
    elif intent == "open_approvals":
        spoken = _t(lang, "approve_prompt", n=0)
        facts = {"open_view": "approvals"}
        requires_screen = True
    elif intent == "open_news":
        spoken = (
            "Opening the student-life newsfeed. Public RSS, Reddit and government sources are live. "
            "University notices come only from the linked university mailbox — I do not scrape the portal, "
            "and I do not speak as the dean or the union. "
            "If you need crisis help, Samaritans is 116 123. I am not a counsellor."
        )
        facts = {"open_view": "news", "action": "signpost"}
    elif intent == "mailbox_cleanup":
        spoken, facts = await _mailbox_cleanup_answer(session, user_id)
    elif intent == "mailbox_alerts":
        spoken, facts = await _mailbox_alert_answer(session, user_id)
    elif intent == "mailbox_draft":
        spoken, facts = await _mailbox_draft_answer(session, user_id, lang)
        requires_screen = True
    elif intent == "conflict":
        spoken, facts = await _conflict_answer(session, user_id, lang)
    elif intent == "reschedule":
        spoken, facts, requires_screen = await _reschedule_answer(session, user_id, lang)
    elif intent == "spoken_confirm":
        spoken = _t(lang, "spoken_yes_blocked")
        requires_screen = True
        facts = {"action": "none", "reason": "spoken_yes_insufficient"}
    elif intent == "reconcile":
        spoken = _t(lang, "reconcile_done")
        facts = {"handoff": "orchestrator", "open_view": "conflicts"}
        requires_screen = True
    elif intent in {row["id"] for row in STUDENT_TOOLS}:
        spoken, facts, requires_screen = await execute_tool(session, user_id, intent, text)
    else:
        spoken, facts, requires_screen = await answer_with_policies(session, user_id, text)
    facts = await _with_coaching(
        session,
        user_id,
        {
            **facts,
            "engine": "grok_bot",
            "policy": policy.get("policy", facts.get("policy")),
            "blocked": False,
            "writes": False,
            **(
                {"injection_stripped": policy["injection_stripped"]}
                if policy.get("injection_stripped")
                else {}
            ),
        },
    )

    if unsupported:
        spoken = _t("en", "unsupported") + " " + spoken

    turn = await _store(
        session,
        user_id,
        lang,
        source,
        text,
        transcript_confidence,
        intent,
        spoken,
        facts,
        requires_screen,
    )
    return _out(turn, auto, unsupported)


async def _email_answer(
    session: AsyncSession, user_id: str, lang: str
) -> tuple[str, dict[str, Any]]:
    mailbox = await get_connection(session, user_id, "src_mailbox")
    email = await get_connection(session, user_id, "src_email")
    granted = any(c is not None and c.permission_state == "granted" for c in (mailbox, email))
    if not granted:
        return (
            "I can only read mail you have authorised. Connect the student mailbox or forwarded mail first. "
            "I will not guess the inbox.",
            {"open_view": "sources", "mail_authorised": False},
        )
    observations = (
        (
            await session.execute(
                select(SourceObservation).where(
                    SourceObservation.user_id == user_id,
                    SourceObservation.source_type.in_(("email", "mailbox")),
                )
            )
        )
        .scalars()
        .all()
    )
    excerpts = [
        {"source": o.source_type, "excerpt": o.excerpt, "observed_at": o.observed_at.isoformat()}
        for o in observations
    ]
    spoken, facts = await _week_answer(session, user_id, lang)
    facts["mail_authorised"] = True
    facts["mail"] = excerpts
    facts["open_view"] = "mailbox"
    return (
        "Authorised mail only — no hidden monitoring. Opening the mailbox desk.\n"
        + "\n".join(f"- {m['source']}: {m['excerpt'][:160]}" for m in excerpts[:5])
        + "\n\n"
        + spoken,
        facts,
    )


async def _mailbox_alert_answer(session: AsyncSession, user_id: str) -> tuple[str, dict[str, Any]]:
    from app.policies.consent import ConsentError
    from app.services.mailbox import mailbox_desk

    try:
        desk = await mailbox_desk(session, user_id)
    except ConsentError:
        return (
            "Connect the university mailbox first. I will not guess the inbox.",
            {"open_view": "sources", "mail_authorised": False},
        )
    alerts = desk["alerts"]
    lines = "\n".join(f"- P0 {item['subject']}" for item in alerts) or "No P0 alerts."
    return (
        "Priority hierarchy: P0 alerts first, then P1 university mail. "
        "I do not send until you approve on screen.\n" + lines,
        {"open_view": "mailbox", "alerts": alerts, "hierarchy": desk["hierarchy"]},
    )


async def _mailbox_cleanup_answer(
    session: AsyncSession, user_id: str
) -> tuple[str, dict[str, Any]]:
    from app.policies.consent import ConsentError
    from app.services.mailbox import cleanup_mailbox

    try:
        result = await cleanup_mailbox(session, user_id)
    except ConsentError:
        return (
            "Connect authorised mail first. I will not clean an inbox I cannot see.",
            {"open_view": "sources", "mail_authorised": False},
        )
    return (
        f"Archived {result['counts']['archived_now']} clutter messages (P2/P3). "
        f"Kept {result['counts']['kept_p0_p1']} deadline and university messages. "
        "Nothing was sent.",
        {"open_view": "mailbox", **result},
    )


async def _mailbox_draft_answer(
    session: AsyncSession, user_id: str, lang: str
) -> tuple[str, dict[str, Any]]:
    del lang
    from app.policies.consent import ConsentError
    from app.services.mailbox import draft_from_item, mailbox_desk

    try:
        desk = await mailbox_desk(session, user_id)
    except ConsentError:
        return (
            "Connect authorised mail first.",
            {"open_view": "sources", "mail_authorised": False},
        )
    target = next(
        (item for item in desk["items"] if item["priority"] == "p0" and item["state"] == "inbox"),
        None,
    )
    if target is None:
        return (
            "No P0 mail needs a draft. I will not invent a recipient.",
            {"open_view": "mailbox", "action": "none"},
        )
    try:
        drafted = await draft_from_item(session, user_id, target["id"])
    except ConsentError as exc:
        return (
            "I can draft only after the student mailbox is connected. "
            "Even then the message stays unsent until you approve it on screen. "
            f"({exc.code})",
            {"open_view": "mailbox", "can_send": False, "mail_id": target["id"]},
        )
    return (
        f"Drafted a reply to {target['from']} about {target['subject']}. "
        "It is in the demo outbox and not sent. Approve it on screen — spoken yes is not enough.",
        {"open_view": "mailbox", **drafted},
    )


async def _with_coaching(
    session: AsyncSession, user_id: str, facts: dict[str, Any]
) -> dict[str, Any]:
    obligations = (
        (await session.execute(select(Obligation).where(Obligation.user_id == user_id)))
        .scalars()
        .all()
    )
    conflicts = (
        (
            await session.execute(
                select(ConflictingClaim).where(
                    ConflictingClaim.user_id == user_id, ConflictingClaim.resolution.is_(None)
                )
            )
        )
        .scalars()
        .all()
    )
    pending = (
        (
            await session.execute(
                select(ApprovalRequest).where(
                    ApprovalRequest.user_id == user_id,
                    ApprovalRequest.state == "pending",
                )
            )
        )
        .scalars()
        .all()
    )
    minutes = sum(o.estimated_minutes for o in obligations)
    earliest = min((o.due_at for o in obligations if o.due_at), default=None)
    facts["five_w"] = {
        "who": "FAVL (Frank Van Laarhoven)",
        "what": [o.title for o in obligations] or ["no reconciled obligations yet"],
        "when": earliest.isoformat() if earliest else None,
        "where": sorted({o.course_or_context for o in obligations}) or ["unknown"],
        "why": "Keep assessed and recruiting work from becoming a surprise, without completing homework.",
        "how": "Scout extracts, Verifier escalates conflicts, Planner uses CP-SAT, Guardian requires approval.",
    }
    facts["swot"] = {
        "strengths": ["Authorised sources", "Provenance on every claim", "Human approval gate"],
        "weaknesses": ["Material deadline still unresolved"]
        if conflicts
        else ["No live LMS OAuth in the MVP"],
        "opportunities": ["14-day recovery plan", "Clarification draft ready"],
        "threats": ["Conflicting instructions", "20-hour weekly cap", "Saturday work shift"],
    }
    facts["gap"] = {
        "needed_minutes": minutes,
        "weekly_limit_minutes": 20 * 60,
        "open_conflicts": len(conflicts),
        "note": "Gap is hours and decisions, not ability. TermPilot does not score academic talent.",
    }
    facts["kpi"] = {
        "verified_obligations": sum(1 for o in obligations if o.verification_state == "verified"),
        "open_conflicts": len(conflicts),
        "pending_approvals": len(pending),
        "kind": "demo",
    }
    facts["smart"] = {
        "specific": "Resolve the Control Systems Problem Set deadline or keep it explicitly unresolved.",
        "measurable": "Zero silent deadline guesses; one recorded student decision.",
        "achievable": "Uses only authorised time and the 20-hour cap.",
        "relevant": "Stops a surprise deadline this fortnight.",
        "time_bound": "Before the earlier claimed due date, if one exists.",
    }
    facts["empathy"] = {
        "stance": "Workload pressure is treated as a scheduling fact, not a diagnosis.",
        "note": "I will not infer health, disability, nationality or ability from language or tone.",
    }
    facts.setdefault("open_view", facts.get("open_view"))
    return facts


async def _week_answer(
    session: AsyncSession, user_id: str, lang: str
) -> tuple[str, dict[str, Any]]:
    obligations = (
        (await session.execute(select(Obligation).where(Obligation.user_id == user_id)))
        .scalars()
        .all()
    )
    if not obligations:
        return _t(lang, "no_obligations"), {"obligations": []}
    conflict = (
        (
            await session.execute(
                select(ConflictingClaim).where(
                    ConflictingClaim.user_id == user_id, ConflictingClaim.resolution.is_(None)
                )
            )
        )
        .scalars()
        .first()
    )
    items = [
        {
            "title": o.title,
            "course_or_context": o.course_or_context,
            "due_at": o.due_at.isoformat() if o.due_at else None,
            "verification_state": o.verification_state,
            "priority": o.priority,
        }
        for o in obligations
    ]
    lines = [_t(lang, "week_intro")]
    for item in items:
        due = item["due_at"] or "needs_review"
        lines.append(
            f"- {item['course_or_context']} {item['title']} · {due} · {item['verification_state']}"
        )
    if conflict:
        lines.append(_t(lang, "conflict"))
    return "\n".join(lines), {"obligations": items, "open_conflict": bool(conflict)}


async def _conflict_answer(
    session: AsyncSession, user_id: str, lang: str
) -> tuple[str, dict[str, Any]]:
    conflict = (
        (
            await session.execute(
                select(ConflictingClaim).where(
                    ConflictingClaim.user_id == user_id, ConflictingClaim.resolution.is_(None)
                )
            )
        )
        .scalars()
        .first()
    )
    if conflict is None:
        return _t(lang, "week_intro"), {"open_conflict": False}
    return _t(lang, "conflict"), {
        "open_conflict": True,
        "field": conflict.field_name,
        "obligation_id": conflict.obligation_id,
    }


async def _reschedule_answer(
    session: AsyncSession, user_id: str, lang: str
) -> tuple[str, dict[str, Any], bool]:
    plan = (
        (
            await session.execute(
                select(Plan).where(Plan.user_id == user_id).order_by(Plan.created_at.desc())
            )
        )
        .scalars()
        .first()
    )
    if plan is None:
        return _t(lang, "no_obligations"), {}, True
    blocks = (
        (await session.execute(select(PlanBlock).where(PlanBlock.plan_id == plan.id)))
        .scalars()
        .all()
    )
    tue = [b for b in blocks if b.start_at.weekday() == 1 and b.kind == "study"]
    wed_busy = sum(
        int((b.end_at - b.start_at).total_seconds() // 60)
        for b in blocks
        if b.start_at.weekday() == 2
    )
    # Preferable evening window 19:00-22:00 = 180 minutes minus busy evening overlap.
    free = max(0, 180 - min(wed_busy, 180))
    need = 90
    if tue:
        need = max(
            90,
            int((tue[0].end_at - tue[0].start_at).total_seconds() // 60),
        )
    facts = {
        "requested": "move_tuesday_study_to_wednesday",
        "free_minutes_wednesday_evening": free,
        "needed_minutes": need,
        "calendar_changed": False,
    }
    if free < need:
        return _t(lang, "move_partial", free=free, need=need), facts, True
    return _t(lang, "move_ok"), facts, True


async def approval_voice_prompt(session: AsyncSession, user_id: str, lang: str) -> dict[str, Any]:
    pending = (
        (
            await session.execute(
                select(ApprovalRequest).where(
                    ApprovalRequest.user_id == user_id,
                    ApprovalRequest.state == ApprovalState.PENDING.value,
                )
            )
        )
        .scalars()
        .all()
    )
    n = 0
    if pending:
        n = len(pending[0].diff_json.get("create") or [])
    text = _t(lang, "approve_prompt", n=n)
    return {"spoken_text": text, "display_text": text, "count": n, "requires_on_screen": True}


async def _store(
    session: AsyncSession,
    user_id: str,
    lang: str,
    source: str,
    transcript: str,
    confidence: float,
    intent: str,
    spoken: str,
    facts: dict[str, Any],
    requires_screen: bool,
) -> VoiceTurn:
    turn = VoiceTurn(
        id=new_id("vce"),
        user_id=user_id,
        language=lang,
        source=source,
        transcript=transcript[:2000],
        transcript_confidence=confidence,
        intent=intent,
        spoken_text=spoken,
        display_text=spoken,
        facts_json=facts,
        requires_on_screen=requires_screen,
        audio_retained=False,
        created_at=clock.now(),
    )
    session.add(turn)
    await record_audit(
        session,
        user_id=user_id,
        correlation_id=turn.id,
        agent=AgentName.ORCHESTRATOR.value,
        event_type="voicebridge_turn",
        object_type="voice_turn",
        object_id=turn.id,
        confidence=confidence,
        summary=f"{lang} {intent} audio_retained=false",
    )
    return turn


def _out(turn: VoiceTurn, auto: bool, unsupported: bool) -> dict[str, Any]:
    return {
        "id": turn.id,
        "language": turn.language,
        "language_auto": auto,
        "unsupported_language": unsupported,
        "source": turn.source,
        "transcript": turn.transcript,
        "transcript_confidence": turn.transcript_confidence,
        "intent": turn.intent,
        "spoken_text": turn.spoken_text,
        "display_text": turn.display_text,
        "facts": turn.facts_json,
        "requires_on_screen": turn.requires_on_screen,
        "audio_retained": False,
        "bot": "orchestrator",
        "tts": {
            "provider": "xai" if get_settings().use_live_grok else "browser_fallback",
            "voice_id": "eve",
            "endpoint": "https://api.x.ai/v1/tts",
        },
        "stt": {
            "provider": "xai" if get_settings().use_live_grok else "browser_fallback",
            "endpoint": "https://api.x.ai/v1/stt",
        },
    }


async def list_turns(session: AsyncSession, user_id: str) -> list[dict[str, Any]]:
    rows = (
        (
            await session.execute(
                select(VoiceTurn)
                .where(VoiceTurn.user_id == user_id)
                .order_by(VoiceTurn.created_at.asc())
            )
        )
        .scalars()
        .all()
    )
    return [
        {
            "id": t.id,
            "language": t.language,
            "source": t.source,
            "transcript": t.transcript,
            "display_text": t.display_text,
            "intent": t.intent,
            "created_at": t.created_at.isoformat(),
            "audio_retained": t.audio_retained,
        }
        for t in rows
    ]


async def delete_transcripts(session: AsyncSession, user_id: str) -> dict[str, int]:
    existing = (
        (await session.execute(select(VoiceTurn.id).where(VoiceTurn.user_id == user_id)))
        .scalars()
        .all()
    )
    await session.execute(delete(VoiceTurn).where(VoiceTurn.user_id == user_id))
    await record_audit(
        session,
        user_id=user_id,
        correlation_id=new_id("vce"),
        event_type="voicebridge_transcripts_deleted",
        summary="Student deleted VoiceBridge transcripts. No audio was stored.",
    )
    return {"deleted": len(existing)}


async def transcribe_bytes(data: bytes, filename: str, language: str) -> dict[str, Any]:
    settings = get_settings()
    if not settings.use_live_grok or not settings.xai_api_key:
        return {
            "ok": False,
            "fallback": "browser",
            "reason": "XAI_API_KEY not configured. Use browser SpeechRecognition.",
        }
    import httpx

    files = {"file": (filename or "clip.webm", data)}
    form: dict[str, str] = {}
    if language in {"en", "es", "nl"}:
        form["language"] = language
        form["format"] = "true"
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{settings.xai_base_url}/stt",
            headers={"Authorization": f"Bearer {settings.xai_api_key}"},
            files=files,
            data=form,
        )
    if response.status_code >= 400:
        return {"ok": False, "fallback": "browser", "reason": f"stt_{response.status_code}"}
    payload = response.json()
    confidences = [
        w.get("confidence") or 0.0 for w in payload.get("words") or [] if isinstance(w, dict)
    ]
    mean = sum(confidences) / len(confidences) if confidences else 0.85
    return {
        "ok": True,
        "text": payload.get("text") or "",
        "language": payload.get("language") or language,
        "confidence": mean,
        "audio_retained": False,
    }


async def synthesise(text: str, language: str) -> dict[str, Any]:
    settings = get_settings()
    if not settings.use_live_grok or not settings.xai_api_key:
        return {"ok": False, "fallback": "browser", "reason": "XAI_API_KEY not configured."}
    import httpx

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{settings.xai_base_url}/tts",
            headers={
                "Authorization": f"Bearer {settings.xai_api_key}",
                "Content-Type": "application/json",
            },
            json={"text": text[:4000], "voice_id": "eve", "language": language},
        )
    if response.status_code >= 400:
        return {"ok": False, "fallback": "browser", "reason": f"tts_{response.status_code}"}
    return {
        "ok": True,
        "content_type": response.headers.get("content-type", "audio/mpeg"),
        "audio": response.content,
    }
