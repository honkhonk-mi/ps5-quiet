import { ButtonItem, PanelSection, PanelSectionRow, staticClasses } from "@decky/ui";
import { callable, definePlugin, toaster } from "@decky/api";
import { useCallback, useEffect, useRef, useState } from "react";
import { FaFan } from "react-icons/fa";

interface Status {
  supported: boolean; ready: boolean; reason?: string | null;
  temperature_c?: number | null; fan_percent?: number | null;
  cooldown_seconds?: number;
}
const readStatus = callable<[], Status>("get_status");
const quietGPU = callable<[], { ok: boolean; error?: string }>("quiet_gpu");

function Content() {
  const [status, setStatus] = useState<Status>();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState(false);
  const mounted = useRef(false);
  const refresh = useCallback(async () => {
    try {
      const value = await readStatus();
      if (mounted.current) setStatus(value);
    } catch {
      if (mounted.current) setStatus({ supported: false, ready: false, reason: "Cannot connect to the plugin. Reopen it and try again." });
    }
  }, []);
  useEffect(() => {
    mounted.current = true;
    void refresh();
    const timer = setInterval(() => void refresh(), 3000);
    return () => { mounted.current = false; clearInterval(timer); };
  }, [refresh]);
  const reset = async () => {
    if (busy) return;
    setBusy(true); setError(false); setMessage("Reapplying the GPU minimum…");
    try {
      const result = await quietGPU();
      const body = result.ok ? "Reset complete. The previous GPU minimum has been restored."
        : result.error ?? "Could not complete the reset.";
      if (mounted.current) { setMessage(body); setError(!result.ok); }
      toaster.toast({ title: "PS5 Quiet", body });
    } catch {
      if (mounted.current) { setError(true); setMessage("Connection lost. Reopen the plugin and check the result."); }
    } finally {
      if (mounted.current) { setBusy(false); await refresh(); }
    }
  };
  const label = busy ? "Resetting…" : status?.cooldown_seconds
    ? `Try again in ${status.cooldown_seconds}s` : "Quiet the fans";
  return <PanelSection>
    <PanelSectionRow>
      <div style={{ display: "flex", gap: 12, marginBottom: 12 }}>
        <div style={{ flex: 1, background: "rgba(255,255,255,0.06)", borderRadius: 8, padding: 12 }}>
          <div style={{ fontSize: 12, opacity: 0.65 }}>Temperature</div>
          <div style={{ fontSize: 24, marginTop: 4 }}>{status?.temperature_c != null ? `${status.temperature_c.toFixed(1)} °C` : "—"}</div>
        </div>
        <div style={{ flex: 1, background: "rgba(255,255,255,0.06)", borderRadius: 8, padding: 12 }}>
          <div style={{ fontSize: 12, opacity: 0.65 }}>Fan</div>
          <div style={{ fontSize: 24, marginTop: 4 }}>{status?.fan_percent != null ? `${status.fan_percent}%` : "—"}</div>
        </div>
      </div>
    </PanelSectionRow>
    <PanelSectionRow><ButtonItem layout="below" disabled={busy || !status?.ready} onClick={reset}>{label}</ButtonItem></PanelSectionRow>
    <PanelSectionRow><div style={{ fontSize: 13, lineHeight: 1.5, marginTop: 10, opacity: 0.8 }}>
      Reapplies the GPU minimum to work around hot idle. Your cooling profile is preserved.
    </div></PanelSectionRow>
    {status?.reason && !busy && <PanelSectionRow><div role="status" style={{ fontSize: 13, lineHeight: 1.5, marginTop: 10 }}>{status.reason}</div></PanelSectionRow>}
    {message && <PanelSectionRow><div role="status" style={{ fontSize: 13, lineHeight: 1.5, marginTop: 10, color: error ? "#ffb4ad" : "#b2dfc6" }}>{message}</div></PanelSectionRow>}
    <PanelSectionRow><div style={{ fontSize: 12, opacity: 0.55, lineHeight: 1.5, marginTop: 12 }}>
      Use from the Steam menu with the game closed. Fan speed will decrease gradually if hot idle was the cause.
    </div></PanelSectionRow>
  </PanelSection>;
}
export default definePlugin(() => ({
  name: "PS5 Quiet", titleView: <div className={staticClasses.Title}>PS5 Quiet</div>,
  content: <Content />, icon: <FaFan />, onDismount() {},
}));
