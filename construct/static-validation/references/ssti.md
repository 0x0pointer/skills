# ssti: Server-side template injection

## Claim to verify
Attacker data becomes part of a template's **source** (not its context data) and is compiled by
a template engine capable of expression evaluation.

## Refute if
- The user value is passed only as context data to a fixed template
  (`render_template("x.html", name=v)`, `res.render("view", { v })`, `model.addAttribute`).
- The template source comes from trusted storage only writable by privileged staff (still
  `low` if staff and end users are distinct trust levels).
- A logic-less engine without code execution is used (Mustache, Handlebars without custom
  helpers) and the impact is limited to data exposure within the context (rate accordingly).

## Framework protections to check
- Dangerous: `render_template_string(x)`, `Template(x)`, `Environment().from_string(x)`,
  `jinja2.Template(f"...{x}...")`, Twig `createTemplate`, Freemarker `new Template(..., x)`,
  Velocity `evaluate`, Thymeleaf view names / fragment expressions built from input
  (`return "user/" + lang`), `ejs.render(x)`, `pug.compile(x)`, Go `template.New().Parse(x)`,
  Razor runtime compilation of input.
- String formatting *into* a template before rendering (`render_template_string("Hi " + name)`)
  is injection even though the engine sees a "fixed" call.
- Jinja2 `SandboxedEnvironment` limits but has a history of escapes: treat as `plausible`, lower
  severity.

## confirmed_static when
A cited source flows into cited template-source construction or compilation on a reachable path.

## Common false positives
- Variables named `template` holding a template *name* chosen from a fixed map.

## Severity
Engines with code execution (Jinja2, Twig, Freemarker, Velocity, Thymeleaf SpEL, EJS, Pug):
`critical`/`high`. Logic-less engines: `medium` at most.

## Remediation
Render fixed templates and pass user values as context data.
