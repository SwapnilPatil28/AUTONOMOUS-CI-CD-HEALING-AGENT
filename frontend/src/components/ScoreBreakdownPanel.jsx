import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell } from "recharts";

export default function ScoreBreakdownPanel({ score }) {
  if (!score) return null;

  const chartData = [
    { name: "Base", value: score.base_score },
    { name: "Speed Bonus", value: score.speed_bonus },
    { name: "Efficiency Penalty", value: -score.efficiency_penalty },
    { name: "Final", value: score.final_score }
  ];

  const barColors = {
    Base: "#22d3ee",
    "Speed Bonus": "#38bdf8",
    "Efficiency Penalty": "#fb7185",
    Final: "#fbbf24"
  };

  const tooltipStyle = {
    background: "rgba(15, 23, 42, 0.92)",
    border: "1px solid rgba(148, 163, 184, 0.35)",
    borderRadius: "12px",
    color: "#f8fafc",
    boxShadow: "0 0 24px rgba(0, 0, 0, 0.45)"
  };

  return (
    <section className="card">
      <h2>Score Breakdown Panel</h2>
      <div className="score-grid">
        <p><strong>Base Score:</strong> {score.base_score}</p>
        <p><strong>Speed Bonus:</strong> +{score.speed_bonus}</p>
        <p><strong>Efficiency Penalty:</strong> -{score.efficiency_penalty}</p>
        <p className="final-score"><strong>Final Total Score:</strong> {score.final_score}</p>
      </div>
      <div className="chart-wrap">
        <ResponsiveContainer width="100%" height={250}>
          <BarChart data={chartData}>
            <CartesianGrid stroke="rgba(148, 163, 184, 0.18)" strokeDasharray="4 4" vertical={false} />
            <XAxis
              dataKey="name"
              tick={{ fill: "rgba(226, 232, 240, 0.85)", fontSize: 12 }}
              axisLine={{ stroke: "rgba(148, 163, 184, 0.35)" }}
              tickLine={{ stroke: "rgba(148, 163, 184, 0.35)" }}
            />
            <YAxis
              tick={{ fill: "rgba(226, 232, 240, 0.75)", fontSize: 12 }}
              axisLine={{ stroke: "rgba(148, 163, 184, 0.35)" }}
              tickLine={{ stroke: "rgba(148, 163, 184, 0.35)" }}
            />
            <Tooltip
              cursor={{ fill: "rgba(51, 65, 85, 0.25)" }}
              contentStyle={tooltipStyle}
              labelStyle={{ color: "#f8fafc", fontWeight: 600 }}
              itemStyle={{ color: "#f8fafc" }}
              formatter={(value) => [
                <span style={{ color: "#f8fafc", fontWeight: 700 }}>{value}</span>,
                <span style={{ color: "rgba(226, 232, 240, 0.9)" }}>Score</span>
              ]}
            />
            <Bar dataKey="value" radius={[8, 8, 6, 6]}>
              {chartData.map((entry) => (
                <Cell key={entry.name} fill={barColors[entry.name]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
