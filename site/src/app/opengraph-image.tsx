import { ImageResponse } from "next/og";

export const alt = "Payment Observatory — observe every link around 80,000 payment events";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OpenGraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          position: "relative",
          overflow: "hidden",
          background: "#141C22",
          color: "#F1EEE8",
          padding: "68px 76px",
          fontFamily: "Georgia, serif",
        }}
      >
        <div style={{ display: "flex", flexDirection: "column", justifyContent: "space-between", width: 720 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 16, fontFamily: "Arial, sans-serif", fontSize: 22, letterSpacing: "0.08em", textTransform: "uppercase" }}>
            <span style={{ width: 46, height: 2, background: "#E4876D" }} />
            Payment Observatory
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 22 }}>
            <div style={{ fontSize: 72, lineHeight: 0.98, letterSpacing: "-0.035em" }}>Observe every link around 80,000 payment events</div>
            <div style={{ fontFamily: "Arial, sans-serif", fontSize: 24, lineHeight: 1.4, color: "#A3B2B8" }}>
              Transaction activity, settlement, review, retention, and relational design in one deployable analytical system.
            </div>
          </div>
          <div style={{ display: "flex", gap: 28, fontFamily: "monospace", fontSize: 17, color: "#E4876D" }}>
            <span>6 LINKED TABLES</span>
            <span>2022—2024</span>
            <span>SQL + PYTHON</span>
          </div>
        </div>

        <div style={{ position: "absolute", right: 70, top: 72, width: 340, height: 470, display: "flex", alignItems: "center", justifyContent: "center" }}>
          <div style={{ position: "absolute", width: 330, height: 330, border: "2px solid #E4876D", borderRadius: 999, transform: "rotate(-18deg)" }} />
          <div style={{ position: "absolute", width: 245, height: 390, border: "2px solid #A7D5D8", borderRadius: 999, transform: "rotate(32deg)" }} />
          <div style={{ position: "absolute", width: 205, height: 205, border: "1px solid #74CFAF", borderRadius: 999 }} />
          <div style={{ width: 134, height: 134, borderRadius: 999, display: "flex", alignItems: "center", justifyContent: "center", background: "#202E37", border: "4px solid #E4876D", color: "#F1EEE8", fontFamily: "Arial, sans-serif", fontSize: 22, textAlign: "center" }}>
            payment<br />event
          </div>
          <div style={{ position: "absolute", right: 12, top: 90, width: 20, height: 20, borderRadius: 999, background: "#A7D5D8" }} />
          <div style={{ position: "absolute", right: 5, bottom: 104, width: 20, height: 20, borderRadius: 999, background: "#74CFAF" }} />
          <div style={{ position: "absolute", left: 12, bottom: 80, width: 20, height: 20, borderRadius: 999, background: "#E8849A" }} />
        </div>
      </div>
    ),
    size,
  );
}
