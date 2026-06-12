import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";

const APOLLO_BASE_URL = "https://api.apollo.io/api/v1";
const CONFIG_PATH = path.join(os.homedir(), ".letta", "extensions", "apollo-api.config.json");
const ENV_KEY = "APOLLO_API_KEY";

function ensureConfigDir() {
  fs.mkdirSync(path.dirname(CONFIG_PATH), { recursive: true });
}

function readConfig() {
  try {
    const raw = fs.readFileSync(CONFIG_PATH, "utf8");
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch (error) {
    if (error && error.code === "ENOENT") return {};
    return {};
  }
}

function writeConfig(config) {
  ensureConfigDir();
  fs.writeFileSync(CONFIG_PATH, `${JSON.stringify(config, null, 2)}\n`, { mode: 0o600 });
  try {
    fs.chmodSync(CONFIG_PATH, 0o600);
  } catch {
    // chmod is best-effort on Windows.
  }
}

function runPowerShell(script, input) {
  const result = spawnSync(
    "powershell.exe",
    ["-NoProfile", "-NonInteractive", "-Command", script],
    { input, encoding: "utf8", windowsHide: true },
  );

  if (result.error) throw result.error;
  if (result.status !== 0) {
    const message = result.stderr && result.stderr.trim() ? result.stderr.trim() : "PowerShell secret operation failed.";
    throw new Error(message);
  }

  return String(result.stdout || "").trim();
}

function protectSecret(secret) {
  if (process.platform !== "win32") {
    throw new Error(`Persistent API key storage is only supported on Windows in this extension. Set ${ENV_KEY} instead.`);
  }

  return runPowerShell(
    "Add-Type -AssemblyName System.Security; $plain = [Console]::In.ReadToEnd(); $bytes = [Text.Encoding]::UTF8.GetBytes($plain); $encrypted = [Security.Cryptography.ProtectedData]::Protect($bytes, $null, [Security.Cryptography.DataProtectionScope]::CurrentUser); [Convert]::ToBase64String($encrypted)",
    secret,
  );
}

function unprotectSecret(encryptedSecret) {
  if (process.platform !== "win32") {
    throw new Error(`Saved Apollo API keys can only be decrypted on Windows. Set ${ENV_KEY} instead.`);
  }

  return runPowerShell(
    "Add-Type -AssemblyName System.Security; $encrypted = [Convert]::FromBase64String([Console]::In.ReadToEnd()); $bytes = [Security.Cryptography.ProtectedData]::Unprotect($encrypted, $null, [Security.Cryptography.DataProtectionScope]::CurrentUser); [Text.Encoding]::UTF8.GetString($bytes)",
    encryptedSecret,
  );
}

function saveApiKey(apiKey) {
  const encryptedApiKey = protectSecret(apiKey);
  writeConfig({
    encryptedApiKey,
    storage: "windows-dpapi",
    updatedAt: new Date().toISOString(),
  });
}

function readApiKey() {
  const envKey = process.env[ENV_KEY];
  if (envKey && envKey.trim()) {
    return { apiKey: envKey.trim(), source: ENV_KEY };
  }

  const config = readConfig();
  if (typeof config.encryptedApiKey === "string" && config.encryptedApiKey.trim()) {
    return { apiKey: unprotectSecret(config.encryptedApiKey.trim()), source: `${CONFIG_PATH} (Windows DPAPI)` };
  }

  if (typeof config.apiKey === "string" && config.apiKey.trim()) {
    return { apiKey: config.apiKey.trim(), source: `${CONFIG_PATH} (legacy plain text)` };
  }

  return { apiKey: null, source: null };
}

function maskKey(apiKey) {
  if (!apiKey) return "not configured";
  if (apiKey.length <= 8) return `${apiKey.slice(0, 2)}...${apiKey.slice(-2)}`;
  return `${apiKey.slice(0, 4)}...${apiKey.slice(-4)}`;
}

function addParams(url, params = {}) {
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
    url.searchParams.set(key, String(value));
  }
}

function normalizePath(inputPath) {
  const rawPath = String(inputPath || "").trim();
  if (!rawPath) throw new Error("Apollo API path is required.");
  if (/^https?:\/\//i.test(rawPath)) {
    const url = new URL(rawPath);
    if (url.origin !== "https://api.apollo.io") {
      throw new Error("Only https://api.apollo.io endpoints are allowed.");
    }
    if (!url.pathname.startsWith("/api/v1/")) {
      throw new Error("Only Apollo /api/v1 endpoints are allowed.");
    }
    return url.pathname.replace(/^\/api\/v1/, "") + url.search;
  }
  return rawPath.startsWith("/") ? rawPath : `/${rawPath}`;
}

function summarizeApolloResponse(data) {
  if (!data || typeof data !== "object") return data;

  if (data.person && typeof data.person === "object") {
    const person = data.person;
    const org = person.organization && typeof person.organization === "object" ? person.organization : null;
    return {
      request_id: data.request_id ?? null,
      waterfall: data.waterfall ?? null,
      person: {
        id: person.id ?? null,
        name: person.name ?? ([person.first_name, person.last_name].filter(Boolean).join(" ") || null),
        title: person.title ?? null,
        headline: person.headline ?? null,
        email: person.email ?? null,
        email_status: person.email_status ?? null,
        linkedin_url: person.linkedin_url ?? null,
        city: person.city ?? null,
        state: person.state ?? null,
        country: person.country ?? null,
        organization_name: person.organization_name ?? org?.name ?? null,
        phone_numbers: Array.isArray(person.phone_numbers)
          ? person.phone_numbers.map((phone) => ({
              raw_number: phone.raw_number ?? null,
              sanitized_number: phone.sanitized_number ?? null,
              type: phone.type ?? null,
              status: phone.status ?? null,
            }))
          : undefined,
      },
      organization: org
        ? {
            id: org.id ?? null,
            name: org.name ?? null,
            website_url: org.website_url ?? null,
            primary_domain: org.primary_domain ?? null,
            linkedin_url: org.linkedin_url ?? null,
            industry: org.industry ?? null,
            estimated_num_employees: org.estimated_num_employees ?? null,
            city: org.city ?? null,
            state: org.state ?? null,
            country: org.country ?? null,
          }
        : null,
    };
  }

  if (Array.isArray(data.users)) {
    return {
      users: data.users.map((user) => ({
        id: user.id ?? null,
        name: user.name ?? ([user.first_name, user.last_name].filter(Boolean).join(" ") || null),
        email: user.email ?? null,
        title: user.title ?? null,
        role: user.role ?? null,
      })),
      pagination: data.pagination ?? null,
      total_entries: data.total_entries ?? null,
    };
  }

  if (Array.isArray(data.people)) {
    return {
      people: data.people.map((person) => ({
        id: person.id ?? person.person_id ?? null,
        name: person.name ?? ([person.first_name, person.last_name].filter(Boolean).join(" ") || null),
        title: person.title ?? null,
        email: person.email ?? null,
        email_status: person.email_status ?? null,
        linkedin_url: person.linkedin_url ?? null,
        organization_name: person.organization_name ?? person.organization?.name ?? null,
      })),
      pagination: data.pagination ?? null,
      total_entries: data.total_entries ?? null,
    };
  }

  return data;
}

async function callApollo({ method = "GET", endpointPath, params = {}, body = undefined, responseMode = "summary", signal }) {
  const { apiKey } = readApiKey();
  if (!apiKey) {
    return {
      status: "error",
      content: `Apollo API key is not configured. Run /apollo-key <api_key> or set ${ENV_KEY} in the local environment, then /reload.`,
    };
  }

  const normalizedPath = normalizePath(endpointPath);
  const url = new URL(`${APOLLO_BASE_URL}${normalizedPath.startsWith("/") ? normalizedPath : `/${normalizedPath}`}`);
  addParams(url, params);

  const upperMethod = String(method || "GET").toUpperCase();
  const options = {
    method: upperMethod,
    headers: {
      "Cache-Control": "no-cache",
      "Content-Type": "application/json",
      accept: "application/json",
      "x-api-key": apiKey,
    },
    signal,
  };

  if (body !== undefined && body !== null && upperMethod !== "GET" && upperMethod !== "HEAD") {
    options.body = typeof body === "string" ? body : JSON.stringify(body);
  }

  const response = await fetch(url, options);
  const text = await response.text();
  let data;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text;
  }

  const result = {
    ok: response.ok,
    status: response.status,
    statusText: response.statusText,
    endpoint: `${upperMethod} ${url.pathname}${url.search}`,
    data: responseMode === "raw" ? data : summarizeApolloResponse(data),
  };

  if (!response.ok) {
    result.error = "Apollo API request failed.";
  }

  return result;
}

function commandHelp() {
  return [
    "Apollo API key commands:",
    "  /apollo-key <api_key>       Save the key locally",
    "  /apollo-key set <api_key>   Save the key locally",
    "  /apollo-key status          Show whether a key is configured",
    "  /apollo-key clear           Remove the locally saved key",
    "",
    `Environment variable ${ENV_KEY} takes precedence over the saved key.`,
    "The key is not written to agent memory or the system prompt.",
  ].join("\n");
}

function registerApolloKeyCommand(letta, disposers) {
  if (!letta.capabilities.commands) return;

  disposers.push(letta.commands.register({
    id: "apollo-key",
    description: "Save, clear, or check the local Apollo.io API key used by Apollo extension tools.",
    args: "[set <api_key>|status|clear]",
    showInTranscript: false,
    run(ctx) {
      const input = String(ctx.args || "").trim();
      if (!input || input === "help" || input === "--help" || input === "-h") {
        return { type: "output", output: commandHelp() };
      }

      const [first, ...rest] = input.split(/\s+/);
      const action = first.toLowerCase();

      if (action === "status") {
        const { apiKey, source } = readApiKey();
        return {
          type: "output",
          output: apiKey
            ? `Apollo API key configured from ${source}. Key: ${maskKey(apiKey)}`
            : `Apollo API key is not configured. Run /apollo-key <api_key> or set ${ENV_KEY}.`,
        };
      }

      if (action === "clear" || action === "remove" || action === "delete") {
        const config = readConfig();
        delete config.apiKey;
        delete config.encryptedApiKey;
        delete config.storage;
        config.updatedAt = new Date().toISOString();
        writeConfig(config);
        return { type: "output", output: `Removed locally saved Apollo API key from ${CONFIG_PATH}.` };
      }

      const apiKey = action === "set" ? rest.join(" ").trim() : input;
      if (!apiKey) {
        return { type: "output", output: "No API key provided. Use /apollo-key <api_key>." };
      }

      saveApiKey(apiKey);
      return {
        type: "output",
        output: `Saved Apollo API key locally at ${CONFIG_PATH} using Windows DPAPI encryption. Key: ${maskKey(apiKey)}`,
      };
    },
  }));
}

function registerApolloTools(letta, disposers) {
  if (!letta.capabilities.tools) return;

  disposers.push(letta.tools.register({
    name: "apollo_people_enrichment",
    description: "Use Apollo.io People Enrichment to enrich one person by email, name, company domain, LinkedIn URL, or Apollo person ID. This may consume Apollo credits, especially when reveal or waterfall options are enabled.",
    parameters: {
      type: "object",
      properties: {
        first_name: { type: "string", description: "Person first name." },
        last_name: { type: "string", description: "Person last name." },
        name: { type: "string", description: "Full person name." },
        email: { type: "string", description: "Person email address." },
        hashed_email: { type: "string", description: "MD5 or SHA-256 hash of the person's email." },
        organization_name: { type: "string", description: "Employer organization name." },
        domain: { type: "string", description: "Employer domain, without www or @." },
        id: { type: "string", description: "Apollo person ID." },
        linkedin_url: { type: "string", description: "Person LinkedIn profile URL." },
        reveal_personal_emails: { type: "boolean", description: "Set true to request personal emails. May consume credits. Default false." },
        reveal_phone_number: { type: "boolean", description: "Set true to request phone numbers. Requires webhook_url and may consume credits. Default false." },
        webhook_url: { type: "string", description: "HTTPS webhook URL required when reveal_phone_number is true." },
        run_waterfall_email: { type: "boolean", description: "Set true to run waterfall email enrichment. May consume credits. Default false." },
        run_waterfall_phone: { type: "boolean", description: "Set true to run waterfall phone enrichment. May consume credits. Default false." },
        response_mode: { type: "string", enum: ["summary", "raw"], description: "Return concise summary or raw Apollo JSON. Default summary." },
      },
      additionalProperties: false,
    },
    requiresApproval: true,
    parallelSafe: true,
    async run(ctx) {
      const args = ctx.args || {};
      const identifyingFields = ["first_name", "last_name", "name", "email", "hashed_email", "organization_name", "domain", "id", "linkedin_url"];
      if (!identifyingFields.some((field) => args[field])) {
        return { status: "error", content: "Provide at least one identifying field, such as email, linkedin_url, id, or name plus domain." };
      }
      if (args.reveal_phone_number && !args.webhook_url) {
        return { status: "error", content: "webhook_url is required when reveal_phone_number is true." };
      }

      const { response_mode, ...params } = args;
      return callApollo({
        method: "POST",
        endpointPath: "/people/match",
        params,
        responseMode: response_mode || "summary",
        signal: ctx.signal,
      });
    },
  }));

  disposers.push(letta.tools.register({
    name: "apollo_users_search",
    description: "Call Apollo.io GET /users/search using optional query parameters, matching the provided curl example. Use for Apollo user search when the user asks to search Apollo users.",
    parameters: {
      type: "object",
      properties: {
        params: {
          type: "object",
          description: "Query parameters to send to /users/search. Leave empty to match the basic curl example.",
          additionalProperties: { type: ["string", "number", "boolean"] },
        },
        response_mode: { type: "string", enum: ["summary", "raw"], description: "Return concise summary or raw Apollo JSON. Default summary." },
      },
      additionalProperties: false,
    },
    requiresApproval: true,
    parallelSafe: true,
    async run(ctx) {
      return callApollo({
        method: "GET",
        endpointPath: "/users/search",
        params: ctx.args?.params || {},
        responseMode: ctx.args?.response_mode || "summary",
        signal: ctx.signal,
      });
    },
  }));

  disposers.push(letta.tools.register({
    name: "apollo_api_request",
    description: "Make an authenticated request to an Apollo.io /api/v1 endpoint when a specific Apollo extension tool does not cover the needed endpoint. Requires approval because some Apollo API calls consume credits or mutate Apollo data.",
    parameters: {
      type: "object",
      properties: {
        method: { type: "string", enum: ["GET", "POST", "PUT", "PATCH", "DELETE"], description: "HTTP method. Default GET." },
        path: { type: "string", description: "Apollo /api/v1 path, such as /people/match or /users/search. Full https://api.apollo.io/api/v1 URLs are also accepted." },
        params: {
          type: "object",
          description: "Query parameters to append to the request URL.",
          additionalProperties: { type: ["string", "number", "boolean"] },
        },
        body: {
          type: "object",
          description: "JSON body for non-GET requests, if the Apollo endpoint expects one.",
          additionalProperties: true,
        },
        response_mode: { type: "string", enum: ["summary", "raw"], description: "Return concise summary or raw Apollo JSON. Default summary." },
      },
      required: ["path"],
      additionalProperties: false,
    },
    requiresApproval: true,
    parallelSafe: false,
    async run(ctx) {
      const args = ctx.args || {};
      return callApollo({
        method: args.method || "GET",
        endpointPath: args.path,
        params: args.params || {},
        body: args.body,
        responseMode: args.response_mode || "summary",
        signal: ctx.signal,
      });
    },
  }));
}

export default function activate(letta) {
  const disposers = [];

  registerApolloKeyCommand(letta, disposers);
  registerApolloTools(letta, disposers);

  return () => {
    for (const dispose of disposers.reverse()) dispose();
  };
}
