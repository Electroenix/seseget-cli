import { useEffect, useRef } from "react";
import { io } from "socket.io-client";
import type { DownloadTask } from "../types/api";

// 使用同源连接：生产环境直连当前服务，开发环境由 Vite 代理 /socket.io 到 12450
export function useDownloadSocket(
  token: string | null,
  onData: (tasks: DownloadTask[]) => void,
  onFinished?: () => void
) {
  const onDataRef = useRef(onData);
  const onFinishedRef = useRef(onFinished);

  useEffect(() => {
    onDataRef.current = onData;
    onFinishedRef.current = onFinished;
  }, [onData, onFinished]);

  useEffect(() => {
    const socket = io(window.location.origin, {
      transports: ["polling", "websocket"],
      auth: { token: token ?? "" },
    });
    socket.on("connect_error", (err) => {
      console.error("Socket.IO connect error:", err.message);
    });

    socket.on("download_status", (data: DownloadTask[]) => {
      onDataRef.current(data);
    });

    socket.on("download_finished", () => {
      onFinishedRef.current?.();
    });

    return () => {
      socket.disconnect();
    };
  }, [token]);
}
