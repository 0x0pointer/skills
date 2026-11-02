# .NET: ASP.NET Core MVC, Minimal APIs, Razor Pages, EF Core

## Sources

- `[FromQuery]`, `[FromRoute]`, `[FromBody]`, `[FromForm]`, `[FromHeader]`, implicit model
  binding of action parameters and complex types, `HttpContext.Request.Query / Form / Headers /
  Cookies / Body`, `IFormFile.FileName / OpenReadStream`, Minimal API handler parameters,
  SignalR hub method arguments, gRPC request messages.
- Consumers: Azure Service Bus / RabbitMQ / MassTransit message handlers, webhook controllers,
  `HttpClient` responses from third parties.

## Sinks and their safe variants

| Bug class | Dangerous | Usually safe |
|---|---|---|
| sqli | `SqlCommand(str + x)`, `FromSqlRaw($"... {x}")` / `ExecuteSqlRaw` with concatenation or interpolated string **variable**, Dapper `Query(str + x)` | `FromSqlInterpolated($"... {x}")` / `FromSql` (parameterises), `SqlParameter`, Dapper `Query(sql, new { x })`, LINQ |
| sqli (dynamic LINQ) | `System.Linq.Dynamic.Core` `Where(x)` / `OrderBy(x)` with input | allowlist |
| cmdi | `Process.Start("cmd.exe", "/c " + x)`, `ProcessStartInfo { FileName = "bash", Arguments = "-c " + x }` | fixed executable with `ArgumentList.Add(x)` |
| path-traversal | `File.*(Path.Combine(base, x))` (an absolute `x` replaces `base`), `PhysicalFile(x)`, `ZipArchive.ExtractToDirectory` on old frameworks, `entry.FullName` | `Path.GetFullPath(Path.Combine(base, x)).StartsWith(fullBase + Path.DirectorySeparatorChar)`, `Path.GetFileName(x)` |
| ssrf | `HttpClient.GetAsync(x)`, `WebRequest.Create(x)`, `HttpClient.BaseAddress` from input | allowlist; `SocketsHttpHandler.ConnectCallback` that validates the address |
| xss | `@Html.Raw(x)`, `new HtmlString(x)`, `MarkupString` in Blazor, `Content(x, "text/html")` | Razor `@x` (encodes), `HtmlEncoder` |
| deserialization | `BinaryFormatter`, `NetDataContractSerializer`, `SoapFormatter`, `LosFormatter`, `ObjectStateFormatter`, Json.NET `TypeNameHandling` other than `None`, `JavaScriptSerializer` with `SimpleTypeResolver` | `System.Text.Json` into concrete types |
| xxe | `XmlDocument` / `XmlTextReader` with `XmlResolver` set and DTD processing on (.NET Framework < 4.5.2 defaults) | .NET Core defaults; `DtdProcessing.Prohibit` |
| open-redirect | `Redirect(returnUrl)` | `LocalRedirect(returnUrl)`, `Url.IsLocalUrl(returnUrl)` |
| crypto-misuse | `System.Random` for tokens, `MD5` / `SHA1` for passwords, `RijndaelManaged` ECB, `TokenValidationParameters` with `ValidateIssuerSigningKey = false` / `RequireSignedTokens = false` / `ValidateLifetime = false` | `RandomNumberGenerator`, `PasswordHasher<T>` / PBKDF2 with high iterations, `AesGcm` |
| mass-assignment | binding a request directly to an EF entity (`[FromBody] User user` then `_db.Update(user)`), `TryUpdateModelAsync(entity)` without an include list | input DTOs, `[Bind("A,B")]`, `[BindNever]` on sensitive properties |

## Propagation and sanitisers

- `+`, `string.Format`, `$"..."` interpolated strings, `StringBuilder` propagate. Interpolated
  strings are only parameterised by `FromSqlInterpolated` / `FromSql` when passed **directly**
  as `FormattableString`; assigning to a `string` first loses the parameterisation.
- Model binding to `int`, `Guid`, enums neutralises. `[RegularExpression]`, `[StringLength]`
  apply only if `ModelState.IsValid` is checked or `[ApiController]` auto-validation is on.

## Auth and framework protections

- `[Authorize]` on controller or action, `[AllowAnonymous]` overrides it. A global
  `FallbackPolicy` / `RequireAuthorization()` on endpoints makes routes authenticated by default;
  check `Program.cs`.
- Policies (`[Authorize(Policy = "...")]`) need matching `AddAuthorization` registration;
  resource-based checks use `IAuthorizationService.AuthorizeAsync(User, resource, policy)`;
  a missing call in a new action is an IDOR candidate.
- Antiforgery: MVC form posts need `[ValidateAntiForgeryToken]` or global
  `AutoValidateAntiforgeryTokenAttribute`; Minimal APIs need `.WithAntiforgery()` for forms.
