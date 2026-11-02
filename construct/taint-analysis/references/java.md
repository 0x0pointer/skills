# Java / Kotlin: Spring Boot, Spring MVC / WebFlux, Jakarta EE

## Sources

- Spring MVC / WebFlux: `@RequestParam`, `@PathVariable`, `@RequestBody` (DTO or entity),
  `@RequestHeader`, `@CookieValue`, `@ModelAttribute`, `HttpServletRequest.getParameter /
  getHeader / getInputStream`, `MultipartFile.getOriginalFilename / getInputStream`,
  `ServerRequest` in functional endpoints, GraphQL `@Argument`.
- Messaging: `@KafkaListener`, `@RabbitListener`, `@JmsListener`, `@SqsListener` payloads.
- Jakarta: `@QueryParam`, `@PathParam`, `@FormParam`, `@HeaderParam`, servlet request.
- Second-order: entity fields previously written by other users; `RestTemplate` / `WebClient`
  responses from third parties.

## Sinks and their safe variants

| Bug class | Dangerous | Usually safe |
|---|---|---|
| sqli | `Statement.execute*(str + x)`, `JdbcTemplate.query(str + x)`, `EntityManager.createQuery("... " + x)` (JPQL/HQL injection), `createNativeQuery(str + x)`, `@Query` with SpEL `?#{...}` on input, MyBatis `${x}`, jOOQ `DSL.field(str)` / `.where(String)` | `PreparedStatement` with `?`, named parameters `:x`, Spring Data derived queries, MyBatis `#{x}`, Criteria API |
| sqli (identifiers) | `Sort.by(userInput)` into native queries, `ORDER BY` concatenation | allowlist of sortable properties |
| cmdi | `Runtime.exec(str)`, `ProcessBuilder("sh", "-c", str)` | `ProcessBuilder(List.of(cmd, arg))` without shell |
| code-injection | SpEL `ExpressionParser.parseExpression(x)` (with `StandardEvaluationContext`), Groovy / Nashorn / JSR-223 `eval`, OGNL, MVEL | `SimpleEvaluationContext`, no evaluation of input |
| path-traversal | `new File(base, x)`, `Paths.get(base, x)`, `Files.*`, `ResourceLoader.getResource(x)`, `ZipEntry.getName()` during extraction (zip slip) | `base.resolve(x).normalize().startsWith(base)` after `toRealPath` |
| ssrf | `RestTemplate.getForObject(x)`, `WebClient.get().uri(x)`, `new URL(x).openConnection()`, `HttpClient.send` with user URI, Feign with dynamic URL | allowlist; resolve and check address; disable redirects |
| xss | Thymeleaf `th:utext`, JSP `<%= %>` / `${}` without `<c:out>`, `@ResponseBody` HTML strings, `produces = TEXT_HTML` with concatenation | `th:text`, `<c:out>`, OWASP Java Encoder |
| ssti | Thymeleaf template names from input (`return "page/" + x` from a controller, fragment expression injection), Freemarker / Velocity templates built from input | constant view names |
| deserialization | `ObjectInputStream.readObject` on untrusted bytes, `XMLDecoder`, XStream without allowlist, Jackson `enableDefaultTyping` / `@JsonTypeInfo(use = Id.CLASS)`, SnakeYAML `new Yaml().load` (pre 2.0), Kryo without registration | JSON into concrete DTOs, `ObjectInputFilter`, SnakeYAML `SafeConstructor` |
| xxe | `DocumentBuilderFactory`, `SAXParserFactory`, `XMLInputFactory`, `TransformerFactory`, `Unmarshaller` without disabling DTDs / external entities | `setFeature("http://apache.org/xml/features/disallow-doctype-decl", true)` |
| ldap-injection | `DirContext.search(base, "(uid=" + x + ")", ...)` | `LdapQueryBuilder`, `LdapEncoder.filterEncode` |
| open-redirect | `"redirect:" + x`, `response.sendRedirect(x)` | allowlist / relative only |
| crypto-misuse | `java.util.Random` for tokens, `MessageDigest("MD5"/"SHA-1")` for passwords, `Cipher.getInstance("AES")` (ECB default), static IVs, JJWT `parse` without key / `parseUnsecured`, trusting `alg` | `SecureRandom`, `BCryptPasswordEncoder` / Argon2, `AES/GCM/NoPadding` with random IV, `parseSignedClaims` with a key |
| mass-assignment | `@RequestBody Entity` / `@ModelAttribute Entity` bound straight to a JPA entity then saved; `BeanUtils.copyProperties(dto, entity)` with all fields | dedicated request DTO with only writable fields, `@InitBinder setAllowedFields` |

## Propagation and sanitisers

- String concatenation, `String.format`, `StringBuilder`, `MessageFormat` propagate.
- `Long.parseLong`, `UUID.fromString`, enum binding (`@RequestParam Status s`) neutralise
  injection for that value.
- Bean Validation (`@Valid` + `@Pattern`, `@Size`, `@Email`) only applies when `@Valid` /
  `@Validated` is present on the parameter and the constraint restricts the dangerous characters.

## Auth and framework protections

- Spring Security `SecurityFilterChain`: rule **order** matters (first match wins), and
  `permitAll()` patterns such as `/api/public/**` may match more than intended. Check
  `requestMatchers` against the new route's path, including trailing-slash and suffix variants.
- Method security: `@PreAuthorize`, `@Secured`, `@RolesAllowed` only work with
  `@EnableMethodSecurity` and on Spring-proxied beans; self-invocation bypasses them.
- Ownership checks are usually explicit (`repo.findByIdAndOwnerId`) or SpEL
  (`@PreAuthorize("@authz.canRead(#id)")`); `findById(id)` alone is unscoped.
- CSRF: enabled by default for session apps; `csrf().disable()` or `csrf(AbstractHttpConfigurer::disable)` matters only with cookie auth.
