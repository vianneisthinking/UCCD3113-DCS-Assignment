import React, { useEffect, useMemo, useState } from "react";
import { AlertTriangle, CheckCircle2, Clock, LogOut, Radio, Search, Sparkles, Tag, X } from "lucide-react";
import { Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ApiError, currentUser, getStats, getTickets, login, reclassifyTicket, updateTicket } from "./api";

const STATUSES = ["pending_classification", "open", "in_progress", "resolved", "closed"];
const PRIORITIES = ["low", "medium", "high"];
const LABELS = {
  pending_classification: "Pending classification", open: "Open", in_progress: "In Progress",
  resolved: "Resolved", closed: "Closed", low: "Low", medium: "Medium", high: "High",
  technical_support: "Technical Support", account_access: "Account Access",
  billing_payment: "Billing & Payment", delivery_order: "Delivery & Order", general_enquiry: "General Enquiry"
};
const COLORS = { low: "#5eead4", medium: "#fbbf24", high: "#f87171", pending_classification: "#fbbf24", open: "#60a5fa", in_progress: "#c084fc", resolved: "#4ade80", closed: "#94a3b8" };
const PIE_COLORS = ["#a78bfa", "#38bdf8", "#f472b6", "#4ade80", "#94a3b8"];
const label = (value) => LABELS[value] || value || "Unclassified";
const percent = (value) => value == null ? "—" : `${Math.round(value * 100)}%`;
const timeAgo = (iso) => {
  const hours = Math.floor((Date.now() - new Date(iso).getTime()) / 3600000);
  if (hours < 1) return "just now";
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
};

function Badge({ value }) {
  const color = COLORS[value] || "#94a3b8";
  return <span className="badge" style={{ color, background: `${color}22` }}>{label(value)}</span>;
}

function Login({ onAuthenticated }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const submit = async (event) => {
    event.preventDefault(); setBusy(true); setError("");
    try {
      const result = await login(email.trim(), password);
      if (result.role !== "staff") throw new ApiError("This account does not have staff access.", 403);
      sessionStorage.setItem("staff_access_token", result.access_token);
      onAuthenticated(result.access_token);
    } catch (err) { setError(err.message); } finally { setBusy(false); }
  };
  return <main className="login-page"><form className="login-card" onSubmit={submit}>
    <div className="eyebrow"><Radio size={14} /> Authorized staff</div>
    <h1>Support Ticket Console</h1><p>Sign in with an existing staff account.</p>
    {error && <div className="error" role="alert">{error}</div>}
    <label>Email<input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoComplete="username" /></label>
    <label>Password<input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required autoComplete="current-password" /></label>
    <button disabled={busy}>{busy ? "Signing in…" : "Sign in"}</button>
  </form></main>;
}

function StatCard({ labelText, value, Icon, color }) {
  return <div className="stat"><span>{labelText}<Icon size={15} color={color} /></span><strong>{value}</strong></div>;
}

export default function App() {
  const [token, setToken] = useState(() => sessionStorage.getItem("staff_access_token"));
  const [user, setUser] = useState(null);
  const [tickets, setTickets] = useState([]);
  const [stats, setStats] = useState(null);
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [priorityFilter, setPriorityFilter] = useState("");
  const [selectedId, setSelectedId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const logout = () => { sessionStorage.removeItem("staff_access_token"); setToken(null); setUser(null); };
  const handleError = (err) => { if (err.status === 401 || err.status === 403) logout(); else setError(err.message); };
  const refresh = async () => {
    if (!token) return; setLoading(true); setError("");
    try {
      const [me, ticketData, statsData] = await Promise.all([
        currentUser(token), getTickets(token, { status: statusFilter, priority: priorityFilter }), getStats(token)
      ]);
      if (me.role !== "staff") throw new ApiError("Staff access required.", 403);
      setUser(me); setTickets(ticketData); setStats(statsData);
    } catch (err) { handleError(err); } finally { setLoading(false); }
  };
  useEffect(() => { refresh(); }, [token, statusFilter, priorityFilter]);

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return tickets;
    return tickets.filter((t) => String(t.id).includes(needle) || t.complaint.toLowerCase().includes(needle) || label(t.category).toLowerCase().includes(needle));
  }, [tickets, query]);
  const selected = tickets.find((t) => t.id === selectedId) || null;
  const chartCategories = Object.entries(stats?.by_category || {}).map(([name, value]) => ({ name: label(name), value }));
  const chartPriorities = Object.entries(stats?.by_priority || {}).map(([name, value]) => ({ name: label(name), key: name, value }));

  const mutate = async (action, success) => {
    setError("");
    try { await action(); setNotice(success); setTimeout(() => setNotice(""), 2200); await refresh(); }
    catch (err) { handleError(err); }
  };
  if (!token) return <Login onAuthenticated={setToken} />;

  return <div className="app"><header><div><div className="eyebrow"><Radio size={13} /> Live backend queue</div><h1>Support Ticket Console</h1><small>{user ? `Signed in as ${user.name}` : "Validating session…"}</small></div><div className="header-actions"><button onClick={refresh} disabled={loading}>{loading ? "Refreshing…" : "Refresh"}</button><button onClick={logout}><LogOut size={14} /> Logout</button></div></header>
    {error && <div className="error" role="alert">{error}</div>}
    <section className="stats">
      <StatCard labelText="Total Tickets" value={stats?.total_tickets ?? "—"} Icon={Tag} color="#94a3b8" />
      <StatCard labelText="Open" value={(stats?.by_status?.open || 0) + (stats?.by_status?.in_progress || 0)} Icon={Clock} color="#60a5fa" />
      <StatCard labelText="Overdue" value={stats?.overdue ?? "—"} Icon={AlertTriangle} color="#f87171" />
      <StatCard labelText="AI Pending" value={stats?.pending_classification ?? "—"} Icon={Sparkles} color="#a78bfa" />
    </section>
    <section className="charts"><div className="panel"><h2>Tickets by category</h2><ResponsiveContainer width="100%" height={190}><PieChart><Pie data={chartCategories} dataKey="value" nameKey="name" innerRadius={42} outerRadius={74}>{chartCategories.map((item, i) => <Cell key={item.name} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}</Pie><Tooltip /></PieChart></ResponsiveContainer></div>
      <div className="panel"><h2>Tickets by priority</h2><ResponsiveContainer width="100%" height={190}><BarChart data={chartPriorities}><CartesianGrid strokeDasharray="3 3" stroke="#ffffff12" vertical={false} /><XAxis dataKey="name" stroke="#94a3b8" /><YAxis allowDecimals={false} stroke="#94a3b8" /><Tooltip /><Bar dataKey="value">{chartPriorities.map((item) => <Cell key={item.key} fill={COLORS[item.key]} />)}</Bar></BarChart></ResponsiveContainer></div></section>
    <section className="filters"><div className="search"><Search size={15} /><input aria-label="Search tickets" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search ID, complaint, or category…" /></div><select aria-label="Priority filter" value={priorityFilter} onChange={(e) => setPriorityFilter(e.target.value)}><option value="">Priority: All</option>{PRIORITIES.map((p) => <option key={p} value={p}>{label(p)}</option>)}</select><select aria-label="Status filter" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}><option value="">Status: All</option>{STATUSES.map((s) => <option key={s} value={s}>{label(s)}</option>)}</select><span>{filtered.length} tickets</span></section>
    <section className="table-wrap"><table><thead><tr><th>Ticket</th><th>Category</th><th>Priority</th><th>Status</th><th>Confidence</th><th>Department</th><th>Created</th></tr></thead><tbody>
      {!loading && filtered.length === 0 && <tr><td colSpan="7" className="empty">No tickets match these filters.</td></tr>}
      {filtered.map((t) => <tr key={t.id} onClick={() => setSelectedId(t.id)}><td><code>#TICK-{t.id}</code><div>{t.complaint}</div></td><td><Badge value={t.category} /></td><td><Badge value={t.priority} /></td><td><Badge value={t.status} /></td><td>{percent(t.category_confidence)}</td><td>{t.department}</td><td>{timeAgo(t.created_at)}</td></tr>)}
    </tbody></table></section>
    {selected && <div className="drawer-backdrop" onClick={() => setSelectedId(null)}><aside onClick={(e) => e.stopPropagation()}><button className="close" aria-label="Close ticket" onClick={() => setSelectedId(null)}><X /></button><code>#TICK-{selected.id}</code><h2>{selected.complaint}</h2><div className="badge-row"><Badge value={selected.category} /><Badge value={selected.priority} /><Badge value={selected.status} /></div><div className="detail"><span>Department</span><strong>{selected.department}</strong><span>AI category confidence</span><strong>{percent(selected.category_confidence)}</strong><span>AI priority confidence</span><strong>{percent(selected.priority_confidence)}</strong><span>SLA due</span><strong>{new Date(selected.sla_due_at).toLocaleString()}</strong></div><h3>Update status</h3><div className="status-buttons">{STATUSES.filter((s) => s !== "pending_classification").map((s) => <button key={s} className={selected.status === s ? "active" : ""} onClick={() => mutate(() => updateTicket(token, selected.id, s), `Ticket ${selected.id} updated`)}>{label(s)}</button>)}</div>{selected.status === "pending_classification" && <button className="reclassify" onClick={() => mutate(() => reclassifyTicket(token, selected.id), `Ticket ${selected.id} classified`)}><Sparkles size={14} /> Retry AI classification</button>}{selected.status === "resolved" && <p className="resolved"><CheckCircle2 size={15} /> Marked resolved</p>}</aside></div>}
    {notice && <div className="toast">{notice}</div>}
  </div>;
}
