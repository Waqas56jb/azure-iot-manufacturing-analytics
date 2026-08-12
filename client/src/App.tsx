import { useEffect, useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ComposedChart,
  Legend,
  Line,
  Pie,
  PieChart,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";
import type { AnalyticsData } from "./types";

const COPPER = "#d4894a";
const STEEL = "#4ea3a1";
const DANGER = "#e06a4e";
const MUTED = "#a39a8f";
const INK = "#f2ebe3";
const FAIL_COLORS = [COPPER, STEEL, "#c96b5d", "#8bb7ff", "#e2b07a"];

type Filter = "ALL" | "L" | "M" | "H";

const tooltipStyle = {
  background: "rgba(20,24,28,0.95)",
  border: "1px solid rgba(242,235,227,0.12)",
  borderRadius: 12,
  color: INK,
};

function fmt(n: number) {
  return n.toLocaleString();
}

export default function App() {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<Filter>("ALL");

  useEffect(() => {
    fetch("/data/analytics.json")
      .then((r) => {
        if (!r.ok) throw new Error(`Failed to load analytics (${r.status})`);
        return r.json();
      })
      .then(setData)
      .catch((e: Error) => setError(e.message));
  }, []);

  const filteredScatter = useMemo(() => {
    if (!data) return [];
    if (filter === "ALL") return data.scatter;
    return data.scatter.filter((d) => d.type === filter);
  }, [data, filter]);

  const productView = useMemo(() => {
    if (!data) return [];
    if (filter === "ALL") return data.byProductType;
    return data.byProductType.filter((d) => d.type === filter);
  }, [data, filter]);

  if (error) {
    return (
      <div className="error">
        <h1>Couldn’t load dashboard</h1>
        <p>{error}</p>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="loading">
        <h1>ForgeSight</h1>
        <p>Loading plant analytics…</p>
      </div>
    );
  }

  const { kpis, meta } = data;

  return (
    <div className="page">
      <header className="hero">
        <div className="brand-row">
          <div>
            <p className="eyebrow">Manufacturing IoT · Aggregation Desk</p>
            <h1 className="brand">{meta.title}</h1>
          </div>
          <div className="meta-chip">
            <strong>{fmt(meta.records)}</strong> telemetry cycles analyzed
          </div>
        </div>
        <p className="hero-copy">
          One-page operations view of machine health, failure modes, and process
          stress — built from aggregated plant telemetry. No model training, just
          clear plant truth.
        </p>
        <div className="filters">
          {(["ALL", "L", "M", "H"] as Filter[]).map((f) => (
            <button
              key={f}
              className={`filter-btn ${filter === f ? "active" : ""}`}
              onClick={() => setFilter(f)}
            >
              {f === "ALL" ? "All product types" : `${f} quality`}
            </button>
          ))}
        </div>
      </header>

      <section className="kpi-grid">
        <article className="kpi">
          <div className="label">Failure rate</div>
          <div className="value">{kpis.failureRate}%</div>
          <div className="hint">{fmt(kpis.failures)} failed cycles</div>
        </article>
        <article className="kpi">
          <div className="label">Healthy share</div>
          <div className="value">{kpis.healthyRate}%</div>
          <div className="hint">Stable operating window</div>
        </article>
        <article className="kpi">
          <div className="label">Avg torque</div>
          <div className="value">{kpis.avgTorque}</div>
          <div className="hint">Nm across all runs</div>
        </article>
        <article className="kpi">
          <div className="label">Avg RPM</div>
          <div className="value">{fmt(kpis.avgRpm)}</div>
          <div className="hint">Spindle speed mean</div>
        </article>
        <article className="kpi">
          <div className="label">Avg tool wear</div>
          <div className="value">{kpis.avgToolWear}</div>
          <div className="hint">Minutes of use</div>
        </article>
        <article className="kpi">
          <div className="label">High-risk share</div>
          <div className="value">{kpis.highRiskShare}%</div>
          <div className="hint">Wear/torque stressed cycles</div>
        </article>
      </section>

      <section className="stack">
        <div className="grid-2">
          <article className="panel">
            <h2>Failure rate by product type</h2>
            <p className="desc">
              Compare L / M / H quality classes — volume vs failure intensity.
            </p>
            <div style={{ width: "100%", height: 300 }}>
              <ResponsiveContainer>
                <ComposedChart data={productView}>
                  <CartesianGrid stroke="rgba(242,235,227,0.08)" vertical={false} />
                  <XAxis dataKey="label" stroke={MUTED} tick={{ fill: MUTED }} />
                  <YAxis
                    yAxisId="left"
                    stroke={MUTED}
                    tick={{ fill: MUTED }}
                    tickFormatter={(v) => `${v}%`}
                  />
                  <YAxis
                    yAxisId="right"
                    orientation="right"
                    stroke={MUTED}
                    tick={{ fill: MUTED }}
                  />
                  <Tooltip contentStyle={tooltipStyle} />
                  <Legend />
                  <Bar
                    yAxisId="right"
                    dataKey="total"
                    name="Cycles"
                    fill={STEEL}
                    radius={[8, 8, 0, 0]}
                    opacity={0.55}
                  />
                  <Line
                    yAxisId="left"
                    type="monotone"
                    dataKey="failureRate"
                    name="Failure %"
                    stroke={COPPER}
                    strokeWidth={3}
                    dot={{ r: 5, fill: COPPER }}
                  />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </article>

          <article className="panel">
            <h2>Failure mode mix</h2>
            <p className="desc">Which mechanical failure types dominate the plant.</p>
            <div style={{ width: "100%", height: 300 }}>
              <ResponsiveContainer>
                <PieChart>
                  <Pie
                    data={data.failureTypes}
                    dataKey="count"
                    nameKey="code"
                    innerRadius={68}
                    outerRadius={105}
                    paddingAngle={3}
                  >
                    {data.failureTypes.map((_, i) => (
                      <Cell key={i} fill={FAIL_COLORS[i % FAIL_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={tooltipStyle} />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </article>
        </div>

        <div className="grid-3">
          <article className="panel">
            <h2>Risk band profile</h2>
            <p className="desc">Operating stress bands from wear & torque rules.</p>
            <div style={{ width: "100%", height: 260 }}>
              <ResponsiveContainer>
                <BarChart data={data.riskBands}>
                  <CartesianGrid stroke="rgba(242,235,227,0.08)" vertical={false} />
                  <XAxis dataKey="band" stroke={MUTED} tick={{ fill: MUTED }} />
                  <YAxis stroke={MUTED} tick={{ fill: MUTED }} />
                  <Tooltip contentStyle={tooltipStyle} />
                  <Bar dataKey="total" name="Cycles" fill={STEEL} radius={[8, 8, 0, 0]} />
                  <Bar dataKey="failures" name="Failures" fill={DANGER} radius={[8, 8, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </article>

          <article className="panel">
            <h2>Tool wear vs failures</h2>
            <p className="desc">Failure rate climbs as tools age through bins.</p>
            <div style={{ width: "100%", height: 260 }}>
              <ResponsiveContainer>
                <AreaChart data={data.wearBins}>
                  <defs>
                    <linearGradient id="wearFill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor={COPPER} stopOpacity={0.55} />
                      <stop offset="100%" stopColor={COPPER} stopOpacity={0.02} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid stroke="rgba(242,235,227,0.08)" vertical={false} />
                  <XAxis dataKey="range" stroke={MUTED} tick={{ fill: MUTED, fontSize: 11 }} />
                  <YAxis stroke={MUTED} tick={{ fill: MUTED }} tickFormatter={(v) => `${v}%`} />
                  <Tooltip contentStyle={tooltipStyle} />
                  <Area
                    type="monotone"
                    dataKey="failureRate"
                    name="Failure %"
                    stroke={COPPER}
                    fill="url(#wearFill)"
                    strokeWidth={2.5}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </article>

          <article className="panel">
            <h2>Torque stress bins</h2>
            <p className="desc">Higher torque bands carry heavier failure load.</p>
            <div style={{ width: "100%", height: 260 }}>
              <ResponsiveContainer>
                <BarChart data={data.torqueBins}>
                  <CartesianGrid stroke="rgba(242,235,227,0.08)" vertical={false} />
                  <XAxis dataKey="range" stroke={MUTED} tick={{ fill: MUTED }} />
                  <YAxis stroke={MUTED} tick={{ fill: MUTED }} tickFormatter={(v) => `${v}%`} />
                  <Tooltip contentStyle={tooltipStyle} />
                  <Bar
                    dataKey="failureRate"
                    name="Failure %"
                    fill={COPPER}
                    radius={[8, 8, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </article>
        </div>

        <div className="grid-2">
          <article className="panel">
            <h2>RPM × torque operating map</h2>
            <p className="desc">
              Sampled cycles — copper marks failures, steel marks healthy runs
              {filter !== "ALL" ? ` · filtered to ${filter}` : ""}.
            </p>
            <div style={{ width: "100%", height: 340 }}>
              <ResponsiveContainer>
                <ScatterChart>
                  <CartesianGrid stroke="rgba(242,235,227,0.08)" />
                  <XAxis
                    type="number"
                    dataKey="rpm"
                    name="RPM"
                    stroke={MUTED}
                    tick={{ fill: MUTED }}
                    domain={["auto", "auto"]}
                  />
                  <YAxis
                    type="number"
                    dataKey="torque"
                    name="Torque"
                    stroke={MUTED}
                    tick={{ fill: MUTED }}
                  />
                  <ZAxis type="number" dataKey="wear" range={[40, 180]} />
                  <Tooltip
                    cursor={{ strokeDasharray: "3 3" }}
                    contentStyle={tooltipStyle}
                  />
                  <Scatter
                    name="Healthy"
                    data={filteredScatter.filter((d) => !d.failed)}
                    fill={STEEL}
                    fillOpacity={0.55}
                  />
                  <Scatter
                    name="Failed"
                    data={filteredScatter.filter((d) => d.failed)}
                    fill={DANGER}
                    fillOpacity={0.9}
                  />
                  <Legend />
                </ScatterChart>
              </ResponsiveContainer>
            </div>
          </article>

          <article className="panel">
            <h2>Process temperature delta</h2>
            <p className="desc">
              Failure intensity across process−air temperature gaps.
            </p>
            <div style={{ width: "100%", height: 340 }}>
              <ResponsiveContainer>
                <ComposedChart data={data.tempDeltaBins}>
                  <CartesianGrid stroke="rgba(242,235,227,0.08)" vertical={false} />
                  <XAxis dataKey="range" stroke={MUTED} tick={{ fill: MUTED }} />
                  <YAxis stroke={MUTED} tick={{ fill: MUTED }} />
                  <Tooltip contentStyle={tooltipStyle} />
                  <Legend />
                  <Bar
                    dataKey="total"
                    name="Cycles"
                    fill={STEEL}
                    opacity={0.45}
                    radius={[8, 8, 0, 0]}
                  />
                  <Line
                    type="monotone"
                    dataKey="failureRate"
                    name="Failure %"
                    stroke={COPPER}
                    strokeWidth={3}
                  />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </article>
        </div>

        <div className="grid-2">
          <article className="panel">
            <h2>Failure mix by product class</h2>
            <p className="desc">Stacked failure codes within L / M / H segments.</p>
            <div style={{ width: "100%", height: 300 }}>
              <ResponsiveContainer>
                <BarChart data={data.failureMixByType}>
                  <CartesianGrid stroke="rgba(242,235,227,0.08)" vertical={false} />
                  <XAxis dataKey="type" stroke={MUTED} tick={{ fill: MUTED }} />
                  <YAxis stroke={MUTED} tick={{ fill: MUTED }} />
                  <Tooltip contentStyle={tooltipStyle} />
                  <Legend />
                  {["TWF", "HDF", "PWF", "OSF", "RNF"].map((code, i) => (
                    <Bar
                      key={code}
                      dataKey={code}
                      stackId="a"
                      fill={FAIL_COLORS[i]}
                      radius={i === 4 ? [6, 6, 0, 0] : 0}
                    />
                  ))}
                </BarChart>
              </ResponsiveContainer>
            </div>
          </article>

          <article className="panel">
            <h2>Plant insights</h2>
            <p className="desc">Aggregation takeaways for ops review.</p>
            <div className="insights">
              {data.insights.map((text, i) => (
                <div className="insight" key={i}>
                  <div className="n">{i + 1}</div>
                  <p>{text}</p>
                </div>
              ))}
              <div className="insight">
                <div className="n">★</div>
                <p>
                  Median tool wear on failed cycles:{" "}
                  <strong>{kpis.medianWearFailures} min</strong>. Watch wear past
                  ~200 min and torque above ~60 Nm.
                </p>
              </div>
            </div>
          </article>
        </div>

        <article className="panel">
          <h2>Highest-wear failure events</h2>
          <p className="desc">
            Top stressed failed cycles — useful for maintenance prioritization.
          </p>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>UDI</th>
                  <th>Product</th>
                  <th>Type</th>
                  <th>Failure</th>
                  <th>Risk</th>
                  <th>Wear</th>
                  <th>Torque</th>
                  <th>RPM</th>
                  <th>ΔTemp</th>
                </tr>
              </thead>
              <tbody>
                {data.topFailures.map((row) => (
                  <tr key={row.udi}>
                    <td>{row.udi}</td>
                    <td>{row.productId}</td>
                    <td>{row.type}</td>
                    <td>{row.failureType}</td>
                    <td>
                      <span className={`badge ${row.risk.toLowerCase()}`}>
                        {row.risk}
                      </span>
                    </td>
                    <td>{row.wear}</td>
                    <td>{row.torque}</td>
                    <td>{row.rpm}</td>
                    <td>{row.tempDelta}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </article>
      </section>
    </div>
  );
}
