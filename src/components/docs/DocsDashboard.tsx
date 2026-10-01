import React, { useMemo, useState } from 'react';
import {
  BookOpen,
  Rocket,
  KeyRound,
  Cpu,
  MessageSquare,
  Plug,
  Server,
  Brain,
  Compass,
  Code2,
  Wrench,
  ShieldCheck
} from 'lucide-react';
import { OPENAI_BASE } from '../../lib/api/client';
import { CodeBlock } from '../chat/CodeBlock';
import { Badge } from '../ui/Badge';
import { cn } from '../../lib/utils';

const BASE = OPENAI_BASE ?? 'http://127.0.0.1:8000/v1';
const HOST = BASE.replace(/\/v1$/, '');

type SectionId =
  | 'overview'
  | 'quickstart'
  | 'local-api'
  | 'authentication'
  | 'models'
  | 'chat'
  | 'compatibility'
  | 'ollama'
  | 'memory'
  | 'browser'
  | 'examples'
  | 'troubleshooting'
  | 'security';

const SECTIONS: { id: SectionId; label: string; icon: React.ReactNode }[] = [
  { id: 'overview', label: 'Overview', icon: <BookOpen className="w-4 h-4" /> },
  { id: 'quickstart', label: 'Quick Start', icon: <Rocket className="w-4 h-4" /> },
  { id: 'local-api', label: 'Local API', icon: <Server className="w-4 h-4" /> },
  { id: 'authentication', label: 'Authentication', icon: <KeyRound className="w-4 h-4" /> },
  { id: 'models', label: 'Models', icon: <Cpu className="w-4 h-4" /> },
  { id: 'chat', label: 'Chat Completions', icon: <MessageSquare className="w-4 h-4" /> },
  { id: 'compatibility', label: 'OpenAI Compatibility', icon: <Plug className="w-4 h-4" /> },
  { id: 'ollama', label: 'Ollama', icon: <Server className="w-4 h-4" /> },
  { id: 'memory', label: 'Memory', icon: <Brain className="w-4 h-4" /> },
  { id: 'browser', label: 'Browser Tools', icon: <Compass className="w-4 h-4" /> },
  { id: 'examples', label: 'API Examples', icon: <Code2 className="w-4 h-4" /> },
  { id: 'troubleshooting', label: 'Troubleshooting', icon: <Wrench className="w-4 h-4" /> },
  { id: 'security', label: 'Security', icon: <ShieldCheck className="w-4 h-4" /> }
];

const H2: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <h2 className="text-base font-semibold tracking-tight text-primary pb-2 border-b border-border">
    {children}
  </h2>
);

const P: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <p className="text-sm text-secondary leading-relaxed">{children}</p>
);

const UL: React.FC<{ items: React.ReactNode[] }> = ({ items }) => (
  <ul className="list-disc pl-5 space-y-1 text-sm text-secondary leading-relaxed marker:text-muted">
    {items.map((item, i) => (
      <li key={i}>{item}</li>
    ))}
  </ul>
);

const Inline: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <code className="inline-code">{children}</code>
);

const Method: React.FC<{ verb: 'GET' | 'POST'; path: string }> = ({ verb, path }) => (
  <div className="flex items-center gap-3 py-2">
    <Badge variant={verb === 'GET' ? 'default' : 'emerald'}>{verb}</Badge>
    <code className="text-sm font-mono text-primary">{path}</code>
  </div>
);

const Blocked: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div className="flex items-start gap-2 p-3 rounded-md bg-panel border border-border">
    <p className="text-xs text-muted leading-relaxed">{children}</p>
  </div>
);

export const DocsDashboard: React.FC = () => {
  const [active, setActive] = useState<SectionId>('overview');

  const sections = useMemo(
    () =>
      ({
        overview: (
          <div className="space-y-4">
            <H2>INTLLM Local API</H2>
            <P>
              INTLLM runs an OpenAI-compatible HTTP API on your machine. It routes every
              request through the same INTLLM runtime — memory retrieval, local model
              inference via Ollama, and the tool gateway — so any OpenAI-compatible client
              can talk to your local models.
            </P>
            <P>
              Everything is local-first. Nothing is sent to a cloud service unless you
              explicitly enable live web retrieval for a request.
            </P>
            <div className="grid gap-2 sm:grid-cols-2">
              <div className="p-3 rounded-md bg-panel border border-border">
                <div className="text-[10px] uppercase tracking-wider text-muted">Base URL</div>
                <code className="text-sm font-mono text-primary break-all">{BASE}</code>
              </div>
              <div className="p-3 rounded-md bg-panel border border-border">
                <div className="text-[10px] uppercase tracking-wider text-muted">Auth header</div>
                <code className="text-sm font-mono text-primary">
                  Authorization: Bearer sk-intllm-…
                </code>
              </div>
            </div>
            <P>Currently implemented and tested endpoints:</P>
            <div className="rounded-md border border-border divide-y divide-border">
              <Method verb="GET" path="/v1/models" />
              <Method verb="GET" path="/v1/models/{model}" />
              <Method verb="POST" path="/v1/chat/completions" />
            </div>
            <Blocked>
              Endpoints such as <Inline>/v1/embeddings</Inline>, <Inline>/v1/responses</Inline>,
              audio, images and files are not implemented. They are intentionally not exposed
              and must not be assumed to work.
            </Blocked>
          </div>
        ),
        quickstart: (
          <div className="space-y-4">
            <H2>Quick Start</H2>
            <P>
              INTLLM must be running before clients can connect. Start it with the
              <Inline>intllm</Inline> command (the web UI opens automatically) or run the API
              only with <Inline>intllm serve</Inline>.
            </P>
            <P>1. Confirm the runtime is healthy:</P>
            <CodeBlock language="bash">{`curl ${HOST}/api/health`}</CodeBlock>
            <P>2. Create an API key in Settings → API, then use it below.</P>
            <P>3. List the models served by your local Ollama:</P>
            <CodeBlock language="bash">{`curl ${BASE}/models \\
  -H "Authorization: Bearer $INTLLM_API_KEY"`}</CodeBlock>
            <P>4. Send a chat completion:</P>
            <CodeBlock language="bash">{`curl ${BASE}/chat/completions \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer $INTLLM_API_KEY" \\
  -d '{
    "model": "qwen3:8b",
    "messages": [{"role": "user", "content": "Hello INTLLM"}],
    "stream": false
  }'`}</CodeBlock>
          </div>
        ),
        'local-api': (
          <div className="space-y-4">
            <H2>Local API</H2>
            <P>
              The API binds to <Inline>127.0.0.1</Inline> by default. LAN exposure is an
              explicit opt-in via <Inline>INTLLM_HOST</Inline> and must be chosen deliberately.
            </P>
            <div className="rounded-md border border-border divide-y divide-border">
              <Method verb="GET" path="/v1/models" />
              <Method verb="GET" path="/v1/models/{model}" />
              <Method verb="POST" path="/v1/chat/completions" />
            </div>
            <P>
              Machine-readable technical documentation is always available from FastAPI:
            </P>
            <UL
              items={[
                <><Inline>{HOST}/openapi.json</Inline> — the OpenAPI schema</>,
                <><Inline>{HOST}/docs</Inline> — Swagger UI</>,
                <><Inline>{HOST}/redoc</Inline> — ReDoc</>
              ]}
            />
          </div>
        ),
        authentication: (
          <div className="space-y-4">
            <H2>Authentication</H2>
            <P>
              The INTLLM local API uses its own API keys. These are INTLLM keys — they are not
              Ollama credentials. Pass the key as a Bearer token or via the
              <Inline>x-api-key</Inline> header:
            </P>
            <CodeBlock language="http">{`Authorization: Bearer sk-intllm-xxxxxxxxxxxxxxxxxxxxxxxx
# or
x-api-key: sk-intllm-xxxxxxxxxxxxxxxxxxxxxxxx`}</CodeBlock>
            <UL
              items={[
                'Keys are generated locally and only a salted scrypt hash + short fingerprint is stored.',
                'The full key is shown exactly once at creation time; it can never be retrieved again.',
                'Keys are revocable and can be labelled.',
                'Last-used time is tracked when a key authenticates a request.'
              ]}
            />
            <Blocked>
              While no keys exist yet, INTLLM allows loopback requests as a bootstrap so you can
              create the first key from the UI. As soon as a key exists, authentication is
              required.
            </Blocked>
          </div>
        ),
        models: (
          <div className="space-y-4">
            <H2>Models</H2>
            <P>
              Models are whatever Ollama reports as installed on this machine. INTLLM does not
              invent models or provide a cloud fallback.
            </P>
            <CodeBlock language="bash">{`curl ${BASE}/models \\
  -H "Authorization: Bearer $INTLLM_API_KEY"`}</CodeBlock>
            <P>Response:</P>
            <CodeBlock language="json">{`{
  "object": "list",
  "data": [
    { "id": "qwen3:8b", "object": "model", "created": 1730000000, "owned_by": "intllm" }
  ]
}`}</CodeBlock>
            <P>Retrieve a single model:</P>
            <CodeBlock language="bash">{`curl ${BASE}/models/qwen3:8b \\
  -H "Authorization: Bearer $INTLLM_API_KEY"`}</CodeBlock>
            <Blocked>
              An unknown model returns HTTP 404 with an OpenAI-shaped error body.
            </Blocked>
          </div>
        ),
        chat: (
          <div className="space-y-4">
            <H2>Chat Completions</H2>
            <Method verb="POST" path="/v1/chat/completions" />
            <P>
              Supports <Inline>stream: false</Inline> (JSON) and <Inline>stream: true</Inline>{' '}
              (Server-Sent Events). Standard OpenAI fields are accepted:{' '}
              <Inline>model</Inline>, <Inline>messages</Inline>, <Inline>temperature</Inline>,{' '}
              <Inline>top_p</Inline>, <Inline>max_tokens</Inline>, <Inline>stop</Inline>.
            </P>
            <P>INTLLM-specific toggles are passed as extra body fields:</P>
            <CodeBlock language="json">{`{
  "model": "qwen3:8b",
  "messages": [{"role": "user", "content": "Search the web for today's news"}],
  "intllm_use_brain": true,
  "intllm_use_web": false
}`}</CodeBlock>
            <UL
              items={[
                <><Inline>intllm_use_brain</Inline> — include relevant long-term memory in the model context (default true).</>,
                <><Inline>intllm_use_web</Inline> — enable live web retrieval for this request (default false).</>
              ]}
            />
            <P>Streaming responses follow the OpenAI chunk format and terminate with:</P>
            <CodeBlock language="text">{`data: [DONE]`}</CodeBlock>
          </div>
        ),
        compatibility: (
          <div className="space-y-4">
            <H2>OpenAI Compatibility</H2>
            <P>
              Point any OpenAI-compatible client at the local base URL, an INTLLM API key, and a
              model name returned by <Inline>/v1/models</Inline>.
            </P>
            <CodeBlock language="text">{`Base URL: ${BASE}
API Key:  sk-intllm-...
Model:    qwen3:8b`}</CodeBlock>
            <P>Compatibility notes — what to expect:</P>
            <UL
              items={[
                'Supported: chat completions (streaming and non-streaming) and model listing.',
                'Chat responses use the standard choices/usage shape; usage maps Ollama prompt/eval counters.',
                'Not supported: embeddings, responses API, audio, images, files, fine-tuning and batches.',
                'Unsupported request fields are accepted and ignored so clients with extra parameters still work.',
                'INTLLM does not claim tested compatibility with any specific third-party tool unless verified against this build.'
              ]}
            />
          </div>
        ),
        ollama: (
          <div className="space-y-4">
            <H2>Ollama</H2>
            <P>
              INTLLM uses your local Ollama server for inference. The backend detects whether
              Ollama is installed, running and which models are installed.
            </P>
            <UL
              items={[
                <>Endpoint (default <Inline>http://127.0.0.1:11434</Inline>) is configured with <Inline>INTLLM_OLLAMA_URL</Inline>.</>,
                'If Ollama is unavailable, API calls fail with a clear 503 instead of fabricated output.',
                'Pull models in the Models workspace before making requests.'
              ]}
            />
            <Blocked>
              INTLLM does not bundle Ollama and does not silently install it. Install Ollama
              separately, then start it (INTLLM can start it when a local executable is found).
            </Blocked>
          </div>
        ),
        memory: (
          <div className="space-y-4">
            <H2>Memory</H2>
            <P>
              INTLLM keeps layered memory in local PostgreSQL with pgvector. During a chat,
              relevant memory is retrieved and added to the model context; retrieved memory is
              labelled in the response activities.
            </P>
            <UL
              items={[
                'L0 Flash Brain — very fast micro-cache for recent/hot items.',
                'L1 Hot Cache — short-lived context.',
                'L2 Secondary Brain — durable vector store (PostgreSQL + pgvector).',
                'Background maintenance keeps indexes and freshness up to date at low priority.'
              ]}
            />
            <Blocked>
              If pgvector is unavailable, semantic memory does not silently pretend to work:
              INTLLM reports the database as misconfigured with an actionable remediation step.
            </Blocked>
          </div>
        ),
        browser: (
          <div className="space-y-4">
            <H2>Browser Tools</H2>
            <P>
              The browser agent and other tools run through the INTLLM tool gateway, which
              enforces per-action permission policy. Actions that require approval will not run
              silently.
            </P>
            <UL
              items={[
                'Tool execution never bypasses the gateway.',
                'Browser automation is optional (Playwright) and reported as unavailable when not installed.',
                'Filesystem access is restricted to the configured workspace allowlist.'
              ]}
            />
          </div>
        ),
        examples: (
          <div className="space-y-4">
            <H2>API Examples</H2>
            <P>cURL — non-streaming:</P>
            <CodeBlock language="bash">{`curl ${BASE}/chat/completions \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer $INTLLM_API_KEY" \\
  -d '{
    "model": "qwen3:8b",
    "messages": [{"role": "user", "content": "Hello INTLLM"}]
  }'`}</CodeBlock>
            <P>cURL — streaming:</P>
            <CodeBlock language="bash">{`curl ${BASE}/chat/completions \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer $INTLLM_API_KEY" \\
  -d '{"model":"qwen3:8b","messages":[{"role":"user","content":"Hello"}],"stream":true}'`}</CodeBlock>
            <P>Python (OpenAI SDK):</P>
            <CodeBlock language="python">{`from openai import OpenAI

client = OpenAI(base_url="${BASE}", api_key="sk-intllm-...")

stream = client.chat.completions.create(
    model="qwen3:8b",
    messages=[{"role": "user", "content": "Hello INTLLM"}],
    stream=True,
)
for chunk in stream:
    print(chunk.choices[0].delta.content or "", end="")`}</CodeBlock>
            <P>JavaScript / TypeScript (OpenAI SDK):</P>
            <CodeBlock language="typescript">{`import OpenAI from "openai";

const client = new OpenAI({
  baseURL: "${BASE}",
  apiKey: "sk-intllm-...",
});

const res = await client.chat.completions.create({
  model: "qwen3:8b",
  messages: [{ role: "user", content: "Hello INTLLM" }],
});
console.log(res.choices[0].message.content);`}</CodeBlock>
            <Blocked>
              CLI tools that only require an OpenAI-compatible chat endpoint can use the same
              base URL and key. INTLLM does not claim tested compatibility with any specific CLI
              unless it has been verified against this build.
            </Blocked>
          </div>
        ),
        troubleshooting: (
          <div className="space-y-4">
            <H2>Troubleshooting</H2>
            <UL
              items={[
                <><strong>401 authentication_error</strong> — no or invalid API key. Create one in Settings → API.</>,
                <><strong>503 service_unavailable</strong> — PostgreSQL or Ollama is unavailable. Run <Inline>intllm doctor</Inline> for a real readiness report.</>,
                <><strong>404 not_found</strong> on a model — the model is not installed in Ollama. Check Models.</>,
                <><strong>Stalled stream</strong> — the model may still be loading; INTLLM reports errors as an SSE error frame followed by <Inline>[DONE]</Inline>.</>,
                <><strong>pgvector missing</strong> — install the pgvector extension for your PostgreSQL server and restart.</>
              ]}
            />
          </div>
        ),
        security: (
          <div className="space-y-4">
            <H2>Security</H2>
            <UL
              items={[
                'API keys are hashed with scrypt; only a fingerprint is stored for lookup.',
                'Secrets are redacted from logs and never exposed in frontend bundles.',
                'The API binds to localhost by default; LAN exposure is an explicit choice.',
                'CORS is restricted to configured local origins.',
                'Request bodies are size-limited and inputs validated with clear error contracts.',
                'Tool and browser execution always passes through the permission gateway.'
              ]}
            />
          </div>
        )
      }) as Record<SectionId, React.ReactNode>,
    []
  );

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-6xl mx-auto px-4 md:px-6 py-6">
        <div className="border-b border-border pb-4 mb-5">
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-semibold tracking-tight text-primary">Docs</h1>
            <Badge variant="outline">Local API reference</Badge>
          </div>
          <p className="text-xs text-secondary mt-1">
            Everything INTLLM actually implements — the local OpenAI-compatible API, authentication,
            memory and tools. No unsupported endpoints are documented.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-[210px_1fr] gap-6">
          <nav className="space-y-0.5 md:sticky md:top-0 self-start" aria-label="Docs sections">
            {SECTIONS.map((sec) => (
              <button
                key={sec.id}
                onClick={() => setActive(sec.id)}
                aria-current={active === sec.id ? 'true' : undefined}
                className={cn(
                  'w-full flex items-center gap-2.5 h-8 px-2.5 rounded-md text-[13px] transition-colors text-left focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring',
                  active === sec.id
                    ? 'bg-panel-hover text-primary font-medium'
                    : 'text-secondary hover:text-primary hover:bg-panel-hover'
                )}
              >
                <span className={cn(active === sec.id ? 'text-accent' : 'text-muted')}>
                  {sec.icon}
                </span>
                <span>{sec.label}</span>
              </button>
            ))}
          </nav>

          <div className="min-w-0 max-w-3xl">{sections[active]}</div>
        </div>
      </div>
    </div>
  );
};
