// ==========================
// FILE: src/lib/useApiState.js
// ==========================
// Simple React helpers for loading/error states

import { useCallback, useState } from "react";

export function useAsync() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const run = useCallback(async (fn) => {
    setLoading(true); setError(null);
    try { return await fn(); }
    catch (e) { setError(e); throw e; }
    finally { setLoading(false); }
  }, []);
  return { loading, error, run };
}