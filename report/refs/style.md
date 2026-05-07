# NullPointer Studio — Report CSS & Style Reference

## Color Palette

```css
--bg:        #13112e;   /* page background */
--bg-card:   #1a1840;   /* finding cards, stat boxes */
--bg-raised: #2d2b55;   /* table headers, elevated elements */
--bg-deep:   #0d0b20;   /* code blocks */
--text:      #e8e6f0;   /* body text */
--muted:     #9b98b8;   /* secondary text, labels */
--dim:       #6b6890;   /* footer text, separators */
--green:     #5bf29b;   /* LOW severity, accent, subtitle */
--purple:    #7b78ff;   /* INFO severity, accent, borders */
--border:    rgba(123,120,255,0.28);
```

## Severity Colors

| Severity | Text color | Background | Border |
|---|---|---|---|
| CRITICAL | `#ff4d6d` | `rgba(255,77,109,0.12)` | `#ff4d6d` |
| HIGH | `#ff8c42` | `rgba(255,140,66,0.12)` | `#ff8c42` |
| MEDIUM | `#ffd166` | `rgba(255,209,102,0.1)` | `#ffd166` |
| LOW | `#5bf29b` | `rgba(91,242,155,0.08)` | `#5bf29b` |
| INFO | `#7b78ff` | `rgba(123,120,255,0.08)` | `#7b78ff` |

## Typography

```css
/* Headers, badges, monospace labels */
font-family: 'Chakra Petch', monospace;

/* Body text, paragraphs */
font-family: 'Outfit', sans-serif;

/* Code blocks, metadata, footers */
font-family: 'IBM Plex Mono', monospace;
```

Google Fonts import URL:
```
https://fonts.googleapis.com/css2?family=Chakra+Petch:wght@400;600;700&family=Outfit:wght@300;400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap
```

## Full CSS String (embed verbatim as CSS_STR in generator)

```css
@import url('https://fonts.googleapis.com/css2?family=Chakra+Petch:wght@400;600;700&family=Outfit:wght@300;400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');

:root {
  --bg:        #13112e;
  --bg-card:   #1a1840;
  --bg-raised: #2d2b55;
  --bg-deep:   #0d0b20;
  --text:      #e8e6f0;
  --muted:     #9b98b8;
  --dim:       #6b6890;
  --green:     #5bf29b;
  --purple:    #7b78ff;
  --border:    rgba(123,120,255,0.28);
}

@page {
  size: A4;
  margin: 2.3cm 2.2cm 2cm 2.2cm;
  background: #13112e;
  @bottom-left {
    content: "{client} Penetration Test Report · {date}";
    font-family: 'IBM Plex Mono', monospace;
    font-size: 7pt;
    color: #6b6890;
  }
  @bottom-right {
    content: "NullPointer Studio · CONFIDENTIAL · Page " counter(page);
    font-family: 'IBM Plex Mono', monospace;
    font-size: 7pt;
    color: #6b6890;
  }
}

@page cover-page { margin: 0; @bottom-left { content: none; } @bottom-right { content: none; } }

html, body {
  background: #13112e;
  color: #e8e6f0;
  font-family: 'Outfit', sans-serif;
  font-size: 9.5pt;
  line-height: 1.65;
  margin: 0; padding: 0;
}

/* ── COVER PAGE ───────────────────────────────────── */
.cover {
  page: cover-page;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  min-height: 29.7cm; background: #13112e; text-align: center; position: relative;
}
.cover::before {
  content: "";
  position: absolute; top:0; left:0; right:0; height:6px;
  background: linear-gradient(90deg, #5bf29b, #7b78ff, #5bf29b);
}
.cover-logo { height: 180px; margin-bottom: 2.5cm; }
.cover-classification {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 8pt; letter-spacing: 0.2em; color: #ff4d6d;
  border: 1px solid #ff4d6d; padding: 4px 16px; margin-bottom: 1cm; display: inline-block;
}
.cover-title {
  font-family: 'Chakra Petch', monospace; font-size: 28pt; font-weight: 700;
  color: #fff; line-height: 1.15; margin-bottom: 0.4cm;
}
.cover-subtitle {
  font-family: 'Chakra Petch', monospace; font-size: 14pt; font-weight: 400;
  color: #5bf29b; margin-bottom: 1.5cm; letter-spacing: 0.05em;
}
.cover-divider {
  width: 80px; height: 2px;
  background: linear-gradient(90deg, transparent, #7b78ff, transparent);
  margin: 0 auto 1.5cm;
}
.cover-meta {
  width: 100%; max-width: 14cm;
  border-top: 1px solid rgba(123,120,255,0.3); padding-top: 0.8cm; margin-top: 1cm;
}
.cover-meta table { width: 100%; border-collapse: collapse; text-align: left; }
.cover-meta td { padding: 5px 12px; font-size: 9pt; }
.cover-meta td:first-child { color: #9b98b8; font-family: 'IBM Plex Mono', monospace; font-size: 8pt; width: 40%; }
.cover-footer {
  position: absolute; bottom: 1cm;
  font-family: 'IBM Plex Mono', monospace; font-size: 7pt; color: #6b6890;
}

/* ── STAT BOXES ───────────────────────────────────── */
.stat-row {
  display: flex; justify-content: space-around; gap: 12px;
  margin: 20px 0 24px; flex-wrap: wrap;
}
.stat-box {
  flex: 1; min-width: 70px; background: #0d0b20;
  border: 1px solid rgba(123,120,255,0.2); border-radius: 6px;
  padding: 14px 10px; text-align: center;
}
.stat-num { font-family: 'Chakra Petch', monospace; font-size: 20pt; font-weight: 700; display: block; line-height: 1.1; }
.stat-label { font-size: 7pt; color: #9b98b8; text-transform: uppercase; letter-spacing: 0.1em; display: block; margin-top: 4px; }

/* ── PAGE STRUCTURE ───────────────────────────────── */
h1 {
  font-family: 'Chakra Petch', monospace; font-size: 16pt; font-weight: 700;
  color: #fff; border-bottom: 1px solid rgba(123,120,255,0.3);
  padding-bottom: 6px; margin: 0 0 16px;
}
h2 { font-family: 'Chakra Petch', monospace; font-size: 11pt; color: #7b78ff; margin: 16px 0 8px; }
h3 { font-family: 'Chakra Petch', monospace; font-size: 10pt; color: #9b98b8; margin: 12px 0 6px; }
h4 { font-family: 'Chakra Petch', monospace; font-size: 8.5pt; color: #7b78ff;
     text-transform: uppercase; letter-spacing: 0.08em; margin: 14px 0 6px; }
p { margin: 0 0 8px; }
.section { margin-bottom: 24px; }
.page-break { page-break-before: always; }

/* ── TABLES ───────────────────────────────────────── */
.dashboard-table, .meta-table, .remediation-table {
  width: 100%; border-collapse: collapse; font-size: 8.5pt; margin: 10px 0;
}
.dashboard-table th, .meta-table th, .remediation-table th {
  background: #2d2b55; color: #9b98b8; font-family: 'IBM Plex Mono', monospace;
  font-size: 7.5pt; text-transform: uppercase; letter-spacing: 0.06em;
  padding: 7px 10px; text-align: left; border-bottom: 1px solid rgba(123,120,255,0.3);
}
.dashboard-table td, .meta-table td, .remediation-table td {
  padding: 6px 10px; border-bottom: 1px solid rgba(123,120,255,0.1); vertical-align: top;
}
.dashboard-table tr:hover td { background: rgba(123,120,255,0.05); }

/* ── FINDING CARDS ────────────────────────────────── */
.finding {
  background: #1a1840; border-radius: 6px;
  border-left-width: 4px; border-left-style: solid;
  margin-bottom: 20px; page-break-inside: avoid;
}
.finding-header {
  padding: 12px 16px 10px;
  border-bottom: 1px solid rgba(123,120,255,0.15);
}
.finding-title-row { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; flex-wrap: wrap; }
.finding-id { font-family: 'IBM Plex Mono', monospace; font-size: 8.5pt; color: #7b78ff; font-weight: 500; }
.finding-title { font-family: 'Chakra Petch', monospace; font-size: 10.5pt; font-weight: 600; color: #fff; }
.finding-body { padding: 12px 16px 14px; font-size: 8.5pt; line-height: 1.8; color: #9b98b8; }
.finding-meta { width: 100%; border-collapse: collapse; font-size: 8pt; margin-bottom: 14px; }
.finding-meta td {
  padding: 3px 8px; border-bottom: 1px solid rgba(123,120,255,0.08); vertical-align: top;
  text-transform: uppercase; letter-spacing: 0.06em; background: rgba(123,120,255,0.06); width: 18%;
}
.finding-meta td:nth-child(even) {
  color: #e8e6f0; font-family: 'Outfit', sans-serif; text-transform: none;
  letter-spacing: 0; width: 32%; background: transparent;
}

/* ── SEVERITY BADGE ───────────────────────────────── */
.badge {
  font-family: 'IBM Plex Mono', monospace; font-size: 7pt; font-weight: 500;
  padding: 2px 8px; border-radius: 3px; white-space: nowrap; letter-spacing: 0.08em;
}

/* ── CODE BLOCKS ──────────────────────────────────── */
.code-block {
  background: #0d0b20; border: 1px solid rgba(123,120,255,0.2); border-radius: 4px;
  padding: 10px 12px; font-family: 'IBM Plex Mono', monospace; font-size: 7.5pt;
  color: #5bf29b; white-space: pre-wrap; word-break: break-all;
  margin: 6px 0 10px; overflow: hidden;
}

/* ── BUSINESS RISK BOX ────────────────────────────── */
.risk-box {
  border-left: 3px solid #ff8c42; background: rgba(255,140,66,0.06);
  padding: 8px 12px; border-radius: 0 4px 4px 0; margin: 6px 0 10px;
  font-size: 8.5pt; color: #e8e6f0; line-height: 1.6;
}

/* ── CALLOUT / HANDLING NOTICE ────────────────────── */
.callout {
  border: 1px solid rgba(123,120,255,0.3); border-radius: 6px;
  background: rgba(123,120,255,0.05); padding: 12px 16px; margin: 16px 0;
  font-size: 8.5pt; line-height: 1.8; color: #9b98b8;
}

ul { margin: 4px 0 8px 16px; padding: 0; }
li { margin-bottom: 3px; }
strong { color: #e8e6f0; }
code { font-family: 'IBM Plex Mono', monospace; font-size: 8pt; color: #5bf29b;
       background: rgba(91,242,155,0.08); padding: 1px 4px; border-radius: 2px; }
```

## HTML Structures

### Cover page skeleton

```html
<div class="cover">
  <img class="cover-logo" src="{LOGO_SRC}" alt="NullPointer Studio">
  <div class="cover-classification">CONFIDENTIAL</div>
  <div class="cover-title">Penetration Test Report</div>
  <div class="cover-subtitle">{target_domain}</div>
  <div class="cover-divider"></div>
  <div class="cover-meta">
    <table>
      <tr><td>Client</td><td>{client}</td></tr>
      <tr><td>Target</td><td>{target_url}</td></tr>
      <tr><td>Test type</td><td>{engagement_type}</td></tr>
      <tr><td>Framework</td><td>{framework}</td></tr>
      <tr><td>Test date</td><td>{test_date}</td></tr>
      <tr><td>Report date</td><td>{report_date}</td></tr>
      <tr><td>Prepared by</td><td>NullPointer Studio</td></tr>
      <tr><td>Version</td><td>1.0</td></tr>
    </table>
  </div>
  <div class="cover-footer">NullPointer Studio · security research &amp; consulting</div>
</div>
```

### Finding card (finding_section function output)

```html
<div class="finding" style="border-left:4px solid {severity_color};">
  <div class="finding-header">
    <div class="finding-title-row">
      <span class="finding-id">{np_id}</span>
      <span class="badge" style="background:{sev_bg};color:{sev_color};border:1px solid {sev_color};">{SEV_LABEL}</span>
      <span class="finding-title">{title}</span>
    </div>
    <table class="finding-meta">
      <tr><td>OWASP</td><td>{owasp}</td><td>ASVS</td><td>{asvs}</td></tr>
      <tr><td>Endpoint</td><td colspan="3"><code>{endpoint}</code></td></tr>
      <tr><td>Auth Required</td><td>{auth}</td><td>Confirmed</td><td>{confirmed}</td></tr>
    </table>
  </div>
  <div class="finding-body">
    <h4>Description</h4>{description}
    <h4>Business Risk</h4>{business_risk}
    <h4>Evidence</h4>{evidence}
    <h4>Reproduction Steps</h4>{steps}
    <h4>Remediation</h4>{remediation}
  </div>
</div>
```

### INFO finding card (simplified — no Evidence/Steps)

```html
<div class="finding" style="border-left:4px solid #7b78ff;">
  <div class="finding-header">
    <div class="finding-title-row">
      <span class="finding-id">{np_id}</span>
      <span class="badge" ...>INFO</span>
      <span class="finding-title">{title}</span>
    </div>
  </div>
  <div class="finding-body">
    <h4>Description</h4>{description}
    <h4>Business Risk</h4>{business_risk}
    <h4>Recommendations</h4>{remediation}
  </div>
</div>
```

### Stat box row

```html
<div class="stat-row">
  <div class="stat-box">
    <span class="stat-num" style="color:#ff4d6d;">{critical_count}</span>
    <span class="stat-label">Critical</span>
  </div>
  <div class="stat-box">
    <span class="stat-num" style="color:#ff8c42;">{high_count}</span>
    <span class="stat-label">High</span>
  </div>
  <!-- ... medium, low, info, total -->
</div>
```

## Page layout order

```
1. Cover page            (page: cover-page, no footer)
2. Handling notice       (half page callout)
3. Stat boxes            (severity counts)
4. Executive Summary     (h1 + section)
5. Scope & Methodology   (h1 + table + bullets)
6. --- page break ---
7. Risk Dashboard        (h1 + full dashboard-table)
8. --- page break ---
9. Findings              (one finding card per finding, page-break-inside: avoid)
10. --- page break ---
11. Remediation Summary  (h1 + remediation-table)
12. Clean Controls       (h1 + dashboard-table, only if clean controls documented)
13. Footer callout       (NullPointer Studio · permission statement)
```

## Logo path

```
/Users/riccardo.tencate/Desktop/agent-smith/templates/FullLogo_Transparent.png
```

Always embed as base64 data URI — never as a file path — so the PDF is self-contained.
