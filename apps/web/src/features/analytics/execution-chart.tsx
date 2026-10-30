"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
export type Daily = {
  date: string;
  succeeded: number;
  failed: number;
  other: number;
};

export default function ExecutionChart({ daily }: { daily: Daily[] }) {
  const data = daily.map((point) => ({ ...point, label: point.date.slice(5) }));
  return (
    <>
      <div
        className="h-64 min-w-0"
        role="img"
        aria-label="Execution outcomes by UTC request day. Exact values are available in the table below."
      >
        <ResponsiveContainer width="100%" height="100%" minWidth={0}>
          <BarChart
            data={data}
            accessibilityLayer
            margin={{ left: -20, right: 10, top: 10, bottom: 0 }}
          >
            <CartesianGrid
              strokeDasharray="3 3"
              vertical={false}
              stroke="#e2e8f0"
            />
            <XAxis
              dataKey="label"
              tick={{ fontSize: 11 }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              allowDecimals={false}
              tick={{ fontSize: 11 }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            <Bar
              dataKey="succeeded"
              name="Succeeded"
              stackId="runs"
              fill="#0f766e"
              isAnimationActive={false}
            />
            <Bar
              dataKey="failed"
              name="Failed"
              stackId="runs"
              fill="#b91c1c"
              isAnimationActive={false}
            />
            <Bar
              dataKey="other"
              name="In progress / cancelled"
              stackId="runs"
              fill="#94a3b8"
              isAnimationActive={false}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <details className="mt-4 text-xs text-slate-500">
        <summary className="cursor-pointer">View exact daily values</summary>
        <div className="mt-3 overflow-auto">
          <table>
            <caption className="sr-only">
              Execution counts by UTC request date and current status
            </caption>
            <thead>
              <tr>
                <th>Date (UTC)</th>
                <th>Succeeded</th>
                <th>Failed</th>
                <th>Other</th>
              </tr>
            </thead>
            <tbody>
              {daily.map((d) => (
                <tr key={d.date}>
                  <td>{d.date}</td>
                  <td>{d.succeeded}</td>
                  <td>{d.failed}</td>
                  <td>{d.other}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </>
  );
}
