import { ImageResponse } from "next/og";

export const size = { width: 64, height: 64 };
export const contentType = "image/png";

export default function Icon() {
  return new ImageResponse(
    (
      <div style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", borderRadius: 14, background: "#141C22", border: "3px solid #E4876D" }}>
        <div style={{ width: 32, height: 32, display: "flex", alignItems: "center", justifyContent: "center", borderRadius: 999, border: "2px solid #A7D5D8", color: "#F1EEE8", fontFamily: "Arial", fontSize: 18, fontWeight: 700 }}>P</div>
      </div>
    ),
    size,
  );
}
