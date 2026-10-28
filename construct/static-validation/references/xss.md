# xss: Cross-site scripting

## Claim to verify
Attacker-controlled data is rendered into an HTML, attribute, URL or script context of a page
viewed by **another** user (or by the victim via a crafted link) without context-appropriate
encoding.

## Refute if
- The template engine auto-escapes this output (Django/Jinja2-in-Flask `{{ }}`, Razor `@x`,
  Blade `{{ }}`, Thymeleaf `th:text`, React JSX text, Vue `{{ }}`, Angular interpolation, Go
  `html/template`) and no raw-output construct is used.
- The response content type is not HTML-rendered (`application/json` with
  `X-Content-Type-Options: nosniff`, file download with `Content-Disposition: attachment`).
- The data is sanitised with an HTML sanitiser (DOMPurify, bleach/nh3, HtmlSanitizer, OWASP
  Java HTML Sanitizer) **after** the last modification and before rendering.
- The value is numeric / enum / server-generated.
- Only the attacker sees it (self-XSS with no CSRF or sharing vector): `refuted` or `low`.

## Framework protections to check
- Raw constructs: `|safe`, `mark_safe`, `Markup`, `{% autoescape off %}`, `{!! !!}`, `|raw`,
  `th:utext`, `@Html.Raw`, `dangerouslySetInnerHTML`, `v-html`, `[innerHTML]`,
  `bypassSecurityTrustHtml`, `template.HTML`, `innerHTML =`, `document.write`, `$(...).html()`.
- Context mismatch: HTML-escaping inside a `<script>` block, an event handler attribute, or an
  unquoted attribute is insufficient; `href`/`src` need scheme checks (`javascript:`).
- Jinja2 outside Flask defaults to `autoescape=False` unless configured.
- CSP reduces impact but does not refute unless it is strict (nonce/hash based, no
  `unsafe-inline`) and present on this response.

## confirmed_static when
Attacker data is cited flowing into a cited raw/unescaped output in a page another user loads,
and no sanitiser is on the path.

## Common false positives
- JSON APIs consumed by a framework that escapes on render.
- Admin-only input rendered only to admins (still report as `low` if admins are distinct users).

## Severity
Stored XSS visible to other users or admins: `high`. Reflected: `medium`. DOM-only with
unlikely trigger: `low`.

## Remediation
Remove the raw construct or sanitise with an HTML sanitiser; encode for the actual context.
