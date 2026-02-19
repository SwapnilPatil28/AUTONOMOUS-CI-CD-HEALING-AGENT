import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

export default function ScoreBreakdownPanel({ score }) {
  if (!score) return null;

  const chartData = [
    { name: "Base", value: score.base_score },
    { name: "Speed Bonus", value: score.speed_bonus },
    { name: "Efficiency Penalty", value: -score.efficiency_penalty },
    { name: "Final", value: score.final_score }
  ];

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
            <XAxis dataKey="name" />
            <YAxis />
            <Tooltip />
            <Bar dataKey="value" fill="#2563eb" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
