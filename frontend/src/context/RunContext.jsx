import { createContext, useCallback, useContext, useMemo, useState } from "react";
import { getRun, startRun } from "../utils/api";

const RunContext = createContext(null);

export function RunProvider({ children }) {
  const [runData, setRunData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const runAgent = useCallback(async (payload) => {
    setError("");
    setIsLoading(true);
    try {
      const started = await startRun(payload);
      let finished = false;
      while (!finished) {
        const details = await getRun(started.run_id);
        setRunData(details);
        finished = details.status === "PASSED" || details.status === "FAILED";
        if (!finished) {
          await new Promise((resolve) => setTimeout(resolve, 2500));
        }
      }
    } catch (err) {
      setError(err.message || "Unexpected error while running agent.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  const value = useMemo(
    () => ({
      runData,
      isLoading,
      error,
      runAgent
    }),
    [runData, isLoading, error, runAgent]
  );

  return <RunContext.Provider value={value}>{children}</RunContext.Provider>;
}

export function useRunContext() {
  const context = useContext(RunContext);
  if (!context) {
    throw new Error("useRunContext must be used inside RunProvider.");
  }
  return context;
}
