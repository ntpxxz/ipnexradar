"use client";

import { useState } from "react";
import { ArrowLeft, Search, RefreshCw, Network } from "lucide-react";
import Link from "next/link";

export default function UnusedIps() {
    const [subnet, setSubnet] = useState("192.168.1.0/24");
    const [unusedIps, setUnusedIps] = useState<string[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [totalUnused, setTotalUnused] = useState(0);

    const fetchUnusedIps = async () => {
        if (!subnet) return;
        setLoading(true);
        setError(null);
        try {
            const res = await fetch(`http://127.0.0.1:8000/api/network/unused?subnet=${encodeURIComponent(subnet)}`);
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || "Failed to fetch unused IPs");

            setUnusedIps(data.unused_ips || []);
            setTotalUnused(data.total_unused || 0);
        } catch (err: any) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen p-6 md:p-12 relative overflow-hidden flex flex-col">
            <div className="absolute top-[-10%] right-[-10%] w-96 h-96 bg-blue-500/10 rounded-full blur-[100px]" />

            <div className="max-w-4xl mx-auto w-full relative z-10 flex-1 flex flex-col">
                <header className="flex items-center gap-4 mb-8">
                    <Link href="/">
                        <button className="p-2 bg-white/5 hover:bg-white/10 rounded-lg transition-colors border border-white/10">
                            <ArrowLeft className="w-5 h-5 text-gray-300" />
                        </button>
                    </Link>
                    <div>
                        <h1 className="text-3xl font-extrabold tracking-tight">Unused IPs</h1>
                        <p className="text-gray-400 text-sm">Find available IP addresses in your subnet</p>
                    </div>
                </header>

                <div className="glass-panel p-6 rounded-2xl mb-8 border border-white/10 flex flex-col md:flex-row gap-4">
                    <div className="flex-1 relative">
                        <Network className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
                        <input
                            type="text"
                            value={subnet}
                            onChange={(e) => setSubnet(e.target.value)}
                            placeholder="e.g. 192.168.1.0/24"
                            className="w-full bg-white/5 border border-white/10 rounded-xl pl-10 pr-4 py-3 text-white outline-none focus:border-[#00f0ff] transition-colors"
                        />
                    </div>
                    <button
                        onClick={fetchUnusedIps}
                        disabled={loading}
                        className={`px-6 py-3 bg-[#00f0ff] text-black font-semibold rounded-xl hover:bg-[#00c0cc] transition-all flex items-center justify-center gap-2 ${loading ? 'opacity-70' : ''}`}
                    >
                        {loading ? <RefreshCw className="w-5 h-5 animate-spin" /> : <Search className="w-5 h-5" />}
                        Check Availability
                    </button>
                </div>

                {error && (
                    <div className="glass-panel p-4 rounded-xl border border-[#ff3366] text-[#ff3366] mb-8 bg-[#ff3366]/5">
                        Error: {error}
                    </div>
                )}

                <div className="glass-panel p-6 rounded-2xl flex-1 border border-white/10 overflow-hidden flex flex-col">
                    <div className="flex items-center justify-between mb-6 pb-4 border-b border-white/10">
                        <h2 className="text-xl font-semibold">Available IPs</h2>
                        {totalUnused > 0 && (
                            <span className="bg-[#00ff66]/10 text-[#00ff66] px-3 py-1 rounded-full text-sm font-medium">
                                {totalUnused} IPs Unused
                            </span>
                        )}
                    </div>

                    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3 overflow-y-auto pr-2 custom-scrollbar">
                        {unusedIps.length > 0 ? (
                            unusedIps.map((ip) => (
                                <div key={ip} className="bg-white/5 border border-white/10 p-3 rounded-lg text-center font-mono text-sm hover:bg-white/10 transition-colors">
                                    {ip}
                                </div>
                            ))
                        ) : (
                            <div className="col-span-full py-12 text-center text-gray-500">
                                {loading ? "Scanning for available IPs..." : "Enter a subnet and check availability to see unused IPs."}
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
