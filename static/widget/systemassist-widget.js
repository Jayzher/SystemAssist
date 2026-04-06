/*!
 * SystemAssist Widget v1.0.0
 * Drop-in floating AI chat widget — works with any web application.
 *
 * RECOMMENDED — proxyUrl mode (API key stays server-side, never exposed to browser):
 *   <script>
 *     window.SystemAssistConfig = {
 *       proxyUrl: '/api/sa/chat/',   // your own backend endpoint that holds the key
 *       userId:   'user-123',
 *       userName: 'Alice',
 *     };
 *   </script>
 *   <script src="systemassist-widget.js"></script>
 *
 * Direct mode (API key exposed in page source — only for trusted/internal tools):
 *   <script>
 *     window.SystemAssistConfig = {
 *       apiUrl:  'https://your-sa-instance.com',
 *       apiKey:  'your-master-api-key',
 *       userId:  'user-123',
 *       userName: 'Alice',
 *     };
 *   </script>
 *   <script src="systemassist-widget.js"></script>
 */
(function (global) {
  'use strict';

  // ─── 1. CONFIG ──────────────────────────────────────────────────────────────
  function getConfig() {
    var gc = global.SystemAssistConfig || {};
    var el = (
      document.querySelector('script[data-sa-proxy-url]') ||
      document.querySelector('script[data-sa-api-url]')  ||
      document.querySelector('script[data-sa-api-key]')
    );
    var ds = el ? el.dataset : {};
    return {
      proxyUrl:    (ds.saProxyUrl    || gc.proxyUrl    || ''),
      healthUrl:   (ds.saHealthUrl   || gc.healthUrl   || ''),
      sessionUrl:  (ds.saSessionUrl  || gc.sessionUrl  || ''),
      apiUrl:      (ds.saApiUrl      || gc.apiUrl      || '').replace(/\/$/, ''),
      apiKey:      (ds.saApiKey      || gc.apiKey      || ''),
      userId:      (ds.saUserId      || gc.userId      || ''),
      userName:    (ds.saUserName    || gc.userName    || ''),
      title:       (ds.saTitle       || gc.title       || 'SystemAssist AI'),
      subtitle:    (ds.saSubtitle    || gc.subtitle    || 'Ask about your activity'),
      placeholder: (ds.saPlaceholder || gc.placeholder || 'Ask me anything\u2026'),
    };
  }

  // ─── 2. CSS (embedded) ──────────────────────────────────────────────────────
  var CSS = (
    /* ── reset scoped to widget root ── */
    '#sa-root,#sa-root *{box-sizing:border-box}' +

    /* ── overlay ── */
    '#sa-overlay{position:fixed;inset:0;z-index:99997;background:rgba(0,0,0,.52);' +
    'backdrop-filter:blur(3px);-webkit-backdrop-filter:blur(3px);' +
    'opacity:0;pointer-events:none;transition:opacity .25s ease}' +
    '#sa-overlay.sa-vis{opacity:1;pointer-events:auto}' +

    /* ── floating action button ── */
    '#sa-fab{position:fixed;bottom:24px;right:24px;z-index:99996;' +
    'width:56px;height:56px;border-radius:50%;border:none;cursor:pointer;' +
    'background:linear-gradient(135deg,#6366f1 0%,#8b5cf6 100%);color:#fff;' +
    'display:flex;align-items:center;justify-content:center;' +
    'box-shadow:0 4px 20px rgba(99,102,241,.55),0 2px 8px rgba(0,0,0,.25);' +
    'transition:transform .2s ease,box-shadow .2s ease;outline:none;' +
    'padding:0}' +
    '#sa-fab:hover{transform:scale(1.1);box-shadow:0 6px 28px rgba(99,102,241,.7),0 3px 12px rgba(0,0,0,.3)}' +
    '#sa-fab:active{transform:scale(.94)}' +
    '#sa-fab svg{width:25px;height:25px}' +

    /* ── off-canvas panel ── */
    '#sa-panel{position:fixed;top:0;right:0;bottom:0;width:390px;max-width:100vw;' +
    'z-index:99998;background:#0f172a;color:#f1f5f9;' +
    'font-family:"Inter",-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;' +
    'font-size:14px;display:flex;flex-direction:column;' +
    'transform:translateX(105%);transition:transform .32s cubic-bezier(.4,0,.2,1);' +
    'box-shadow:-8px 0 48px rgba(0,0,0,.45)}' +
    '#sa-panel.sa-on{transform:translateX(0)}' +
    '@media(max-width:440px){#sa-panel{width:100vw}}' +

    /* ── header ── */
    '.sa-hd{padding:14px 14px 13px;border-bottom:1px solid rgba(255,255,255,.07);' +
    'display:flex;align-items:center;gap:11px;background:rgba(255,255,255,.03);flex-shrink:0}' +
    '.sa-hd-av{width:38px;height:38px;border-radius:11px;' +
    'background:linear-gradient(135deg,#6366f1,#8b5cf6);' +
    'display:flex;align-items:center;justify-content:center;flex-shrink:0}' +
    '.sa-hd-av svg{width:19px;height:19px;color:#fff}' +
    '.sa-hd-info{flex:1;min-width:0}' +
    '.sa-hd-title{font-weight:700;font-size:14.5px;color:#f1f5f9;line-height:1.2}' +
    '.sa-hd-sub{font-size:11px;color:#475569;margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}' +
    '.sa-dot{width:7px;height:7px;border-radius:50%;flex-shrink:0;' +
    'background:#f59e0b;transition:background .35s ease,box-shadow .35s ease}' +
    '.sa-dot.sa-online{background:#22c55e;box-shadow:0 0 7px #22c55e99}' +
    '.sa-dot.sa-offline{background:#ef4444;box-shadow:0 0 5px #ef444466}' +
    '.sa-dot.sa-checking{background:#f59e0b;animation:sa-chk 1.1s ease-in-out infinite}' +
    '@keyframes sa-chk{0%,100%{opacity:1}50%{opacity:.3}}' +
    '.sa-hd-acts{display:flex;gap:5px;flex-shrink:0}' +
    '.sa-ibtn{width:30px;height:30px;border-radius:8px;border:none;cursor:pointer;' +
    'background:rgba(255,255,255,.06);color:#94a3b8;' +
    'display:flex;align-items:center;justify-content:center;' +
    'transition:background .15s,color .15s;outline:none}' +
    '.sa-ibtn:hover{background:rgba(255,255,255,.13);color:#f1f5f9}' +
    '.sa-ibtn svg{width:14px;height:14px}' +

    /* ── messages ── */
    '#sa-msgs{flex:1;overflow-y:auto;padding:14px 13px;' +
    'display:flex;flex-direction:column;gap:10px;scroll-behavior:smooth}' +
    '#sa-msgs::-webkit-scrollbar{width:4px}' +
    '#sa-msgs::-webkit-scrollbar-track{background:transparent}' +
    '#sa-msgs::-webkit-scrollbar-thumb{background:rgba(255,255,255,.1);border-radius:4px}' +

    /* ── message bubbles ── */
    '.sa-m{display:flex;animation:sa-fi .22s ease}' +
    '.sa-m.u{justify-content:flex-end}' +
    '.sa-m.a{justify-content:flex-start}' +
    '.sa-b{max-width:82%;padding:9px 13px;border-radius:16px;' +
    'line-height:1.58;font-size:13.5px;word-break:break-word}' +
    '.sa-m.u .sa-b{background:linear-gradient(135deg,#6366f1,#8b5cf6);' +
    'color:#fff;border-bottom-right-radius:3px}' +
    '.sa-m.a .sa-b{background:rgba(255,255,255,.08);color:#cbd5e1;' +
    'border-bottom-left-radius:3px;white-space:pre-wrap}' +

    /* ── loading dots ── */
    '.sa-ld-dots{display:flex;gap:5px}' +
    '.sa-b.ld span{width:7px;height:7px;border-radius:50%;background:#6366f1;' +
    'animation:sa-db 1.2s infinite ease-in-out}' +
    '.sa-b.ld span:nth-child(2){animation-delay:.18s}' +
    '.sa-b.ld span:nth-child(3){animation-delay:.36s}' +
    '@keyframes sa-db{0%,60%,100%{transform:translateY(0)}30%{transform:translateY(-7px)}}' +
    '@keyframes sa-fi{from{opacity:0;transform:translateY(7px)}to{opacity:1;transform:translateY(0)}}' +

    /* ── footer / form ── */
    '#sa-ft{padding:11px 13px 15px;border-top:1px solid rgba(255,255,255,.07);flex-shrink:0}' +
    '#sa-form{display:flex;align-items:center;gap:7px;' +
    'background:rgba(255,255,255,.07);border:1.5px solid rgba(255,255,255,.1);' +
    'border-radius:14px;padding:5px 5px 5px 13px;transition:border-color .15s}' +
    '#sa-form:focus-within{border-color:rgba(99,102,241,.65)}' +
    '#sa-inp{flex:1;background:none;border:none;outline:none;color:#f1f5f9;' +
    'font-size:13.5px;font-family:inherit;padding:5px 0;min-width:0}' +
    '#sa-inp::placeholder{color:#334155}' +
    '#sa-inp:disabled{opacity:.5}' +
    '#sa-send{width:34px;height:34px;border-radius:10px;border:none;cursor:pointer;' +
    'background:linear-gradient(135deg,#6366f1,#8b5cf6);color:#fff;' +
    'display:flex;align-items:center;justify-content:center;' +
    'transition:opacity .15s,transform .15s;flex-shrink:0;outline:none}' +
    '#sa-send:hover{opacity:.88;transform:scale(1.08)}' +
    '#sa-send:disabled{opacity:.38;cursor:not-allowed;transform:none}' +
    '#sa-send svg{width:15px;height:15px}' +
    '.sa-pw{text-align:center;font-size:10.5px;color:#1e293b;margin-top:7px;letter-spacing:.01em}' +
    '.sa-pw a{color:#293548;text-decoration:none;transition:color .15s}' +
    '.sa-pw a:hover{color:#6366f1}' +

    /* ── body scroll lock ── */
    '.sa-lock{overflow:hidden!important}'
  );

  // ─── 3. HTML BUILDER ────────────────────────────────────────────────────────
  function icon(path, extra) {
    return (
      '<svg ' + (extra || '') + ' fill="none" stroke="currentColor" ' +
      'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24">' +
      path + '</svg>'
    );
  }

  function buildHTML(cfg) {
    var chatPath = '<path d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"/>';
    var xPath    = '<path d="M6 18L18 6M6 6l12 12"/>';
    var aiPath   = '<path d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/>';
    var newPath  = '<path d="M12 5v14M5 12h14"/>';
    var sendPath = '<path d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"/>';

    return (
      /* overlay */
      '<div id="sa-overlay"></div>' +

      /* panel */
      '<div id="sa-panel" role="dialog" aria-modal="true" aria-label="' + esc(cfg.title) + '">' +

        /* header */
        '<div class="sa-hd">' +
          '<div class="sa-hd-av">' + icon(aiPath) + '</div>' +
          '<div class="sa-hd-info">' +
            '<div class="sa-hd-title">' + esc(cfg.title) + '</div>' +
            '<div class="sa-hd-sub">' + esc(cfg.subtitle) + '</div>' +
          '</div>' +
          '<div id="sa-dot" class="sa-dot sa-checking" title="Checking\u2026"></div>' +
          '<div class="sa-hd-acts">' +
            '<button id="sa-new" class="sa-ibtn" title="New conversation" aria-label="New conversation">' +
              icon(newPath) +
            '</button>' +
            '<button id="sa-close" class="sa-ibtn" title="Close" aria-label="Close">' +
              icon(xPath) +
            '</button>' +
          '</div>' +
        '</div>' +

        /* messages */
        '<div id="sa-msgs" aria-live="polite" aria-label="Chat messages"></div>' +

        /* footer */
        '<div id="sa-ft">' +
          '<form id="sa-form" autocomplete="off">' +
            '<input id="sa-inp" type="text" autocomplete="off"' +
            ' placeholder="' + esc(cfg.placeholder) + '" aria-label="Chat input"/>' +
            '<button id="sa-send" type="submit" aria-label="Send">' +
              icon(sendPath) +
            '</button>' +
          '</form>' +
          '<p class="sa-pw">Powered by <a href="#" tabindex="-1">SystemAssist AI</a></p>' +
        '</div>' +

      '</div>' +

      /* FAB */
      '<button id="sa-fab" aria-label="Open AI assistant" aria-expanded="false">' +
        icon(chatPath) +
      '</button>'
    );
  }

  // ─── 4. HELPERS ─────────────────────────────────────────────────────────────
  function esc(s) {
    return String(s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function getCsrf() {
    var m = document.cookie.match(/(?:^|;)\s*csrftoken=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : '';
  }

  // ─── 5. INIT ────────────────────────────────────────────────────────────────
  function init() {
    if (document.getElementById('sa-fab')) return;

    var cfg = getConfig();

    /* inject styles */
    var styleEl = document.createElement('style');
    styleEl.id = 'sa-widget-css';
    styleEl.textContent = CSS;
    document.head.appendChild(styleEl);

    /* inject markup */
    var root = document.createElement('div');
    root.id = 'sa-root';
    root.innerHTML = buildHTML(cfg);
    document.body.appendChild(root);

    /* refs */
    var overlay  = document.getElementById('sa-overlay');
    var panel    = document.getElementById('sa-panel');
    var fab      = document.getElementById('sa-fab');
    var closeBtn = document.getElementById('sa-close');
    var newBtn   = document.getElementById('sa-new');
    var msgs     = document.getElementById('sa-msgs');
    var form     = document.getElementById('sa-form');
    var inp      = document.getElementById('sa-inp');
    var sendBtn  = document.getElementById('sa-send');

    /* state */
    var SESSION_KEY = 'sa_sid_' + (cfg.userId || 'anon');
    var sessionId   = null;
    try { sessionId = localStorage.getItem(SESSION_KEY); } catch (_) {}
    var isOpen = false;
    var busy   = false;

    /* ── status dot ── */
    function setStatus(state) {
      var dot = document.getElementById('sa-dot');
      if (!dot) return;
      dot.className = 'sa-dot sa-' + state;
      dot.title = state === 'online' ? 'Connected'
                : state === 'offline' ? 'Disconnected'
                : 'Checking\u2026';
    }

    var _lastGoodStatus = null;

    async function checkHealth() {
      if (!_lastGoodStatus) setStatus('checking');
      try {
        var url, opts;
        if (cfg.healthUrl) {
          url  = cfg.healthUrl;
          opts = { method: 'GET', credentials: 'same-origin',
                   headers: { 'X-CSRFToken': getCsrf() } };
        } else if (cfg.proxyUrl) {
          url  = cfg.proxyUrl.replace(/\/chat\/?$/, '/health/');
          opts = { method: 'GET', credentials: 'same-origin',
                   headers: { 'X-CSRFToken': getCsrf() } };
        } else if (cfg.apiUrl) {
          url  = cfg.apiUrl + '/health';
          opts = { method: 'GET',
                   headers: { 'X-Api-Key': cfg.apiKey } };
        } else {
          setStatus('offline'); return;
        }
        var res = await fetch(url, opts);
        if (res.ok) {
          _lastGoodStatus = true;
          setStatus('online');
        } else if (_lastGoodStatus) {
          setStatus('online');
        } else {
          setStatus('offline');
        }
      } catch (_) {
        if (!_lastGoodStatus) setStatus('offline');
      }
    }

    /* ── open / close ── */
    function open() {
      isOpen = true;
      panel.classList.add('sa-on');
      overlay.classList.add('sa-vis');
      fab.classList.add('sa-on');
      fab.setAttribute('aria-expanded', 'true');
      document.body.classList.add('sa-lock');
      checkHealth();
      setTimeout(function () { inp.focus(); }, 330);
    }

    function close() {
      isOpen = false;
      panel.classList.remove('sa-on');
      overlay.classList.remove('sa-vis');
      fab.classList.remove('sa-on');
      fab.setAttribute('aria-expanded', 'false');
      document.body.classList.remove('sa-lock');
    }

    fab.addEventListener('click',    function () { isOpen ? close() : open(); });
    closeBtn.addEventListener('click', close);
    overlay.addEventListener('click',  close);
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && isOpen) close();
    });

    /* ── message helpers ── */
    function addMsg(role, text) {
      var wrap = document.createElement('div');
      wrap.className = 'sa-m ' + role;
      var bub = document.createElement('div');
      bub.className = 'sa-b';
      bub.textContent = text;
      wrap.appendChild(bub);
      msgs.appendChild(wrap);
      msgs.scrollTop = msgs.scrollHeight;
    }

    var _loadingTimer = null;

    function addLoading() {
      var wrap = document.createElement('div');
      wrap.className = 'sa-m a';
      wrap.id = 'sa-typing';
      wrap.innerHTML =
        '<div class="sa-b ld">' +
          '<div class="sa-ld-dots"><span></span><span></span><span></span></div>' +
          '<span id="sa-elapsed" style="font-size:11px;' +
            'color:#64748b;letter-spacing:0">thinking\u2026</span>' +
        '</div>';
      msgs.appendChild(wrap);
      msgs.scrollTop = msgs.scrollHeight;
      var secs = 0;
      _loadingTimer = setInterval(function () {
        secs++;
        var el = document.getElementById('sa-elapsed');
        if (el) el.textContent = secs + 's\u2026';
      }, 1000);
    }

    function removeLoading() {
      if (_loadingTimer) { clearInterval(_loadingTimer); _loadingTimer = null; }
      var el = document.getElementById('sa-typing');
      if (el) el.parentNode.removeChild(el);
    }

    /* ── new conversation ── */
    function clearSession() {
      sessionId = null;
      try { localStorage.removeItem(SESSION_KEY); } catch (_) {}
      msgs.innerHTML = '';
      addMsg('a', 'New conversation started. How can I help you?');
    }
    newBtn.addEventListener('click', clearSession);

    /* ── send message ── */
    async function sendMessage(text) {
      if (!text.trim() || busy) return;

      var useProxy = !!cfg.proxyUrl;
      if (!useProxy && (!cfg.apiUrl || !cfg.apiKey)) {
        addMsg('a', '\u26a0\ufe0f Widget not configured.\nProvide proxyUrl (recommended) or apiUrl + apiKey.');
        return;
      }

      busy = true;
      sendBtn.disabled = true;
      inp.disabled = true;

      addMsg('u', text);
      addLoading();

      try {
        var payload = { query: text, limit: 10 };
        if (sessionId) payload.session_id = sessionId;

        /* proxy mode — CSRF token, no API key, user_id injected server-side */
        var url, headers;
        if (useProxy) {
          url = cfg.proxyUrl;
          headers = {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrf(),
          };
        } else {
          /* direct mode — API key in header (only for trusted/internal tools) */
          if (cfg.userId) payload.user_id = cfg.userId;
          url = cfg.apiUrl + '/api/chat';
          headers = {
            'Content-Type': 'application/json',
            'X-Api-Key': cfg.apiKey,
          };
        }

        var res = await fetch(url, {
          method: 'POST',
          credentials: 'same-origin',
          headers: headers,
          body: JSON.stringify(payload),
        });

        removeLoading();

        if (res.ok) {
          var data = await res.json();
          if (data.session_id) {
            sessionId = data.session_id;
            try { localStorage.setItem(SESSION_KEY, sessionId); } catch (_) {}
          }
          addMsg('a', data.response || '(empty response)');
        } else {
          var errBody = {};
          try { errBody = await res.json(); } catch (_) {}
          addMsg('a', '\u26a0\ufe0f ' + (errBody.detail || ('Error ' + res.status)));
        }
      } catch (ex) {
        removeLoading();
        var target = cfg.proxyUrl || cfg.apiUrl;
        addMsg('a', '\u26a0\ufe0f Could not reach SystemAssist.\n' + target + '\n\n' + ex.message);
      } finally {
        busy = false;
        sendBtn.disabled = false;
        inp.disabled = false;
        inp.focus();
      }
    }

    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var text = inp.value.trim();
      if (text) {
        inp.value = '';
        sendMessage(text);
      }
    });

    /* ── initial health check + session mount ── */
    checkHealth();
    if (cfg.sessionUrl) {
      fetch(cfg.sessionUrl, { method: 'GET', credentials: 'same-origin',
        headers: { 'X-CSRFToken': getCsrf() } })
        .catch(function () {});
    }

    /* ── welcome message ── */
    var who = cfg.userName ? ('Hi ' + cfg.userName + '! \ud83d\udc4b') : 'Hi there! \ud83d\udc4b';
    addMsg('a', who + " I\u2019m your AI activity assistant.\n\nAsk me what you\u2019ve been doing, find patterns, or get a summary of your recent actions.");
  }

  // ─── 6. AUTO-INIT ───────────────────────────────────────────────────────────
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  global.SystemAssistWidget = { init: init };

})(window);
