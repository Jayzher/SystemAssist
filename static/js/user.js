function userApp() {
  return {
    // Auth
    apiUrl: localStorage.getItem('sa_user_url') || window.location.origin,
    sessionToken: localStorage.getItem('sa_session_token') || '',
    isLoggedIn: false,
    loginLoading: false,
    loginError: '',
    userInfo: null,

    // Navigation
    activeTab: 'activity',
    tabs: [
      { id:'activity', label:'My Activity', icon:'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2' },
      { id:'chat', label:'Ask AI', icon:'M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z' },
      { id:'insights', label:'Insights', icon:'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z' },
    ],

    // Activity (Logs)
    logs: [], logLoading: false, logError: '',
    logFilter: { module:'', category:'', limit:'50' },
    expandedLog: null,

    // Chat
    messages: [], chatSessionId: null, chatInput: '', chatLoading: false, chatError: '',

    // Insights
    stats: null, statsLoading: false,

    // Misc
    toast: '',

    headers() {
      return { 'Content-Type':'application/json', 'X-Session-Token': this.sessionToken };
    },

    async init() {
      if (this.sessionToken) {
        await this.validateSession();
      }
    },

    showToast(msg) { this.toast = msg; setTimeout(() => { this.toast = ''; }, 2500); },

    saveToken() { localStorage.setItem('sa_user_url', this.apiUrl); localStorage.setItem('sa_session_token', this.sessionToken); },

    // ── AUTH ─────────────────────────────────────────────────────────
    async validateSession() {
      this.loginLoading = true;
      this.loginError = '';
      try {
        const r = await fetch(`${this.apiUrl}/api/auth/session`, { headers: this.headers() });
        if (r.ok) {
          const d = await r.json();
          this.userInfo = d;
          this.isLoggedIn = true;
          this.saveToken();
          await this.loadActivity();
        } else {
          const d = await r.json();
          this.loginError = d.detail || 'Session invalid or expired';
          this.isLoggedIn = false;
          localStorage.removeItem('sa_session_token');
        }
      } catch(e) {
        this.loginError = 'Connection error: ' + e.message;
      } finally {
        this.loginLoading = false;
      }
    },

    async login() {
      if (!this.sessionToken.trim()) { this.loginError = 'Please enter your session token'; return; }
      this.saveToken();
      await this.validateSession();
    },

    async logout() {
      try { await fetch(`${this.apiUrl}/api/auth/session`, { method:'DELETE', headers: this.headers() }); } catch(e) {}
      this.isLoggedIn = false;
      this.sessionToken = '';
      this.userInfo = null;
      this.messages = [];
      this.logs = [];
      this.stats = null;
      localStorage.removeItem('sa_session_token');
    },

    // ── ACTIVITY (LOGS) ─────────────────────────────────────────────
    async loadActivity() {
      if (!this.isLoggedIn) return;
      this.logLoading = true;
      this.logError = '';
      this.expandedLog = null;
      try {
        const p = new URLSearchParams({ user_id: this.userInfo.user_id, limit: this.logFilter.limit });
        if (this.logFilter.module) p.append('module', this.logFilter.module);
        if (this.logFilter.category) p.append('category', this.logFilter.category);
        const r = await fetch(`${this.apiUrl}/api/logs?${p}`, { headers: this.headers() });
        const d = await r.json();
        if (!r.ok) this.logError = d.detail || 'Failed to load';
        else this.logs = d.logs || [];
      } catch(e) { this.logError = 'Error: ' + e.message; }
      finally { this.logLoading = false; }
    },

    // ── CHAT ────────────────────────────────────────────────────────
    async sendChat() {
      if (this.chatLoading || !this.chatInput.trim()) return;
      this.chatError = '';
      const query = this.chatInput.trim();
      this.messages.push({ role:'user', content: query });
      this.chatInput = '';
      this.chatLoading = true;
      this.$nextTick(() => { const el = document.getElementById('user-chat-messages'); if(el) el.scrollTop = el.scrollHeight; });
      try {
        const body = { query, limit: 10 };
        if (this.chatSessionId) body.session_id = this.chatSessionId;
        const r = await fetch(`${this.apiUrl}/api/chat`, { method:'POST', headers: this.headers(), body: JSON.stringify(body) });
        const d = await r.json();
        if (!r.ok) this.chatError = d.detail || 'Failed';
        else { this.chatSessionId = d.session_id; this.messages.push({ role:'ai', content: d.response }); }
      } catch(e) { this.chatError = 'Error: ' + e.message; }
      finally {
        this.chatLoading = false;
        this.$nextTick(() => { const el = document.getElementById('user-chat-messages'); if(el) el.scrollTop = el.scrollHeight; });
      }
    },

    // ── INSIGHTS ────────────────────────────────────────────────────
    async loadInsights() {
      if (!this.isLoggedIn) return;
      this.statsLoading = true;
      try {
        const r = await fetch(`${this.apiUrl}/api/stats/user/${this.userInfo.user_id}?days=30`, { headers: this.headers() });
        if (r.ok) this.stats = await r.json();
      } catch(e) { console.error('Insights error', e); }
      finally { this.statsLoading = false; }
    },

    getCatColor(cat) {
      const m = { ERROR:'#ef4444', AUTH:'#eab308', CRUD:'#3b82f6', QUERY:'#22c55e', API:'#a855f7', SYSTEM:'#64748b' };
      return m[cat] || '#64748b';
    },
  };
}
