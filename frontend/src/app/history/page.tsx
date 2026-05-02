"use client";

import { useEffect, useState } from "react";
import { ArrowLeft, Clock, ShieldAlert, Zap, ArrowRight } from "lucide-react";
import Link from "next/link";

interface Log {
  log_id: number;
  device_id: number;
  change_type: string;
  field_changed: string | null;
  old_value: string | null;
  new_value: string | null;
  changed_at: string;
  mac_address: string;
  ip_address: string;
}

export default function HistoryPage() {
  const [logs, setLogs] = useState<Log[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchLogs = async () => {
      try {
        const res = await fetch("http://127.0.0.1:8000/api/logs");
        if (!res.ok) throw new Error("Failed to fetch logs");
        const json = await res.json();
        setLogs(json.data || []);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchLogs();
  }, []);

  const getChangeBadge = (type: string) => {
    switch (type) {
      case 'INSERT':
        return <span className="bg-[#00ff66]/10 text-[#00ff66] px-2 py-1 rounded text-xs font-semibold flex items-center gap-1 w-max"><Zap className="w-3 h-3"/> New Device</span>;
      case 'STATUS_CHANGE':
        return <span className="bg-yellow-500/10 text-yellow-500 px-2 py-1 rounded text-xs font-semibold flex items-center gap-1 w-max"><Clock className="w-3 h-3"/> Status Change</span>;
      case 'UPDATE_IP':
      case 'UPDATE_HOSTNAME':
        return <span className="bg-[#00f0ff]/10 text-[#00f0ff] px-2 py-1 rounded text-xs font-semibold flex items-center gap-1 w-max"><ArrowRight className="w-3 h-3"/> Data Updated</span>;
      case 'SUSPICIOUS_CHANGE':
        return <span className="bg-[#ff3366]/10 text-[#ff3366] px-2 py-1 rounded text-xs font-semibold flex items-center gap-1 w-max"><ShieldAlert className="w-3 h-3"/> Suspicious</span>;
      default:
        return <span className="bg-white/10 text-white px-2 py-1 rounded text-xs font-semibold">{type}</span>;
    }
  };

  return (
    <div className="min-h-screen p-6 md:p-12 relative overflow-hidden">
      {/* Background gradients */}
      <div className="absolute top-[-10%] left-[-10%] w-96 h-96 bg-purple-500/10 rounded-full blur-[100px]" />
      <div className="absolute bottom-[-10%] right-[-10%] w-96 h-96 bg-blue-500/10 rounded-full blur-[100px]" />
      
      <div className="max-w-7xl mx-auto relative z-10">
        <header className="flex flex-col md:flex-row justify-between items-start md:items-center mb-10 gap-4">
          <div>
            <h1 className="text-4xl font-extrabold tracking-tight mb-2">
              <span className="gradient-text">Audit</span> Trail
            </h1>
            <p className="text-gray-400 text-sm">Review historical changes and security events</p>
          </div>
          <Link href="/">
            <button className="flex items-center gap-2 glass-panel px-6 py-2 rounded-lg hover:bg-white/10 transition-colors text-sm">
              <ArrowLeft className="w-4 h-4" /> Back to Radar
            </button>
          </Link>
        </header>

        {error ? (
          <div className="glass-panel p-6 rounded-2xl border-[#ff3366] border">
            <h3 className="text-[#ff3366] font-bold">Error loading logs</h3>
            <p className="text-sm text-gray-300">{error}</p>
          </div>
        ) : (
          <div className="glass-panel rounded-2xl overflow-hidden">
            <div className="p-6 border-b border-white/10">
              <h3 className="text-lg font-semibold flex items-center gap-2"><Clock className="w-5 h-5 text-gray-400"/> Recent Activity Log (Top 100)</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-white/5 text-xs uppercase tracking-wider text-gray-400">
                    <th className="p-4 font-medium">Timestamp</th>
                    <th className="p-4 font-medium">Device Reference</th>
                    <th className="p-4 font-medium">Event Type</th>
                    <th className="p-4 font-medium">Details (Old ➝ New)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {loading ? (
                    <tr><td colSpan={4} className="p-8 text-center text-gray-400">Loading history...</td></tr>
                  ) : logs.length === 0 ? (
                    <tr><td colSpan={4} className="p-8 text-center text-gray-400">No events found.</td></tr>
                  ) : logs.map((log) => (
                    <tr key={log.log_id} className="hover:bg-white/5 transition-colors">
                      <td className="p-4 text-sm text-gray-300 whitespace-nowrap">
                        {log.changed_at}
                      </td>
                      <td className="p-4">
                        <div className="text-sm font-mono text-gray-300">{log.mac_address}</div>
                        <div className="text-xs text-gray-500 mt-1">ID: {log.device_id} | {log.ip_address}</div>
                      </td>
                      <td className="p-4">
                        {getChangeBadge(log.change_type)}
                      </td>
                      <td className="p-4 text-sm">
                        {log.change_type === 'INSERT' ? (
                          <span className="text-gray-400">Device discovered on network</span>
                        ) : log.change_type === 'SUSPICIOUS_CHANGE' ? (
                          <div className="text-[#ff3366]">
                            <span className="block font-bold mb-1">MAC Mismatch!</span>
                            <span className="text-gray-400">Expected:</span> <span className="font-mono">{log.old_value}</span><br/>
                            <span className="text-gray-400">Detected:</span> <span className="font-mono">{log.new_value}</span>
                          </div>
                        ) : (
                          <div className="flex items-center gap-2">
                            <span className="text-gray-500 capitalize">{log.field_changed?.replace('_', ' ')}:</span>
                            <span className="text-[#ff3366] line-through">{log.old_value || 'None'}</span>
                            <span className="text-gray-500">➝</span>
                            <span className="text-[#00ff66]">{log.new_value || 'None'}</span>
                          </div>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
