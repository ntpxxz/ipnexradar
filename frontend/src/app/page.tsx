"use client";

import { useEffect, useState, useMemo } from "react";
import { Activity, ShieldAlert, MonitorSmartphone, Server, RefreshCw, Clock, History, Search, Filter, Download, Plus, X } from "lucide-react";
import Link from "next/link";

interface Device {
  device_id: string | number;
  mac_address: string;
  ip_address: string;
  hostname: string;
  model: string;
  process: string;
  status: string;
  is_reserved: string | boolean | number;
  first_seen: string;
  last_seen: string;
  has_recent_ip_change: boolean;
  remark?: string;
}

interface Log {
  log_id: string | number;
  change_type: string;
}

export default function Dashboard() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [logs, setLogs] = useState<Log[]>([]);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());
  const [error, setError] = useState<string | null>(null);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  // Search & Filter States
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | "online" | "offline">("all");

  // Manual Scan States
  const [subnet, setSubnet] = useState("192.168.1.0/24");
  const [isScanning, setIsScanning] = useState(false);
  const [scanMessage, setScanMessage] = useState("");

  // Manual Register States
  const [showAddForm, setShowAddForm] = useState(false);
  const [newDevice, setNewDevice] = useState({ hostname: "", ip_address: "", mac_address: "", is_reserved: false });
  const [formLoading, setFormLoading] = useState(false);

  type SortField = 'hostname' | 'process' | 'model' | 'ip_address' | 'mac_address' | 'status' | 'last_seen';
  const [sortField, setSortField] = useState<SortField>('ip_address');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');

  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 15;

  const filteredAndSortedDevices = useMemo(() => {
    let result = devices.filter(device => {
      const matchesSearch =
        device.hostname?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        device.process?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        device.model?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        device.ip_address?.includes(searchTerm) ||
        device.mac_address?.toLowerCase().includes(searchTerm.toLowerCase());

      const matchesStatus = statusFilter === "all" || device.status === statusFilter;

      return matchesSearch && matchesStatus;
    });

    result.sort((a, b) => {
      const aValue = a[sortField] || '';
      const bValue = b[sortField] || '';
      if (aValue < bValue) return sortDirection === 'asc' ? -1 : 1;
      if (aValue > bValue) return sortDirection === 'asc' ? 1 : -1;
      return 0;
    });

    return result;
  }, [devices, searchTerm, statusFilter, sortField, sortDirection]);

  useEffect(() => {
    setCurrentPage(1);
  }, [searchTerm, statusFilter]);

  const totalPages = Math.max(1, Math.ceil(filteredAndSortedDevices.length / itemsPerPage));
  const paginatedDevices = filteredAndSortedDevices.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  const exportToCSV = () => {
    const headers = ["ID", "Control/Host", "Process", "Model", "IP Address", "MAC Address", "Status", "First Seen", "Last Seen"];
    const rows = filteredAndSortedDevices.map(d => [
      d.device_id,
      d.hostname || "Unknown",
      d.process || "",
      d.model || "",
      d.ip_address,
      d.mac_address,
      d.status,
      d.first_seen,
      d.last_seen
    ]);

    const csvContent = [
      headers.join(","),
      ...rows.map(r => r.join(","))
    ].join("\n");

    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const link = document.createElement("a");
    const url = URL.createObjectURL(blob);
    link.setAttribute("href", url);
    link.setAttribute("download", `ipnex_report_${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = "hidden";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const fetchDevices = async () => {
    try {
      const [resDevices, resLogs] = await Promise.all([
        fetch("http://127.0.0.1:8000/api/devices"),
        fetch("http://127.0.0.1:8000/api/logs")
      ]);

      if (!resDevices.ok || !resLogs.ok) throw new Error("Failed to fetch data");

      const jsonDevices = await resDevices.json();
      const jsonLogs = await resLogs.json();

      setDevices(jsonDevices.data || []);
      setLogs(jsonLogs.data || []);
      setLastUpdated(new Date());
      setError(null);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDevices();
    const interval = setInterval(fetchDevices, 10000); // Polling every 10s
    return () => clearInterval(interval);
  }, []);

  const handleManualScan = async () => {
    if (!subnet) return;
    setIsScanning(true);
    setScanMessage("");
    try {
      const res = await fetch("http://127.0.0.1:8000/api/scan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ subnet })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Scan failed");
      setScanMessage(`${data.message} (${data.devices_found} devices)`);
      fetchDevices();
    } catch (err: any) {
      setScanMessage(`Error: ${err.message}`);
    } finally {
      setIsScanning(false);
    }
  };

  const handleManualAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormLoading(true);
    try {
      const res = await fetch("http://127.0.0.1:8000/api/devices", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(newDevice)
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || "Failed to register device");
      }
      setNewDevice({ hostname: "", ip_address: "", mac_address: "", is_reserved: false });
      setShowAddForm(false);
      fetchDevices();
      alert("Device registered successfully!");
    } catch (err: any) {
      alert(`Error: ${err.message}`);
    } finally {
      setFormLoading(false);
    }
  };

  const totalDevices = devices.length;
  const spoofingCount = logs.filter((log) => log.change_type === "SUSPICIOUS_CHANGE").length;

  return (
    <div className="min-h-screen p-6 md:p-12 relative overflow-hidden">
      {/* Background gradients */}
      <div className="absolute top-[-10%] left-[-10%] w-96 h-96 bg-blue-500/10 rounded-full blur-[100px]" />
      <div className="absolute bottom-[-10%] right-[-10%] w-96 h-96 bg-purple-500/10 rounded-full blur-[100px]" />

      <div className="max-w-7xl mx-auto relative z-10">
        <header className="flex flex-col md:flex-row justify-between items-start md:items-center mb-10 gap-4">
          <div>
            <h1 className="text-4xl font-extrabold tracking-tight mb-2">
              <span className="gradient-text">IPNEX</span> Radar
            </h1>
            <p className="text-gray-400 text-sm">Advanced IP Monitoring & Anti-Spoofing System</p>
          </div>
          <div className="flex items-center gap-4 glass-panel px-4 py-2 rounded-full">
            <Clock className="w-4 h-4 text-gray-400" />
            <span className="text-sm text-gray-300">
              Updated: {mounted ? lastUpdated.toLocaleTimeString() : "--:--:--"}
            </span>
            <button
              onClick={() => fetchDevices()}
              className="p-2 hover:bg-white/10 rounded-full transition-colors"
              title="Refresh Data"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''} text-[#00f0ff]`} />
            </button>
            <Link href="/unused-ips">
              <button
                className="flex items-center gap-2 p-2 px-3 hover:bg-white/10 rounded-full transition-colors"
                title="Find Unused IPs"
              >
                <Search className="w-4 h-4 text-[#00ff66]" />
                <span className="text-sm font-medium text-[#00ff66] hidden sm:block">Free IPs</span>
              </button>
            </Link>
            <Link href="/history">
              <button
                className="flex items-center gap-2 p-2 px-3 hover:bg-white/10 rounded-full transition-colors"
                title="View Audit Trail"
              >
                <History className="w-4 h-4 text-purple-400" />
                <span className="text-sm font-medium text-purple-400 hidden sm:block">Logs</span>
              </button>
            </Link>
          </div>
        </header>

        {/* Stats Row */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
          <div className="glass-panel p-6 rounded-2xl flex items-center justify-between border-l-4 border-l-[#00f0ff]">
            <div>
              <p className="text-gray-400 text-sm mb-1">Active Devices</p>
              <h2 className="text-3xl font-bold">{totalDevices}</h2>
            </div>
            <div className="p-4 bg-[#00f0ff]/10 rounded-xl">
              <Activity className="w-6 h-6 text-[#00f0ff]" />
            </div>
          </div>

          <div className="glass-panel p-6 rounded-2xl flex items-center justify-between border-l-4 border-l-[#00ff66]">
            <div>
              <p className="text-gray-400 text-sm mb-1">Authorized</p>
              <h2 className="text-3xl font-bold">
                {devices.filter(d => d.status === 'online').length}
              </h2>
            </div>
            <div className="p-4 bg-[#00ff66]/10 rounded-xl">
              <ShieldAlert className="w-6 h-6 text-[#00ff66]" />
            </div>
          </div>

          <div className="glass-panel p-6 rounded-2xl flex items-center justify-between border-l-4 border-l-[#ff3366] pulse-red">
            <div>
              <p className="text-gray-400 text-sm mb-1">Spoofing Alerts</p>
              <h2 className="text-3xl font-bold text-[#ff3366]">{spoofingCount}</h2>

            </div>
            <div className="p-4 bg-[#ff3366]/10 rounded-xl">
              <ShieldAlert className="w-6 h-6 text-[#ff3366]" />
            </div>
          </div>
        </div>

        {/* Manual Controls Panel */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-10">
          {/* Manual Scan */}
          <div className="glass-panel p-6 rounded-2xl">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Activity className="w-5 h-5 text-[#00f0ff]" /> Manual Network Scan
            </h3>
            <div className="flex items-center gap-3">
              <input
                type="text"
                value={subnet}
                onChange={(e) => setSubnet(e.target.value)}
                placeholder="e.g. 192.168.1.0/24"
                className="bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-white outline-none focus:border-[#00f0ff] transition-colors flex-1"
              />
              <button
                onClick={handleManualScan}
                disabled={isScanning}
                className={`bg-[#00f0ff] text-black px-6 py-2 rounded-lg font-semibold transition-all hover:bg-[#00c0cc] ${isScanning ? 'opacity-70 cursor-not-allowed' : ''} flex items-center gap-2`}
              >
                {isScanning ? <RefreshCw className="w-4 h-4 animate-spin" /> : <span>Scan Now</span>}
              </button>
            </div>
            {scanMessage && (
              <div className={`mt-3 text-xs px-3 py-2 rounded-lg border ${scanMessage.startsWith('Error') ? 'bg-[#ff3366]/10 border-[#ff3366]/30 text-[#ff3366]' : 'bg-[#00ff66]/10 border-[#00ff66]/30 text-[#00ff66]'}`}>
                {scanMessage}
              </div>
            )}
          </div>

          {/* Manual Add Device */}
          <div className="glass-panel p-6 rounded-2xl relative overflow-hidden">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <Plus className="w-5 h-5 text-[#00ff66]" /> Register Device
              </h3>
              <button
                onClick={() => setShowAddForm(!showAddForm)}
                className="bg-[#00ff66]/10 text-[#00ff66] px-3 py-1 rounded-lg text-xs hover:bg-[#00ff66]/20 transition-all"
              >
                {showAddForm ? "Close Form" : "Open Form"}
              </button>
            </div>

            {showAddForm ? (
              <form onSubmit={handleManualAdd} className="space-y-3 animate-in fade-in duration-300">
                <div className="grid grid-cols-2 gap-3">
                  <input
                    type="text"
                    placeholder="Hostname"
                    value={newDevice.hostname}
                    onChange={(e) => setNewDevice({ ...newDevice, hostname: e.target.value })}
                    required
                    className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-xs text-white outline-none focus:border-[#00ff66]"
                  />
                  <input
                    type="text"
                    placeholder="IP Address"
                    value={newDevice.ip_address}
                    onChange={(e) => setNewDevice({ ...newDevice, ip_address: e.target.value })}
                    required
                    className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-xs text-white outline-none focus:border-[#00ff66]"
                  />
                </div>
                <div className="flex gap-3">
                  <input
                    type="text"
                    placeholder="MAC Address"
                    value={newDevice.mac_address}
                    onChange={(e) => setNewDevice({ ...newDevice, mac_address: e.target.value })}
                    required
                    className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-xs text-white outline-none focus:border-[#00ff66] flex-1"
                  />
                  <button
                    type="submit"
                    disabled={formLoading}
                    className="bg-[#00ff66] text-black px-4 rounded-lg text-xs font-bold hover:bg-[#00cc55] transition-all disabled:opacity-50"
                  >
                    {formLoading ? "Adding..." : "Add Device"}
                  </button>
                </div>
              </form>
            ) : (
              <p className="text-sm text-gray-500 mt-2">Manually register a device into the master registry without scanning.</p>
            )}
          </div>
        </div>

        {/* Main Content Controls */}
        <div className="flex flex-col md:flex-row items-center justify-between gap-4 mb-6">
          <div className="relative w-full md:w-96">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
            <input
              type="text"
              placeholder="Search by Hostname, IP or MAC..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full bg-white/5 border border-white/10 rounded-xl pl-10 pr-4 py-2 text-sm text-white outline-none focus:border-[#00f0ff] transition-colors"
            />
          </div>

          <div className="flex items-center gap-2 w-full md:w-auto">
            <div className="flex bg-white/5 p-1 rounded-xl border border-white/10">
              <button
                onClick={() => setStatusFilter("all")}
                className={`px-4 py-1.5 rounded-lg text-xs font-medium transition-all ${statusFilter === 'all' ? 'bg-[#00f0ff] text-black shadow-lg shadow-[#00f0ff]/20' : 'text-gray-400 hover:text-white'}`}
              >
                All
              </button>
              <button
                onClick={() => setStatusFilter("online")}
                className={`px-4 py-1.5 rounded-lg text-xs font-medium transition-all ${statusFilter === 'online' ? 'bg-[#00ff66] text-black shadow-lg shadow-[#00ff66]/20' : 'text-gray-400 hover:text-white'}`}
              >
                Online
              </button>
              <button
                onClick={() => setStatusFilter("offline")}
                className={`px-4 py-1.5 rounded-lg text-xs font-medium transition-all ${statusFilter === 'offline' ? 'bg-gray-500 text-white shadow-lg' : 'text-gray-400 hover:text-white'}`}
              >
                Offline
              </button>
            </div>

            <button
              onClick={exportToCSV}
              className="flex items-center gap-2 px-4 py-2 bg-white/5 border border-white/10 rounded-xl text-sm text-gray-300 hover:bg-white/10 transition-colors ml-auto md:ml-0"
            >
              <Download className="w-4 h-4" />
              <span>Export CSV</span>
            </button>
          </div>
        </div>

        {/* Main Content */}
        {error ? (
          <div className="glass-panel p-6 rounded-2xl border-[#ff3366] border">
            <h3 className="text-[#ff3366] font-bold flex items-center gap-2 mb-2">
              <ShieldAlert /> Connection Error
            </h3>
            <p className="text-sm text-gray-300">{error}</p>
            <p className="text-xs text-gray-500 mt-2">Please ensure the FastAPI backend is running.</p>
          </div>
        ) : (
          <div className="glass-panel rounded-2xl overflow-hidden">
            <div className="p-6 border-b border-white/10">
              <h3 className="text-lg font-semibold">Device Registry</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-white/5 text-xs uppercase tracking-wider text-gray-400 select-none">
                    <th className="p-4 font-medium cursor-pointer hover:text-white transition-colors" onClick={() => handleSort('hostname')}>
                      Control {sortField === 'hostname' ? (sortDirection === 'asc' ? '↑' : '↓') : ''}
                    </th>
                    <th className="p-4 font-medium cursor-pointer hover:text-white transition-colors" onClick={() => handleSort('process')}>
                      Process {sortField === 'process' ? (sortDirection === 'asc' ? '↑' : '↓') : ''}
                    </th>
                    <th className="p-4 font-medium cursor-pointer hover:text-white transition-colors" onClick={() => handleSort('model')}>
                      Model {sortField === 'model' ? (sortDirection === 'asc' ? '↑' : '↓') : ''}
                    </th>
                    <th className="p-4 font-medium cursor-pointer hover:text-white transition-colors" onClick={() => handleSort('ip_address')}>
                      IP Address {sortField === 'ip_address' ? (sortDirection === 'asc' ? '↑' : '↓') : ''}
                    </th>
                    <th className="p-4 font-medium cursor-pointer hover:text-white transition-colors" onClick={() => handleSort('mac_address')}>
                      MAC Address {sortField === 'mac_address' ? (sortDirection === 'asc' ? '↑' : '↓') : ''}
                    </th>
                    <th className="p-4 font-medium cursor-pointer hover:text-white transition-colors" onClick={() => handleSort('status')}>
                      Status {sortField === 'status' ? (sortDirection === 'asc' ? '↑' : '↓') : ''}
                    </th>
                    <th className="p-4 font-medium cursor-pointer hover:text-white transition-colors" onClick={() => handleSort('last_seen')}>
                      Last Seen {sortField === 'last_seen' ? (sortDirection === 'asc' ? '↑' : '↓') : ''}
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {loading && devices.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="p-8 text-center text-gray-400">Loading radar data...</td>
                    </tr>
                  ) : paginatedDevices.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="p-8 text-center text-gray-400">No devices match your search or filter.</td>
                    </tr>
                  ) : paginatedDevices.map((device, i) => (
                    <tr key={device.device_id || i} className="hover:bg-white/5 transition-colors group">
                      <td className="p-4">
                        <div className="flex items-center gap-3">
                          <div className="p-2 bg-white/5 rounded-lg group-hover:bg-[#00f0ff]/20 transition-colors">
                            {device.is_reserved ? (
                              <Server className="w-5 h-5 text-gray-300 group-hover:text-[#00f0ff]" />
                            ) : (
                              <MonitorSmartphone className="w-5 h-5 text-gray-300 group-hover:text-[#00f0ff]" />
                            )}
                          </div>
                          <div>
                            <p className="font-medium text-sm text-gray-200">
                              {device.hostname || 'Unknown Host'}
                            </p>
                            {device.has_recent_ip_change && (
                              <span className="text-[10px] bg-orange-500/20 text-orange-400 px-1.5 py-0.5 rounded border border-orange-500/30 flex items-center gap-1 w-max mt-1">
                                <Activity className="w-2.5 h-2.5" /> IP Recently Changed
                              </span>
                            )}
                            {device.remark && !device.has_recent_ip_change && (
                              <span className="text-[10px] bg-purple-500/20 text-purple-400 px-1.5 py-0.5 rounded border border-purple-500/30 flex items-center gap-1 w-max mt-1">
                                <Activity className="w-2.5 h-2.5" /> {device.remark}
                              </span>
                            )}
                          </div>
                        </div>
                      </td>
                      <td className="p-4">
                        <span className="text-sm text-gray-300">
                          {device.process || '--'}
                        </span>
                      </td>
                      <td className="p-4">
                        <span className="text-sm text-gray-300">
                          {device.model || '--'}
                        </span>
                      </td>
                      <td className="p-4">
                        <span className="font-mono text-sm text-[#00f0ff] bg-[#00f0ff]/10 px-2 py-1 rounded">
                          {device.ip_address}
                        </span>
                      </td>
                      <td className="p-4">
                        <span className="font-mono text-sm text-gray-400">
                          {device.mac_address}
                        </span>
                      </td>
                      <td className="p-4">
                        {device.status === 'online' ? (
                          <span className="text-xs font-medium bg-[#00ff66]/10 text-[#00ff66] px-2 py-1 rounded-full">
                            Online
                          </span>
                        ) : (
                          <span className="text-xs font-medium bg-gray-500/20 text-gray-400 px-2 py-1 rounded-full">
                            Offline
                          </span>
                        )}
                      </td>
                      <td className="p-4 text-sm text-gray-400">
                        {device.last_seen}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {/* Pagination Controls */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between p-4 border-t border-white/10 text-sm bg-white/5">
                <span className="text-gray-400">
                  Showing {((currentPage - 1) * itemsPerPage) + 1} to {Math.min(currentPage * itemsPerPage, filteredAndSortedDevices.length)} of {filteredAndSortedDevices.length}
                </span>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                    disabled={currentPage === 1}
                    className="px-3 py-1 rounded bg-white/5 hover:bg-white/10 border border-white/10 disabled:opacity-50 transition-colors cursor-pointer"
                  >
                    Prev
                  </button>
                  <span className="px-3 text-gray-300">Page {currentPage} of {totalPages}</span>
                  <button
                    onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                    disabled={currentPage === totalPages}
                    className="px-3 py-1 rounded bg-white/5 hover:bg-white/10 border border-white/10 disabled:opacity-50 transition-colors cursor-pointer"
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
