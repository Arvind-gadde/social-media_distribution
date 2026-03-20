import { useState } from "react";
import clsx from "clsx";
import toast from "react-hot-toast";
import api from "../api/client";
import { useAuthStore } from "../store/authStore";
import { PLATFORMS } from "../types";
import { Bell, User, Link2, Shield, AlertCircle } from "lucide-react";

export default function SettingsPage() {
  const user = useAuthStore((state) => state.user);
  const [pushEnabled, setPushEnabled] = useState(false);
  const [connectingId, setConnectingId] = useState<string | null>(null);
  const [disconnectingId, setDisconnectingId] = useState<string | null>(null);

  const handleConnect = async (platformId: string) => {
    setConnectingId(platformId);
    try {
      const res = await api.get(`/platforms/${platformId}/oauth-url`);
      window.open(res.data.url, "_blank", "width=600,height=700");
    } catch (err: any) {
      // Show the backend's human-readable message (e.g. "Set LINKEDIN_CLIENT_ID…")
      const detail =
        err?.response?.data?.detail ||
        `Could not get OAuth URL for ${platformId}`;
      toast.error(detail, { duration: 6000 });
    } finally {
      setConnectingId(null);
    }
  };

  const handleDisconnect = async (platformId: string) => {
    setDisconnectingId(platformId);
    try {
      await api.delete(`/platforms/${platformId}/disconnect`);
      toast.success(`Disconnected from ${platformId}`);
    } catch {
      toast.error("Disconnect failed");
    } finally {
      setDisconnectingId(null);
    }
  };

  const handlePushToggle = async () => {
    if (!pushEnabled) {
      if (!("Notification" in window)) {
        toast.error("Push not supported in this browser");
        return;
      }
      const permission = await Notification.requestPermission();
      if (permission !== "granted") {
        toast.error("Permission denied");
        return;
      }
      setPushEnabled(true);
      toast.success("Push notifications enabled");
      return;
    }
    setPushEnabled(false);
    toast.success("Notifications disabled");
  };

  const connectedCount = PLATFORMS.filter((p) =>
    user?.connected_platforms?.includes(p.id)
  ).length;

  return (
    <div className="mx-auto max-w-2xl space-y-5 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col gap-1 pt-1">
        <h1 className="text-2xl font-bold text-white tracking-tight">Settings</h1>
        <p className="text-sm text-white/50">Manage your account and connected channels</p>
      </div>

      {/* Profile card */}
      <div className="card p-5">
        <div className="flex items-center gap-2 mb-4">
          <User size={14} className="text-white/40" />
          <h2 className="text-xs font-semibold text-white/45 uppercase tracking-wide">Profile</h2>
        </div>
        <div className="flex items-center gap-4">
          <div className="relative shrink-0">
            <img
              src={
                user?.avatar_url ||
                `https://ui-avatars.com/api/?name=${encodeURIComponent(user?.name ?? "U")}&background=6839d8&color=fff&bold=true`
              }
              className="h-16 w-16 rounded-2xl object-cover border border-white/15"
              alt={user?.name}
            />
            <span className="absolute -bottom-1 -right-1 h-3.5 w-3.5 rounded-full bg-emerald-400 ring-2 ring-[#090b11]" />
          </div>
          <div className="min-w-0">
            <p className="text-base font-bold text-white">{user?.name}</p>
            <p className="text-sm text-white/45 mt-0.5">{user?.email}</p>
            <span className="mt-2 inline-flex items-center gap-1.5 rounded-full border border-emerald-500/25 bg-emerald-500/10 px-2.5 py-0.5 text-[11px] font-semibold text-emerald-300">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
              Active
            </span>
          </div>
        </div>
      </div>

      {/* Connected Platforms */}
      <div className="card overflow-hidden p-0">
        <div className="flex items-center justify-between px-5 py-4 border-b border-white/[0.07]">
          <div className="flex items-center gap-3">
            <Link2 size={14} className="text-white/40" />
            <div>
              <h2 className="text-sm font-semibold text-white">Connected Platforms</h2>
              <p className="text-xs text-white/40 mt-0.5">
                Connect accounts to enable auto-publishing
              </p>
            </div>
          </div>
          <span className="badge text-[11px] border border-brand-400/25 bg-brand-500/10 text-brand-200">
            {connectedCount}/{PLATFORMS.length}
          </span>
        </div>

        {/* Info banner — guides user when OAuth creds are missing */}
        <div className="mx-5 mt-4 mb-1 flex items-start gap-2 rounded-xl border border-amber-400/20 bg-amber-500/[0.07] px-3.5 py-3">
          <AlertCircle size={14} className="text-amber-400 mt-0.5 shrink-0" />
          <p className="text-xs text-amber-200/80 leading-relaxed">
            If Connect opens a blank or error page, the platform credentials are not yet set in{" "}
            <code className="bg-white/10 px-1 py-0.5 rounded text-amber-100">backend/.env</code>.
            Add the keys and <strong>restart the backend</strong>.
          </p>
        </div>

        <div className="divide-y divide-white/[0.05] mt-2">
          {PLATFORMS.map((platform) => {
            const connected = user?.connected_platforms?.includes(platform.id);
            const isConnecting = connectingId === platform.id;
            const isDisconnecting = disconnectingId === platform.id;

            return (
              <div
                key={platform.id}
                className="flex items-center gap-3.5 px-5 py-3.5 transition-colors hover:bg-white/[0.025]"
              >
                <span className="text-2xl shrink-0">{platform.icon}</span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-white">{platform.name}</p>
                  <p className={clsx("text-xs mt-0.5", connected ? "text-emerald-400" : "text-white/35")}>
                    {connected ? "✓ Connected" : "Not connected"}
                  </p>
                </div>
                {connected ? (
                  <button
                    type="button"
                    onClick={() => handleDisconnect(platform.id)}
                    disabled={isDisconnecting}
                    className="shrink-0 rounded-lg border border-red-400/20 bg-red-500/[0.08] px-3 py-1.5 text-xs font-semibold text-red-300 transition-all hover:border-red-400/40 hover:bg-red-500/15 hover:text-red-200 disabled:opacity-50"
                  >
                    {isDisconnecting ? "…" : "Disconnect"}
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={() => handleConnect(platform.id)}
                    disabled={isConnecting}
                    className="shrink-0 btn-primary px-3 py-1.5 text-xs disabled:opacity-50"
                  >
                    {isConnecting ? "…" : "Connect"}
                  </button>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Push Notifications */}
      <div className="card p-5">
        <div className="flex items-center gap-2 mb-4">
          <Bell size={14} className="text-white/40" />
          <h2 className="text-xs font-semibold text-white/45 uppercase tracking-wide">Notifications</h2>
        </div>
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-sm font-semibold text-white">Push Notifications</p>
            <p className="text-xs text-white/40 mt-0.5">Get notified when posts succeed or fail</p>
          </div>
          <button
            type="button"
            onClick={handlePushToggle}
            role="switch"
            aria-checked={pushEnabled}
            className={clsx(
              "relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors duration-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-400/50",
              pushEnabled ? "bg-brand-600" : "bg-white/20"
            )}
          >
            <span
              className={clsx(
                "inline-block h-4 w-4 transform rounded-full bg-white shadow-sm transition-transform duration-200",
                pushEnabled ? "translate-x-6" : "translate-x-1"
              )}
            />
          </button>
        </div>
      </div>

      {/* Security */}
      <div className="card p-5">
        <div className="flex items-center gap-2 mb-4">
          <Shield size={14} className="text-white/40" />
          <h2 className="text-xs font-semibold text-white/45 uppercase tracking-wide">Security</h2>
        </div>
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-sm font-semibold text-white">Account Security</p>
            <p className="text-xs text-white/40 mt-0.5">Your account is protected with secure authentication</p>
          </div>
          <span className="badge-green text-[11px]">Protected</span>
        </div>
      </div>
    </div>
  );
}
