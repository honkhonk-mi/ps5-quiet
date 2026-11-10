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
      if (mounted.current) setStatus({ supported: false, ready: false, reason: "Нет связи с плагином. Откройте его заново." });
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
    setBusy(true); setError(false); setMessage("Переприменяю частоту GPU…");
    try {
      const result = await quietGPU();
      const body = result.ok ? "Сброс выполнен. Прежние настройки GPU возвращены."
        : result.error ?? "Не удалось выполнить сброс.";
      if (mounted.current) { setMessage(body); setError(!result.ok); }
      toaster.toast({ title: "PS5 Quiet", body });
    } catch {
      if (mounted.current) { setError(true); setMessage("Связь прервалась. Откройте плагин и проверьте результат."); }
    } finally {
      if (mounted.current) { setBusy(false); await refresh(); }
    }
  };
  const label = busy ? "Сбрасываю…" : status?.cooldown_seconds
    ? `Повтор через ${status.cooldown_seconds} с` : "Утихомирить фаны";
  return <PanelSection>
    <PanelSectionRow>
      <div style={{ display: "flex", gap: 12, marginBottom: 12 }}>
        <div style={{ flex: 1, background: "rgba(255,255,255,0.06)", borderRadius: 8, padding: 12 }}>
          <div style={{ fontSize: 12, opacity: 0.65 }}>Температура</div>
          <div style={{ fontSize: 24, marginTop: 4 }}>{status?.temperature_c != null ? `${status.temperature_c.toFixed(1)} °C` : "—"}</div>
        </div>
        <div style={{ flex: 1, background: "rgba(255,255,255,0.06)", borderRadius: 8, padding: 12 }}>
          <div style={{ fontSize: 12, opacity: 0.65 }}>Вентилятор</div>
          <div style={{ fontSize: 24, marginTop: 4 }}>{status?.fan_percent != null ? `${status.fan_percent}%` : "—"}</div>
        </div>
      </div>
    </PanelSectionRow>
    <PanelSectionRow><ButtonItem layout="below" disabled={busy || !status?.ready} onClick={reset}>{label}</ButtonItem></PanelSectionRow>
    <PanelSectionRow><div style={{ fontSize: 13, lineHeight: 1.5, marginTop: 10, opacity: 0.8 }}>
      Повторяет сброс GPU, который раньше убирал лишний нагрев. Профиль охлаждения сохраняется.
    </div></PanelSectionRow>
    {status?.reason && !busy && <PanelSectionRow><div role="status" style={{ fontSize: 13, lineHeight: 1.5, marginTop: 10 }}>{status.reason}</div></PanelSectionRow>}
    {message && <PanelSectionRow><div role="status" style={{ fontSize: 13, lineHeight: 1.5, marginTop: 10, color: error ? "#ffb4ad" : "#b2dfc6" }}>{message}</div></PanelSectionRow>}
    <PanelSectionRow><div style={{ fontSize: 12, opacity: 0.55, lineHeight: 1.5, marginTop: 12 }}>
      Используйте в меню Steam при закрытой игре. Вентилятор снизит обороты постепенно, если причиной был лишний нагрев GPU.
    </div></PanelSectionRow>
  </PanelSection>;
}
export default definePlugin(() => ({
  name: "PS5 Quiet", titleView: <div className={staticClasses.Title}>PS5 Quiet</div>,
  content: <Content />, icon: <FaFan />, onDismount() {},
}));
