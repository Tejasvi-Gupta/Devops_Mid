# LabGrid frontend

LabGrid is the React/Vite web interface for the Environment Provisioning Platform. It provides separate, responsive workspaces for students and instructors while keeping provisioning approvals and device trust visible.

## Development

From this directory:

```powershell
npm install
npm run dev
```

The interface uses the existing `/api` proxy and backend contracts. Validate changes with:

```powershell
npm run lint
npm test
npm run build
```

The visual system is defined in `src/index.css` and shared layout/status primitives live in `src/ui.jsx`. Keep new screens role-aware, keyboard accessible, and explicit about loading, empty, error, and destructive states.
