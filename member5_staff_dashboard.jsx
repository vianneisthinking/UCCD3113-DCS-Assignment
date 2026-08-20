import React, { useState, useMemo } from "react";
import {
  PieChart, Pie, Cell, ResponsiveContainer, Tooltip,
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Legend
} from "recharts";
import {
  Search, Filter, ChevronDown, X, Clock, User, Tag,
  AlertTriangle, CheckCircle2, ArrowUpRight, Radio, Sparkles
} from "lucide-react";


// ---------- MOCK DATA GENERATION (stand-in for GET /api/tickets) ----------
const CATEGORIES = ["Billing", "Technical", "Account", "Shipping", "General"];
const PRIORITIES = ["Low", "Medium", "High", "Critical"];
const STATUSES = ["New", "In Progress", "Escalated", "Resolved"];
const AGENTS = ["Unassigned", "N. Rahman", "J. Tan", "S. Kumar", "A. Wong"];

const PRIORITY_COLOR = {
  Low: "#5eead4",
  Medium: "#fbbf24",
  High: "#fb923c",
  Critical: "#f87171",
};
const STATUS_COLOR = {
  New: "#60a5fa",
  "In Progress": "#fbbf24",
  Escalated: "#f87171",
  Resolved: "#4ade80",
};
const CATEGORY_COLOR = {
  Billing: "#a78bfa",
  Technical: "#38bdf8",
  Account: "#f472b6",
  Shipping: "#4ade80",
  General: "#94a3b8",
};

const SUBJECTS = {
  Billing: ["Duplicate charge on invoice", "Refund not received", "Payment method declined", "Subscription upgrade billing issue"],
  Technical: ["App crashes on login", "API returning 500 error", "Sync failing between devices", "Slow dashboard load time"],
  Account: ["Cannot reset password", "Account locked after login attempts", "Email change not verified", "2FA device lost"],
  Shipping: ["Package marked delivered but not received", "Wrong item shipped", "Delivery delayed 5 days", "Tracking number invalid"],
  General: ["Feature request: dark mode", "Question about pricing tiers", "Feedback on new UI", "How to export data"],
};

function seedTickets(n = 42) {
  let id = 1000;
  const now = Date.now();
  return Array.from({ length: n }, () => {
    const category = CATEGORIES[Math.floor(Math.random() * CATEGORIES.length)];
    const priority = PRIORITIES[Math.floor(Math.random() * PRIORITIES.length)];
    const status = STATUSES[Math.floor(Math.random() * STATUSES.length)];
    const subject = SUBJECTS[category][Math.floor(Math.random() * SUBJECTS[category].length)];
    const assignedTo = status === "New" ? "Unassigned" : AGENTS[Math.floor(Math.random() * AGENTS.length)];
    const hoursAgo = Math.floor(Math.random() * 96);
    return {
      id: `TKT-${id++}`,
      subject,
      customer: `customer${Math.floor(Math.random() * 900 + 100)}@mail.com`,
      category,
      priority,
      status,
      aiConfidence: Math.floor(60 + Math.random() * 40),
      createdAt: new Date(now - hoursAgo * 3600 * 1000).toISOString(),
      assignedTo,
    };
  }).sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));
}

// API HOOK: fetch tickets
async function apiGetTickets() {
  await new Promise((r) => setTimeout(r, 150)); // simulate latency
  return seedTickets();
}

// API HOOK: update a ticket
async function apiUpdateTicket(id, patch) {
  await new Promise((r) => setTimeout(r, 120));
  return { id, ...patch, ok: true };
}

function timeAgo(iso) {
  const diffMs = Date.now() - new Date(iso).getTime();
  const h = Math.floor(diffMs / 3600000);
  if (h < 1) return "just now";
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

function Badge({ color, children }) {
  return (
    <span
      className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium"
      style={{ backgroundColor: `${color}22`, color }}
    >
      {children}
    </span>
  );
}

function StatCard({ label, value, icon: Icon, accent }) {
  return (
    <div className="flex-1 min-w-[140px] rounded-xl border border-white/10 bg-white/[0.03] p-4">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs uppercase tracking-wide text-slate-400">{label}</span>
        <Icon size={15} style={{ color: accent }} />
      </div>
      <div className="text-2xl font-semibold text-slate-100 tabular-nums">{value}</div>
    </div>
  );
}

export default function StaffDashboard() {
  const [tickets, setTickets] = useState(() => seedTickets());
  const [loading, setLoading] = useState(false);
  const [query, setQuery] = useState("");
  const [catFilter, setCatFilter] = useState("All");
  const [prioFilter, setPrioFilter] = useState("All");
  const [statusFilter, setStatusFilter] = useState("All");
  const [selected, setSelected] = useState(null);
  const [toast, setToast] = useState(null);

  const refresh = async () => {
    setLoading(true);
    const data = await apiGetTickets();
    setTickets(data);
    setLoading(false);
  };

  const filtered = useMemo(() => {
    return tickets.filter((t) => {
      const q = query.trim().toLowerCase();
      const matchesQuery =
        !q ||
        t.id.toLowerCase().includes(q) ||
        t.subject.toLowerCase().includes(q) ||
        t.customer.toLowerCase().includes(q);
      return (
        matchesQuery &&
        (catFilter === "All" || t.category === catFilter) &&
        (prioFilter === "All" || t.priority === prioFilter) &&
        (statusFilter === "All" || t.status === statusFilter)
      );
    });
  }, [tickets, query, catFilter, prioFilter, statusFilter]);

  const stats = useMemo(() => {
    const total = tickets.length;
    const byCategory = CATEGORIES.map((c) => ({
      name: c,
      value: tickets.filter((t) => t.category === c).length,
    }));
    const byPriority = PRIORITIES.map((p) => ({
      name: p,
      value: tickets.filter((t) => t.priority === p).length,
    }));
    const open = tickets.filter((t) => t.status !== "Resolved").length;
    const escalated = tickets.filter((t) => t.status === "Escalated").length;
    const avgConfidence = Math.round(
      tickets.reduce((s, t) => s + t.aiConfidence, 0) / (total || 1)
    );
    return { total, byCategory, byPriority, open, escalated, avgConfidence };
  }, [tickets]);

  const updateTicket = async (id, patch) => {
    // optimistic update
    setTickets((prev) => prev.map((t) => (t.id === id ? { ...t, ...patch } : t)));
    setSelected((prev) => (prev && prev.id === id ? { ...prev, ...patch } : prev));
    await apiUpdateTicket(id, patch);
    setToast(`${id} updated`);
    setTimeout(() => setToast(null), 1800);
  };

  return (
    <div className="min-h-screen w-full bg-[#0b0e14] text-slate-200 font-sans">
      <div className="max-w-6xl mx-auto px-5 py-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <div className="flex items-center gap-2 text-slate-400 text-xs uppercase tracking-widest mb-1">
              <Radio size={13} className="text-teal-400 animate-pulse" />
              Live Queue
            </div>
            <h1 className="text-xl font-semibold text-slate-50">Support Ticket Console</h1>
          </div>
          <button
            onClick={refresh}
            className="text-xs px-3 py-1.5 rounded-lg border border-white/10 bg-white/[0.04] hover:bg-white/[0.08] transition-colors text-slate-300"
          >
            {loading ? "Refreshing…" : "Refresh"}
          </button>
        </div>

        {/* Stat cards */}
        <div className="flex flex-wrap gap-3 mb-6">
          <StatCard label="Total Tickets" value={stats.total} icon={Tag} accent="#94a3b8" />
          <StatCard label="Open" value={stats.open} icon={Clock} accent="#60a5fa" />
          <StatCard label="Escalated" value={stats.escalated} icon={AlertTriangle} accent="#f87171" />
          <StatCard label="Avg AI Confidence" value={`${stats.avgConfidence}%`} icon={Sparkles} accent="#a78bfa" />
        </div>

        {/* Charts */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
            <div className="text-xs uppercase tracking-wide text-slate-400 mb-3">
              Tickets by Category (AI-classified)
            </div>
            <ResponsiveContainer width="100%" height={190}>
              <PieChart>
                <Pie
                  data={stats.byCategory}
                  dataKey="value"
                  nameKey="name"
                  innerRadius={45}
                  outerRadius={75}
                  paddingAngle={3}
                >
                  {stats.byCategory.map((entry) => (
                    <Cell key={entry.name} fill={CATEGORY_COLOR[entry.name]} stroke="none" />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ background: "#161b24", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8, fontSize: 12 }}
                />
                <Legend
                  verticalAlign="bottom"
                  height={24}
                  formatter={(val) => <span style={{ color: "#94a3b8", fontSize: 11 }}>{val}</span>}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>

          <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
            <div className="text-xs uppercase tracking-wide text-slate-400 mb-3">
              Tickets by Priority
            </div>
            <ResponsiveContainer width="100%" height={190}>
              <BarChart data={stats.byPriority}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" vertical={false} />
                <XAxis dataKey="name" tick={{ fill: "#94a3b8", fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} axisLine={false} tickLine={false} allowDecimals={false} />
                <Tooltip
                  contentStyle={{ background: "#161b24", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8, fontSize: 12 }}
                  cursor={{ fill: "rgba(255,255,255,0.04)" }}
                />
                <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                  {stats.byPriority.map((entry) => (
                    <Cell key={entry.name} fill={PRIORITY_COLOR[entry.name]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap gap-2 mb-3 items-center">
          <div className="flex items-center gap-2 bg-white/[0.04] border border-white/10 rounded-lg px-3 py-1.5 flex-1 min-w-[200px]">
            <Search size={14} className="text-slate-500" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search ID, subject, or customer…"
              className="bg-transparent outline-none text-sm placeholder:text-slate-500 w-full text-slate-200"
            />
          </div>
          {[
            { val: catFilter, set: setCatFilter, opts: CATEGORIES, label: "Category" },
            { val: prioFilter, set: setPrioFilter, opts: PRIORITIES, label: "Priority" },
            { val: statusFilter, set: setStatusFilter, opts: STATUSES, label: "Status" },
          ].map((f) => (
            <div key={f.label} className="relative">
              <select
                value={f.val}
                onChange={(e) => f.set(e.target.value)}
                className="appearance-none bg-white/[0.04] border border-white/10 rounded-lg pl-3 pr-7 py-1.5 text-sm text-slate-300 outline-none cursor-pointer hover:bg-white/[0.07]"
              >
                <option value="All">{f.label}: All</option>
                {f.opts.map((o) => (
                  <option key={o} value={o}>{o}</option>
                ))}
              </select>
              <ChevronDown size={13} className="absolute right-2 top-2.5 text-slate-500 pointer-events-none" />
            </div>
          ))}
          <span className="text-xs text-slate-500 ml-auto">{filtered.length} of {tickets.length} tickets</span>
        </div>

        {/* Ticket table */}
        <div className="rounded-xl border border-white/10 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-white/[0.04] text-left text-slate-400 text-xs uppercase tracking-wide">
                <th className="px-3 py-2.5 font-medium">Ticket</th>
                <th className="px-3 py-2.5 font-medium">Category</th>
                <th className="px-3 py-2.5 font-medium">Priority</th>
                <th className="px-3 py-2.5 font-medium">Status</th>
                <th className="px-3 py-2.5 font-medium">Confidence</th>
                <th className="px-3 py-2.5 font-medium">Assigned</th>
                <th className="px-3 py-2.5 font-medium">Created</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={7} className="text-center py-8 text-slate-500 text-sm">
                    No tickets match these filters.
                  </td>
                </tr>
              )}
              {filtered.map((t) => (
                <tr
                  key={t.id}
                  onClick={() => setSelected(t)}
                  className="border-t border-white/5 hover:bg-white/[0.03] cursor-pointer transition-colors"
                >
                  <td className="px-3 py-2.5">
                    <div className="font-mono text-xs text-slate-400">{t.id}</div>
                    <div className="text-slate-200">{t.subject}</div>
                  </td>
                  <td className="px-3 py-2.5">
                    <Badge color={CATEGORY_COLOR[t.category]}>{t.category}</Badge>
                  </td>
                  <td className="px-3 py-2.5">
                    <Badge color={PRIORITY_COLOR[t.priority]}>{t.priority}</Badge>
                  </td>
                  <td className="px-3 py-2.5">
                    <Badge color={STATUS_COLOR[t.status]}>{t.status}</Badge>
                  </td>
                  <td className="px-3 py-2.5 text-slate-400 tabular-nums">{t.aiConfidence}%</td>
                  <td className="px-3 py-2.5 text-slate-400">{t.assignedTo}</td>
                  <td className="px-3 py-2.5 text-slate-500 whitespace-nowrap">{timeAgo(t.createdAt)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Detail drawer */}
      {selected && (
        <div className="fixed inset-0 z-20 flex justify-end" onClick={() => setSelected(null)}>
          <div className="absolute inset-0 bg-black/50" />
          <div
            onClick={(e) => e.stopPropagation()}
            className="relative w-full max-w-sm h-full bg-[#11151d] border-l border-white/10 p-5 overflow-y-auto"
          >
            <div className="flex items-center justify-between mb-4">
              <div className="font-mono text-xs text-slate-500">{selected.id}</div>
              <button onClick={() => setSelected(null)} className="text-slate-500 hover:text-slate-200">
                <X size={16} />
              </button>
            </div>
            <h2 className="text-base font-semibold text-slate-50 mb-1">{selected.subject}</h2>
            <div className="flex items-center gap-1.5 text-xs text-slate-500 mb-4">
              <User size={12} /> {selected.customer}
            </div>

            <div className="flex flex-wrap gap-1.5 mb-5">
              <Badge color={CATEGORY_COLOR[selected.category]}>{selected.category}</Badge>
              <Badge color={PRIORITY_COLOR[selected.priority]}>{selected.priority}</Badge>
              <Badge color={STATUS_COLOR[selected.status]}>{selected.status}</Badge>
            </div>

            <div className="rounded-lg border border-white/10 bg-white/[0.03] p-3 mb-5">
              <div className="flex items-center gap-1.5 text-xs text-slate-400 mb-1">
                <Sparkles size={12} className="text-violet-400" /> AI Classification Confidence
              </div>
              <div className="h-2 rounded-full bg-white/10 overflow-hidden">
                <div
                  className="h-full rounded-full bg-violet-400"
                  style={{ width: `${selected.aiConfidence}%` }}
                />
              </div>
              <div className="text-right text-xs text-slate-400 mt-1">{selected.aiConfidence}%</div>
            </div>

            <label className="block text-xs uppercase tracking-wide text-slate-500 mb-1.5">Update Status</label>
            <div className="grid grid-cols-2 gap-2 mb-4">
              {STATUSES.map((s) => (
                <button
                  key={s}
                  onClick={() => updateTicket(selected.id, { status: s })}
                  className={`text-xs py-1.5 rounded-lg border transition-colors ${
                    selected.status === s
                      ? "border-teal-400/40 bg-teal-400/10 text-teal-300"
                      : "border-white/10 bg-white/[0.03] text-slate-400 hover:bg-white/[0.07]"
                  }`}
                >
                  {s}
                </button>
              ))}
            </div>

            <label className="block text-xs uppercase tracking-wide text-slate-500 mb-1.5">Assign To</label>
            <select
              value={selected.assignedTo}
              onChange={(e) => updateTicket(selected.id, { assignedTo: e.target.value })}
              className="w-full bg-white/[0.04] border border-white/10 rounded-lg px-3 py-2 text-sm text-slate-300 outline-none mb-5"
            >
              {AGENTS.map((a) => (
                <option key={a} value={a}>{a}</option>
              ))}
            </select>

            {selected.status !== "Escalated" && (
              <button
                onClick={() => updateTicket(selected.id, { status: "Escalated", priority: "Critical" })}
                className="w-full flex items-center justify-center gap-1.5 text-xs py-2 rounded-lg border border-red-400/30 bg-red-400/10 text-red-300 hover:bg-red-400/20 transition-colors"
              >
                <ArrowUpRight size={13} /> Escalate Ticket
              </button>
            )}
            {selected.status === "Resolved" && (
              <div className="flex items-center gap-1.5 text-xs text-emerald-400 mt-3 justify-center">
                <CheckCircle2 size={13} /> Marked resolved
              </div>
            )}
          </div>
        </div>
      )}

      {/* Toast */}
      {toast && (
        <div className="fixed bottom-5 left-1/2 -translate-x-1/2 bg-[#161b24] border border-white/10 text-slate-200 text-xs px-4 py-2 rounded-lg shadow-lg z-30">
          {toast}
        </div>
      )}
    </div>
  );
}
