"""Messages the custom actions send, in English and Spanish.

The conversation language comes from Rasa's built-in `language` slot (set by the
website's language picker through the set_language flow). Responses defined in
domain.yml are translated there with Rasa's `translation:` blocks; everything an
action says comes from this table.
"""

from __future__ import annotations

from typing import Any

MESSAGES: dict[str, dict[str, str]] = {
    "en": {
        "welcome_back": "Welcome back! 🌸 Here’s what I can help with:\n• Find events this week. Try “What’s on this week?”\n• Search by type or place. Try “Find garden events” or “Events near Silverton”\n• Post your own event, or set a reminder for one you saved",
        "first_hello": "Hello, I’m glad you’re here. 🌸 Let’s find out what you enjoy.",
        "prefs_saved": "Thanks for sharing! I’ve saved your preferences so I can tailor ideas for you.",
        "guest_cannot_post": "To share an event, please create a free Bloom account first, so neighbors know who is hosting. Go to Settings, then “Create a free account”. I haven’t posted anything.",
        "missing_detail": "I’m missing a detail, so I haven’t posted it. We can try again when you’re ready.",
        "bad_datetime": "I couldn’t understand the date or time, so I haven’t posted it yet. Let’s try again. You can say something like “next Tuesday at 2 PM”.",
        "save_failed": "I’m sorry, something went wrong and your event was not posted. Please try again in a moment.",
        "posted": "Your event, {title}, is posted for {date} at {time}. 🎉 Neighbors can see it on Bloom right now. Thank you for bringing people together!",
        "not_posted": "No problem. I haven’t posted the event.",
        "date_unclear": "Sorry, I didn’t catch the date. You can say “this Saturday”, “November 20”, or “11/20”.",
        "date_past": "That date has already passed. What upcoming day will it be?",
        "confirm_unclear": "Sorry, I didn’t catch that. Please say “yes” to post your event, or “no” to cancel.",
        "skip_desc_ok": "No problem, I’ll leave the description blank.",
        "skip_required": "I need this one to continue. A few words is plenty, or say “cancel” to stop.",
        "time_unclear": "Sorry, I didn’t catch the time. You can say “2 PM”, “10:30 in the morning”, or “noon”.",
        "review_header": "Here’s what I have:",
        "label_event": "Event", "label_day": "Day", "label_time": "Time", "label_place": "Place",
        "label_host": "Host", "label_details": "Details",
        "none_optional": "None (optional)",
        "not_provided": "not provided",
        "found": "I found {n} local events. 🌸 Here are the {shown} that may fit you best. Every event is still listed in the Events tab, so nothing is hidden.",
        "found_near": "I found {near} events within {radius} miles of {place}. 📍 Here are the closest good matches. Everything else is still in the Events tab.",
        "found_near_one": "I found 1 event within {radius} miles of {place}. 📍 Here it is first, followed by the next closest. Everything else is still in the Events tab.",
        "nothing_near": "I don’t see events within {radius} miles of {place} yet. Bloom’s listings focus on the Salem area for now, so here are the nearest ones. 📍",
        "choose_more": "Choose an event to hear more:",
        "tell_about": "Tell me about {title}",
        "details": "{title} is on {date} at {time}, at {location}. {description} Would you like to save it to My Events?",
        "details_yes": "⭐ Yes, save it",
        "details_no": "Not this time",
        "which_event": "Which event would you like to hear about? You can tap one or tell me its name.",
        "no_rsvp": "No problem. I haven’t saved it.",
        "rsvp_which": "Tell me which event you’d like to save, and I’ll add it to My Events.",
        "rsvp_missing": "I couldn’t find that event. You can ask me to show the events again.",
        "rsvp_saved": "⭐ I saved {title} to My Events. Would you like a reminder? Say “remind me a day before” or “remind me 2 hours before”.",
        "interests_added": "I’ve added that to your interests. 🌱 Here are local events you might like, closest matches first.",
        "cancelled": "That’s okay. I’ve stopped that for now. What would you like to do instead?",
        "repeat_none": "I don’t have a message to repeat yet.",
        "hello": "Hello! 🌸 I’m glad you stopped by. Would you like to find a local event?",
        "help_short": "I can help you find Salem events, learn about an event, save it to My Events with a reminder, or post an event.",
        "fallback_free": "I’m here to help you find friendly local activities. You can ask me to find events or help you post one.",
        "go_back_ok": "Okay, let’s go back to the previous question. ↩",
        "go_back_first": "This is the first question, so there’s nothing before it. You can answer it, or say “cancel” to stop.",
        "go_back_nothing": "There’s no question to go back to right now. You can ask me to find events or post one.",
        "why_interest": "it matches your interest in {list}",
        "why_asked": "it’s the kind of event you asked about ({list})",
        "why_center50": "it’s from Center 50+, made for older adults",
        "why_specialty": "{source} is a favorite for people with your interests",
        "why_time": "it’s in the {tod}, when you like to go out",
        "reminder_which": "Which event should I remind you about? Save one first by saying “save” followed by its name, or tap ⭐ Save on an event.",
        "reminder_set": "⏰ Done! I’ll remind you {when} about {title} by {how}.",
        "reminder_calendar": "⏰ I noted a reminder {when} for {title}. For an alert on your phone or computer, open My Events and tap “📅 Add to calendar”.",
        "reminder_1d": "1 day before", "reminder_2h": "2 hours before",
        "reminder_when": "When should I remind you? ⏰",
        "reminder_payload_1d": "Remind me 1 day before", "reminder_payload_2h": "Remind me 2 hours before",
        "how_email": "email", "how_sms": "text message",
        "email_off": "Email reminders are not set up on this Bloom server yet.",
        "sms_off": "Text reminders not configured.",
        "language_set": "Okay, I’ll speak English. 🌸",
        "tod_morning": "morning", "tod_afternoon": "afternoon", "tod_evening": "evening",
        "all_day": "all day",
    },
    "es": {
        "welcome_back": "¡Bienvenido de nuevo! 🌸 Puedo ayudarle a:\n• Encontrar eventos de esta semana. Pruebe “¿Qué hay esta semana?”\n• Buscar por tipo o lugar. Pruebe “Buscar eventos de jardinería” o “Eventos cerca de Silverton”\n• Publicar su propio evento o poner un recordatorio para uno guardado",
        "first_hello": "Hola, me alegra que esté aquí. 🌸 Vamos a conocer lo que le gusta.",
        "prefs_saved": "¡Gracias por compartir! Guardé sus preferencias para sugerirle mejores ideas.",
        "guest_cannot_post": "Para compartir un evento, primero cree una cuenta gratuita de Bloom, así los vecinos saben quién organiza. Vaya a Configuración y luego a “Crear una cuenta gratuita”. No publiqué nada.",
        "missing_detail": "Me falta un dato, así que no lo publiqué. Podemos intentarlo de nuevo cuando quiera.",
        "bad_datetime": "No entendí la fecha o la hora, así que todavía no lo publiqué. Intentémoslo otra vez. Puede decir algo como “el próximo martes a las 2 de la tarde”.",
        "save_failed": "Lo siento, algo salió mal y su evento no se publicó. Por favor, inténtelo de nuevo en un momento.",
        "posted": "Su evento, {title}, está publicado para el {date} a las {time}. 🎉 Los vecinos ya lo pueden ver en Bloom. ¡Gracias por reunir a la comunidad!",
        "not_posted": "No hay problema. No publiqué el evento.",
        "date_unclear": "Perdón, no entendí la fecha. Puede decir “este sábado”, “20 de noviembre” o “11/20”.",
        "date_past": "Esa fecha ya pasó. ¿Qué día próximo será?",
        "confirm_unclear": "Perdón, no le entendí. Diga “sí” para publicar su evento o “no” para cancelar.",
        "skip_desc_ok": "No hay problema, dejaré la descripción en blanco.",
        "skip_required": "Necesito esta respuesta para continuar. Unas pocas palabras bastan, o diga “cancelar” para detenerse.",
        "time_unclear": "Perdón, no entendí la hora. Puede decir “2 PM”, “10:30 de la mañana” o “mediodía”.",
        "review_header": "Esto es lo que tengo:",
        "label_event": "Evento", "label_day": "Día", "label_time": "Hora", "label_place": "Lugar",
        "label_host": "Organiza", "label_details": "Detalles",
        "none_optional": "Ninguno (opcional)",
        "not_provided": "sin dato",
        "found": "Encontré {n} eventos locales. 🌸 Estos son los {shown} que pueden quedarle mejor. Todos los eventos siguen en la pestaña Eventos; no se oculta nada.",
        "found_near": "Encontré {near} eventos a menos de {radius} millas de {place}. 📍 Estos son los más cercanos. Todo lo demás sigue en la pestaña Eventos.",
        "found_near_one": "Encontré 1 evento a menos de {radius} millas de {place}. 📍 Aparece primero, seguido de los más cercanos. Todo lo demás sigue en la pestaña Eventos.",
        "nothing_near": "Todavía no veo eventos a menos de {radius} millas de {place}. Por ahora Bloom se enfoca en la zona de Salem, así que estos son los más cercanos. 📍",
        "choose_more": "Elija un evento para saber más:",
        "tell_about": "Cuéntame sobre {title}",
        "details": "{title} es el {date} a las {time}, en {location}. {description} ¿Quiere guardarlo en Mis eventos?",
        "details_yes": "⭐ Sí, guardarlo",
        "details_no": "Esta vez no",
        "which_event": "¿De qué evento le gustaría saber? Puede tocar uno o decirme su nombre.",
        "no_rsvp": "No hay problema. No lo guardé.",
        "rsvp_which": "Dígame qué evento quiere guardar y lo agregaré a Mis eventos.",
        "rsvp_missing": "No encontré ese evento. Puede pedirme que le muestre los eventos otra vez.",
        "rsvp_saved": "⭐ Guardé {title} en Mis eventos. ¿Quiere un recordatorio? Diga “recuérdame un día antes” o “recuérdame 2 horas antes”.",
        "interests_added": "Agregué eso a sus intereses. 🌱 Estos son eventos locales que le pueden gustar, los más parecidos primero.",
        "cancelled": "Está bien. Lo detuve por ahora. ¿Qué le gustaría hacer?",
        "repeat_none": "Todavía no tengo un mensaje para repetir.",
        "hello": "¡Hola! 🌸 Me alegra su visita. ¿Le gustaría encontrar un evento local?",
        "help_short": "Puedo ayudarle a encontrar eventos en Salem, contarle sobre un evento, guardarlo en Mis eventos con un recordatorio, o publicar un evento.",
        "fallback_free": "Estoy aquí para ayudarle a encontrar actividades locales. Puede pedirme que busque eventos o que le ayude a publicar uno.",
        "go_back_ok": "Muy bien, volvamos a la pregunta anterior. ↩",
        "go_back_first": "Esta es la primera pregunta, así que no hay una anterior. Puede responderla o decir “cancelar” para detenerse.",
        "go_back_nothing": "Ahora no hay una pregunta a la que volver. Puede pedirme que busque eventos o que publique uno.",
        "why_interest": "coincide con su interés en {list}",
        "why_asked": "es el tipo de evento que pidió ({list})",
        "why_center50": "es del Center 50+, pensado para adultos mayores",
        "why_specialty": "{source} es un favorito para personas con sus intereses",
        "why_time": "es por la {tod}, cuando le gusta salir",
        "reminder_which": "¿De qué evento quiere un recordatorio? Primero guarde uno diciendo “guardar” y su nombre, o toque ⭐ Guardar en un evento.",
        "reminder_set": "⏰ ¡Listo! Le recordaré {when} sobre {title} por {how}.",
        "reminder_calendar": "⏰ Anoté un recordatorio {when} para {title}. Para una alerta en su teléfono o computadora, abra Mis eventos y toque “📅 Agregar al calendario”.",
        "reminder_1d": "1 día antes", "reminder_2h": "2 horas antes",
        "reminder_when": "¿Cuándo quiere que le recuerde? ⏰",
        "reminder_payload_1d": "Recuérdame 1 día antes", "reminder_payload_2h": "Recuérdame 2 horas antes",
        "how_email": "correo electrónico", "how_sms": "mensaje de texto",
        "email_off": "Los recordatorios por correo todavía no están configurados en este servidor de Bloom.",
        "sms_off": "Los recordatorios por mensaje de texto no están configurados.",
        "language_set": "¡Claro! Desde ahora le hablo en español. 🌸",
        "tod_morning": "mañana", "tod_afternoon": "tarde", "tod_evening": "noche",
        "all_day": "todo el día",
    },
}

WEEKDAYS_ES = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MONTHS_ES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
             "noviembre", "diciembre"]


def language_of(tracker: Any) -> str:
    """'es' or 'en' from the tracker's language slot (or a plain language code)."""
    if isinstance(tracker, str):
        return tracker if tracker in MESSAGES else "en"
    try:
        lang = tracker.get_slot("language") if tracker is not None else None
    except Exception:  # tests pass simple stand-ins
        lang = None
    return lang if lang in MESSAGES else "en"


def t(tracker: Any, key: str, **values: Any) -> str:
    lang = language_of(tracker)
    text = MESSAGES[lang].get(key) or MESSAGES["en"][key]
    return text.format(**values)


def friendly_date_in(iso: str, lang: str = "en") -> str:
    from datetime import date

    try:
        d = date.fromisoformat(iso)
    except (TypeError, ValueError):
        return str(iso)
    if lang == "es":
        return f"{WEEKDAYS_ES[d.weekday()]} {d.day} de {MONTHS_ES[d.month - 1]}"
    return d.strftime("%A, %B %-d")
