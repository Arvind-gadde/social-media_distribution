import { useState } from "react";
import { useAuthStore } from "../store/authStore";
import { PLATFORMS } from "../types";
import toast from "react-hot-toast";
import api from "../api/client";
import clsx from "clsx";

export default function SettingsPage() {
  const user = useAuthStore((s) => s.user);
  const [pushEnabled, setPushEnabled] = useState(false);

  const handleConnect = (platformId: string) => {
    api.get(`/platforms/${platformId}/oauth-url`).then(r => {
      window.open(r.data.url, "_blank", "width=600,height=700");
    }).catch(() => toast.error(`Could not get OAuth URL for ${platformId}`));
  };

  const handleDisconnect = (platformId: string) => {
    api.delete(`/platforms/${platformId}/disconnect`).then(() => {
      toast.success(`Disconnected from ${platformId}`);
    }).catch(() => toast.error("Disconnect failed"));
  };

  const handlePushToggle = async () => {
    if (!pushEnabled) {
      if (!("Notification" in window)) return toast.error("Push not supported in this browser");
      const perm = await Notification.requestPermission();
      if (perm !== "granted") return toast.error("Permission denied");
      setPushEnabled(true);
      toast.success("🔔 Push notifications enabled!");
    } else {
      setPushEnabled(false);
      toast.success("Notifications disabled");
    }
  };

  return (
    <div className="p-6 max-w-2xl space-y-6 animate-fade-in">
      <h1 className="text-2xl font-bold text-slate-800">Settings</h1>

      {/* Profile */}
      <div className="card p-5 flex items-center gap-4">
        <img src={user?.avatar_url || `https://ui-avatars.com/api/?name=${user?.name}`}
          className="w-16 h-16 rounded-2xl object-cover" alt="" />
        <div>
          <p className="font-semibold text-slate-800">{user?.name}</p>
          <p className="text-sm text-slate-500">{user?.email}</p>
        </div>
      </div>

      {/* Connected Platforms */}
      <div className="card">
        <div className="px-5 py-4 border-b border-slate-100">
          <h2 className="font-semibold text-slate-700">Connected Platforms</h2>
          <p className="text-xs text-slate-400 mt-0.5">Connect your accounts to enable automatic publishing</p>
        </div>
        <div className="divide-y divide-slate-50">
          {PLATFORMS.map((p) => {
            const connected = user?.connected_platforms?.includes(p.id);
            return (
              <div key={p.id} className="px-5 py-3.5 flex items-center gap-3">
                <span className="text-2xl">{p.icon}</span>
                <div className="flex-1">
                  <p className="font-medium text-slate-700 text-sm">{p.name}</p>
                  <p className={clsx("text-xs", connected ? "text-emerald-500" : "text-slate-400")}>
                    {connected ? "Connected" : "Not connected"}
                  </p>
                </div>
                {connected ? (
                  <button onClick={() => handleDisconnect(p.id)}
                    className="text-xs text-red-400 hover:text-red-600 border border-red-200 hover:border-red-400 px-3 py-1.5 rounded-lg transition-colors">
                    Disconnect
                  </button>
                ) : (
                  <button onClick={() => handleConnect(p.id)}
                    className="text-xs btn-primary py-1.5 px-3">
                    Connect
                  </button>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Push Notifications */}
      <div className="card p-5 flex items-center justify-between">
        <div>
          <p className="font-medium text-slate-700">🔔 Push Notifications</p>
          <p className="text-sm text-slate-400">Get notified when posts succeed or fail</p>
        </div>
        <button onClick={handlePushToggle}
          className={clsx("relative inline-flex h-6 w-11 items-center rounded-full transition-colors duration-200",
            pushEnabled ? "bg-brand-600" : "bg-slate-200")}>
          <span className={clsx("inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform duration-200",
            pushEnabled ? "translate-x-6" : "translate-x-1")} />
        </button>
      </div>
    </div>
  );
}