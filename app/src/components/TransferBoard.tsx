// Tafel nach „An Rezeption“: Kurzcode groß (Festbreite, gesperrt) und QR-Code für das Handy.
import type { TransferCreated } from "../api";
import { QrCanvas } from "./QrCanvas";

function formatTime(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "" : d.toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" });
}

type Props = { result: TransferCreated };

export function TransferBoard({ result }: Props) {
  // QR enthält die Rezeptions-URL mit Code, damit auch ein Handy-Scan direkt landet.
  const url = `${window.location.origin}/transfer?code=${result.code}`;
  return (
    <section className="board" aria-label="Kurzcode für die Rezeption">
      <div className="board-text">
        <h2>An Rezeption gesendet</h2>
        <p className="transfer-code" aria-label="Kurzcode">
          {result.code}
        </p>
        <p className="muted">
          An der Rezeption unter <strong>/transfer</strong> eingeben – gültig bis {formatTime(result.expires_at)} Uhr.
        </p>
      </div>
      <QrCanvas text={url} size={180} label={`QR-Code für Kurzcode ${result.code}`} />
    </section>
  );
}
