function app() {
  return {
    // Auth
    isAuthed: false,
    authLoading: false,
    authError: '',

    // UI
    drawerOpen: false,
    activeTab: 'dashboard',
    apiUrl: localStorage.getItem('sa_url') || window.location.origin,
    apiKey: localStorage.getItem('sa_key') || '',
    userId: localStorage.getItem('sa_uid') || '',

    // Chat
    messages: [], sessionId: null, chatInput: '', chatLoading: false, chatError: '',

    // Endpoints
    endpoints: [], showModal: false,
    form: { name:'', description:'', field_mapping: { user_id:'', module:'', action:'', entity:'', category:'', description:'', metadata:'' } },
    previewJson: '', previewResult: null, previewError: '', regLoading: false, regError: '',

    // Logs
    logs: [], logLoading: false, logError: '',
    logFilter: { user_id:'', module:'', category:'', limit:'50' },
    expandedLog: null,

    // Apps
    appsList: [], showAppModal: false,
    appForm: { name:'', description:'', allowed_domain:'', owner_name:'' },
    appRegLoading: false, appRegError: '', newAppKey: null,

    // Dashboard
    dashStats: null, dashLoading: false,

    // Tools
    summaryUserId: '', summaryDays: 7, summaryModule: '', summaryResult: '', summaryLoading: false,
    reindexLoading: false, reindexResult: '',

    // Misc
    toast: '',
    showSettings: false,
    tabs: [
      { id:'dashboard', label:'Dashboard', icon:'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-4 0a1 1 0 01-1-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 01-1 1' },
      { id:'chat', label:'AI Chat', icon:'M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z' },
      { id:'logs', label:'Logs', icon:'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2' },
      { id:'endpoints', label:'Endpoints', icon:'M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1' },
      { id:'apps', label:'Apps', icon:'M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10' },
      { id:'tools', label:'Tools', icon:'M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z M15 12a3 3 0 11-6 0 3 3 0 016 0z' },
    ],
    mappingFields: [
      { key:'user_id', required:true, example:'userId or user.id' },
      { key:'module', required:false, example:'service or app.name' },
      { key:'action', required:false, example:'event or action' },
      { key:'entity', required:false, example:'resource or entity' },
      { key:'category', required:false, example:'severity or level' },
      { key:'description', required:false, example:'message or msg' },
      { key:'metadata', required:false, example:'data or payload' },
    ],

    save() {
      localStorage.setItem('sa_url', this.apiUrl);
      localStorage.setItem('sa_key', this.apiKey);
      localStorage.setItem('sa_uid', this.userId);
    },
    headers() { return { 'Content-Type':'application/json', 'X-Api-Key': this.apiKey }; },

    async login() {
      if (!this.apiKey.trim()) { this.authError = 'API key is required'; return; }
      this.authLoading = true; this.authError = '';
      try {
        const r = await fetch(`${this.apiUrl}/api/apps`, {
          headers: { 'Content-Type':'application/json', 'X-Api-Key': this.apiKey }
        });
        if (r.ok) {
          this.isAuthed = true;
          sessionStorage.setItem('sa_authed', '1');
          this.save();
          this.$nextTick(() => this.loadDashboard());
        } else if (r.status === 401) {
          this.authError = 'Invalid API key. Please try again.';
        } else {
          this.authError = `Server error (${r.status}). Check the API URL.`;
        }
      } catch(e) {
        this.authError = 'Connection failed: ' + e.message;
      } finally { this.authLoading = false; }
    },

    logout() {
      this.isAuthed = false;
      sessionStorage.removeItem('sa_authed');
      this.drawerOpen = false;
      this.dashStats = null;
      this.appsList = [];
      this.endpoints = [];
    },

    async init() {
      const wasAuthed = sessionStorage.getItem('sa_authed');
      if (wasAuthed && this.apiKey) {
        this.isAuthed = true;
        await this.loadDashboard();
      }
      this.$watch('activeTab', async (tab) => {
        this.drawerOpen = false;
        if (tab === 'dashboard') await this.loadDashboard();
        if (tab === 'endpoints') await this.loadEndpoints();
        if (tab === 'apps') await this.loadApps();
      });
    },

    showToast(msg) { this.toast = msg; setTimeout(() => { this.toast = ''; }, 2500); },
    copy(text) { navigator.clipboard.writeText(text).then(() => this.showToast('Copied!')); },

    // ── DASHBOARD ───────────────────────────────────────────────────
    async loadDashboard() {
      this.dashLoading = true;
      try {
        const res = await fetch(`${this.apiUrl}/api/stats?days=30`, { headers: this.headers() });
        if (res.ok) this.dashStats = await res.json();
      } catch(e) { console.error('Dashboard load failed', e); }
      finally { this.dashLoading = false; }
    },
    getTimelineMax() {
      if (!this.dashStats?.timeline) return 1;
      return Math.max(...this.dashStats.timeline.map(t => t.count), 1);
    },
    getCatColor(cat) {
      const m = { ERROR:'#ef4444', AUTH:'#eab308', CRUD:'#3b82f6', QUERY:'#22c55e', API:'#a855f7', SYSTEM:'#64748b' };
      return m[cat] || '#64748b';
    },

    // ── CHAT ────────────────────────────────────────────────────────
    async sendChat() {
      if (this.chatLoading || !this.chatInput.trim() || !this.userId.trim()) return;
      this.chatError = '';
      const query = this.chatInput.trim();
      this.messages.push({ role:'user', content: query });
      this.chatInput = '';
      this.chatLoading = true;
      this.$nextTick(() => { const el = document.getElementById('chat-messages'); if(el) el.scrollTop = el.scrollHeight; });
      try {
        const body = { user_id: this.userId, query, limit: 10 };
        if (this.sessionId) body.session_id = this.sessionId;
        const res = await fetch(`${this.apiUrl}/api/chat`, { method:'POST', headers: this.headers(), body: JSON.stringify(body) });
        const data = await res.json();
        if (!res.ok) this.chatError = data.detail || 'Request failed';
        else { this.sessionId = data.session_id; this.messages.push({ role:'ai', content: data.response }); }
      } catch(e) { this.chatError = 'Connection error: ' + e.message; }
      finally {
        this.chatLoading = false;
        this.$nextTick(() => { const el = document.getElementById('chat-messages'); if(el) el.scrollTop = el.scrollHeight; });
      }
    },

    // ── APPS ────────────────────────────────────────────────────────
    async loadApps() {
      try { const r = await fetch(`${this.apiUrl}/api/apps`, { headers: this.headers() }); const d = await r.json(); this.appsList = d.apps || []; }
      catch(e) { console.error('Failed to load apps', e); }
    },
    resetAppForm() { this.appForm = { name:'', description:'', allowed_domain:'', owner_name:'' }; this.appRegLoading = false; this.appRegError = ''; this.newAppKey = null; },
    async registerNewApp() {
      if (!this.appForm.name || !this.appForm.allowed_domain) return;
      this.appRegLoading = true; this.appRegError = '';
      try {
        const r = await fetch(`${this.apiUrl}/api/apps`, { method:'POST', headers: this.headers(), body: JSON.stringify(this.appForm) });
        const d = await r.json();
        if (!r.ok) this.appRegError = d.detail || 'Registration failed';
        else { this.newAppKey = d.api_key; await this.loadApps(); }
      } catch(e) { this.appRegError = 'Error: ' + e.message; }
      finally { this.appRegLoading = false; }
    },
    async deleteApp(appId) {
      if (!confirm('Delete this app? All sessions become invalid.')) return;
      try { await fetch(`${this.apiUrl}/api/apps/${appId}`, { method:'DELETE', headers: this.headers() }); await this.loadApps(); this.showToast('App deleted'); }
      catch(e) { this.showToast('Delete failed'); }
    },

    // ── ENDPOINTS ───────────────────────────────────────────────────
    async loadEndpoints() {
      try { const r = await fetch(`${this.apiUrl}/api/endpoints`, { headers: this.headers() }); const d = await r.json(); this.endpoints = d.endpoints || []; }
      catch(e) { console.error('Failed to load endpoints', e); }
    },
    resetForm() {
      this.form = { name:'', description:'', field_mapping: { user_id:'', module:'', action:'', entity:'', category:'', description:'', metadata:'' } };
      this.previewJson = ''; this.previewResult = null; this.previewError = ''; this.regError = ''; this.regLoading = false;
    },
    async registerEndpoint() {
      if (!this.form.name || !this.form.field_mapping.user_id) return;
      this.regLoading = true; this.regError = '';
      try {
        const mapping = {};
        for (const [k,v] of Object.entries(this.form.field_mapping)) { if(v.trim()) mapping[k] = v.trim(); }
        const r = await fetch(`${this.apiUrl}/api/endpoints`, { method:'POST', headers: this.headers(), body: JSON.stringify({ name: this.form.name, description: this.form.description, field_mapping: mapping }) });
        const d = await r.json();
        if (!r.ok) this.regError = d.detail || 'Registration failed';
        else { this.showModal = false; await this.loadEndpoints(); this.showToast(`Endpoint "${this.form.name}" registered`); }
      } catch(e) { this.regError = 'Error: ' + e.message; }
      finally { this.regLoading = false; }
    },
    async deleteEndpoint(id) {
      if (!confirm('Delete this endpoint?')) return;
      try { await fetch(`${this.apiUrl}/api/endpoints/${id}`, { method:'DELETE', headers: this.headers() }); await this.loadEndpoints(); this.showToast('Endpoint deleted'); }
      catch(e) { this.showToast('Delete failed'); }
    },
    async runPreview() {
      this.previewResult = null; this.previewError = '';
      let sample;
      try { sample = JSON.parse(this.previewJson); } catch { this.previewError = 'Invalid JSON'; return; }
      const mapping = {};
      for (const [k,v] of Object.entries(this.form.field_mapping)) { if(v.trim()) mapping[k] = v.trim(); }
      if (!mapping.user_id) { this.previewError = 'Set user_id mapping first'; return; }
      try {
        const r = await fetch(`${this.apiUrl}/api/endpoints/preview`, { method:'POST', headers: this.headers(), body: JSON.stringify({ field_mapping: mapping, sample_data: sample }) });
        const d = await r.json();
        if (!r.ok) this.previewError = d.detail || 'Preview failed';
        else this.previewResult = d.normalized;
      } catch(e) { this.previewError = 'Error: ' + e.message; }
    },

    // ── LOGS ────────────────────────────────────────────────────────
    async loadLogs() {
      this.logError = '';
      if (!this.logFilter.user_id.trim()) { this.logError = 'User ID is required'; return; }
      this.logLoading = true; this.expandedLog = null;
      try {
        const p = new URLSearchParams({ user_id: this.logFilter.user_id, limit: this.logFilter.limit });
        if (this.logFilter.module) p.append('module', this.logFilter.module);
        if (this.logFilter.category) p.append('category', this.logFilter.category);
        const r = await fetch(`${this.apiUrl}/api/logs?${p}`, { headers: this.headers() });
        const d = await r.json();
        if (!r.ok) this.logError = d.detail || 'Failed to fetch logs';
        else this.logs = d.logs || [];
      } catch(e) { this.logError = 'Error: ' + e.message; }
      finally { this.logLoading = false; }
    },

    // ── TOOLS ───────────────────────────────────────────────────────
    async generateSummary() {
      if (!this.summaryUserId.trim()) return;
      this.summaryLoading = true; this.summaryResult = '';
      try {
        const body = { user_id: this.summaryUserId, days: this.summaryDays };
        if (this.summaryModule) body.module = this.summaryModule;
        const r = await fetch(`${this.apiUrl}/api/summary`, { method:'POST', headers: this.headers(), body: JSON.stringify(body) });
        const d = await r.json();
        if (!r.ok) this.summaryResult = 'Error: ' + (d.detail || 'Failed');
        else this.summaryResult = d.summary;
      } catch(e) { this.summaryResult = 'Error: ' + e.message; }
      finally { this.summaryLoading = false; }
    },
    async reindex() {
      this.reindexLoading = true; this.reindexResult = '';
      try {
        const r = await fetch(`${this.apiUrl}/api/reindex`, { method:'POST', headers: this.headers() });
        const d = await r.json();
        if (!r.ok) this.reindexResult = 'Error: ' + (d.detail || 'Failed');
        else this.reindexResult = `Reindex complete. ${d.indexed} entries indexed.`;
      } catch(e) { this.reindexResult = 'Error: ' + e.message; }
      finally { this.reindexLoading = false; }
    },
  };
}
