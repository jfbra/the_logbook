# React front-end options and mobile code sharing

Date: 2026-11-26
Ticket: #77 (part of map #71)

Method: every factual claim was read from the owning project's official documentation during this session (react.dev, vite.dev, nextjs.org, reactrouter.com, remix.run blog, docs.expo.dev, reactnative.dev, tanstack.com). The fetch tool summarises pages, so quotes are as returned by it. Items marked **Inference** are my reasoning, not a documented fact. Items under "Unverified" could not be confirmed (two Expo pages returned 404).

## Summary

- React is only a library for building screens out of components; routing, data fetching and build tooling are separate choices. Frameworks (Next.js, React Router framework mode, Expo) bundle those choices.
- For The Logbook (one user, a separate TypeScript API, hosted behind Tailscale, no search-engine traffic), a **Vite + React Router + TanStack Query single-page app (SPA)** is the lightest fit and teaches the most transferable pieces. Next.js and React Router framework mode both work, but their headline strength (server rendering) has little to offer here. (Recommendation, inference.)
- Sharing code with a future Expo / React Native app is real but narrower than people expect: you can share **logic and types** (API client, validation, domain rules, data-fetching hooks), not **screens or markup**. No web framework choice changes that much, so the mobile hook is cheap: keep logic in a separate shared package in a monorepo.
- Expo can target the web too, but that is a different bet (one UI codebase for phone and web) and not what this map's current scope assumes.

## 1. What React actually is

Per React's own Quick Start (https://react.dev/learn): React is a library for building user interfaces out of components.
- A component is "a piece of the UI (user interface) that has its own logic and appearance"; components are "JavaScript functions that return markup."
- The markup syntax is JSX; "It is optional, but most React projects use JSX."
- A component remembers things via **state** (`useState`); calling the setter "tells React to call your component function again", a **re-render**. Functions starting with `use` are **Hooks**. Data is passed down as **props**.

Plain-English version: you describe what the screen should look like for a given piece of data, and React redraws the right parts when the data changes. It does not by itself know about URLs, servers or databases. Those come from other libraries or a framework.

The React docs say: "If you want to build a new app or website with React, we recommend starting with a framework," and name Next.js, React Router (v7) and Expo (https://react.dev/learn/creating-a-react-app). They also state "Full-stack frameworks do not require a server": all support client-side rendering, SPAs and static generation, and "allow you to add server-side rendering on a per-route basis." Building from scratch "gives you more flexibility, but does require that you make choices on which tools to use for routing, data fetching, and other common usage patterns" and is "a lot like building your own framework." Vite, Parcel and RSbuild are listed as starting points for that route.

## 2. Single-page app vs server rendering

Next.js's docs define a "strict SPA" (https://nextjs.org/docs/app/guides/single-page-applications):
- **Client-side rendering (CSR):** one HTML file; "Every route, page transition, and data fetch is handled by JavaScript in the browser."
- **No full-page reloads.**
- Their stated downsides: strict SPAs "often require large amounts of JavaScript to load before the page can be interactive" and "client data waterfalls can be challenging to manage" (a waterfall is one request waiting on another before it can start).

Server rendering (SSR) means the server builds the HTML for each request (or at build time, "static generation") so the browser gets content before the JavaScript arrives. **Hydration** is then React "attaching event handlers to the DOM, to make the static HTML interactive" (Next.js docs, server-and-client-components).

Trade-off in short: SPA = simplest to host (static files) and simplest mentally (one runtime: the browser), at the cost of a slower first paint and weaker indexing by search engines. SSR = faster first paint and better for public content, at the cost of running a Node server (or build-time work) and a harder mental model (code that runs in two places).

**Inference:** for a logbook used by one person after login, behind Tailscale, SSR's benefits (SEO, first paint for anonymous visitors) are mostly irrelevant.

## 3. The options

### 3a. Vite single-page app (React from a build tool)
- Vite is "a build tool that aims to provide a faster and leaner development experience for modern web projects": a dev server with fast Hot Module Replacement plus a build command that "bundles your code with Rolldown, pre-configured to output highly optimized static assets for production." Current major is Vite 8; needs Node 20.19+ or 22.12+ (https://vite.dev/guide/).
- `create-vite` has `react-ts` and `react-compiler-ts` templates.
- Routing and data fetching are not included: you add a router (e.g. React Router) and a data library (e.g. TanStack Query).
- Output is a folder of static files. **Inference/standard practice:** serve from any static server such as nginx; because all URLs map to one `index.html`, the server must rewrite unknown paths to it (React Router's SPA docs say the same: "configure your host to rewrite all URLs to `index.html`").
- Learning curve: lowest ceremony, but you make and own more choices. React's docs note this is "a lot like building your own framework."

### 3b. Next.js (App Router)
- Described by React docs as a framework "to enable full-stack React apps" (Vercel-maintained).
- Defaults: layouts and pages are **Server Components**, which "fetch data and render parts of your UI on the server", and you opt into **Client Components** (with `"use client"`) for state, event handlers and browser APIs (https://nextjs.org/docs/app/getting-started/server-and-client-components). This split (what runs where, what can cross the boundary, props must be serializable) is the main extra concept to learn.
- It can run as an SPA / static export (`output: 'export'` yields an `out` folder deployable to "any web server that can serve HTML/CSS/JS static assets", nginx example in the docs). But in a static export, these are **unsupported**: Server Actions, cookies, rewrites, redirects, headers, default image optimization, ISR, dynamic routes without `generateStaticParams()` and others (https://nextjs.org/docs/app/guides/static-exports). So the parts that make Next.js distinctive are exactly what you give up when your API is a separate service.
- If run with its server (not static), it is a second Node service in the Compose stack alongside the API.
- Learning curve: steepest of the web options.

### 3c. React Router v7 (and Remix)
- Remix history: the Remix team wrote "What we planned to release as Remix v3 is now going to be released as React Router v7", and as of their December 2024 update recommended React Router v7 for new projects (https://remix.run/blog/merging-remix-and-react-router). So "Remix" for a new project effectively means React Router v7. I did not verify anything newer.
- React Router has three additive modes (https://reactrouter.com/start/modes): **Declarative** (URL matching, links, navigation), **Data** (adds `loader`, `action`, pending states), **Framework** (wraps Data mode in a Vite plugin: type-safe routes, code splitting, "SPA, SSR, and static rendering strategies"). "Moving from Declarative to Data to Framework simply adds more features at the cost of architectural control."
- SPA in framework mode: set `ssr: false`; it still pre-renders the root route at build time to `index.html`; `react-router build` outputs `build/client` to deploy to a static host; use `clientLoader`/`clientAction` for browser-side data; a loader on any route other than root is not allowed in SPA mode unless pre-rendered (https://reactrouter.com/how-to/spa).
- Learning curve: moderate. Declarative or Data mode inside a Vite app is the gentlest on-ramp; framework mode adds conventions and a build plugin.

### 3d. Expo (React Native), including its web target
- React docs: Expo "is a React framework that lets you create universal Android, iOS, and web apps with truly native UIs."
- Expo supports web through React Native for Web (RNW), which provides `<View>`/`<Text>` that wrap DOM elements such as `<div>`/`<p>` (https://docs.expo.dev/workflow/web/). Expo recommends RNW for cross-platform projects because it "maximizes code reuse", and notes web-only DOM components "won't render on native platforms."
- Expo Router: file-based routing for Android, iOS and web with "a unified navigation structure"; static rendering (SSG) on web is supported, but "Server-side rendering currently requires custom infrastructure to set up" (https://docs.expo.dev/router/introduction/).
- Using Expo for the web front end too is possible, but it means writing the web UI in React Native primitives (no `<div>`, no HTML/CSS layout model as such). **Inference:** that suits teams wanting one UI codebase; it is a heavier, less conventional way to build a data-dense web app, and is outside the stated scope (mobile app out of scope; hooks only).

## 4. What "shared code between web and mobile" honestly means

Facts:
- React Native does not use HTML or the DOM. Components are "backed by the same views as Android and iOS": `<View>` (analogous to a non-scrolling `<div>`), `<Text>` (analogous to `<p>`), `<Image>`, `<ScrollView>`, `<TextInput>` (https://reactnative.dev/docs/intro-react-native-components). The page carries a warning that it describes a legacy API set not yet updated for the New Architecture; the component list itself is the long-standing core.
- Therefore a web component written with `<div>`, `<table>`, CSS files, etc. cannot run in React Native, and vice versa. Expo says web-only DOM components "won't render on native platforms."
- Expo supports monorepos: root `workspaces` globs (`apps/*`, `packages/*`), shared packages "don't need to be published", and since SDK 52 Metro (the React Native bundler) is configured for monorepos automatically (https://docs.expo.dev/guides/monorepos/). Known pitfalls listed there: duplicate React / React Native versions cause build or runtime errors; isolated dependency installs (SDK 54+) can break some libraries (pnpm `nodeLinker: hoisted` is the documented workaround); some native build files hardcode `node_modules` paths.
- TanStack Query "is designed to work out of the box with React Native", but online status and app focus need wiring (`onlineManager` to NetInfo/Expo Network, `focusManager` to `AppState`) because those are browser events on the web (https://tanstack.com/query/latest/docs/framework/react/react-native).

What this means in practice (**inference** built on the facts above):

| Shareable (plain TypeScript, no UI) | Not shareable |
|---|---|
| Request/response types, validation schemas, the API client | Screens, layout, markup (`<div>` vs `<View>`) |
| Domain logic: grade conversion, ascent rules from `CONTEXT.md`, formatting | Styling (CSS vs React Native style objects) |
| Data-fetching hooks (TanStack Query hooks call the API client), with small platform wiring as above | Navigation / routing libraries (React Router vs Expo Router / React Navigation) |
| Client-generated IDs, `updated_at` handling, sync rules | Browser-only APIs (`localStorage`, `window`) vs native storage and device APIs |

Rule of thumb: share what is not about the screen. This is why TypeScript end to end has value: one `Route`/`Ascent` type and validator used by the API, the web app and later the phone app.

Option to share more: Expo's RNW approach shares UI too, at the price of building the web UI out of React Native primitives. Not needed for this map.

## 5. Routing and data fetching, side by side

| | Vite + React Router + TanStack Query | Next.js | React Router framework mode | Expo Router |
|---|---|---|---|---|
| Routing | Library, you configure routes in code | Files under `app/` | Route config / files, Vite plugin | Files under `app/` |
| Data fetching | Your choice; TanStack Query handles caching, deduplication, refetching ("server state") | Server Components, Server Actions, or client libraries (SWR / TanStack Query) | `loader`/`action` (server) or `clientLoader`/`clientAction` (SPA) | Your choice (TanStack Query works) |
| Build output | Static files | Node server, or static `out` (with limits) | Node server, or static `build/client` (SPA) | Native binaries; web via static render |
| Extra concepts | Few | Server vs Client Components, caching, hydration | Loaders/actions, build-time root render | Native build tooling, platform differences |

TanStack Query (formerly React Query) rationale from its docs: server state "is persisted remotely in a location you may not control", needs asynchronous APIs, and "can be changed by others without your knowledge", so it needs caching, deduplication, background refetching and stale-data handling (https://tanstack.com/query/latest/docs/framework/react/overview).

## 6. Recommendation (for the owner to confirm, not a decision)

1. **Web: Vite + React + TypeScript, React Router in Data or Declarative mode, TanStack Query for server data.** Static files served by a small nginx container; the TypeScript API stays a separate container. Reasons: matches the already-decided separate API; one runtime to learn (browser); smallest Compose change; every piece is reusable knowledge.
2. **Keep the door open to React Router framework mode** (SPA, `ssr: false`) if you later want conventions and typed routes; it is additive over Data mode, per its docs.
3. **Choose Next.js only if** you specifically want to learn server components or expect public, indexable pages. It would add a Node service or forfeit its server features through static export.
4. **Mobile hook:** a monorepo with `apps/web`, `apps/api` and `packages/shared` (types, validators, API client, domain logic, query hooks without platform wiring). Do not build the Expo app now.
5. Pin React / TypeScript versions through one workspace to avoid the duplicate-React problem Expo warns about.

Main risks of the recommendation: you assemble the pieces yourself (React's docs call that "building your own framework"); SPAs load more JavaScript up front (Next.js docs); sharing is limited to non-UI logic.

## Unverified / not covered

- The Expo "universal apps" recommendations page and the "platform-specific code" page returned 404; Expo's web-sharing claims here rest on the web and router pages only.
- No benchmark or bundle-size data was gathered.
- Whether Remix continues as a separate project after December 2024 was not verified.
- Vite's SPA fallback behaviour on hosts was not read from Vite docs; the "rewrite to index.html" point is from React Router's SPA guide and the Next.js nginx example.
- Hosting specifics (nginx image, Compose layout) belong to other tickets.
