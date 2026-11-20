/* Reminder settings for saved events (My Events tab).
 * Calendar (.ics) reminders always work. Email and text depend on the server's .env;
 * when a channel isn't configured it is shown disabled with a clear note. */
(function () {
  "use strict";
  let cache = null;        // { eventId: [ {timing, channel, status, send_at} ] }
  let loading = false;
  let config = { email: false, sms: false, calendar: true };

  function B() { return window.Bloom; }
  async function load() {
    if (loading) return;
    loading = true;
    try {
      const data = await B().api("/api/reminders?owner=" + encodeURIComponent(B().senderId));
      cache = {};
      (data.reminders || []).forEach(function (r) { (cache[r.event_id] = cache[r.event_id] || []).push(r); });
      config = data.config || config;
    } catch (e) { cache = cache || {}; }
    loading = false;
    B().rerender();
  }

  function panel(ev, m) {
    const t = B().t, el = B().el, button = B().button;
    if (cache === null) load();
    const p = B().profile || {};
    const session = B().session;
    const email = p.reminderEmail || (session && session.user.email) || "";
    const phone = p.phone || "";
    const box = el("section", "reminder-panel");
    box.setAttribute("aria-label", t("mine.remindTitle") + ": " + ev.title);
    box.appendChild(el("p", "reminder-title", t("mine.remind")));

    // When
    const timingRow = el("div", "choice-row");
    const existing = (cache && cache[ev.id]) || [];
    const current = (existing.find(function (r) { return r.channel !== "calendar"; }) || {}).timing || p.reminderTiming || "1d";
    [["2h", "mine.twoHours"], ["1d", "mine.dayBefore"], ["3d", "mine.threeDays"], ["1w", "mine.week"], ["2w", "mine.twoWeeks"]].forEach(function (o) {
      const label = el("label", "choice");
      const input = el("input");
      input.type = "radio"; input.name = "timing-" + ev.id; input.value = o[0]; input.checked = o[0] === current;
      label.append(input, el("span", "choice-text", t(o[1])));
      timingRow.appendChild(label);
    });
    box.appendChild(timingRow);

    // How
    const howRow = el("div", "choice-row");
    const channels = {};
    [["email", "mine.byEmail", config.email, email], ["sms", "mine.byText", config.sms, phone]].forEach(function (c) {
      const label = el("label", "choice" + (c[2] ? "" : " is-off"));
      const input = el("input");
      input.type = "checkbox"; input.value = c[0];
      input.disabled = !c[2];
      input.checked = c[2] && existing.some(function (r) { return r.channel === c[0]; });
      channels[c[0]] = input;
      label.append(input, el("span", "choice-text", t(c[1])));
      howRow.appendChild(label);
    });
    box.appendChild(howRow);
    const notes = el("ul", "reminder-notes");
    notes.appendChild(el("li", null, config.email ? (email ? t("mine.emailTo", { email: email }) : t("mine.noEmail")) : t("set.emailOff")));
    notes.appendChild(el("li", null, config.sms ? (phone ? t("mine.phoneTo", { phone: phone }) : t("mine.noPhone")) : t("set.textOff")));
    box.appendChild(notes);

    const status = el("p", "reminder-status");
    status.setAttribute("role", "status");
    const active = existing.filter(function (r) { return r.channel !== "calendar"; });
    if (active.length) {
      status.textContent = active.map(function (r) {
        return t(r.channel === "email" ? "mine.byEmail" : "mine.byText") + ": " + t("mine.status." + r.status, { when: r.send_at.replace("T", " ") });
      }).join(" · ");
    }

    const actions = el("div", "card-actions");
    function timing() { return (box.querySelector('input[name="timing-' + ev.id + '"]:checked') || {}).value || "1d"; }
    function chosen() { return Object.keys(channels).filter(function (k) { return channels[k].checked; }); }
    async function submit(test) {
      const list = chosen();
      if (!list.length) { status.textContent = t("mine.noChannel"); return; }
      try {
        const data = await B().api(test ? "/api/reminders/test" : "/api/reminders", { method: "POST", body: {
          owner: B().senderId, event_id: ev.id, timing: timing(), channels: list, email: email, phone: phone, lang: window.BloomI18n.lang } });
        const parts = Object.keys(data.results || {}).map(function (k) {
          return t(k === "email" ? "mine.byEmail" : "mine.byText") + ": " + t("mine.status." + data.results[k].status, { when: (data.results[k].send_at || "").replace("T", " ") });
        });
        status.textContent = parts.join(" · ");
        if (test && data.results.email && data.results.email.ok) status.textContent += " " + t("mine.mailhog");
        if (!test) { cache = null; load(); }
      } catch (e) { status.textContent = e.message; }
    }
    actions.appendChild(button("btn btn-primary btn-small", t("mine.setReminder"), function () { submit(false); }));
    actions.appendChild(button("btn btn-secondary btn-small", t("mine.calendarIcs"), function () {
      B().downloadIcs(ev, m.date, [{ "2h": 120, "1d": 1440, "3d": 4320, "1w": 10080, "2w": 20160 }[timing()] || 1440]);
    }));
    if (config.email || config.sms) actions.appendChild(button("btn btn-ghost btn-small", t("mine.testReminder"), function () { submit(true); }));
    box.appendChild(actions);
    box.appendChild(status);
    return box;
  }

  window.BloomReminders = { panel: panel, reload: function () { cache = null; } };
}());
