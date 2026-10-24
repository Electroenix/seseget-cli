import { useEffect, useRef } from "react";
import { io, Socket } from "socket.io-client";
import type { DownloadTask } from "../types/api";

// 使用同源连接：生产环境直连当前服务，开发环境由 Vite 代理 /socket.io 到 12450
const TOKEN_KEY = "seseget_auth_token";

function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function useDownloadSocket(
  onData: (tasks: DownloadTask[]) => void,
  onFinished?: () => void
) {
  const socketRef = useRef<Socket | null>(null);
  const onDataRef = useRef(onData);
  const onFinishedRef = useRef(onFinished);

  useEffect(() => {
    onDataRef.current = onData;
    onFinishedRef.current = onFinished;
  }, [onData, onFinished]);

  useEffect(() => {
    const socket = io(window.location.origin, {
      transports: ["polling", "websocket"],
      auth: { token: getToken() ?? "" },
    });
    socketRef.current = socket;

    socket.on("connect", () => {
      console.log("Socket.IO connected:", socket.id);
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

    socket.on("disconnect", (reason) => {
      console.log("Socket.IO disconnected:", reason);
    });

    return () => {
      socket.disconnect();
      socketRef.current = null;
    };
  }, []);

  return socketRef;
}
