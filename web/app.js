(function () {
  "use strict";

  /* ------------------------------------------------------------------ *
   * Survey options
   * ------------------------------------------------------------------ */
  const INTERESTS = [
    ["gardening", "🌱", "Gardening"],
    ["music", "🎵", "Music & concerts"],
    ["crafts", "🧶", "Arts & crafts"],
    ["books", "📚", "Book clubs & reading"],
    ["walking", "🚶", "Walking & nature"],
    ["fitness", "🧘", "Gentle exercise (yoga, tai chi)"],
    ["games", "🃏", "Cards, bingo & board games"],
    ["cooking", "🥧", "Cooking & potlucks"],
    ["faith", "🕊️", "Faith & spiritual groups"],
    ["volunteering", "🤝", "Volunteering"],
    ["learning", "🎓", "Classes & lifelong learning"],
    ["tech", "💻", "Help with phones & computers"],
    ["history", "🏛️", "History & museums"],
    ["dancing", "💃", "Dancing"],
    ["health", "❤️", "Health & wellness talks"],
    ["movies", "🎬", "Movies & theater"],
    ["family", "👨‍👩‍👧", "Grandkids & family outings"],
    ["social", "☕", "Coffee & conversation"]
  ];
  const AREAS = [
    ["downtown", "Downtown"], ["west", "West Salem"], ["south", "South Salem"],
    ["northeast", "Northeast"], ["east", "East / Southeast"], ["keizer", "Keizer"], ["unsure", "Not sure"]
  ];
  const DISTANCES = [["near", "Close to home"], ["town", "Anywhere in Salem"], ["far", "I’ll go farther for the right thing"]];
  const TRANSPORT = [["drive", "I drive"], ["ride", "Rides from family/friends"], ["bus", "Bus (Cherriots)"], ["needride", "I could use help getting rides"]];
  const DAYS = [["Mon", "Mon"], ["Tue", "Tue"], ["Wed", "Wed"], ["Thu", "Thu"], ["Fri", "Fri"], ["Sat", "Sat"], ["Sun", "Sun"]];
  const TIMES = [["morning", "Mornings"], ["afternoon", "Afternoons"], ["evening", "Evenings"]];
  const GROUPS = [["small", "Small & cozy"], ["large", "Big & lively"], ["either", "Either is fine"]];
  const NEEDS = [
    ["accessible", "Wheelchair accessible"], ["seating", "Seating available"], ["hearing", "Hearing assistance"],
    ["free", "Free or low cost"], ["bus", "Near a bus line"], ["parking", "Easy parking"]
  ];
  const INTEREST_LABEL = Object.fromEntries(INTERESTS.map(function (i) { return [i[0], i[2]]; }));
  const AREA_LABEL = Object.fromEntries(AREAS);
  const NEED_LABEL = Object.fromEntries(NEEDS);

  /* ------------------------------------------------------------------ *
   * Sample events (fictional — for demo). `day` = days from today.
   * ------------------------------------------------------------------ */
  const EVENTS = [
    { id: 1, title: "Morning Garden Club: Planting Winter Bulbs", day: 1, time: "10:00 AM", tod: "morning", place: "Bush’s Pasture Park greenhouse", area: "south", tags: ["gardening", "walking", "social"], group: "small", cost: "Free", needs: ["accessible", "seating", "parking", "free"], host: "Bloom Garden Friends", desc: "Get your hands in the soil and plant tulip and daffodil bulbs for spring. Gloves, tools and hot cider provided. No experience needed." },
    { id: 2, title: "Chair Yoga for Every Body", day: 1, time: "9:30 AM", tod: "morning", place: "Center 50+ Activity Room", area: "northeast", tags: ["fitness", "health"], group: "small", cost: "$3", needs: ["accessible", "seating", "bus", "parking", "free"], host: "Instructor Linda M.", desc: "A slow, friendly yoga class done entirely from a chair. Great for balance, flexibility and easing stiff joints." },
    { id: 3, title: "Afternoon Book Circle: Cozy Mysteries", day: 2, time: "2:00 PM", tod: "afternoon", place: "Salem Public Library, Room B", area: "downtown", tags: ["books", "social", "learning"], group: "small", cost: "Free", needs: ["accessible", "seating", "hearing", "bus", "free"], host: "Library volunteers", desc: "This month we’re reading a light, cozy mystery. Large-print and audiobook copies are available at the front desk." },
    { id: 4, title: "Big Band Afternoon Dance", day: 3, time: "1:30 PM", tod: "afternoon", place: "Grand Hall on Commercial St", area: "downtown", tags: ["dancing", "music", "social"], group: "large", cost: "$5", needs: ["accessible", "seating", "bus"], host: "Willamette Swing Society", desc: "A live 12-piece band plays classics from the 40s and 50s. Dance, tap your toes, or just enjoy the music from a comfy seat." },
    { id: 5, title: "Smartphone Help Hour", day: 2, time: "10:30 AM", tod: "morning", place: "West Salem Community Room", area: "west", tags: ["tech", "learning"], group: "small", cost: "Free", needs: ["accessible", "seating", "parking", "free"], host: "High school tech volunteers", desc: "Bring your phone or tablet and your questions. Patient student volunteers help with photos, video calls with family, texting and more." },
    { id: 6, title: "Riverfront Walking Group", day: 4, time: "8:30 AM", tod: "morning", place: "Riverfront Park, carousel entrance", area: "downtown", tags: ["walking", "fitness", "social"], group: "small", cost: "Free", needs: ["bus", "parking", "free"], host: "Walk Salem", desc: "An easy, flat 1-mile loop along the river at a conversational pace. Benches along the way and coffee afterwards for those who’d like it." },
    { id: 7, title: "Community Potluck & Recipe Swap", day: 5, time: "5:30 PM", tod: "evening", place: "First Street Fellowship Hall", area: "northeast", tags: ["cooking", "social", "faith"], group: "large", cost: "Free (bring a dish if you can)", needs: ["accessible", "seating", "parking", "free"], host: "Neighbors of NE Salem", desc: "Bring a favorite dish and the recipe card to swap. Coming empty-handed is perfectly fine too, there’s always plenty." },
    { id: 8, title: "Knit & Chat Circle", day: 3, time: "10:00 AM", tod: "morning", place: "The Yarn Nook café", area: "south", tags: ["crafts", "social"], group: "small", cost: "Free", needs: ["seating", "parking", "free"], host: "Knit & Chat regulars", desc: "Knitters, crocheters and beginners welcome. This season we’re making hats and scarves to donate to a local shelter." },
    { id: 9, title: "Bingo Bonanza", day: 6, time: "1:00 PM", tod: "afternoon", place: "Keizer Community Center", area: "keizer", tags: ["games", "social"], group: "large", cost: "$2 per card", needs: ["accessible", "seating", "hearing", "parking"], host: "Keizer Lions Club", desc: "Afternoon bingo with fun prizes and snacks. Large-print cards are available." },
    { id: 10, title: "Willamette Valley History Talk", day: 7, time: "2:00 PM", tod: "afternoon", place: "Mission Mill Museum", area: "downtown", tags: ["history", "learning"], group: "large", cost: "$4 (free for members)", needs: ["accessible", "seating", "hearing", "bus"], host: "Local historian Dr. Ruth Alvarez", desc: "Old photographs and stories about how Salem grew along the river. Stay for questions and tea afterwards." },
    { id: 11, title: "Food Bank Volunteer Morning", day: 8, time: "9:00 AM", tod: "morning", place: "Marion-Polk Food Share warehouse", area: "east", tags: ["volunteering", "social"], group: "large", cost: "Free", needs: ["accessible", "seating", "parking", "free"], host: "Volunteer coordinator", desc: "Sort and pack food for families in need. Seated tasks are available. A great way to meet people while helping out." },
    { id: 12, title: "Classic Movie Matinee: Musicals", day: 9, time: "1:00 PM", tod: "afternoon", place: "Historic Elsinore Theatre", area: "downtown", tags: ["movies", "music"], group: "large", cost: "$5", needs: ["accessible", "seating", "hearing", "bus"], host: "Elsinore Friends", desc: "A beloved classic musical on the big screen. Captions are on, and popcorn is included." },
    { id: 13, title: "Tai Chi in the Park", day: 10, time: "9:00 AM", tod: "morning", place: "Minto-Brown Island Park shelter", area: "south", tags: ["fitness", "walking", "health"], group: "small", cost: "Free", needs: ["parking", "free"], host: "Instructor Wei Chen", desc: "Slow, flowing movements for balance and calm. Moved under the shelter if it rains." },
    { id: 14, title: "Grandparents & Grandkids Craft Day", day: 11, time: "11:00 AM", tod: "morning", place: "West Salem Library branch", area: "west", tags: ["family", "crafts"], group: "large", cost: "Free", needs: ["accessible", "seating", "parking", "free"], host: "Library children’s staff", desc: "Make holiday ornaments together. All supplies provided. Kids 4 to 12 with a grandparent or special adult." },
    { id: 15, title: "Healthy Aging: Sleep & Memory", day: 12, time: "3:00 PM", tod: "afternoon", place: "Salem Health Community Room", area: "northeast", tags: ["health", "learning"], group: "large", cost: "Free", needs: ["accessible", "seating", "hearing", "bus", "parking", "free"], host: "Community nurse educator", desc: "A friendly talk with practical tips for better sleep and keeping your memory sharp. Q&A to follow." },
    { id: 16, title: "Evening Choir Sing-Along", day: 13, time: "6:30 PM", tod: "evening", place: "Court Street Chapel", area: "downtown", tags: ["music", "faith", "social"], group: "large", cost: "Free", needs: ["accessible", "seating", "bus", "free"], host: "Court Street Singers", desc: "No auditions, no pressure. Come sing seasonal favorites or just listen. Lyric sheets in large print." },
    { id: 17, title: "Coffee & Conversation Morning", day: 4, time: "10:00 AM", tod: "morning", place: "Broadway Commons Café", area: "downtown", tags: ["social"], group: "small", cost: "Coffee on us", needs: ["accessible", "seating", "bus", "free"], host: "Bloom neighbors", desc: "A relaxed table for anyone who wants to meet new people. A host will greet you at the door, so you’ll never be sitting alone." },
    { id: 18, title: "Bridge & Cribbage Club", day: 9, time: "6:00 PM", tod: "evening", place: "South Salem Senior Center", area: "south", tags: ["games", "social"], group: "small", cost: "Free", needs: ["accessible", "seating", "parking", "free"], host: "Card club members", desc: "Friendly games for all skill levels. Want to learn bridge? A teacher sets aside the first half hour for beginners." },
    { id: 19, title: "Watercolor for Beginners", day: 14, time: "1:00 PM", tod: "afternoon", place: "Keizer Art Association", area: "keizer", tags: ["crafts", "learning"], group: "small", cost: "$10, supplies included", needs: ["accessible", "seating", "parking"], host: "Artist June Park", desc: "Paint a simple autumn landscape step by step. You’ll take your painting home. Absolutely no experience needed." },
    { id: 20, title: "Birdwatching Stroll", day: 6, time: "8:00 AM", tod: "morning", place: "Fairmount Hill trailhead", area: "south", tags: ["walking", "learning"], group: "small", cost: "Free", needs: ["free"], host: "Salem Bird Friends", desc: "Spot winter birds with an experienced guide. Binoculars are available to borrow. Some gentle hills." }
  ];

  /* ------------------------------------------------------------------ *
   * Storage (fails gracefully)
   * ------------------------------------------------------------------ */
  const KEY = "bloom-profile-v1";
  const RSVP_KEY = "bloom-rsvps-v1";
  function load(key, fallback) {
    try { const v = localStorage.getItem(key); return v ? JSON.parse(v) : fallback; } catch (e) { return fallback; }
  }
  function save(key, value) {
    try { localStorage.setItem(key, JSON.stringify(value)); } catch (e) { /* private mode: in-memory only */ }
  }
  if (new URLSearchParams(location.search).has("reset")) {
    try { localStorage.removeItem(KEY); localStorage.removeItem(RSVP_KEY); } catch (e) {}
  }

  // ?demo jumps straight to a filled-in sample profile (handy for presentations).
  if (new URLSearchParams(location.search).has("demo")) {
    save(KEY, {
      name: "Margaret", interests: ["gardening", "books", "fitness", "social"], area: "south", distance: "town",
      transport: ["bus"], days: ["Tue", "Wed", "Thu"], times: ["morning", "afternoon"], group: "small",
      needs: ["seating", "free"], notes: "", completed: true
    });
  }

  let profile = load(KEY, null);
  let rsvps = new Set(load(RSVP_KEY, []));
  let sortMode = "match";
  let readAloud = false;

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
  function eventDate(ev) {
    if (ev.date) {
      const parts = ev.date.split("-").map(Number);
      return new Date(parts[0], parts[1] - 1, parts[2]);
    }
    const d = new Date();
    d.setHours(0, 0, 0, 0);
    d.setDate(d.getDate() + ev.day);
    return d;
  }
  function timeOfDay(t) {
    const m = /^(\d+):\d+ (AM|PM)$/.exec(t || "");
    if (!m) return "afternoon";
    const h = (Number(m[1]) % 12) + (m[2] === "PM" ? 12 : 0);
    return h < 12 ? "morning" : h < 17 ? "afternoon" : "evening";
  }
  function areaText(a) { return AREA_LABEL[a] || "Salem"; }

  /* Community events shared by neighbors (server-backed, visible to everyone) */
  let communityEvents = [];
  function fromApi(e) {
    return {
      id: "c" + e.id, apiId: e.id, community: true, mine: e.createdBy === senderId,
      title: e.title, date: e.date, time: e.time, tod: timeOfDay(e.time), place: e.place, area: e.area,
      tags: e.tags || [], group: e.group, cost: e.cost, needs: e.needs || [], host: e.host, desc: e.desc
    };
  }
  async function loadCommunityEvents() {
    try {
      const res = await fetch("/api/events", { cache: "no-store" });
      if (!res.ok) throw new Error(String(res.status));
      communityEvents = ((await res.json()).events || []).map(fromApi);
    } catch (e) { /* API offline: sample events still work */ }
  }
  function allEvents() { return EVENTS.concat(communityEvents); }
  function dayKey(d) { return d.toLocaleDateString("en-US", { weekday: "short" }); }
  function speak(text) {
    if (!("speechSynthesis" in window)) return;
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.rate = 0.92;
    window.speechSynthesis.speak(u);
  }

  /* ------------------------------------------------------------------ *
   * Survey
   * ------------------------------------------------------------------ */
  function buildChoices(containerId, name, options, type, withIcon) {
    const box = $(containerId);
    options.forEach(function (opt) {
      const label = el("label", withIcon ? "check-card" : "choice");
      const input = document.createElement("input");
      input.type = type;
      input.name = name;
      input.value = opt[0];
      label.appendChild(input);
      if (withIcon) {
        label.appendChild(el("span", "check-icon", opt[1]));
        label.appendChild(el("span", "check-text", opt[2]));
      } else {
        label.appendChild(el("span", "choice-text", opt[1]));
      }
      box.appendChild(label);
    });
  }
  buildChoices("interest-options", "interests", INTERESTS, "checkbox", true);
  buildChoices("area-options", "area", AREAS, "radio");
  buildChoices("distance-options", "distance", DISTANCES, "radio");
  buildChoices("transport-options", "transport", TRANSPORT, "checkbox");
  buildChoices("day-options", "days", DAYS, "checkbox");
  buildChoices("time-options", "times", TIMES, "checkbox");
  buildChoices("group-options", "group", GROUPS, "radio");
  buildChoices("needs-options", "needs", NEEDS, "checkbox");

  const form = $("survey-form");
  const steps = Array.from(form.querySelectorAll(".step"));
  let step = 0;

  function showStep(n) {
    step = n;
    steps.forEach(function (s, i) { s.hidden = i !== n; });
    $("back-btn").hidden = n === 0;
    $("next-btn").textContent = n === 0 ? "Let’s begin →" : n === steps.length - 1 ? "Show my events 🌸" : "Next →";
    $("skip-btn").textContent = n === 0 ? "Skip for now" : "Skip this question";
    $("step-count").textContent = n === 0 ? "" : "Step " + n + " of " + (steps.length - 1);
    $("progress-bar").style.width = (n / (steps.length - 1)) * 100 + "%";
    const heading = steps[n].querySelector(".step-title");
    if (heading) { heading.setAttribute("tabindex", "-1"); heading.focus(); }
    if (readAloud && heading) speak(heading.textContent);
  }

  function values(name) {
    return Array.from(form.querySelectorAll('input[name="' + name + '"]:checked')).map(function (i) { return i.value; });
  }
  function readForm() {
    return {
      name: $("name").value.trim(),
      interests: values("interests"),
      area: values("area")[0] || "",
      distance: values("distance")[0] || "",
      transport: values("transport"),
      days: values("days"),
      times: values("times"),
      group: values("group")[0] || "",
      needs: values("needs"),
      notes: $("notes").value.trim(),
      completed: true
    };
  }
  function fillForm(p) {
    if (!p) return;
    $("name").value = p.name || "";
    $("notes").value = p.notes || "";
    ["interests", "transport", "days", "times", "needs"].forEach(function (n) {
      form.querySelectorAll('input[name="' + n + '"]').forEach(function (i) { i.checked = (p[n] || []).indexOf(i.value) !== -1; });
    });
    ["area", "distance", "group"].forEach(function (n) {
      form.querySelectorAll('input[name="' + n + '"]').forEach(function (i) { i.checked = p[n] === i.value; });
    });
  }

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    if (step < steps.length - 1) { showStep(step + 1); return; }
    finishSurvey(readForm());
  });
  $("back-btn").addEventListener("click", function () { showStep(Math.max(0, step - 1)); });
  $("skip-btn").addEventListener("click", function () {
    if (step === 0) { finishSurvey(Object.assign(readForm(), { completed: false })); return; }
    // clear this step's answers and move on
    steps[step].querySelectorAll("input:checked").forEach(function (i) { i.checked = false; });
    if (step < steps.length - 1) showStep(step + 1); else finishSurvey(readForm());
  });

  function finishSurvey(p) {
    profile = p;
    save(KEY, profile);
    show("matching");
    setTimeout(function () { renderHome(); show("home"); }, p.completed ? 1100 : 200);
  }

  /* ------------------------------------------------------------------ *
   * Matching — transparent, never hides anything
   * ------------------------------------------------------------------ */
  function score(ev) {
    const p = profile || {};
    const reasons = [];
    const cautions = [];
    let s = 0;
    const d = eventDate(ev);

    const hits = ev.tags.filter(function (t) { return (p.interests || []).indexOf(t) !== -1; });
    if (hits.length) {
      s += 4 * hits.length;
      reasons.push("You enjoy " + hits.map(function (h) { return INTEREST_LABEL[h].toLowerCase(); }).join(" and "));
    }
    if ((p.days || []).length && p.days.indexOf(dayKey(d)) !== -1) { s += 2; reasons.push(d.toLocaleDateString("en-US", { weekday: "long" }) + "s work for you"); }
    if ((p.times || []).length) {
      if (p.times.indexOf(ev.tod) !== -1) { s += 2; reasons.push("It’s in the " + ev.tod + ", when you’re free"); }
      else { s -= 1; cautions.push("This is in the " + ev.tod); }
    }
    if (p.area && p.area !== "unsure") {
      if (p.area === ev.area) { s += 3; reasons.push("It’s close to you in " + areaText(ev.area)); }
      else if (p.distance === "near") { s -= 1; cautions.push("It’s a bit farther, in " + areaText(ev.area)); }
    }
    if (p.group && p.group !== "either") {
      if (p.group === ev.group) { s += 1; reasons.push(ev.group === "small" ? "A small, cozy group" : "A big, lively crowd"); }
    }
    (p.needs || []).forEach(function (n) {
      if (ev.needs.indexOf(n) !== -1) { s += 1; }
      else { cautions.push("Check with the host about: " + NEED_LABEL[n].toLowerCase()); }
    });
    if ((p.needs || []).length && (p.needs || []).every(function (n) { return ev.needs.indexOf(n) !== -1; })) {
      reasons.push("Meets what’s important to you (" + p.needs.map(function (n) { return NEED_LABEL[n].toLowerCase(); }).join(", ") + ")");
    }
    if ((p.transport || []).indexOf("bus") !== -1 && ev.needs.indexOf("bus") !== -1 && (p.needs || []).indexOf("bus") === -1) {
      s += 1; reasons.push("Easy to reach by bus");
    }

    let level = "new";
    if (s >= 9) level = "great"; else if (s >= 4) level = "good";
    return { ev: ev, date: d, score: s, reasons: reasons, cautions: cautions, level: level };
  }
  const LEVEL_TEXT = { great: "★ Great match", good: "Good match", new: "Something new to try" };

  /* ------------------------------------------------------------------ *
   * Rendering
   * ------------------------------------------------------------------ */
  function dateBlock(d) {
    const b = el("div", "date-block");
    b.setAttribute("aria-hidden", "true");
    b.appendChild(el("span", "date-dow", d.toLocaleDateString("en-US", { weekday: "short" })));
    b.appendChild(el("span", "date-day", String(d.getDate())));
    b.appendChild(el("span", "date-mon", d.toLocaleDateString("en-US", { month: "short" })));
    return b;
  }

  function card(m, featured) {
    const ev = m.ev;
    const c = el("article", "event-card" + (featured ? " featured" : ""));
    c.dataset.level = m.level;

    const top = el("div", "card-top");
    top.appendChild(dateBlock(m.date));
    const head = el("div", "card-head");
    const badges = el("div", "badges");
    if (profile && profile.completed) badges.appendChild(el("span", "badge badge-" + m.level, LEVEL_TEXT[m.level]));
    if (ev.mine) badges.appendChild(el("span", "badge badge-mine", "✎ Posted by you"));
    else if (ev.community) badges.appendChild(el("span", "badge badge-neighbor", "🏡 Shared by a neighbor"));
    if (badges.children.length) head.appendChild(badges);
    head.appendChild(el("h3", null, ev.title));
    const whenText = m.date.toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric" }) + " · " + ev.time;
    head.appendChild(el("p", "meta", "🗓 " + whenText));
    head.appendChild(el("p", "meta", "📍 " + ev.place + (ev.area ? " (" + areaText(ev.area) + ")" : "")));
    head.appendChild(el("p", "meta", "💵 " + ev.cost));
    top.appendChild(head);
    c.appendChild(top);

    if (profile && profile.completed && (m.reasons.length || m.cautions.length)) {
      const why = el("div", "why");
      if (m.reasons.length) {
        why.appendChild(el("p", "why-title", "Why we suggested this"));
        const ul = el("ul");
        m.reasons.forEach(function (r) { ul.appendChild(el("li", null, r)); });
        why.appendChild(ul);
      }
      if (m.cautions.length) {
        const ul2 = el("ul", "cautions");
        m.cautions.forEach(function (r) { ul2.appendChild(el("li", null, r)); });
        why.appendChild(ul2);
      }
      c.appendChild(why);
    }

    const details = el("div", "details");
    details.hidden = true;
    details.appendChild(el("p", null, ev.desc));
    details.appendChild(el("p", "meta", "Hosted by " + ev.host));
    const access = ev.needs.map(function (n) { return NEED_LABEL[n]; }).join(" · ");
    if (access) details.appendChild(el("p", "meta", "♿ " + access));
    c.appendChild(details);

    const actions = el("div", "card-actions");
    const going = rsvps.has(ev.id);
    const rsvp = el("button", "btn " + (going ? "btn-done" : "btn-primary"), going ? "✓ You’re going" : "I’m interested");
    rsvp.type = "button";
    rsvp.setAttribute("aria-pressed", String(going));
    rsvp.addEventListener("click", function () {
      if (rsvps.has(ev.id)) rsvps.delete(ev.id); else rsvps.add(ev.id);
      save(RSVP_KEY, Array.from(rsvps));
      renderHome();
      if (rsvps.has(ev.id)) toast("Great! We saved " + ev.title + " to your events.");
    });
    const more = el("button", "btn btn-secondary", "More details");
    more.type = "button";
    more.setAttribute("aria-expanded", "false");
    more.addEventListener("click", function () {
      details.hidden = !details.hidden;
      more.setAttribute("aria-expanded", String(!details.hidden));
      more.textContent = details.hidden ? "More details" : "Fewer details";
    });
    const listen = el("button", "btn btn-ghost", "🔊 Listen");
    listen.type = "button";
    listen.addEventListener("click", function () {
      speak(ev.title + ". " + whenText + ", at " + ev.place + ". " + ev.cost + ". " + ev.desc +
        (m.reasons.length ? " We suggested this because: " + m.reasons.join(". ") + "." : ""));
    });
    actions.append(rsvp, more, listen);
    if (ev.mine) {
      const remove = el("button", "btn btn-link", "Remove my event");
      remove.type = "button";
      remove.addEventListener("click", async function () {
        if (!window.confirm("Remove “" + ev.title + "” from Bloom? Neighbors won’t see it anymore.")) return;
        try {
          const res = await fetch("/api/events/" + ev.apiId + "?user=" + encodeURIComponent(senderId), { method: "DELETE" });
          if (!res.ok) throw new Error(String(res.status));
          await loadCommunityEvents();
          renderHome();
          toast("Your event was removed.");
        } catch (e) { toast("Sorry, we couldn’t remove that right now. Please try again."); }
      });
      actions.appendChild(remove);
    }
    c.appendChild(actions);
    return c;
  }

  function greeting() {
    const h = new Date().getHours();
    const part = h < 12 ? "Good morning" : h < 17 ? "Good afternoon" : "Good evening";
    return part + (profile && profile.name ? ", " + profile.name : "") + " 🌸";
  }

  function renderHome() {
    $("greeting").textContent = greeting();
    const chips = $("interest-chips");
    chips.replaceChildren();
    const completed = profile && profile.completed;
    if (completed && profile.interests.length) {
      profile.interests.forEach(function (i) { chips.appendChild(el("span", "chip", INTEREST_LABEL[i])); });
      $("hero-sub").textContent = "Here’s what’s happening around Salem, picked with you in mind.";
      $("edit-profile").textContent = "✏️ Update my interests";
    } else {
      $("hero-sub").textContent = completed
        ? "Here’s what’s happening around Salem."
        : "Here’s what’s happening around Salem. Take our short survey and we’ll put the events you’ll love first.";
      $("edit-profile").textContent = completed ? "✏️ Update my interests" : "🌱 Personalize my events";
    }

    const matches = allEvents().map(score);
    const byMatch = matches.slice().sort(function (a, b) { return b.score - a.score || a.date - b.date; });
    const byDate = matches.slice().sort(function (a, b) { return a.date - b.date || b.score - a.score; });

    const picks = $("top-picks");
    picks.replaceChildren();
    const picksTitle = picks.previousElementSibling;
    if (completed) {
      picksTitle.hidden = false; picks.hidden = false;
      byMatch.slice(0, 3).forEach(function (m) { picks.appendChild(card(m, true)); });
    } else {
      picksTitle.hidden = true; picks.hidden = true;
    }

    const mine = matches.filter(function (m) { return rsvps.has(m.ev.id); });
    $("event-count").textContent = "(" + matches.length + (mine.length ? " · " + mine.length + " saved" : "") + ")";

    const list = $("event-list");
    list.replaceChildren();
    (sortMode === "match" && completed ? byMatch : byDate).forEach(function (m) { list.appendChild(card(m, false)); });
    document.querySelectorAll("[data-sort]").forEach(function (b) {
      b.setAttribute("aria-pressed", String(b.dataset.sort === sortMode));
      if (b.dataset.sort === "match") b.disabled = !completed;
    });
    if (!completed) sortMode = "date";
  }

  document.querySelectorAll("[data-sort]").forEach(function (b) {
    b.addEventListener("click", function () { sortMode = b.dataset.sort; renderHome(); });
  });

  function toast(msg) {
    let t = $("toast");
    if (!t) { t = el("div", "toast"); t.id = "toast"; t.setAttribute("role", "status"); document.body.appendChild(t); }
    t.textContent = msg;
    t.classList.add("show");
    clearTimeout(toast.timer);
    toast.timer = setTimeout(function () { t.classList.remove("show"); }, 3200);
    if (readAloud) speak(msg);
  }

  /* ------------------------------------------------------------------ *
   * Views
   * ------------------------------------------------------------------ */
  function show(view) {
    ["survey", "matching", "home", "create"].forEach(function (v) { $(v).hidden = v !== view; });
    window.scrollTo(0, 0);
  }
  function openSurvey() {
    fillForm(profile);
    show("survey");
    showStep(profile && profile.completed ? 1 : 0);
  }
  $("edit-profile").addEventListener("click", openSurvey);
  $("brand-link").addEventListener("click", function (e) {
    e.preventDefault();
    if (profile) { renderHome(); show("home"); } else openSurvey();
  });
  $("reset").addEventListener("click", function () {
    try { localStorage.removeItem(KEY); localStorage.removeItem(RSVP_KEY); } catch (e) {}
    profile = null; rsvps = new Set(); sortMode = "match";
    form.reset();
    closeChat();
    openSurvey();
  });

  /* ------------------------------------------------------------------ *
   * Share an event — guided, one question group at a time
   * ------------------------------------------------------------------ */
  const cForm = $("create-form");
  const cSteps = Array.from(cForm.querySelectorAll(".c-step"));
  const C_LAST_INPUT = 3, C_REVIEW = 4, C_DONE = 5;
  let cStep = 0;

  buildChoices("ev-tag-options", "ev-tags", INTERESTS, "checkbox", true);
  buildChoices("ev-area-options", "ev-area", AREAS.filter(function (a) { return a[0] !== "unsure"; }), "radio");
  buildChoices("ev-group-options", "ev-group", [["small", "Small & cozy (under 15)"], ["large", "Big & lively"]], "radio");
  buildChoices("ev-cost-options", "ev-cost", [["Free", "Free"], ["other", "There’s a cost"]], "radio");
  buildChoices("ev-needs-options", "ev-needs", NEEDS.filter(function (n) { return n[0] !== "free"; }), "checkbox");

  // Time options every 30 minutes, 7:00 AM – 9:00 PM
  (function () {
    const sel = $("ev-time");
    sel.appendChild(new Option("Choose a time", ""));
    for (let m = 7 * 60; m <= 21 * 60; m += 30) {
      const h = Math.floor(m / 60), mm = m % 60;
      const label = ((h + 11) % 12 + 1) + ":" + (mm ? "30" : "00") + " " + (h < 12 ? "AM" : "PM");
      sel.appendChild(new Option(label, label));
    }
  }());

  function isoDate(d) {
    return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0");
  }
  function quickDates() {
    const box = $("ev-date-quick");
    box.replaceChildren();
    const today = new Date(); today.setHours(0, 0, 0, 0);
    const opts = [["Today", 0], ["Tomorrow", 1]];
    const toSat = (6 - today.getDay() + 7) % 7 || 7;
    if (toSat > 1) opts.push(["This Saturday", toSat]);
    opts.push(["One week from today", 7]);
    opts.forEach(function (o) {
      const d = new Date(today); d.setDate(d.getDate() + o[1]);
      const b = el("button", "pill", o[0] + " · " + d.toLocaleDateString("en-US", { month: "short", day: "numeric" }));
      b.type = "button";
      b.dataset.date = isoDate(d);
      b.addEventListener("click", function () { $("ev-date").value = b.dataset.date; syncQuick(); });
      box.appendChild(b);
    });
    $("ev-date").min = isoDate(today);
  }
  function syncQuick() {
    $("ev-date-quick").querySelectorAll("button").forEach(function (b) {
      b.setAttribute("aria-pressed", String(b.dataset.date === $("ev-date").value));
    });
  }
  $("ev-date").addEventListener("change", syncQuick);
  cForm.addEventListener("change", function (e) {
    if (e.target.name === "ev-cost") $("ev-cost-other").hidden = e.target.value !== "other";
  });

  function cValues(name) {
    return Array.from(cForm.querySelectorAll('input[name="' + name + '"]:checked')).map(function (i) { return i.value; });
  }
  function draft() {
    const tags = cValues("ev-tags");
    const cost = cValues("ev-cost")[0] === "other" ? ($("ev-cost-other").value.trim() || "Small fee") : "Free";
    const needs = cValues("ev-needs");
    if (cost === "Free") needs.push("free");
    return {
      title: $("ev-title").value.trim(),
      tags: tags,
      category: tags.length ? INTEREST_LABEL[tags[0]] : "Community",
      description: $("ev-desc").value.trim(),
      date: $("ev-date").value,
      time: $("ev-time").value,
      location: $("ev-place").value.trim(),
      area: cValues("ev-area")[0] || "",
      group: cValues("ev-group")[0] || "small",
      cost: cost,
      needs: needs,
      host: $("ev-host").value.trim() || (profile && profile.name) || "",
      user: senderId
    };
  }
  function problemFor(step, d) {
    if (step === 0 && !d.title) return ["ev-title", "Please give your event a name."];
    if (step === 1 && !d.date) return ["ev-date", "Please pick a date."];
    if (step === 1 && d.date < isoDate(new Date())) return ["ev-date", "That date has already passed. Please pick another."];
    if (step === 1 && !d.time) return ["ev-time", "Please choose a start time."];
    if (step === 2 && !d.location) return ["ev-place", "Please tell people where the event is."];
    return null;
  }

  function reviewRow(dl, label, value, step) {
    const dt = el("dt", null, label);
    const dd = el("dd", null, value || "—");
    const edit = el("button", "btn btn-link", "Edit");
    edit.type = "button";
    edit.setAttribute("aria-label", "Edit " + label.toLowerCase());
    edit.addEventListener("click", function () { showCStep(step); });
    dd.appendChild(edit);
    dl.append(dt, dd);
  }
  function renderReview() {
    const d = draft();
    const dl = $("ev-review");
    dl.replaceChildren();
    const when = new Date(d.date + "T12:00").toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric" });
    reviewRow(dl, "What", d.title, 0);
    reviewRow(dl, "Kind of event", d.tags.map(function (t) { return INTEREST_LABEL[t]; }).join(", "), 0);
    reviewRow(dl, "Description", d.description, 0);
    reviewRow(dl, "When", when + " at " + d.time, 1);
    reviewRow(dl, "Where", d.location + (d.area ? " (" + areaText(d.area) + ")" : ""), 2);
    reviewRow(dl, "Group", d.group === "large" ? "Big & lively" : "Small & cozy", 3);
    reviewRow(dl, "Cost", d.cost, 3);
    reviewRow(dl, "The place offers", d.needs.filter(function (n) { return n !== "free"; }).map(function (n) { return NEED_LABEL[n]; }).join(", "), 3);
    reviewRow(dl, "Host", d.host || "A Bloom neighbor", 3);
  }

  function showCStep(n) {
    cStep = n;
    cSteps.forEach(function (s, i) { s.hidden = i !== n; });
    $("c-error").textContent = "";
    const total = C_REVIEW;
    $("c-step-count").textContent = n === C_DONE ? "" : "Step " + (n + 1) + " of " + (total + 1);
    $("c-progress-bar").style.width = (Math.min(n, total) / total) * 100 + "%";
    $("c-back").hidden = n === 0 || n === C_DONE;
    $("c-cancel").hidden = n === C_DONE;
    $("c-next").textContent = n === C_REVIEW ? "Post my event 🌸" : n === C_DONE ? "See it with all events →" : n === C_LAST_INPUT ? "Review →" : "Next →";
    $("c-next").disabled = false;
    if (n === C_REVIEW) renderReview();
    const heading = cSteps[n].querySelector(".step-title");
    if (heading) { heading.setAttribute("tabindex", "-1"); heading.focus(); }
    if (readAloud && heading) speak(heading.textContent);
  }

  function openCreate() {
    cForm.reset();
    $("ev-cost-other").hidden = true;
    const free = cForm.querySelector('input[name="ev-cost"][value="Free"]');
    if (free) free.checked = true;
    const small = cForm.querySelector('input[name="ev-group"][value="small"]');
    if (small) small.checked = true;
    if (profile && profile.name) $("ev-host").value = profile.name;
    quickDates();
    closeChat(true);
    show("create");
    showCStep(0);
  }

  async function postEvent() {
    const btn = $("c-next");
    btn.disabled = true;
    btn.textContent = "Posting…";
    try {
      const res = await fetch("/api/events", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(draft())
      });
      const body = await res.json().catch(function () { return {}; });
      if (!res.ok) throw new Error(body.error || "Sorry, we couldn’t post that right now.");
      await loadCommunityEvents();
      showCStep(C_DONE);
    } catch (e) {
      $("c-error").textContent = e.message && e.message.length < 120 ? e.message : "Sorry, we couldn’t post that right now. Please try again in a moment.";
      btn.disabled = false;
      btn.textContent = "Try again";
    }
  }

  cForm.addEventListener("submit", function (e) {
    e.preventDefault();
    if (cStep === C_DONE) { sortMode = "date"; renderHome(); show("home"); toast("Your event is now on Bloom 🌸"); return; }
    if (cStep === C_REVIEW) { postEvent(); return; }
    const problem = problemFor(cStep, draft());
    if (problem) {
      $("c-error").textContent = problem[1];
      $(problem[0]).focus();
      if (readAloud) speak(problem[1]);
      return;
    }
    showCStep(cStep + 1);
  });
  $("c-back").addEventListener("click", function () { showCStep(Math.max(0, cStep - 1)); });
  $("c-cancel").addEventListener("click", function () { renderHome(); show("home"); });
  $("open-create").addEventListener("click", openCreate);

  /* ------------------------------------------------------------------ *
   * Display settings
   * ------------------------------------------------------------------ */
  $("large-text").addEventListener("click", function (e) {
    e.currentTarget.setAttribute("aria-pressed", String(document.body.classList.toggle("large-text")));
  });
  $("contrast").addEventListener("click", function (e) {
    e.currentTarget.setAttribute("aria-pressed", String(document.body.classList.toggle("high-contrast")));
  });
  $("read-aloud").addEventListener("click", function (e) {
    readAloud = !readAloud;
    e.currentTarget.setAttribute("aria-pressed", String(readAloud));
    e.currentTarget.textContent = "🔊 Read aloud: " + (readAloud ? "on" : "off");
    if (!readAloud && "speechSynthesis" in window) window.speechSynthesis.cancel();
    else speak("Read aloud is on.");
  });

  /* ------------------------------------------------------------------ *
   * Ask Bloom chat (Rasa) — optional, degrades gracefully
   * ------------------------------------------------------------------ */
  const messages = $("messages");
  const quickReplies = $("quick-replies");
  const input = $("message-input");
  const status = $("speech-status");
  let senderId;
  try {
    senderId = localStorage.getItem("bloom-user-id");
    if (!senderId) {
      senderId = "bloom-" + (window.crypto && crypto.randomUUID ? crypto.randomUUID() : Date.now() + Math.random().toString(36).slice(2));
      localStorage.setItem("bloom-user-id", senderId);
    }
  } catch (e) { senderId = "bloom-session-" + Date.now(); }

  function addMessage(text, kind) {
    const m = el("p", "message " + kind, text);
    messages.appendChild(m);
    messages.scrollTop = messages.scrollHeight;
    if (kind === "assistant" && readAloud) speak(text);
  }
  function offlineReply() {
    addMessage("I’m having trouble thinking right now, sorry about that! In the meantime, your personalized events are right on the home page, best matches first.", "assistant");
    quickReplies.replaceChildren();
    const b = el("button", "btn btn-secondary", "Show my events");
    b.type = "button";
    b.addEventListener("click", function () { closeChat(); });
    quickReplies.appendChild(b);
  }
  function displayResponses(responses) {
    quickReplies.replaceChildren();
    const failed = (responses || []).some(function (r) { return r.text && /trouble with that/i.test(r.text); });
    if (!responses || !responses.length || failed) { offlineReply(); return; }
    responses.forEach(function (r) {
      if (r.text) addMessage(r.text, "assistant");
      if (r.custom && Array.isArray(r.custom.events)) {
        r.custom.events.forEach(function (ev) {
          addMessage("📅 " + ev.title + " — " + ev.date + " at " + ev.time + ", " + ev.location, "assistant");
        });
      }
      (r.buttons || []).forEach(function (btn) {
        const q = el("button", "btn btn-secondary", btn.title);
        q.type = "button";
        q.addEventListener("click", function () { sendMessage(btn.payload, false); });
        quickReplies.appendChild(q);
      });
    });
  }
  async function sendMessage(text, showUser) {
    const msg = String(text || "").trim();
    if (!msg) return;
    if (showUser) addMessage(msg, "user");
    input.value = "";
    $("send-button").disabled = true;
    status.textContent = "Bloom is thinking…";
    try {
      const ctrl = new AbortController();
      const timer = setTimeout(function () { ctrl.abort(); }, 20000);
      const res = await fetch("/webhooks/rest/webhook", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sender: senderId, message: msg }),
        signal: ctrl.signal
      });
      clearTimeout(timer);
      if (!res.ok) throw new Error(String(res.status));
      displayResponses(await res.json());
      status.textContent = "";
    } catch (e) {
      offlineReply();
      status.textContent = "";
    } finally {
      $("send-button").disabled = false;
      input.focus();
    }
  }
  function openChat() {
    $("chat").hidden = false;
    document.body.classList.add("chat-open");
    if (!messages.children.length) {
      addMessage("Hi" + (profile && profile.name ? " " + profile.name : "") + "! I’m Bloom. Ask me about events, or tell me what you’re in the mood for this week.", "assistant");
    }
    input.focus();
  }
  function closeChat(keepFocus) {
    $("chat").hidden = true;
    document.body.classList.remove("chat-open");
    if (keepFocus !== true) $("open-chat").focus();
  }
  $("open-chat").addEventListener("click", openChat);
  $("close-chat").addEventListener("click", function () { closeChat(); });
  document.addEventListener("keydown", function (e) { if (e.key === "Escape" && !$("chat").hidden) closeChat(); });
  $("chat-form").addEventListener("submit", function (e) { e.preventDefault(); sendMessage(input.value, true); });
  input.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(input.value, true); }
  });

  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  const mic = $("mic-button");
  if (!SR) {
    mic.hidden = true;
  } else {
    const rec = new SR();
    rec.lang = "en-US";
    rec.interimResults = false;
    rec.onstart = function () { mic.textContent = "Listening…"; status.textContent = "Listening. Speak now."; };
    rec.onresult = function (e) { input.value = e.results[0][0].transcript; status.textContent = "Check your words, then press Send."; };
    rec.onerror = function () { status.textContent = "I couldn’t hear that. Try again or type instead."; };
    rec.onend = function () { mic.textContent = "🎙 Speak"; };
    mic.addEventListener("click", function () { try { rec.start(); } catch (e) {} });
  }

  /* ------------------------------------------------------------------ *
   * Start
   * ------------------------------------------------------------------ */
  if (location.hash === "#share") { openCreate(); }
  else if (profile) { renderHome(); show("home"); } else { openSurvey(); }
  loadCommunityEvents().then(function () { if (!$("home").hidden) renderHome(); });
}());
