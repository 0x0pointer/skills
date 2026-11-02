# deserialization: Unsafe deserialization

## Claim to verify
Bytes an attacker controls are deserialised by a mechanism that can instantiate arbitrary types
or invoke code (gadget chains), leading to code execution or object injection.

## Refute if
- The format is data-only and parsed into concrete types: `json.loads`, `JSON.parse`,
  `System.Text.Json` into a DTO, Jackson without default typing, `yaml.safe_load`,
  `SafeConstructor`, protobuf.
- The input is integrity-protected with a server secret **verified before** deserialisation
  (HMAC over the payload with constant-time compare), and the secret is not exposed.
- The deserialised bytes come only from server-written storage the attacker cannot influence
  (check for upload, cache poisoning, or shared buckets).
- Class allowlists are enforced (`ObjectInputFilter`, XStream allowlist, Kryo registration,
  `unserialize(..., ['allowed_classes' => false])`).

## Framework protections to check
- Python: `pickle`, `cPickle`, `dill`, `joblib`, `shelve`, `torch.load` (without
  `weights_only=True`), `numpy.load(allow_pickle=True)`, `yaml.load` without SafeLoader,
  `jsonpickle`.
- Java: `ObjectInputStream`, `XMLDecoder`, XStream, Jackson polymorphic typing, SnakeYAML < 2
  default constructor, Hessian, Kryo.
- .NET: `BinaryFormatter`, `NetDataContractSerializer`, `LosFormatter`, Json.NET
  `TypeNameHandling` != `None`.
- PHP: `unserialize`, `phar://` wrapper reaching file functions.
- Node: `node-serialize`, `funcster`, `serialize-javascript` + `eval`.
- Signed-cookie sessions using pickle (old Django `PickleSerializer`, Flask custom) are safe only
  while the secret is secret.

## confirmed_static when
A cited attacker-controlled byte source (request body, cookie, upload, queue message from an
untrusted producer) reaches a cited unsafe deserialiser on a reachable path, with no integrity
check or allowlist.

## Common false positives
- `pickle.load` on model files bundled with the application.
- Jackson `@JsonTypeInfo(use = Id.NAME)` with a closed set of subtypes.

## Severity
Reachable unsafe deserialisation: `critical`; behind admin auth: `high`.

## Remediation
Switch to a data-only format with concrete types, or verify an HMAC before deserialising and
enforce a class allowlist.
