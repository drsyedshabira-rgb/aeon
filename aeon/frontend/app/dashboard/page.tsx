"use client";

import { useEffect, useState } from "react";

interface ReportSummary {
  report_id: string;
  status: "pending_review" | "submitted" | "rejected" | "draft" | "acknowledged";
  extracted: { suspect_drugs: any[]; reaction: any; confidence: number };
}

const STATUS_COLORS: Record<string, string> = {
  pending_review: "bg-yellow-100 text-yellow-800",
  submitted: "bg-green-100 text-green-800",
  rejected: "bg-red-100 text-red-800",
  draft: "bg-gray-100 text-gray-800",
  acknowledged: "bg-blue-100 text-blue-800",
};

export default function DashboardPage() {
  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/v1/reports")
      .then((res) => res.json())
      .then((data) => setReports(Array.isArray(data) ? data : []))
      .catch(() => setReports([]))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="p-6">Loading reports…</div>;

  return (
    <div className="p-6">
      <h1 className="text-2xl font-semibold mb-4">Recent ADR Reports</h1>
      {reports.length === 0 ? (
        <p className="text-gray-500">No reports yet. Use Snap & Submit to create one.</p>
      ) : (
        <table className="w-full border-collapse">
          <thead>
            <tr className="text-left border-b">
              <th className="py-2">Report ID</th>
              <th>Drug</th>
              <th>Reaction</th>
              <th>Confidence</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {reports.map((r) => (
              <tr key={r.report_id} className="border-b">
                <td className="py-2 font-mono text-sm">{r.report_id.slice(0, 8)}…</td>
                <td>{r.extracted?.suspect_drugs?.[0]?.drug_name ?? "—"}</td>
                <td>{r.extracted?.reaction?.meddra_term ?? "—"}</td>
                <td>{r.extracted?.confidence ?? "—"}</td>
                <td>
                  <span className={`px-2 py-1 rounded text-xs ${STATUS_COLORS[r.status] ?? ""}`}>
                    {r.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
