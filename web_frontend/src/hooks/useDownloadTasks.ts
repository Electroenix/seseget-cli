import { useCallback, useState } from "react";
import type { DownloadTask } from "../types/api";
import { useAuth } from "../contexts/AuthContext";
import { useDownloadSocket } from "./useSocket";

export function useDownloadTasks() {
  const { token } = useAuth();
  const [tasks, setTasks] = useState<DownloadTask[]>([]);
  const [historyVersion, setHistoryVersion] = useState(0);

  const handleFinished = useCallback(() => {
    setHistoryVersion((value) => value + 1);
  }, []);

  useDownloadSocket(token, setTasks, handleFinished);

  return { tasks, historyVersion };
}
