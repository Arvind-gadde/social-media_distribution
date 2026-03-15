import { useState } from "react";
import clsx from "clsx";
import toast from "react-hot-toast";
import api from "../api/client";
import { useAuthStore } from "../store/authStore";
import { PLATFORMS } from "../types";

export default function SettingsPage() {
  const user = useAuthStore((state) => state.user);
  const [pushEnabled, setPushEnabled] = useState(false);

  const handleConnect = (platformId: string) => {
    api
      .get(`/platforms/${platformId}/oauth-url`)
      .then((response) => {
        window.open(response.data.url, "_blank", "width=600,height=700");
      })
      .catch(() => toast.error(`Could not get OAuth URL for ${platformId}`));
  };

  const handleDisconnect = (platformId: string) => {
    api
      .delete(`/platforms/${platformId}/disconnect`)
      .then(() => {
        toast.success(`Disconnected from ${platformId}`);
      })
      .catch(() => toast.error("Disconnect failed"));
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

  return (
    <div className="max-w-2xl space-y-6 p-6 animate-fade-in">
      <h1 className="text-2xl font-bold text-white">Settings</h1>

      <div className="card flex items-center gap-4 p-5">
        <img
          src={user?.avatar_url || `https://ui-avatars.com/api/?name=${user?.name}`}
          className="h-16 w-16 rounded-2xl object-cover"
          alt=""
        />
        <div>
          <p className="font-semibold text-white">{user?.name}</p>
          <p className="text-sm text-white/[0.55]">{user?.email}</p>
        </div>
      </div>

      <div className="card">
        <div className="border-b border-white/10 px-5 py-4">
          <h2 className="font-semibold text-white">Connected Platforms</h2>
          <p className="mt-0.5 text-xs text-white/[0.45]">
            Connect your accounts to enable automatic publishing
          </p>
        </div>
        <div className="divide-y divide-white/5">
          {PLATFORMS.map((platform) => {
            const connected = user?.connected_platforms?.includes(platform.id);
            return (
              <div key={platform.id} className="flex items-center gap-3 px-5 py-3.5">
                <span className="text-2xl">{platform.icon}</span>
                <div className="flex-1">
                  <p className="text-sm font-medium text-white">{platform.name}</p>
                  <p className={clsx("text-xs", connected ? "text-emerald-300" : "text-white/[0.45]")}>
                    {connected ? "Connected" : "Not connected"}
                  </p>
                </div>
                {connected ? (
                  <button
                    type="button"
                    onClick={() => handleDisconnect(platform.id)}
                    className="rounded-lg border border-red-400/25 px-3 py-1.5 text-xs text-red-200 transition-colors hover:border-red-400/45 hover:text-red-100"
                  >
                    Disconnect
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={() => handleConnect(platform.id)}
                    className="btn-primary px-3 py-1.5 text-xs"
                  >
                    Connect
                  </button>
                )}
              </div>
            );
          })}
        </div>
      </div>

      <div className="card flex items-center justify-between p-5">
        <div>
          <p className="font-medium text-white">Push Notifications</p>
          <p className="text-sm text-white/[0.45]">Get notified when posts succeed or fail</p>
        </div>
        <button
          type="button"
          onClick={handlePushToggle}
          className={clsx(
            "relative inline-flex h-6 w-11 items-center rounded-full transition-colors duration-200",
            pushEnabled ? "bg-brand-600" : "bg-white/20"
          )}
        >
          <span
            className={clsx(
              "inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform duration-200",
              pushEnabled ? "translate-x-6" : "translate-x-1"
            )}
          />
        </button>
      </div>
    </div>
  );
}
