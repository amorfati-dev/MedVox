// Zeichnet einen QR-Code (eigener Encoder in qr/encode.ts) auf ein Canvas.
import { useEffect, useRef } from "react";
import { encodeQr } from "../qr/encode";

type Props = { text: string; size?: number; label?: string };

export function QrCanvas({ text, size = 220, label }: Props) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const matrix = encodeQr(text);
    const quiet = 4;
    const modules = matrix.length + quiet * 2;
    const scale = Math.floor(size / modules) || 1;
    const px = scale * modules;
    canvas.width = px;
    canvas.height = px;
    ctx.fillStyle = "#fff";
    ctx.fillRect(0, 0, px, px);
    ctx.fillStyle = "#000";
    matrix.forEach((row, y) =>
      row.forEach((dark, x) => {
        if (dark) ctx.fillRect((x + quiet) * scale, (y + quiet) * scale, scale, scale);
      }),
    );
  }, [text, size]);

  return <canvas ref={ref} className="qr" role="img" aria-label={label ?? `QR-Code: ${text}`} />;
}
