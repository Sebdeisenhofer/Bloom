(function () {
  "use strict";
  const I = window.BloomI18n;
  const t = I.t;

  /* ------------------------------------------------------------------ *
   * Options (labels come from i18n.js, keys like "int.gardening")
   * ------------------------------------------------------------------ */
  const INTERESTS = [
    ["gardening", "🌱"], ["music", "🎵"], ["crafts", "🧶"], ["books", "📚"], ["walking", "🚶"], ["fitness", "🧘"],
    ["games", "🃏"], ["cooking", "🥧"], ["faith", "🕊️"], ["volunteering", "🤝"], ["learning", "🎓"], ["tech", "💻"],
    ["history", "🏛️"], ["dancing", "💃"], ["health", "❤️"], ["movies", "🎬"], ["sports", "🏀"], ["language", "🗣️"],
    ["family", "👨‍👩‍👧"], ["social", "☕"]
  ];
  const AREAS = ["downtown", "west", "south", "northeast", "east", "keizer", "unsure"];
  const DISTANCES = ["near", "town", "far"];
  const TRANSPORT = ["drive", "ride", "bus", "needride"];
  const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
  const TIMES = ["morning", "afternoon", "evening"];
  const GROUPS = ["small", "large", "either"];
  const NEEDS = ["accessible", "seating", "hearing", "free", "bus", "parking"];
  const COMMUNITY_CATS = ["language", "books", "gardening", "crafts", "walking", "fitness", "games", "music", "cooking",
    "faith", "volunteering", "learning", "tech", "history", "social", "other"];
  // Fallback names if the server doesn't send sourceName (it normally does).
  const SOURCE_FALLBACK = { library: ["Salem Public Library", "📚"], willamette: ["Willamette University", "🏀"],
    heritage: ["Willamette Heritage Center", "🏛"], community: ["Neighbors", "🏡"] };
  const intLabel = function (k) { return t("int." + k); };
  const PAGE = 10;

  /* ------------------------------------------------------------------ *
   * Helpers
   * ------------------------------------------------------------------ */
  const $ = function (id) { return document.getElementById(id); };
  function el(tag, cls, text) {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }
  function button(cls, text, onClick) {
    const b = el("button", cls, text);
    b.type = "button";
    if (onClick) b.addEventListener("click", onClick);
    return b;
  }
  function link(cls, text, href) {
    const a = el("a", cls, text);
    a.href = href;
    a.target = "_blank";
    a.rel = "noopener noreferrer";
    return a;
  }
  function safeUrl(u) { return /^https?:\/\//i.test(u || "") ? u : ""; }
  function load(key, fallback) {
    try { const v = localStorage.getItem(key); return v ? JSON.parse(v) : fallback; } catch (e) { return fallback; }
  }
  function save(key, value) {
    try { localStorage.setItem(key, JSON.stringify(value)); } catch (e) { /* private mode */ }
  }
  function forget(keys) { try { keys.forEach(function (k) { localStorage.removeItem(k); }); } catch (e) {} }
  function pad(n) { return String(n).padStart(2, "0"); }
  function isoDate(d) { return d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate()); }
  function today0() { const d = new Date(); d.setHours(0, 0, 0, 0); return d; }
  function eventDate(ev) {
    const p = String(ev.date || "").split("-").map(Number);
    return new Date(p[0], (p[1] || 1) - 1, p[2] || 1);
  }
  function parseClock(s) {
    const m = /^(\d+):(\d+) (AM|PM)$/.exec(s || "");
    return m ? (Number(m[1]) % 12 + (m[3] === "PM" ? 12 : 0)) * 60 + Number(m[2]) : null;
  }
  function formatClock(mins) {
    mins = Math.min(mins, 23 * 60 + 59);
    const h = Math.floor(mins / 60), mm = mins % 60;
    return ((h + 11) % 12 + 1) + ":" + pad(mm) + " " + (h < 12 ? "AM" : "PM");
  }
  function timeOfDay(s) {
    const m = parseClock(s);
    if (m == null) return "afternoon";
    return m < 12 * 60 ? "morning" : m < 17 * 60 ? "afternoon" : "evening";
  }
  function endInfo(ev) {
    if (ev.endTime) return { time: ev.endTime.replace(/^~/, ""), estimated: ev.endTime.charAt(0) === "~" };
    const start = parseClock(ev.time);
    if (start == null) return null;
    return { time: formatClock(start + ((ev.tags || []).indexOf("sports") >= 0 ? 150 : 90)), estimated: true };
  }
  function timeRange(ev) {
    const end = endInfo(ev);
    return end ? ev.time + " – " + (end.estimated ? t("card.about") + " " : "") + end.time : ev.time;
  }
  function longDate(d) { return d.toLocaleDateString(I.locale(), { weekday: "long", month: "long", day: "numeric" }); }
  function shortDate(d) { return d.toLocaleDateString(I.locale(), { weekday: "short", month: "short", day: "numeric" }); }
  function areaText(a) { return a && a !== "unsure" ? t("area." + a) : "Salem"; }

  /* ------------------------------------------------------------------ *
   * State
   * ------------------------------------------------------------------ */
  const KEY = "bloom-profile-v1";
  const SAVED_KEY = "bloom-saved-v2";
  const SESSION_KEY = "bloom-session-v2";   // { token, user: { id, email, name } }
  const GUEST_KEY = "bloom-guest-v1";
  const DISPLAY_KEY = "bloom-display-v1";
  const params = new URLSearchParams(location.search);
  if (params.has("reset")) forget([KEY, SAVED_KEY, SESSION_KEY, GUEST_KEY, "bloom-rsvps-v1", "bloom-session-v1"]);

  let session = load(SESSION_KEY, null);
  let guestId;
  try {
    guestId = localStorage.getItem("bloom-user-id");
    if (!guestId) {
      guestId = "bloom-" + (window.crypto && crypto.randomUUID ? crypto.randomUUID() : Date.now() + Math.random().toString(36).slice(2));
      localStorage.setItem("bloom-user-id", guestId);
    }
  } catch (e) { guestId = "bloom-session-" + Date.now(); }
  let senderId = session ? session.user.id : guestId;
  let profile = load(KEY, null);
  let saved = new Set(load(SAVED_KEY, []));
  let events = [];          // from /api/events
  let apiReachable = null;  // null = loading
  let config = { email: false, sms: false };
  let sortMode = "date";
  let shownCount = PAGE;
  let readAloud = false;
  let display = load(DISPLAY_KEY, { size: "normal", contrast: false });
  let geo = null;           // resolved location filter {lat, lon, label} or {error}

  function knownVisitor() { return !!session || !!load(GUEST_KEY, false); }
  function displayName() { return (profile && profile.name) || (session && session.user.name) || ""; }

  /* ------------------------------------------------------------------ *
   * Read aloud (Listen buttons turn into "Stop listening" while talking)
   * ------------------------------------------------------------------ */
  let speakingId = null, speakingBtn = null;
  function setListenLabel(btn, on) {
    if (!btn) return;
    btn.textContent = on ? t("card.stop") : t("card.listen");
    btn.setAttribute("aria-pressed", String(on));
    btn.classList.toggle("is-speaking", on);
  }
  function stopSpeaking() {
    if ("speechSynthesis" in window) window.speechSynthesis.cancel();
    setListenLabel(speakingBtn, false);
    speakingBtn = null; speakingId = null;
  }
  function speak(text, btn, id) {
    if (!("speechSynthesis" in window)) return;
    stopSpeaking();
    const u = new SpeechSynthesisUtterance(text);
    u.rate = 0.92;
    u.lang = I.locale();
    if (btn) {
      speakingBtn = btn; speakingId = id;
      setListenLabel(btn, true);
      u.onend = u.onerror = function () { if (speakingId === id) { setListenLabel(speakingBtn, false); speakingBtn = null; speakingId = null; } };
    }
    window.speechSynthesis.speak(u);
  }

  function toast(msg, actionLabel, onAction) {
    let n = $("toast");
    if (!n) { n = el("div", "toast"); n.id = "toast"; n.setAttribute("role", "status"); document.body.appendChild(n); }
    n.replaceChildren(el("span", null, msg));
    if (actionLabel) {
      const b = button("toast-action", actionLabel + " →", function () { n.classList.remove("show"); onAction(); });
      n.appendChild(b);
    }
    n.classList.add("show");
    clearTimeout(toast.timer);
    toast.timer = setTimeout(function () { n.classList.remove("show"); }, actionLabel ? 7000 : 3500);
    if (readAloud) speak(msg);
  }

  /* ------------------------------------------------------------------ *
   * Server calls
   * ------------------------------------------------------------------ */
  function authHeaders(extra) {
    const h = Object.assign({}, extra || {});
    if (session) h.Authorization = "Bearer " + session.token;
    return h;
  }
  async function api(path, opts) {
    opts = opts || {};
    const res = await fetch(path, {
      method: opts.method || "GET",
      headers: authHeaders(opts.body ? { "Content-Type": "application/json" } : {}),
      body: opts.body ? JSON.stringify(opts.body) : undefined,
      cache: "no-store"
    });
    const data = await res.json().catch(function () { return {}; });
    if (res.status === 401 && session && path.indexOf("/api/login") < 0) endSession();
    if (!res.ok) { const err = new Error(data.error || "HTTP " + res.status); err.status = res.status; throw err; }
    return data;
  }
  function fromApi(e) {
    const fb = SOURCE_FALLBACK[e.source] || [e.host, "📅"];
    return {
      id: e.id, title: e.title, date: e.date, time: e.time, endTime: e.endTime || "", tod: timeOfDay(e.time),
      place: e.place, area: e.area || "", city: e.city || "", lat: e.lat, lon: e.lon,
      tags: e.tags || [], group: e.group, cost: e.cost, needs: e.needs || [], host: e.host, desc: e.desc,
      source: e.source || "", sourceName: e.sourceName || fb[0], sourceIcon: e.sourceIcon || fb[1],
      sourceUrl: safeUrl(e.sourceUrl || e.url), ticketUrl: safeUrl(e.ticketUrl), sample: !!e.sample,
      community: e.source === "community", mine: e.source === "community" && e.createdBy === senderId,
      posterName: e.posterName || "", posterEvents: e.posterEvents || 0
    };
  }
  let lastSig = "";
  async function loadEvents() {
    try {
      const data = await api("/api/events");
      events = (data.events || []).map(fromApi);
      apiReachable = true;
      if (data.config) config = data.config;
    } catch (e) { apiReachable = false; }
    const sig = events.map(function (e) { return e.id + e.title + e.date + e.time; }).join("|");
    const changed = sig !== lastSig;
    lastSig = sig;
    return changed;
  }
  async function loadSaved() {
    try {
      const data = await api("/api/saved?owner=" + encodeURIComponent(senderId));
      saved = new Set((data.saved || []).map(Number));
      save(SAVED_KEY, Array.from(saved));
    } catch (e) { /* offline: keep the local copy */ }
  }
  async function toggleSaved(ev) {
    const was = saved.has(ev.id);
    if (was) saved.delete(ev.id); else saved.add(ev.id);
    save(SAVED_KEY, Array.from(saved));
    rerender();
    if (!was) toast(t("toast.saved", { title: ev.title }), t("toast.viewMine"), function () { go("my-events"); });
    else toast(t("toast.unsaved"));
    try {
      if (was) await api("/api/saved/" + ev.id + "?owner=" + encodeURIComponent(senderId), { method: "DELETE" });
      else await api("/api/saved", { method: "POST", body: { owner: senderId, event_id: ev.id } });
    } catch (e) { /* stays saved on this device; will sync next time */ }
  }

  /* ------------------------------------------------------------------ *
   * Matching — transparent, never hides anything
   * ------------------------------------------------------------------ */
  const SOURCE_SPECIALTY = { deepwood: ["gardening", "history", "walking"], lordschryver: ["gardening", "history"],
    heritage: ["history", "crafts"], center50: null };
  function score(ev) {
    const p = profile || {};
    const reasons = [], cautions = [];
    let s = 0;
    const d = eventDate(ev);
    const interests = p.interests || [];
    const hits = ev.tags.filter(function (x) { return interests.indexOf(x) !== -1; });
    if (hits.length) {
      s += 4 * hits.length;
      reasons.push(t("card.youEnjoy", { list: hits.map(function (h) { return intLabel(h).toLowerCase(); }).join(t("card.and")) }));
    }
    // Trusted sources: Center 50+ is made for older adults; garden estates rank first for gardeners.
    if (ev.source === "center50") { s += 3; reasons.push(t("card.trusted", { source: ev.sourceName })); }
    const specialty = SOURCE_SPECIALTY[ev.source];
    if (specialty && specialty.some(function (x) { return interests.indexOf(x) !== -1; })) s += 2;
    const dayKey = DAYS[(d.getDay() + 6) % 7];
    if ((p.days || []).length && p.days.indexOf(dayKey) !== -1) {
      s += 2; reasons.push(t("card.dayWorks", { day: d.toLocaleDateString(I.locale(), { weekday: "long" }) }));
    }
    if ((p.times || []).length) {
      if (p.times.indexOf(ev.tod) !== -1) { s += 2; reasons.push(t("card.timeWorks", { tod: t("tod." + ev.tod) })); }
      else { s -= 1; cautions.push(t("card.timeCaution", { tod: t("tod." + ev.tod) })); }
    }
    if (p.area && p.area !== "unsure" && ev.area) {
      if (p.area === ev.area) { s += 3; reasons.push(t("card.close", { area: areaText(ev.area) })); }
      else if (p.distance === "near") { s -= 1; cautions.push(t("card.far", { area: areaText(ev.area) })); }
    }
    if (p.group && p.group !== "either" && p.group === ev.group) { s += 1; reasons.push(t(ev.group === "small" ? "card.small" : "card.large")); }
    (p.needs || []).forEach(function (n) {
      if (ev.needs.indexOf(n) !== -1) s += 1;
      else cautions.push(t("card.checkNeed", { need: t("need." + n).toLowerCase() }));
    });
    if ((p.needs || []).length && p.needs.every(function (n) { return ev.needs.indexOf(n) !== -1; })) {
      reasons.push(t("card.needsMet", { list: p.needs.map(function (n) { return t("need." + n).toLowerCase(); }).join(", ") }));
    }
    if ((p.transport || []).indexOf("bus") !== -1 && ev.needs.indexOf("bus") !== -1 && (p.needs || []).indexOf("bus") === -1) {
      s += 1; reasons.push(t("card.bus"));
    }
    let level = "new";
    if (s >= 9) level = "great"; else if (s >= 4) level = "good";
    return { ev: ev, date: d, score: s, reasons: reasons, cautions: cautions, level: level, miles: null };
  }

  /* ------------------------------------------------------------------ *
   * Calendar (.ics works everywhere with no setup; Google link too)
   * ------------------------------------------------------------------ */
  function calTimes(ev, d) {
    const ymd = d.getFullYear() + pad(d.getMonth() + 1) + pad(d.getDate());
    const start = parseClock(ev.time);
    if (start == null) return { allDay: true, ymd: ymd };
    let end = parseClock((endInfo(ev) || {}).time);
    if (end == null || end <= start) end = Math.min(start + 90, 23 * 60 + 59);
    const hm = function (m) { return "T" + pad(Math.floor(m / 60)) + pad(m % 60) + "00"; };
    return { allDay: false, ymd: ymd, start: ymd + hm(start), end: ymd + hm(end) };
  }
  function downloadIcs(ev, d, alarmMinutes) {
    const c = calTimes(ev, d);
    const next = new Date(d); next.setDate(next.getDate() + 1);
    const when = c.allDay
      ? "DTSTART;VALUE=DATE:" + c.ymd + "\r\nDTEND;VALUE=DATE:" + next.getFullYear() + pad(next.getMonth() + 1) + pad(next.getDate())
      : "DTSTART;TZID=America/Los_Angeles:" + c.start + "\r\nDTEND;TZID=America/Los_Angeles:" + c.end;
    const esc = function (s) { return String(s || "").replace(/[\\;,]/g, "\\$&").replace(/\n/g, "\\n"); };
    const lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Bloom//Salem//EN", "BEGIN:VEVENT",
      "UID:bloom-" + ev.id + "-" + c.ymd + "@bloom", "DTSTAMP:" + new Date().toISOString().replace(/[-:]/g, "").slice(0, 15) + "Z",
      when, "SUMMARY:" + esc(ev.title), "LOCATION:" + esc(ev.place),
      "DESCRIPTION:" + esc((ev.desc || "") + (ev.sourceUrl ? "\n" + ev.sourceUrl : "") + "\nFound on Bloom")];
    (alarmMinutes || [1440, 120]).forEach(function (m) {
      lines.push("BEGIN:VALARM", "ACTION:DISPLAY", "DESCRIPTION:" + esc(ev.title), "TRIGGER:-PT" + m + "M", "END:VALARM");
    });
    lines.push("END:VEVENT", "END:VCALENDAR");
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([lines.join("\r\n")], { type: "text/calendar" }));
    a.download = ev.title.replace(/[^a-z0-9]+/gi, "-").slice(0, 40) + ".ics";
    document.body.appendChild(a);
    a.click();
    a.remove();
    toast(t("toast.ics"));
  }
  function googleCalendarUrl(ev, d) {
    const c = calTimes(ev, d);
    let dates;
    if (c.allDay) {
      const next = new Date(d); next.setDate(next.getDate() + 1);
      dates = c.ymd + "/" + next.getFullYear() + pad(next.getMonth() + 1) + pad(next.getDate());
    } else dates = c.start + "/" + c.end;
    const q = new URLSearchParams({ action: "TEMPLATE", text: ev.title, dates: dates, ctz: "America/Los_Angeles",
      location: ev.place || "", details: (ev.desc || "") + (ev.sourceUrl ? "\n\n" + ev.sourceUrl : "") + "\n\nFound on Bloom" });
    return "https://calendar.google.com/calendar/render?" + q.toString();
  }

  /* ------------------------------------------------------------------ *
   * Event card
   * ------------------------------------------------------------------ */
  function dateBlock(d) {
    const b = el("div", "date-block");
    b.setAttribute("aria-hidden", "true");
    b.appendChild(el("span", "date-dow", d.toLocaleDateString(I.locale(), { weekday: "short" })));
    b.appendChild(el("span", "date-day", String(d.getDate())));
    b.appendChild(el("span", "date-mon", d.toLocaleDateString(I.locale(), { month: "short" })));
    return b;
  }
  function card(m, opts) {
    opts = opts || {};
    const ev = m.ev;
    const c = el("article", "event-card" + (opts.featured ? " featured" : ""));
    const top = el("div", "card-top");
    top.appendChild(dateBlock(m.date));
    const head = el("div", "card-head");
    const badges = el("div", "badges");
    if (profile && profile.completed) badges.appendChild(el("span", "badge badge-" + m.level, t("card." + m.level)));
    if (ev.mine) badges.appendChild(el("span", "badge badge-mine", t("card.mine")));
    else if (ev.community) badges.appendChild(el("span", "badge badge-neighbor", t("card.neighbor", { name: ev.posterName || t("card.aNeighbor") })));
    else badges.appendChild(el("span", "badge badge-source", ev.sourceIcon + " " + ev.sourceName));
    if (ev.sample) badges.appendChild(el("span", "badge badge-sample", t("card.sample")));
    head.appendChild(badges);
    head.appendChild(el("h3", null, ev.title));
    const whenText = longDate(m.date) + " · " + timeRange(ev);
    head.appendChild(el("p", "meta", "🗓 " + whenText));
    head.appendChild(el("p", "meta", "📍 " + ev.place + (ev.area ? " (" + areaText(ev.area) + ")" : ev.city ? " (" + ev.city + ")" : "") +
      (m.miles != null ? " · " + t("card.miles", { n: m.miles < 10 ? m.miles.toFixed(1) : Math.round(m.miles) }) : "")));
    head.appendChild(el("p", "meta", "💵 " + (ev.cost || t("card.free"))));
    const chips = el("div", "chips");
    ev.tags.slice(0, 4).forEach(function (tag) { if (t("int." + tag) !== "int." + tag) chips.appendChild(el("span", "chip", intLabel(tag))); });
    if (chips.children.length) head.appendChild(chips);
    top.appendChild(head);
    c.appendChild(top);

    // Details (hidden until asked for, to keep the list calm)
    const details = el("div", "details");
    details.hidden = true;
    if (profile && profile.completed && (m.reasons.length || m.cautions.length)) {
      const why = el("div", "why");
      if (m.reasons.length) {
        why.appendChild(el("p", "why-title", t("card.why")));
        const ul = el("ul");
        m.reasons.forEach(function (r) { ul.appendChild(el("li", null, r)); });
        why.appendChild(ul);
      }
      if (m.cautions.length) {
        const ul2 = el("ul", "cautions");
        m.cautions.forEach(function (r) { ul2.appendChild(el("li", null, r)); });
        why.appendChild(ul2);
      }
      details.appendChild(why);
    }
    if (ev.sample) details.appendChild(el("p", "sample-note", t("card.sampleNote", { source: ev.sourceName })));
    details.appendChild(el("p", null, ev.desc));
    details.appendChild(el("p", "meta", t("card.hostedBy", { host: ev.host })));
    if (ev.community) {
      details.appendChild(el("p", "meta poster", "👤 " + (ev.posterName
        ? t(ev.posterEvents === 1 ? "card.sharedByOne" : "card.sharedBy", { name: ev.posterName, n: ev.posterEvents })
        : t("card.neighbor", { name: t("card.aNeighbor") }))));
    }
    const access = ev.needs.map(function (n) { return t("need." + n); }).join(" · ");
    if (access) details.appendChild(el("p", "meta", "♿ " + access));
    const extra = el("div", "card-actions");
    const listen = button("btn btn-ghost btn-small", t("card.listen"));
    listen.setAttribute("aria-pressed", "false");
    if (speakingId === ev.id && window.speechSynthesis && window.speechSynthesis.speaking) { speakingBtn = listen; setListenLabel(listen, true); }
    listen.addEventListener("click", function () {
      if (speakingId === ev.id) { stopSpeaking(); return; }
      speak(ev.title + ". " + whenText.replace("–", "-") + ", " + ev.place + ". " + (ev.cost || "") + ". " + ev.desc, listen, ev.id);
    });
    const cal = button("btn btn-ghost btn-small", t("card.calendar"));
    cal.setAttribute("aria-expanded", "false");
    extra.append(listen, cal);
    if (ev.community && !ev.mine) extra.appendChild(button("btn btn-link report-link", t("card.report"), function () { reportEvent(ev); }));
    if (ev.mine) extra.appendChild(button("btn btn-link", t("card.remove"), function () { removeEvent(ev); }));
    details.appendChild(extra);
    const calPanel = el("div", "cal-panel");
    calPanel.hidden = true;
    calPanel.appendChild(el("p", "cal-title", t("card.calendarTo", { title: ev.title })));
    calPanel.append(link("btn btn-secondary btn-small", t("card.google"), googleCalendarUrl(ev, m.date)),
      button("btn btn-secondary btn-small", t("card.ics"), function () { downloadIcs(ev, m.date); }));
    cal.addEventListener("click", function () { calPanel.hidden = !calPanel.hidden; cal.setAttribute("aria-expanded", String(!calPanel.hidden)); });
    details.appendChild(calPanel);
    c.appendChild(details);

    // Main actions
    const actions = el("div", "card-actions");
    const isSaved = saved.has(ev.id);
    const sv = button("btn " + (isSaved ? "btn-done" : "btn-primary"), isSaved ? t("card.saved") : t("card.save"), function () { toggleSaved(ev); });
    sv.setAttribute("aria-pressed", String(isSaved));
    const more = button("btn btn-secondary", t("card.details"));
    more.setAttribute("aria-expanded", "false");
    more.addEventListener("click", function () {
      details.hidden = !details.hidden;
      more.setAttribute("aria-expanded", String(!details.hidden));
      more.textContent = details.hidden ? t("card.details") : t("card.lessDetails");
    });
    actions.append(sv, more);
    if (ev.sourceUrl) actions.appendChild(link("btn btn-ghost", t("card.website"), ev.sourceUrl));
    if (ev.ticketUrl) actions.appendChild(link("btn btn-ghost", t("card.tickets"), ev.ticketUrl));
    c.appendChild(actions);
    if (opts.after) c.appendChild(opts.after(ev, m));
    return c;
  }
  async function reportEvent(ev) {
    if (!window.confirm(t("confirm.report", { title: ev.title }))) return;
    try {
      await api("/api/events/" + ev.id + "/report", { method: "POST", body: { user: senderId } });
      toast(t("toast.reported"));
      if (await loadEvents()) rerender();
    } catch (e) { toast(t("toast.reportFail")); }
  }
  async function removeEvent(ev) {
    if (!window.confirm(t("confirm.remove", { title: ev.title }))) return;
    try {
      await api("/api/events/" + ev.id, { method: "DELETE" });
      await loadEvents();
      rerender();
      toast(t("toast.removed"));
    } catch (e) { toast(t("toast.removeFail")); }
  }

  // Groups cards under date headings ("Today · Monday, November 16").
  function renderGrouped(container, matches, limit) {
    container.replaceChildren();
    let currentKey = "", group = null;
    const t0 = today0();
    matches.slice(0, limit).forEach(function (m) {
      const key = m.ev.date;
      if (key !== currentKey) {
        currentKey = key;
        const days = Math.round((m.date - t0) / 86400000);
        const label = (days === 0 ? t("events.today2") + " · " : days === 1 ? t("events.tomorrow") + " · " : "") + longDate(m.date);
        const section = el("section", "day-group");
        section.appendChild(el("h3", "day-heading", label));
        group = el("div", "event-list");
        section.appendChild(group);
        container.appendChild(section);
      }
      group.appendChild(card(m));
    });
  }
  function showMoreButton(container, total, onMore) {
    const left = total - shownCount;
    if (left <= 0) return;
    container.appendChild(button("btn btn-secondary show-more", t("events.showMore", { n: Math.min(PAGE, left), left: left }), onMore));
  }

  /* ------------------------------------------------------------------ *
   * Events tab: filters, top picks, grouped results
   * ------------------------------------------------------------------ */
  function fillSelect(sel, options) {
    sel.replaceChildren();
    options.forEach(function (o) { sel.appendChild(new Option(o[1], o[0])); });
  }
  function buildFilterOptions() {
    const kind = $("kind-filter"), cur = kind.value;
    fillSelect(kind, [["", t("events.allKinds")]].concat(INTERESTS.map(function (i) { return [i[0], i[1] + " " + intLabel(i[0])]; })));
    kind.value = cur;
    const src = $("source-filter"), curSrc = src.value;
    const seen = {};
    const list = [["", t("events.allSources")]];
    events.forEach(function (e) { if (!seen[e.source]) { seen[e.source] = 1; list.push([e.source, e.sourceIcon + " " + (e.community ? t("tab.community") : e.sourceName)]); } });
    fillSelect(src, list);
    src.value = curSrc;
  }
  function filtersActive() {
    return ["search-input", "kind-filter", "when-filter", "tod-filter", "source-filter", "place-filter"].some(function (id) { return $(id).value.trim(); });
  }
  function haversine(a, b, c, d) {
    const r = Math.PI / 180, R = 3958.8;
    const x = Math.pow(Math.sin((c - a) * r / 2), 2) + Math.cos(a * r) * Math.cos(c * r) * Math.pow(Math.sin((d - b) * r / 2), 2);
    return 2 * R * Math.asin(Math.sqrt(x));
  }
  let geoQuery = "";
  async function resolvePlace() {
    const q = $("place-filter").value.trim();
    if (q === geoQuery) return;
    geoQuery = q;
    if (!q) { geo = null; return; }
    try {
      const data = await api("/api/geo?q=" + encodeURIComponent(q));
      geo = data.lat != null ? data : { error: true, q: q };
    } catch (e) { geo = { error: true, q: q, textOnly: true }; }
  }
  function matchesFilters(m) {
    const ev = m.ev;
    const kind = $("kind-filter").value;
    if (kind && ev.tags.indexOf(kind) === -1) return false;
    const src = $("source-filter").value;
    if (src && ev.source !== src) return false;
    const tod = $("tod-filter").value;
    if (tod && ev.tod !== tod) return false;
    const when = $("when-filter").value;
    const days = Math.round((m.date - today0()) / 86400000);
    if (when === "today" && days !== 0) return false;
    if (when === "week" && days > 6) return false;
    if (when === "weekend") {
      const toSat = (6 - today0().getDay() + 7) % 7;
      const dow = m.date.getDay();
      if (!((dow === 6 || dow === 0) && days <= toSat + 1)) return false;
    }
    if (when === "pick" && $("date-filter").value && ev.date !== $("date-filter").value) return false;
    const words = $("search-input").value.toLowerCase().split(/\s+/).filter(Boolean);
    if (words.length) {
      const hay = [ev.title, ev.desc, ev.place, ev.host, ev.posterName, ev.sourceName, ev.city, areaText(ev.area)]
        .concat(ev.tags.map(intLabel)).join(" ").toLowerCase();
      if (!words.every(function (w) { return hay.indexOf(w) !== -1; })) return false;
    }
    if (geo && geo.error) {
      const q = geo.q.toLowerCase();
      return [ev.place, ev.city, areaText(ev.area)].join(" ").toLowerCase().indexOf(q) !== -1;
    }
    return true;
  }
  function greetingText() {
    const h = new Date().getHours();
    const part = t(h < 12 ? "events.greetingMorning" : h < 17 ? "events.greetingAfternoon" : "events.greetingEvening");
    return part + (displayName() ? ", " + displayName() : "") + " 🌸";
  }
  function renderEvents() {
    const completed = profile && profile.completed;
    $("greeting").textContent = greetingText();
    $("hero-sub").textContent = t(completed ? "events.sub" : "events.subGuest");
    $("edit-profile").hidden = !!completed;
    buildFilterOptions();
    $("date-filter").hidden = $("when-filter").value !== "pick";
    document.querySelectorAll("[data-sort]").forEach(function (b) { b.setAttribute("aria-pressed", String(b.dataset.sort === sortMode)); });

    const all = events.map(score);
    const filtering = filtersActive();
    const list = filtering ? all.filter(matchesFilters) : all;
    const byDate = function (a, b) { return a.date - b.date || b.score - a.score; };
    const byMatch = function (a, b) { return b.score - a.score || a.date - b.date; };
    const radius = Number($("radius-filter").value);
    let near = null;
    if (geo && geo.lat != null) {
      const pts = geo.points || [[geo.lat, geo.lon]];  // regions ("the coast") measure to their nearest town
      list.forEach(function (m) {
        m.miles = m.ev.lat != null ? Math.min.apply(null, pts.map(function (p) { return haversine(p[0], p[1], m.ev.lat, m.ev.lon); })) : null;
      });
      near = list.filter(function (m) { return m.miles != null && m.miles <= radius; });
    }

    // Top picks: only for a personalized, unfiltered view.
    const picks = $("top-picks");
    picks.replaceChildren();
    const showPicks = completed && !filtering && all.length > 3;
    $("picks-title").hidden = !showPicks;
    picks.hidden = !showPicks;
    if (showPicks) all.slice().sort(byMatch).slice(0, 3).forEach(function (m) { picks.appendChild(card(m, { featured: true })); });

    const container = $("event-list");
    let total;
    if (near) {
      // Never hide: nearby events first, then everything else by distance.
      const far = list.filter(function (m) { return near.indexOf(m) < 0; })
        .sort(function (a, b) { return (a.miles == null ? 1e9 : a.miles) - (b.miles == null ? 1e9 : b.miles); });
      near.sort(sortMode === "match" ? byMatch : byDate);
      total = near.length + far.length;
      container.replaceChildren();
      const nearBox = el("section", "near-group");
      nearBox.appendChild(el("h3", "group-heading", t("events.nearLabel", { place: geo.label }) + " · " + t("events.within", { n: radius }) + " (" + near.length + ")"));
      const nearList = el("div", "event-groups");
      nearBox.appendChild(nearList);
      container.appendChild(nearBox);
      renderGrouped(nearList, near, shownCount);
      if (shownCount > near.length && far.length) {
        const farBox = el("section", "near-group");
        farBox.appendChild(el("h3", "group-heading", t("events.farther") + " (" + far.length + ")"));
        const farList = el("div", "event-list");
        far.slice(0, shownCount - near.length).forEach(function (m) { farList.appendChild(card(m)); });
        farBox.appendChild(farList);
        container.appendChild(farBox);
      }
    } else {
      const ordered = list.slice().sort(sortMode === "match" ? byMatch : byDate);
      total = ordered.length;
      if (sortMode === "match") {
        container.replaceChildren();
        const flat = el("div", "event-list");
        ordered.slice(0, shownCount).forEach(function (m) { flat.appendChild(card(m)); });
        container.appendChild(flat);
      } else renderGrouped(container, ordered, shownCount);
    }
    showMoreButton(container, total, function () { shownCount += PAGE; renderEvents(); });
    if (apiReachable === null && !events.length) container.replaceChildren(el("p", "empty", t("events.loading")));
    if (apiReachable === false && !events.length) container.replaceChildren(el("p", "empty", t("events.offline")));

    $("list-title").textContent = t(filtering ? "events.matching" : "events.all");
    $("event-count").textContent = t("events.count", { n: list.length });
    const st = $("search-status");
    st.hidden = !filtering;
    if (filtering) {
      st.replaceChildren(el("span", null, (geo && geo.error && !geo.textOnly ? t("events.unknownPlace", { q: geo.q }) + " " : "") +
        (list.length ? t("events.showing", { n: list.length, total: all.length }) + " " : t("events.none") + " ")));
      st.appendChild(button("btn btn-link", t("events.clear"), clearFilters));
    }
    const names = [];
    events.forEach(function (e) { if (!e.community && names.indexOf(e.sourceName) < 0) names.push(e.sourceName); });
    $("source-note").textContent = names.length ? t("events.sourceNote", { sources: names.join(", ") }) : "";
  }
  function clearFilters() {
    $("filters").reset();
    geo = null; geoQuery = "";
    shownCount = PAGE;
    renderEvents();
    $("search-input").focus();
  }
  let filterTimer;
  ["search-input", "place-filter"].forEach(function (id) {
    $(id).addEventListener("input", function () {
      clearTimeout(filterTimer);
      filterTimer = setTimeout(async function () { shownCount = PAGE; await resolvePlace(); renderEvents(); }, 350);
    });
  });
  ["kind-filter", "when-filter", "tod-filter", "source-filter", "date-filter", "radius-filter"].forEach(function (id) {
    $(id).addEventListener("change", function () {
      shownCount = PAGE;
      renderEvents();
      if (id === "when-filter" && $(id).value === "pick") $("date-filter").focus();
    });
  });
  $("filters").addEventListener("submit", async function (e) { e.preventDefault(); await resolvePlace(); renderEvents(); });
  document.querySelectorAll("[data-sort]").forEach(function (b) {
    b.addEventListener("click", function () { sortMode = b.dataset.sort; shownCount = PAGE; renderEvents(); });
  });

  /* ------------------------------------------------------------------ *
   * My Events & Volunteer
   * ------------------------------------------------------------------ */
  function savedMatches() {
    return events.filter(function (ev) { return saved.has(ev.id); }).map(score).sort(function (a, b) { return a.date - b.date; });
  }
  function updateSavedCount() {
    const n = savedMatches().length;
    $("saved-count").textContent = String(n);
    $("tab-my-events").setAttribute("aria-label", t("tab.myEvents") + ", " + n);
  }
  function renderMyEvents() {
    const mine = savedMatches();
    const list = $("saved-list");
    list.replaceChildren();
    let key = "", group = null;
    mine.forEach(function (m) {
      if (m.ev.date !== key) {
        key = m.ev.date;
        const section = el("section", "day-group");
        section.appendChild(el("h3", "day-heading", longDate(m.date)));
        group = el("div", "event-list");
        section.appendChild(group);
        list.appendChild(section);
      }
      group.appendChild(card(m, { after: window.BloomReminders ? window.BloomReminders.panel : null }));
    });
    $("saved-empty").hidden = mine.length > 0;
    $("mine-channels").textContent = t("mine.calendarTip");
    updateSavedCount();
  }
  function renderVolunteer() {
    const vol = events.filter(function (ev) { return ev.tags.indexOf("volunteering") !== -1; }).map(score)
      .sort(function (a, b) { return a.date - b.date || b.score - a.score; });
    renderGrouped($("volunteer-list"), vol, vol.length);
    $("volunteer-empty").hidden = vol.length > 0;
  }

  /* ------------------------------------------------------------------ *
   * Community feed
   * ------------------------------------------------------------------ */
  let posts = [], postCat = "", postsLoaded = null;
  async function loadPosts() {
    try { posts = (await api("/api/community?owner=" + encodeURIComponent(senderId))).posts || []; postsLoaded = true; }
    catch (e) { postsLoaded = false; }
  }
  function catIcon(c) { return (INTERESTS.find(function (i) { return i[0] === c; }) || [c, "✨"])[1]; }
  function renderCommunity() {
    const cats = $("community-cats");
    cats.replaceChildren();
    [["", t("com.all")]].concat(COMMUNITY_CATS.map(function (c) { return [c, catIcon(c) + " " + intLabel(c)]; }))
      .forEach(function (c) {
        const count = c[0] ? posts.filter(function (p) { return p.category === c[0]; }).length : posts.length;
        if (c[0] && !count) return;
        const b = button("pill", c[1] + " (" + count + ")", function () { postCat = c[0]; renderCommunity(); });
        b.setAttribute("aria-pressed", String(postCat === c[0]));
        cats.appendChild(b);
      });
    const feed = $("community-feed");
    feed.replaceChildren();
    if (postsLoaded === null) { feed.appendChild(el("p", "empty", t("com.loading"))); return; }
    if (postsLoaded === false) { feed.appendChild(el("p", "empty", t("com.offline"))); return; }
    const shown = posts.filter(function (p) { return !postCat || p.category === postCat; });
    if (!shown.length) feed.appendChild(el("p", "empty", t("com.empty")));
    shown.forEach(function (p) { feed.appendChild(postCard(p)); });
  }
  function postCard(p) {
    const c = el("article", "post-card");
    const badges = el("div", "badges");
    badges.appendChild(el("span", "chip", catIcon(p.category) + " " + intLabel(p.category)));
    if (p.sample) badges.appendChild(el("span", "badge badge-sample", t("com.sample")));
    c.appendChild(badges);
    c.appendChild(el("h3", null, p.title));
    if (p.schedule) c.appendChild(el("p", "meta", "🗓 " + p.schedule));
    if (p.place) c.appendChild(el("p", "meta", "📍 " + p.place));
    if (p.body) c.appendChild(el("p", null, p.body));
    c.appendChild(el("p", "meta poster", "👤 " + t("com.by", { name: p.posterName })));
    const actions = el("div", "card-actions");
    const join = button("btn " + (p.joined ? "btn-done" : "btn-primary"), p.joined ? t("com.joined") : t("com.join"), async function () {
      try {
        const r = await api("/api/community/" + p.id + "/join", { method: "POST", body: { owner: senderId } });
        p.joined = r.joined; p.joins = r.joins;
        renderCommunity();
      } catch (e) { toast(e.message); }
    });
    join.setAttribute("aria-pressed", String(!!p.joined));
    actions.appendChild(join);
    actions.appendChild(el("span", "join-count", t("com.joins", { n: p.joins })));
    const showC = button("btn btn-secondary", t("com.comments", { n: p.comments.length }));
    showC.setAttribute("aria-expanded", "false");
    actions.appendChild(showC);
    if (p.mine) actions.appendChild(button("btn btn-link", t("com.remove"), async function () {
      try { await api("/api/community/" + p.id, { method: "DELETE" }); await loadPosts(); renderCommunity(); } catch (e) { toast(e.message); }
    }));
    c.appendChild(actions);
    const box = el("div", "comments");
    box.hidden = true;
    p.comments.forEach(function (cm) {
      const row = el("div", "comment");
      row.appendChild(el("strong", null, cm.name + ": "));
      row.appendChild(el("span", null, cm.body));
      box.appendChild(row);
    });
    const cform = el("form", "comment-form");
    const input = el("input");
    input.type = "text"; input.maxLength = 600; input.placeholder = t("com.commentPlaceholder");
    input.setAttribute("aria-label", t("com.addComment"));
    cform.append(input, el("button", "btn btn-primary btn-small", t("com.send")));
    cform.addEventListener("submit", async function (e) {
      e.preventDefault();
      if (!session) { pendingAfterAuth = "community"; openAuth("register", t("auth.groupFirst")); return; }
      if (!input.value.trim()) return;
      try {
        await api("/api/community/" + p.id + "/comments", { method: "POST", body: { body: input.value.trim() } });
        await loadPosts();
        renderCommunity();
      } catch (err) { toast(err.message); }
    });
    box.appendChild(cform);
    c.appendChild(box);
    showC.addEventListener("click", function () { box.hidden = !box.hidden; showC.setAttribute("aria-expanded", String(!box.hidden)); if (!box.hidden) input.focus(); });
    return c;
  }
  $("open-post").addEventListener("click", function () {
    if (!session) { pendingAfterAuth = "community-post"; openAuth("register", t("auth.groupFirst")); return; }
    $("post-form").hidden = false;
    $("post-title").focus();
  });
  $("post-cancel").addEventListener("click", function () { $("post-form").hidden = true; $("post-form").reset(); });
  $("post-form").addEventListener("submit", async function (e) {
    e.preventDefault();
    const title = $("post-title").value.trim();
    if (!title) { $("post-error").textContent = t("com.needName"); $("post-title").focus(); return; }
    try {
      await api("/api/community", { method: "POST", body: { title: title, category: $("post-category").value,
        schedule: $("post-when").value.trim(), place: $("post-where").value.trim(), body: $("post-body").value.trim() } });
      $("post-form").reset();
      $("post-form").hidden = true;
      $("post-error").textContent = "";
      await loadPosts();
      renderCommunity();
      toast(t("com.posted"));
    } catch (err) { $("post-error").textContent = err.message; }
  });

  /* ------------------------------------------------------------------ *
   * Settings
   * ------------------------------------------------------------------ */
  function applyDisplay() {
    document.body.classList.toggle("large-text", display.size === "large");
    document.body.classList.toggle("xlarge-text", display.size === "xlarge");
    document.body.classList.toggle("high-contrast", !!display.contrast);
    $("large-text").setAttribute("aria-pressed", String(display.size !== "normal"));
    $("contrast").setAttribute("aria-pressed", String(!!display.contrast));
    $("read-aloud").setAttribute("aria-pressed", String(readAloud));
    $("read-aloud").textContent = t(readAloud ? "a11y.readAloudOn" : "a11y.readAloudOff");
    document.querySelectorAll("[data-size]").forEach(function (b) { b.setAttribute("aria-pressed", String(b.dataset.size === display.size)); });
    $("set-contrast").checked = !!display.contrast;
    $("set-read").checked = readAloud;
    save(DISPLAY_KEY, display);
  }
  $("large-text").addEventListener("click", function () { display.size = display.size === "normal" ? "large" : display.size === "large" ? "xlarge" : "normal"; applyDisplay(); });
  $("contrast").addEventListener("click", function () { display.contrast = !display.contrast; applyDisplay(); });
  $("set-contrast").addEventListener("change", function (e) { display.contrast = e.target.checked; applyDisplay(); });
  document.querySelectorAll("[data-size]").forEach(function (b) { b.addEventListener("click", function () { display.size = b.dataset.size; applyDisplay(); }); });
  function setReadAloud(on) {
    readAloud = on;
    applyDisplay();
    if (!on) stopSpeaking(); else speak(t("a11y.readAloudOn").replace("🔊 ", ""));
  }
  $("read-aloud").addEventListener("click", function () { setReadAloud(!readAloud); });
  $("set-read").addEventListener("change", function (e) { setReadAloud(e.target.checked); });

  function renderLangSwitches() {
    document.querySelectorAll(".lang-switch").forEach(function (box) {
      box.replaceChildren();
      I.languages.forEach(function (l) {
        const b = button("pill", l[1], function () { setLanguage(l[0]); });
        b.setAttribute("aria-pressed", String(I.lang === l[0]));
        b.lang = l[0];
        box.appendChild(b);
      });
    });
  }
  function setLanguage(code) {
    if (code === I.lang) return;
    I.set(code);
    if (profile) { profile.language = code; persistProfile(); }
    languageSentToBot = false;
    buildAllChoices();
    applyDisplay();
    updateAccountUI();
    renderLangSwitches();
    if (!$("survey").hidden) showStep(step);
    if (!$("create").hidden) showCStep(cStep);
    if (!$("auth").hidden) openAuth(authMode, $("auth-lead").classList.contains("intro-alert") ? $("auth-lead").textContent : "");
    if (currentView.indexOf("panel-") === 0 || currentView === "create") renderCrumbs(currentView === "create" ? "events" : currentView.replace("panel-", ""), currentView === "create");
    // Restart the chat greeting in the new language.
    $("messages").replaceChildren();
    $("quick-replies").replaceChildren();
    if (currentView === "panel-chat") startChat(); else syncLanguageToBot();
    rerender();
  }

  function prefRow(dl, label, value) { dl.append(el("dt", null, label), el("dd", null, value || t("set.notAnswered"))); }
  function listText(keys, prefix) { return (keys || []).map(function (k) { return t(prefix + k); }).join(", "); }
  function renderSettings() {
    const p = profile || {};
    const box = $("account-box");
    box.replaceChildren();
    box.classList.toggle("guest", !session);
    $("account-form").hidden = !session;
    $("profile-logout").hidden = !session;
    if (session) {
      box.appendChild(el("p", null, t("set.signedIn", { name: displayName() || session.user.name, email: session.user.email })));
      $("p-name").value = displayName();
    } else {
      box.appendChild(el("p", null, t("set.guest")));
      const row = el("div", "account-box-actions");
      row.append(button("btn btn-primary", t("welcome.register"), function () { openAuth("register"); }),
        button("btn btn-secondary", t("welcome.login"), function () { openAuth("login"); }));
      box.appendChild(row);
    }
    const dl = $("prefs-summary");
    dl.replaceChildren();
    prefRow(dl, t("set.interests"), listText(p.interests, "int."));
    prefRow(dl, t("set.area"), p.area ? areaText(p.area) : "");
    prefRow(dl, t("set.days"), listText(p.days, "day."));
    prefRow(dl, t("set.times"), listText(p.times, "time."));
    prefRow(dl, t("set.groupSize"), p.group ? t("group." + p.group) : "");
    prefRow(dl, t("set.important"), listText(p.needs, "need."));
    $("edit-prefs").textContent = t(p.completed ? "set.updatePrefs" : "set.takeSurvey");
    const mineEvents = events.filter(function (ev) { return ev.mine; }).map(score).sort(function (a, b) { return a.date - b.date; });
    const list = $("my-shared");
    list.replaceChildren();
    mineEvents.forEach(function (m) { list.appendChild(card(m)); });
    $("my-events-count").textContent = "(" + mineEvents.length + ")";
    $("my-shared-empty").hidden = mineEvents.length > 0;
    const status = $("channel-status");
    status.replaceChildren(el("li", null, t("set.calendarOk")), el("li", null, t(config.email ? "set.emailOk" : "set.emailOff")),
      el("li", null, t(config.sms ? "set.textOk" : "set.textOff")));
    $("rem-email").value = p.reminderEmail || (session && session.user.email) || "";
    $("rem-phone").value = p.phone || "";
    const timing = p.reminderTiming || "1d";
    document.querySelectorAll('input[name="def-timing"]').forEach(function (i) { i.checked = i.value === timing; });
  }
  $("reminder-settings").addEventListener("submit", function (e) {
    e.preventDefault();
    profile = Object.assign({ completed: false, interests: [] }, profile || {}, {
      reminderEmail: $("rem-email").value.trim(), phone: $("rem-phone").value.trim(),
      reminderTiming: (document.querySelector('input[name="def-timing"]:checked') || {}).value || "1d"
    });
    persistProfile();
    $("rem-msg").textContent = t("set.saved");
  });
  $("account-form").addEventListener("submit", async function (e) {
    e.preventDefault();
    const name = $("p-name").value.trim();
    if (!name) { $("p-error").textContent = t("auth.needName"); return; }
    profile = Object.assign({ completed: false, interests: [] }, profile || {}, { name: name });
    session.user.name = name;
    save(SESSION_KEY, session);
    save(KEY, profile);
    const problem = await pushAccount();
    $("p-error").textContent = problem;
    if (!problem) { toast(t("set.saved")); updateAccountUI(); await loadEvents(); renderSettings(); }
  });
  $("edit-prefs").addEventListener("click", function () { openSurvey("settings"); });
  $("edit-profile").addEventListener("click", function () { openSurvey("events"); });
  $("profile-logout").addEventListener("click", function () { logout(); });
  $("profile-reset").addEventListener("click", function () {
    if (window.confirm(t(session ? "set.confirmLogout" : "set.confirmStartOver"))) startOver();
  });

  /* ------------------------------------------------------------------ *
   * Views, tabs, breadcrumbs, history
   * ------------------------------------------------------------------ */
  const TABS = ["chat", "events", "my-events", "volunteer", "community", "settings"];
  const VIEWS = ["welcome", "auth", "survey", "matching", "create"].concat(TABS.map(function (x) { return "panel-" + x; }));
  const tabKey = function (tab) { return "tab." + ({ "my-events": "myEvents" }[tab] || tab); };
  let currentView = "";
  function show(view) {
    VIEWS.forEach(function (v) { $(v).hidden = v !== view; });
    currentView = view;
    const inApp = view.indexOf("panel-") === 0 || view === "create";
    $("tabbar").hidden = !inApp;
    $("crumbs").hidden = !inApp;
    const tab = view === "create" ? "events" : view.replace("panel-", "");
    document.querySelectorAll('[role="tab"]').forEach(function (b) {
      const on = b.dataset.tab === tab && inApp;
      b.setAttribute("aria-selected", String(on));
      b.tabIndex = on ? 0 : -1;
    });
    if (inApp) renderCrumbs(tab, view === "create");
    window.scrollTo(0, 0);
  }
  function renderCrumbs(tab, sharing) {
    const ol = $("crumb-list");
    ol.replaceChildren();
    const items = [[t("crumb.home"), "chat"], [t(tabKey(tab)), tab]];
    if (tab === "chat") items.pop();
    if (sharing) items.push([t("crumb.share"), null]);
    items.forEach(function (it, i) {
      const li = el("li");
      if (i < items.length - 1 && it[1]) {
        const a = el("a", null, it[0]);
        a.href = "#" + it[1];
        li.appendChild(a);
      } else {
        li.appendChild(el("span", null, it[0]));
        li.setAttribute("aria-current", "page");
      }
      ol.appendChild(li);
    });
    $("crumb-back").hidden = tab === "chat" && !sharing;
  }
  function go(tab) {
    if (location.hash !== "#" + tab) location.hash = tab; else route();
  }
  function renderTab(tab) {
    if (tab === "events") renderEvents();
    else if (tab === "my-events") renderMyEvents();
    else if (tab === "volunteer") renderVolunteer();
    else if (tab === "community") { renderCommunity(); loadPosts().then(renderCommunity); }
    else if (tab === "settings") renderSettings();
    else if (tab === "chat") startChat();
  }
  function rerender() {
    updateSavedCount();
    if (currentView === "welcome") renderWelcome();
    else if (currentView.indexOf("panel-") === 0) {
      const tab = currentView.replace("panel-", "");
      if (tab === "community") renderCommunity();
      else if (tab !== "chat") renderTab(tab);
    }
  }
  function route() {
    const hash = location.hash.replace("#", "");
    if (!knownVisitor()) { showWelcome(); return; }
    if (!profile) { openSurvey(TABS.indexOf(hash) >= 0 ? hash : "chat"); return; }
    if (hash === "share") { openCreate(); return; }
    const tab = TABS.indexOf(hash) >= 0 ? hash : "chat";
    show("panel-" + tab);
    renderTab(tab);
    if (readAloud) speak(t(tabKey(tab)));
  }
  window.addEventListener("hashchange", route);
  document.querySelectorAll('[role="tab"]').forEach(function (b, i, all) {
    b.addEventListener("click", function () { go(b.dataset.tab); });
    b.addEventListener("keydown", function (e) {
      let j = null;
      if (e.key === "ArrowRight") j = (i + 1) % all.length;
      else if (e.key === "ArrowLeft") j = (i - 1 + all.length) % all.length;
      else if (e.key === "Home") j = 0;
      else if (e.key === "End") j = all.length - 1;
      if (j == null) return;
      e.preventDefault();
      all[j].focus();
      go(all[j].dataset.tab);
    });
  });
  $("crumb-back").addEventListener("click", function () { if (history.length > 1) history.back(); else go("chat"); });
  $("brand-link").addEventListener("click", function (e) {
    e.preventDefault();
    if (!knownVisitor()) showWelcome(); else go("chat");
  });
  $("saved-browse").addEventListener("click", function () { go("events"); });

  /* ------------------------------------------------------------------ *
   * Survey
   * ------------------------------------------------------------------ */
  function buildChoices(containerId, name, keys, prefix, type, icons) {
    const box = $(containerId);
    const checked = Array.from(box.querySelectorAll("input:checked")).map(function (i) { return i.value; });
    box.replaceChildren();
    keys.forEach(function (k) {
      const key = Array.isArray(k) ? k[0] : k;
      const label = el("label", icons ? "check-card" : "choice");
      const inp = document.createElement("input");
      inp.type = type; inp.name = name; inp.value = key;
      inp.checked = checked.indexOf(key) !== -1;
      label.appendChild(inp);
      if (icons) {
        label.appendChild(el("span", "check-icon", k[1]));
        label.appendChild(el("span", "check-text", t(prefix + key)));
      } else label.appendChild(el("span", "choice-text", t(prefix + key)));
      box.appendChild(label);
    });
  }
  function buildAllChoices() {
    buildChoices("interest-options", "interests", INTERESTS, "int.", "checkbox", true);
    buildChoices("area-options", "area", AREAS, "area.", "radio");
    buildChoices("distance-options", "distance", DISTANCES, "dist.", "radio");
    buildChoices("transport-options", "transport", TRANSPORT, "trans.", "checkbox");
    buildChoices("day-options", "days", DAYS, "day.", "checkbox");
    buildChoices("time-options", "times", TIMES, "time.", "checkbox");
    buildChoices("group-options", "group", GROUPS, "group.", "radio");
    buildChoices("needs-options", "needs", NEEDS, "need.", "checkbox");
    buildChoices("ev-tag-options", "ev-tags", INTERESTS, "int.", "checkbox", true);
    buildChoices("ev-area-options", "ev-area", AREAS.filter(function (a) { return a !== "unsure"; }), "area.", "radio");
    buildChoices("ev-group-options", "ev-group", ["small", "large"], "share.", "radio");
    buildChoices("ev-cost-options", "ev-cost", ["Free", "other"], "cost.", "radio");
    buildChoices("ev-needs-options", "ev-needs", NEEDS.filter(function (n) { return n !== "free"; }), "need.", "checkbox");
    const pc = $("post-category"), cur = pc.value || "language";
    fillSelect(pc, COMMUNITY_CATS.map(function (c) { return [c, catIcon(c) + " " + intLabel(c)]; }));
    pc.value = cur;
  }

  const form = $("survey-form");
  const steps = Array.from(form.querySelectorAll(".step"));
  let step = 0;
  let afterSurvey = "chat";
  function showStep(n) {
    step = n;
    steps.forEach(function (s, i) { s.hidden = i !== n; });
    $("back-btn").hidden = n === 0;
    $("next-btn").textContent = t(n === 0 ? "survey.begin" : n === steps.length - 1 ? "survey.finish" : "survey.next");
    $("skip-btn").textContent = t(n === 0 ? "survey.skipNow" : "survey.skipQ");
    $("step-count").textContent = n === 0 ? "" : t("survey.step", { n: n, total: steps.length - 1 });
    $("progress-bar").style.width = (n / (steps.length - 1)) * 100 + "%";
    const heading = steps[n].querySelector(".step-title");
    if (heading) { heading.setAttribute("tabindex", "-1"); heading.focus(); }
    if (readAloud && heading) speak(heading.textContent);
  }
  function values(name) { return Array.from(form.querySelectorAll('input[name="' + name + '"]:checked')).map(function (i) { return i.value; }); }
  function readForm() {
    return Object.assign({}, profile || {}, {
      name: $("name").value.trim() || displayName(),
      interests: values("interests"), area: values("area")[0] || "", distance: values("distance")[0] || "",
      transport: values("transport"), days: values("days"), times: values("times"),
      group: values("group")[0] || "", needs: values("needs"), notes: $("notes").value.trim(), completed: true
    });
  }
  function fillForm(p) {
    $("name").value = (p && p.name) || displayName();
    $("notes").value = (p && p.notes) || "";
    ["interests", "transport", "days", "times", "needs"].forEach(function (n) {
      form.querySelectorAll('input[name="' + n + '"]').forEach(function (i) { i.checked = !!p && (p[n] || []).indexOf(i.value) !== -1; });
    });
    ["area", "distance", "group"].forEach(function (n) {
      form.querySelectorAll('input[name="' + n + '"]').forEach(function (i) { i.checked = !!p && p[n] === i.value; });
    });
  }
  form.addEventListener("submit", function (e) {
    e.preventDefault();
    if (step < steps.length - 1) { showStep(step + 1); return; }
    finishSurvey(readForm());
  });
  $("back-btn").addEventListener("click", function () { showStep(Math.max(0, step - 1)); });
  $("skip-btn").addEventListener("click", function () {
    if (step === 0) { finishSurvey(Object.assign(readForm(), { completed: !!(profile && profile.completed) })); return; }
    steps[step].querySelectorAll("input:checked").forEach(function (i) { i.checked = false; });
    if (step < steps.length - 1) showStep(step + 1); else finishSurvey(readForm());
  });
  function openSurvey(returnTo) {
    afterSurvey = returnTo || "chat";
    fillForm(profile);
    show("survey");
    showStep(profile && profile.completed ? 1 : 0);
  }
  function finishSurvey(p) {
    profile = p;
    persistProfile();
    if (pendingAfterAuth === "share" && session) { pendingAfterAuth = ""; openCreate(); return; }
    show("matching");
    setTimeout(function () {
      const dest = afterSurvey;
      afterSurvey = "chat";
      if (location.hash === "#" + dest) route(); else go(dest);
    }, p.completed ? 900 : 150);
  }

  /* ------------------------------------------------------------------ *
   * Accounts: welcome page, create account, log in, guest mode
   * ------------------------------------------------------------------ */
  let pendingAfterAuth = "";
  let syncTimer;
  function persistProfile() { save(KEY, profile); queueSync(); }
  function queueSync() { if (!session) return; clearTimeout(syncTimer); syncTimer = setTimeout(pushAccount, 400); }
  async function pushAccount() {
    if (!session) return "";
    try { await api("/api/me", { method: "PUT", body: { profile: profile || {} } }); return ""; }
    catch (e) { return e.status === 401 ? t("share.loginAgain") : t("auth.unreachable"); }
  }
  function setSender(id) {
    if (id === senderId) return;
    senderId = id;
    $("messages").replaceChildren();
    $("quick-replies").replaceChildren();
    languageSentToBot = false;
  }
  function setSession(data) {
    session = { token: data.token, user: { id: data.user.id, email: data.user.email, name: data.user.name } };
    save(SESSION_KEY, session);
    forget([GUEST_KEY]);
    setSender(session.user.id);
    updateAccountUI();
  }
  function endSession() {
    session = null;
    forget([SESSION_KEY]);
    setSender(guestId);
    updateAccountUI();
  }
  function applyAccount(user) {
    const sp = user.profile || {};
    if (sp.completed || sp.name) profile = Object.assign({}, sp);
    if (profile && !profile.name && user.name) profile.name = user.name;
    save(KEY, profile);
    if (!(sp.completed || sp.name) && profile) queueSync();
  }
  function updateAccountUI() {
    $("account-btn").textContent = session ? "👤 " + (displayName() || session.user.email) : t("account.login");
    $("logout-btn").hidden = !session;
  }
  async function logout() {
    if (session) { try { await api("/api/logout", { method: "POST" }); } catch (e) {} }
    endSession();
    profile = null; saved = new Set();
    forget([KEY, SAVED_KEY, GUEST_KEY]);
    form.reset();
    showWelcome();
    toast(t("auth.loggedOut"));
  }
  function startOver() {
    if (session) { logout(); return; }
    forget([KEY, SAVED_KEY, GUEST_KEY]);
    profile = null; saved = new Set();
    form.reset();
    showWelcome();
  }
  $("logout-btn").addEventListener("click", logout);
  $("account-btn").addEventListener("click", function () { if (session) go("settings"); else openAuth("login"); });

  let authMode = "register";
  function openAuth(mode, message) {
    authMode = mode;
    const reg = mode === "register";
    $("auth-title").textContent = t(reg ? "auth.registerTitle" : "auth.loginTitle");
    $("auth-lead").textContent = message || t(reg ? "auth.registerLead" : "auth.loginLead");
    $("auth-lead").classList.toggle("intro-alert", !!message);
    $("a-name-wrap").hidden = !reg;
    $("a-confirm-wrap").hidden = !reg;
    $("a-email-help").hidden = !reg;
    $("a-password-help").hidden = !reg;
    $("a-password").setAttribute("autocomplete", reg ? "new-password" : "current-password");
    $("a-submit").textContent = t(reg ? "auth.submitRegister" : "auth.submitLogin");
    $("auth-switch-text").textContent = t(reg ? "auth.haveAccount" : "auth.new");
    $("auth-switch").textContent = t(reg ? "auth.switchLogin" : "auth.switchRegister");
    $("a-error").textContent = "";
    $("a-password").value = ""; $("a-confirm").value = "";
    show("auth");
    $("auth-title").focus();
    if (readAloud) speak($("auth-title").textContent + ". " + $("auth-lead").textContent);
  }
  $("a-show").addEventListener("change", function (e) {
    ["a-password", "a-confirm"].forEach(function (id) { $(id).type = e.target.checked ? "text" : "password"; });
  });
  $("auth-form").addEventListener("submit", async function (e) {
    e.preventDefault();
    const reg = authMode === "register";
    const email = $("a-email").value.trim();
    const name = $("a-name").value.trim();
    const password = $("a-password").value;
    function fail(msg, field) { $("a-error").textContent = msg; if (field) $(field).focus(); if (readAloud) speak(msg); }
    if (!email) return fail(t("auth.needEmail"), "a-email");
    if (reg && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) return fail(t("auth.badEmail"), "a-email");
    if (reg && !name) return fail(t("auth.needName"), "a-name");
    if (!password) return fail(t("auth.needPassword"), "a-password");
    if (reg && password.length < 6) return fail(t("auth.shortPassword"), "a-password");
    if (reg && password !== $("a-confirm").value) return fail(t("auth.mismatch"), "a-confirm");
    $("a-submit").disabled = true;
    try {
      const body = { email: email, password: password };
      if (reg) { body.name = name; body.profile = Object.assign({}, profile || {}, { name: (profile && profile.name) || name }); }
      const data = await api(reg ? "/api/register" : "/api/login", { method: "POST", body: body });
      const guest = senderId;
      setSession(data);
      applyAccount(data.user);
      // Bring this device's guest saves along.
      try {
        const merged = await api("/api/saved/merge", { method: "POST", body: { from: guest } });
        saved = new Set((merged.saved || []).map(Number));
        save(SAVED_KEY, Array.from(saved));
      } catch (err) { await loadSaved(); }
      $("auth-form").reset();
      await loadEvents();
      toast(t(reg ? "auth.welcomeNew" : "auth.welcomeBack", { name: displayName() || email }));
      afterSignIn();
    } catch (err) {
      fail(err.status ? err.message : t("auth.unreachable"));
    } finally { $("a-submit").disabled = false; }
  });
  function afterSignIn() {
    const next = pendingAfterAuth;
    if (!profile || !profile.completed) { openSurvey(next === "share" ? "events" : "chat"); return; }
    pendingAfterAuth = "";
    if (next === "share") openCreate();
    else if (next === "community-post") { go("community"); setTimeout(function () { $("open-post").click(); }, 50); }
    else go(next || "chat");
  }
  $("auth-switch").addEventListener("click", function () {
    openAuth(authMode === "register" ? "login" : "register", pendingAfterAuth ? $("auth-lead").textContent : "");
  });
  function continueAsGuest() {
    pendingAfterAuth = "";
    save(GUEST_KEY, true);
    if (profile) go("chat"); else openSurvey();
  }
  $("auth-guest").addEventListener("click", continueAsGuest);
  $("w-guest").addEventListener("click", continueAsGuest);
  $("w-register").addEventListener("click", function () { openAuth("register"); });
  $("w-login").addEventListener("click", function () { openAuth("login"); });
  $("auth-back").addEventListener("click", function () {
    pendingAfterAuth = "";
    if (knownVisitor()) route(); else showWelcome();
  });
  function renderWelcome() {
    const list = $("welcome-events");
    list.replaceChildren();
    const upcoming = events.map(function (ev) { return { ev: ev, d: eventDate(ev) }; }).sort(function (a, b) { return a.d - b.d; });
    const picked = [], seen = {};
    upcoming.forEach(function (x) { if (!seen[x.ev.source] && picked.length < 4) { seen[x.ev.source] = 1; picked.push(x); } });
    upcoming.forEach(function (x) { if (picked.length < 4 && picked.indexOf(x) < 0) picked.push(x); });
    picked.sort(function (a, b) { return a.d - b.d; }).forEach(function (x) {
      const li = el("li", "preview-item");
      li.appendChild(dateBlock(x.d));
      const box = el("div", "preview-text");
      box.appendChild(el("strong", null, x.ev.title));
      box.appendChild(el("span", null, x.ev.sourceIcon + " " + x.ev.sourceName + " · " + timeRange(x.ev)));
      li.appendChild(box);
      list.appendChild(li);
    });
    $("welcome-events").parentElement.hidden = !picked.length;
  }
  function showWelcome() {
    renderWelcome();
    show("welcome");
  }

  /* ------------------------------------------------------------------ *
   * Share an event (guided form, sub-page of Events)
   * ------------------------------------------------------------------ */
  const cForm = $("create-form");
  const cSteps = Array.from(cForm.querySelectorAll(".c-step"));
  const C_LAST_INPUT = 3, C_REVIEW = 4, C_DONE = 5;
  let cStep = 0;
  (function () {
    const sel = $("ev-time");
    sel.appendChild(new Option("—", ""));
    for (let m = 7 * 60; m <= 21 * 60; m += 30) sel.appendChild(new Option(formatClock(m), formatClock(m)));
  }());
  function quickDates() {
    const box = $("ev-date-quick");
    box.replaceChildren();
    const td = today0();
    const opts = [["share.today", 0], ["share.tomorrow", 1]];
    const toSat = (6 - td.getDay() + 7) % 7 || 7;
    if (toSat > 1) opts.push(["share.saturday", toSat]);
    opts.push(["share.nextWeek", 7]);
    opts.forEach(function (o) {
      const d = new Date(td); d.setDate(d.getDate() + o[1]);
      const b = button("pill", t(o[0]) + " · " + d.toLocaleDateString(I.locale(), { month: "short", day: "numeric" }), function () { $("ev-date").value = b.dataset.date; syncQuick(); });
      b.dataset.date = isoDate(d);
      box.appendChild(b);
    });
    $("ev-date").min = isoDate(td);
  }
  function syncQuick() {
    $("ev-date-quick").querySelectorAll("button").forEach(function (b) { b.setAttribute("aria-pressed", String(b.dataset.date === $("ev-date").value)); });
  }
  $("ev-date").addEventListener("change", syncQuick);
  cForm.addEventListener("change", function (e) { if (e.target.name === "ev-cost") $("ev-cost-other").hidden = e.target.value !== "other"; });
  function cValues(name) { return Array.from(cForm.querySelectorAll('input[name="' + name + '"]:checked')).map(function (i) { return i.value; }); }
  function draft() {
    const tags = cValues("ev-tags");
    const cost = cValues("ev-cost")[0] === "other" ? ($("ev-cost-other").value.trim() || "Small fee") : "Free";
    const needs = cValues("ev-needs");
    if (cost === "Free") needs.push("free");
    return {
      title: $("ev-title").value.trim(), tags: tags, category: tags.length ? intLabel(tags[0]) : "Community",
      description: $("ev-desc").value.trim(), date: $("ev-date").value, time: $("ev-time").value,
      location: $("ev-place").value.trim(), area: cValues("ev-area")[0] || "", group: cValues("ev-group")[0] || "small",
      cost: cost, needs: needs, host: $("ev-host").value.trim() || displayName()
    };
  }
  function problemFor(s, d) {
    if (s === 0 && !d.title) return ["ev-title", t("share.needTitle")];
    if (s === 1 && !d.date) return ["ev-date", t("share.needDate")];
    if (s === 1 && d.date < isoDate(new Date())) return ["ev-date", t("share.pastDate")];
    if (s === 1 && !d.time) return ["ev-time", t("share.needTime")];
    if (s === 2 && !d.location) return ["ev-place", t("share.needPlace")];
    return null;
  }
  function reviewRow(dl, label, value, s) {
    const dd = el("dd", null, value || "—");
    const edit = button("btn btn-link", t("share.edit"), function () { showCStep(s); });
    edit.setAttribute("aria-label", t("share.edit") + ": " + label);
    dd.appendChild(edit);
    dl.append(el("dt", null, label), dd);
  }
  function renderReview() {
    const d = draft();
    const dl = $("ev-review");
    dl.replaceChildren();
    reviewRow(dl, t("share.rWhat"), d.title, 0);
    reviewRow(dl, t("share.rKind"), d.tags.map(intLabel).join(", "), 0);
    reviewRow(dl, t("share.rDesc"), d.description, 0);
    reviewRow(dl, t("share.rWhen"), longDate(new Date(d.date + "T12:00")) + " " + t("share.at") + " " + d.time, 1);
    reviewRow(dl, t("share.rWhere"), d.location + (d.area ? " (" + areaText(d.area) + ")" : ""), 2);
    reviewRow(dl, t("share.rGroup"), t("share." + d.group), 3);
    reviewRow(dl, t("share.rCost"), d.cost, 3);
    reviewRow(dl, t("share.rOffers"), d.needs.filter(function (n) { return n !== "free"; }).map(function (n) { return t("need." + n); }).join(", "), 3);
    reviewRow(dl, t("share.rHost"), d.host, 3);
  }
  function showCStep(n) {
    cStep = n;
    cSteps.forEach(function (s, i) { s.hidden = i !== n; });
    $("c-error").textContent = "";
    $("c-step-count").textContent = n === C_DONE ? "" : t("survey.step", { n: n + 1, total: C_REVIEW + 1 });
    $("c-progress-bar").style.width = (Math.min(n, C_REVIEW) / C_REVIEW) * 100 + "%";
    $("c-back").hidden = n === 0 || n === C_DONE;
    $("c-cancel").hidden = n === C_DONE;
    $("c-next").textContent = t(n === C_REVIEW ? "share.post" : n === C_DONE ? "share.seeAll" : n === C_LAST_INPUT ? "share.review" : "share.next");
    $("c-next").disabled = false;
    if (n === C_REVIEW) renderReview();
    const heading = cSteps[n].querySelector(".step-title");
    if (heading) { heading.setAttribute("tabindex", "-1"); heading.focus(); }
    if (readAloud && heading) speak(heading.textContent);
  }
  function openCreate() {
    if (!session) { pendingAfterAuth = "share"; openAuth("register", t("auth.shareFirst")); return; }
    if (location.hash !== "#share") history.pushState(null, "", "#share");
    cForm.reset();
    $("ev-cost-other").hidden = true;
    const free = cForm.querySelector('input[name="ev-cost"][value="Free"]');
    if (free) free.checked = true;
    const small = cForm.querySelector('input[name="ev-group"][value="small"]');
    if (small) small.checked = true;
    $("ev-host").value = displayName();
    quickDates();
    show("create");
    showCStep(0);
  }
  async function postEvent() {
    const b = $("c-next");
    b.disabled = true;
    b.textContent = t("share.posting");
    try {
      await api("/api/events", { method: "POST", body: draft() });
      await loadEvents();
      showCStep(C_DONE);
    } catch (e) {
      if (e.status === 401) { pendingAfterAuth = "share"; openAuth("login", t("share.loginAgain")); return; }
      $("c-error").textContent = e.message && e.message.length < 160 ? e.message : t("share.failed");
      b.disabled = false;
      b.textContent = t("share.tryAgain");
    }
  }
  cForm.addEventListener("submit", function (e) {
    e.preventDefault();
    if (cStep === C_DONE) { sortMode = "date"; go("events"); toast(t("share.posted")); return; }
    if (cStep === C_REVIEW) { postEvent(); return; }
    const problem = problemFor(cStep, draft());
    if (problem) { $("c-error").textContent = problem[1]; $(problem[0]).focus(); if (readAloud) speak(problem[1]); return; }
    showCStep(cStep + 1);
  });
  $("c-back").addEventListener("click", function () { showCStep(Math.max(0, cStep - 1)); });
  $("c-cancel").addEventListener("click", function () { go("events"); });
  $("open-create").addEventListener("click", openCreate);

  /* ------------------------------------------------------------------ *
   * Chat with the Rasa assistant
   * ------------------------------------------------------------------ */
  const messages = $("messages");
  const quickReplies = $("quick-replies");
  const input = $("message-input");
  const status = $("speech-status");
  let languageSentToBot = false;

  function addMessage(text, kind) {
    const m = el("p", "message " + kind, text);
    messages.appendChild(m);
    messages.scrollTop = messages.scrollHeight;
    if (kind === "assistant" && readAloud) speak(text);
    return m;
  }
  function chatEventCard(ce) {
    const ev = events.find(function (e) { return e.id === ce.id; }) || fromApi({
      id: ce.id, title: ce.title, date: ce.date, time: ce.time, endTime: ce.end_time, place: ce.location,
      host: ce.host || "", desc: ce.description || "", tags: [], source: ce.source, sourceName: ce.source_name,
      sourceIcon: ce.source_icon, sourceUrl: ce.source_url, ticketUrl: ce.ticket_url, sample: ce.sample
    });
    const box = el("div", "message assistant chat-event");
    box.appendChild(el("strong", null, "📅 " + ev.title));
    box.appendChild(el("span", "meta", shortDate(eventDate(ev)) + " · " + timeRange(ev)));
    box.appendChild(el("span", "meta", "📍 " + ev.place + (ce.miles != null ? " · " + t("card.miles", { n: ce.miles }) : "")));
    box.appendChild(el("span", "meta", ev.sourceIcon + " " + ev.sourceName + (ev.sample ? " · " + t("card.sample") : "")));
    const row = el("div", "chat-event-actions");
    const isSaved = saved.has(ev.id);
    const sv = button("btn btn-small " + (isSaved ? "btn-done" : "btn-primary"), isSaved ? t("chat.saved") : t("chat.save"), function () {
      toggleSaved(ev);
      const now = saved.has(ev.id);
      sv.textContent = now ? t("chat.saved") : t("chat.save");
      sv.className = "btn btn-small " + (now ? "btn-done" : "btn-primary");
    });
    row.appendChild(sv);
    if (ev.sourceUrl) row.appendChild(link("btn btn-ghost btn-small", t("card.website"), ev.sourceUrl));
    if (ev.ticketUrl) row.appendChild(link("btn btn-ghost btn-small", t("card.tickets"), ev.ticketUrl));
    box.appendChild(row);
    messages.appendChild(box);
  }
  function offlineReply() {
    addMessage(t("chat.offline"), "assistant");
    quickReplies.replaceChildren(button("btn btn-secondary btn-chip", t("chat.showEvents"), function () { go("events"); }));
  }
  function displayResponses(responses) {
    quickReplies.replaceChildren();
    const failed = (responses || []).some(function (r) { return r.text && /trouble with that/i.test(r.text); });
    if (!responses || !responses.length || failed) { offlineReply(); return; }
    responses.forEach(function (r) {
      if (r.text) addMessage(r.text, "assistant");
      if (r.custom && Array.isArray(r.custom.events)) r.custom.events.forEach(chatEventCard);
      if (r.custom && (r.custom.event_created || r.custom.saved_event || r.custom.reminder)) {
        if (window.BloomReminders) window.BloomReminders.reload();
        loadEvents().then(loadSaved).then(rerender);
      }
      (r.buttons || []).forEach(function (btn) {
        const about = /^(tell me about|cuéntame sobre)\s+/i.test(btn.title);
        const label = about ? "ℹ️ " + btn.title.replace(/^(tell me about|cuéntame sobre)\s+/i, "") : btn.title;
        const q = button("btn btn-secondary btn-chip" + (about ? " btn-chip-event" : ""), label, function () { sendMessage(btn.payload, false, btn.title); });
        q.title = btn.title;
        q.setAttribute("aria-label", btn.title);
        quickReplies.appendChild(q);
      });
    });
    messages.scrollTop = messages.scrollHeight;
  }
  async function postToBot(msg) {
    const ctrl = new AbortController();
    const timer = setTimeout(function () { ctrl.abort(); }, 30000);
    const res = await fetch("/webhooks/rest/webhook", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sender: senderId, message: msg,
        metadata: { language: I.lang, interests: (profile && profile.interests) || [], times: (profile && profile.times) || [] } }),
      signal: ctrl.signal
    });
    clearTimeout(timer);
    if (!res.ok) throw new Error(String(res.status));
    return res.json();
  }
  async function syncLanguageToBot() {
    if (languageSentToBot) return;
    try { await postToBot('/set_language{"lang":"' + I.lang + '"}'); languageSentToBot = true; } catch (e) {}
  }
  async function sendMessage(text, showUser, shownAs) {
    const msg = String(text || "").trim();
    if (!msg) return;
    if (showUser) addMessage(msg, "user");
    else if (shownAs) addMessage(shownAs, "user");
    input.value = "";
    $("send-button").disabled = true;
    status.textContent = t("chat.thinking");
    try {
      await syncLanguageToBot();
      displayResponses(await postToBot(msg));
    } catch (e) { offlineReply(); }
    finally { status.textContent = ""; $("send-button").disabled = false; input.focus(); }
  }
  function startChat() {
    if (messages.children.length) { input.focus(); return; }
    addMessage(t("chat.greeting", { name: displayName() ? " " + displayName() : "" }), "assistant");
    quickReplies.replaceChildren();
    [["chat.q.week", "chat.q.weekMsg"], ["chat.q.garden", "chat.q.gardenMsg"], ["chat.q.near", "chat.q.nearMsg"],
     ["chat.q.volunteer", "chat.q.volunteerMsg"], ["chat.q.post", "chat.q.postMsg"]].forEach(function (q) {
      quickReplies.appendChild(button("btn btn-secondary btn-chip", t(q[0]), function () {
        if (q[0] === "chat.q.post" && !session) { pendingAfterAuth = "chat"; openAuth("register", t("auth.shareFirst")); return; }
        sendMessage(t(q[1]), true);
      }));
    });
    syncLanguageToBot();
  }
  $("chat-form").addEventListener("submit", function (e) { e.preventDefault(); sendMessage(input.value, true); });
  input.addEventListener("keydown", function (e) { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(input.value, true); } });
  $("chat-back").addEventListener("click", function () { sendMessage("/go_back", false, t("chat.back")); });

  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  const mic = $("mic-button");
  if (!SR) mic.hidden = true;
  else {
    const rec = new SR();
    rec.interimResults = false;
    rec.onstart = function () { mic.textContent = t("chat.listening"); status.textContent = t("chat.speakNow"); };
    rec.onresult = function (e) { input.value = e.results[0][0].transcript; status.textContent = t("chat.check"); };
    rec.onerror = function () { status.textContent = t("chat.notHeard"); };
    rec.onend = function () { mic.textContent = t("chat.speak"); };
    mic.addEventListener("click", function () { rec.lang = I.locale(); try { rec.start(); } catch (e) {} });
  }

  /* ------------------------------------------------------------------ *
   * Start
   * ------------------------------------------------------------------ */
  window.Bloom = { api: api, t: t, el: el, button: button, toast: toast, eventDate: eventDate, downloadIcs: downloadIcs,
    rerender: rerender, get senderId() { return senderId; }, get session() { return session; },
    get profile() { return profile; }, get config() { return config; } };
  I.apply();
  if (window.matchMedia && window.matchMedia("(max-width: 760px)").matches) $("more-filters").open = false;
  buildAllChoices();
  renderLangSwitches();
  applyDisplay();
  updateAccountUI();
  (async function start() {
    if (params.has("demo")) {
      try { const data = await api("/api/login", { method: "POST", body: { email: "demo@bloom.local", password: "demo" } }); setSession(data); applyAccount(data.user); } catch (e) {}
    } else if (session) {
      try { applyAccount((await api("/api/me")).user); } catch (e) { /* offline or logged out */ }
    }
    route();
    if (profile && profile.language && profile.language !== I.lang) setLanguage(profile.language);
    await loadEvents();
    await loadSaved();
    rerender();
  }());
  async function refreshBoard() {
    if (document.hidden || ["survey", "create", "auth"].indexOf(currentView) >= 0) return;
    if (await loadEvents()) rerender();
  }
  setInterval(refreshBoard, 120000);
  document.addEventListener("visibilitychange", refreshBoard);
}());
