import { io } from "socket.io-client";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

export function createCollabSocket(token) {
    return io(API_BASE, {
        transports: ["websocket"],
        auth: { token },
    });
}