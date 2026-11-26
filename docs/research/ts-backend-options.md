# TypeScript backend options for The Logbook

Date: 2026-11-26. Ticket: #75 (part of map #71).

Method: facts were read from primary sources (official docs, the projects' own GitHub release and repo APIs, the npm registry API) on this date. The fetch tool summarises pages, so quoted wording is as returned by it. Version numbers and download counts are a snapshot from 2026-11-26 and will drift. Judgement and recommendations are labelled as such. Items I could not verify are under "Unverified".

## Summary

- A **runtime** is the program that executes your code; a **framework** is a library that handles the repetitive parts of a web server. You pick one of each.
- **Runtime: Node.js 26 LTS** is the safe default. Bun and Deno both run TypeScript directly and are good, but both rely on Node compatibility layers, and their trade-offs matter more than their speed for a first rewrite. All three can run Fastify, Hono and Express.
- **Framework shortlist: Hono or Fastify.** Hono has the best end-to-end type story for a React front end (the server's types flow to the client), zero dependencies and a small API. Fastify is the more established, Node-focused choice with schema validation built in and a first-party testing story. Express is the incumbent but gives the least help with types. NestJS is the "batteries and rules" option: powerful, but the most to learn and the most ceremony for a single-user app.
- **Testing:** every option can be tested without starting a real server. Vitest is a good default test runner for all of them.
- My recommendation (judgement, not from a source): Node 26 LTS + Hono (or Fastify if you prefer a more conventional, plugin-based server) + Vitest, with TypeScript checked by `tsc` in CI. The final pick belongs to the decision ticket.

## 1. Concepts, in plain terms

**Runtime.** TypeScript is not run directly by computers; it is JavaScript plus type annotations. A runtime is the engine that executes the JavaScript and provides the standard library for things a browser does not offer: reading files, opening network sockets, talking to databases. Node.js (2009), Deno (2018) and Bun (2021) are the three main server runtimes. The nearest Python analogy: the runtime is CPython, the framework is Django/Flask.

**Type stripping vs type checking.** The runtime only needs the JavaScript, so most simply delete the type annotations ("type stripping") and run what is left. None of them checks the types while running. Checking is a separate step (`tsc --noEmit`, Deno's `deno check`, `bun test --check`), normally run in your editor and CI. Sources in section 2.

**Web framework.** A web server library gives you "a request arrived, send a response". A framework adds the repeating parts: routing (which function handles `GET /ascents/42`), reading and validating request bodies, middleware (code that runs on every request, such as logging, CORS or auth checks), error handling and plugins. Django bundles all of that plus an ORM and admin; the TypeScript frameworks below are mostly the "web layer" only, and you choose the database layer separately (a later ticket).

**Library maturity: how to judge it.** Questions to ask, and where the answer lives:
1. Is it maintained now? Latest release date and cadence (GitHub releases, npm).
2. Is there a stated support policy? (Which versions get security fixes, until when.)
3. Is the API stable? Look for a recent major version with a migration guide and a changelog that treats breaking changes as events.
4. How many people depend on it? npm weekly downloads and GitHub stars are a rough signal only (downloads include automated installs and transitive dependencies).
5. How many dependencies does it pull in? Fewer means a smaller attack surface and fewer upgrade chains.
6. Who runs it, and what is the licence? A foundation or a long record is lower risk than a single sponsor.
7. Do the types come from the library itself, or from a community add-on that can lag?

## 2. Runtimes

### Snapshot

| | Node.js | Bun | Deno |
|---|---|---|---|
| First released | 2009 (repo 2014) | repo 2021 | repo 2018 |
| Current version | 26.13.1 LTS ("Lithium"); 27 is alpha | 1.4.5 (2026-11-19) | 2.9.8 (2026-10-21) |
| Engine | V8 | JavaScriptCore (not V8) | V8 |
| Runs `.ts` directly | Yes, types stripped | Yes | Yes |
| Type checks while running | No | No (opt-in `bun test --check`) | No (opt-in `--check`; `deno test` checks by default) |
| Built-in test runner | `node:test` (stable) | `bun test` (Jest-like) | `deno test` |
| Node/npm compatibility | It is Node | Stated goal: full; gaps listed | Broad; "over 75%" of Node's tests pass (2.8) |
| Security model | None by default | None by default | Permission flags (`-R`, `-E`, `-A`) |

Sources: GitHub releases API for `nodejs/node`, `oven-sh/bun`, `denoland/deno` (e.g. https://api.github.com/repos/oven-sh/bun/releases/latest); https://nodejs.org/dist/index.json; Bun and Deno docs below. Engine for Bun is from general knowledge, not fetched this session (see Unverified).

### Node.js
- Release policy: even-numbered lines become LTS (long-term support: bug and security fixes for a long fixed period). Per the release schedule, 22.x (EOL 2027-04-30) and 24.x (EOL 2028-04-30) are in Maintenance LTS; **26.x is Active LTS from 2026-10-28, EOL 2029-04-30**. The page's guidance: production should use only Active or Maintenance LTS. Source: https://github.com/nodejs/release#release-schedule and https://nodejs.org/en/about/previous-releases
- From Node 27, the schedule becomes annual: every release is promoted to LTS after six months, with 30 months of LTS. Same sources.
- TypeScript: Node strips types and runs the rest. From v22.18.0 `node example.ts` works without a flag, for "erasable syntax" only; `enum`, parameter properties and runtime namespaces fail. Node does no type checking, and ignores `tsconfig.json` at runtime; run `tsc --noEmit` separately. Source: https://nodejs.org/en/learn/typescript/run-natively
- Testing: the built-in `node:test` is Stable (since v20); watch mode and coverage are still marked experimental. Source: https://nodejs.org/api/test.html
- Practical note (judgement): even so, most projects still use a build/runner tool and `tsc`, because of the syntax limits above.

### Bun
- Positioning: an all-in-one runtime, package manager, bundler and test runner. Latest 1.4.5 (GitHub releases API).
- Node compatibility: the docs state the goal is full compatibility and "if a package works in Node.js but not in Bun, Bun considers it a bug". They also list partial modules: `node:async_hooks` (stubs), `node:crypto` (some algorithms missing because BoringSSL lacks them), `node:https`, `node:child_process`, `node:cluster`, `node:module`, `node:worker_threads` and others. Source: https://bun.sh/docs/runtime/nodejs-compat
- TypeScript: runs directly; docs recommend `tsc` with `noEmit` for checking and `@types/bun` for Bun's own APIs. Source: https://bun.sh/docs/runtime/typescript
- Testing: `bun test` is Jest-compatible ("aims for compatibility with Jest, but not everything is implemented"), with snapshots, mocking, watch and coverage. Source: https://bun.sh/docs/cli/test
- Trade-off: the fastest-feeling tooling, but the most gaps against the Node ecosystem that frameworks and libraries are written against.

### Deno
- Positioning: secure-by-default runtime; v2 added much stronger Node/npm compatibility. Latest 2.9.8.
- npm and `package.json`: npm packages import via `npm:` specifiers or `package.json`; native addons need a local `node_modules` and `--allow-ffi`. Source: https://docs.deno.com/runtime/fundamentals/node/
- Permissions: code, including npm packages, runs under permission flags, so a dependency cannot read files or env vars unless you grant it. That is a real security benefit and a real source of friction. Same source.
- TypeScript: strips types to run; `deno check` type-checks (like `tsc --noEmit`); `deno test` checks by default. Deno's own TypeScript-compiler-in-Go (tsgo) support is unstable. Source: https://docs.deno.com/runtime/fundamentals/typescript/
- Testing: built-in `deno test`, also supports `node:test`. Source: https://docs.deno.com/runtime/fundamentals/testing/
- Note from the Deno docs: Deno only supports modern `node16` module resolution, so some npm packages show type errors that `tsc` does not.

### Runtime verdict (judgement)
Hosting is Docker Compose on a homelab VM, so runtime start-up and bundle size do not matter; ecosystem compatibility and longevity do. Node 26 LTS has a published support window to 2029-04-30 and is what every library is tested against. Hono's docs list Bun and Deno as supported runtimes, so with Hono the runtime stays a cheap later swap; with the other frameworks I did not verify Bun/Deno support.

## 3. Frameworks

| | Express | Fastify | Hono | NestJS |
|---|---|---|---|---|
| Latest | 5.3.0 | 5.12.8 | 4.13.22 | 12.6.2 |
| Repo created | 2009 | 2016 | 2021 | 2017 |
| npm downloads, week to 2026-11-24 | ~210M | ~23.8M | ~112M | ~25.2M (`@nestjs/core`) |
| Runtime dependencies (direct) | 28 | 15 | 0 | 5 (`@nestjs/core`) |
| Licence | MIT | MIT | MIT | MIT |
| Written in | JS (types separate) | JS with bundled types | TypeScript | TypeScript |
| Approach | Minimal, middleware | Plugins, JSON-Schema validation | Web-standard, tiny | Opinionated, modules + dependency injection |

Sources: npm registry (`https://registry.npmjs.org/<pkg>/latest`, `https://api.npmjs.org/downloads/point/last-week/<pkg>`); GitHub repos API. Downloads are a popularity hint only; Express's figure is inflated by being a dependency of many other tools.

### Express
- Support policy: "Only the latest version of each major release line receives support." v5.x (Node 18+) support began September 2024; v4.x is also listed as ongoing. Source: https://expressjs.com/en/support/
- Express 5 forwards rejected promises from async handlers to the error handler automatically; this was a common Express 4 pitfall. Source: https://expressjs.com/en/guide/migrating-5.html
- Types: not covered in the official docs I read; Express's TypeScript types are a separate community package (`@types/express`), from general knowledge (not fetched).
- Fit: the most tutorials and examples exist; the least built in (no schema validation, no typed routes). Reasonable if you want the most documentation, weaker for a type-driven API.

### Fastify
- Support policy: each major gets at least six months of LTS; security updates continue six months after the next major. v4 ended 2025-06-30; v5 (released 2024-09-17) end date TBD. v5 is tested against Node 20 and 22 per the table (Node 24 and 26 were not listed on the page when fetched). Source: https://fastify.dev/docs/latest/Reference/LTS/
- Types: first-party types; route types via generics; official type providers for TypeBox and json-schema-to-ts so one schema gives both runtime validation and static types. Docs admit some parts "may be untyped or mistyped". Source: https://fastify.dev/docs/latest/Reference/TypeScript/
- Validation: built-in JSON Schema validation (Ajv).
- Testing: built-in `inject()` fakes a request without opening a network port; the guide uses Node's own test runner. Source: https://fastify.dev/docs/latest/Guides/Testing/
- Fit: mature, Node-focused, fast, schema-first. A good conventional choice; more concepts (plugins, encapsulation, schemas) than Hono.

### Hono
- Small, built on Web Standards (the same `Request`/`Response` objects browsers use); runs on Cloudflare Workers, Deno, Bun, Vercel, AWS Lambda and Node via an adapter (`@hono/node-server`, 2.1.11). Zero dependencies; `hono/tiny` under 14KB. Source: https://hono.dev/docs/ and https://hono.dev/docs/getting-started/nodejs
- Types and the React link: validators define input types and `c.json()` defines response types; the client `hc<AppType>(url)` mirrors the routes with checked types, so a React front end in the same repo gets compile-time errors if the API changes. Caveats: needs `strict: true` in both tsconfigs; server and client Hono versions must match; very many routes slow the editor; `.then()` chains and `c.notFound()` lose types. Source: https://hono.dev/docs/guides/rpc
- Testing: `app.request('/path')` calls the app directly and returns a `Response`; no server. Source: https://hono.dev/docs/guides/testing
- Maturity (judgement): younger (2021) and still on 4.x with very frequent releases (4.13.22 published 2026-11-25), but huge adoption by downloads. I did not find a published LTS policy on the pages I read.

### NestJS
- A framework of rules: modules, controllers and "providers" (services) wired by dependency injection (the framework constructs objects and hands them what they need, usually via decorators, the `@Something()` annotations). Written in TypeScript; new projects generate in strict mode. Runs on top of Express (default), Fastify, or Node's `http` (the docs recommend the latter from v12.3 and say it becomes default in v13). Source: https://docs.nestjs.com/first-steps
- Testing: `@nestjs/testing` builds a test module where you override providers with fakes; new projects use Vitest by default; e2e tests via Supertest or Fastify `inject()`. Source: https://docs.nestjs.com/fundamentals/testing
- Fit: it imposes structure that pays off with many developers and a large codebase, and teaches enterprise patterns (also Angular-like and Spring-like). For a single-user personal app it is the most to learn and the most boilerplate.

## 4. Testing story, common to all (summary)
- All four can be tested in-process, without a network port: Fastify `inject()`, Hono `app.request()`, Nest `createNestApplication()` plus Supertest or `inject()`, Express via Supertest (Supertest is mentioned in the Nest docs and Fastify guide; Express's own docs did not cover testing in what I read).
- Test runners: Node's `node:test` (stable), Vitest (needs Node 22.12+ and Vite 6.4+ per its docs, https://vitest.dev/guide/, latest 5.1.2), `bun test`, `deno test`. Vitest is the one the Nest docs make the default and the Hono docs use in their example, so it is the lowest-risk common choice.
- Type checking is a separate gate in every case: `tsc --noEmit` in CI. TypeScript 7.0 (the native, Go-based rewrite, 7.0.2 released 2026-08-20) is now the `typescript` package on npm; the staging repo README says the port is complete but with "not yet at full feature parity" for some pieces (language service nearly complete, API not ready). Source: https://github.com/microsoft/typescript-go and the GitHub releases API for `microsoft/TypeScript`.

## 5. Learning curve for a newcomer (judgement, grounded in the above)
1. **Hono**: fewest concepts (an app, routes, middleware, validators). Docs are short. The types-to-client feature teaches what TypeScript is good for.
2. **Express**: easiest to find tutorials; few guardrails, so you meet bugs the framework would have caught.
3. **Fastify**: plugin encapsulation and JSON Schema take a day to click, then it is consistent.
4. **NestJS**: decorators, modules and dependency injection are a course in themselves.

## Unverified
- Bun's JavaScript engine (JavaScriptCore) and Node's V8 are from general knowledge, not fetched this session.
- Whether Fastify 5 is tested on Node 24 and 26: the LTS page lists only Node 20 and 22; this may be out of date.
- No LTS or support policy page was found for Hono or NestJS.
- The "Active LTS / Maintenance" labels for Node come from the nodejs/release README as returned by the fetch tool; the site page uses "LTS" only.
- Express TypeScript typings status (separate `@types/express`) not fetched.
- GitHub `NOASSERTION` licence for Node and Bun in the repo API only means the repo has several licence files; not investigated.
