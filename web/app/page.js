"use client";

import { useState, useRef } from "react";

const WS_BASE_URL = "ws://127.0.0.1:8000/ws/audio/";

export default function Home() {
  const [status, setStatus] = useState("disconnected");
  const [amplitude, setAmplitude] = useState(0);
  const [isStreaming, setIsStreaming] = useState(false);

  const audioContextRef = useRef(null);
  const workletNodeRef = useRef(null);
  const sourceRef = useRef(null);
  const streamRef = useRef(null);
  const wsRef = useRef(null);

  const start = async () => {
    setStatus("connecting");

    const clientId = crypto.randomUUID();
    const ws = new WebSocket(WS_BASE_URL + clientId);
    wsRef.current = ws;

    ws.onopen = () => setStatus("connected");
    ws.onclose = () => setStatus("disconnected");
    ws.onerror = () => setStatus("error");

    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    streamRef.current = stream;

    const audioContext = new AudioContext();
    audioContextRef.current = audioContext;
    await audioContext.audioWorklet.addModule("/worklets/pcm-processor.js");

    const source = audioContext.createMediaStreamSource(stream);
    sourceRef.current = source;

    const workletNode = new AudioWorkletNode(audioContext, "pcm-processor");
    workletNodeRef.current = workletNode;

    workletNode.port.onmessage = (event) => {
      const { pcm, rms } = event.data;
      setAmplitude(rms);
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(pcm);
      }
    };

    source.connect(workletNode);
    setIsStreaming(true);
  };

  const stop = () => {
    workletNodeRef.current?.disconnect();
    sourceRef.current?.disconnect();
    audioContextRef.current?.close();
    streamRef.current?.getTracks().forEach((track) => track.stop());
    wsRef.current?.close();
    setIsStreaming(false);
    setStatus("disconnected");
    setAmplitude(0);
  };

  const statusColor =
    status === "connected" ? "#2e7d32" : status === "error" ? "#c62828" : "#666";

  return (
    <main style={{ padding: 40, fontFamily: "sans-serif", maxWidth: 480 }}>
      <h1>Voice Pipeline — Mic Dashboard</h1>

      <p>
        Connection status: <strong style={{ color: statusColor }}>{status}</strong>
      </p>

      <div style={{ marginBottom: 20 }}>
        <button onClick={start} disabled={isStreaming} style={{ marginRight: 10 }}>
          Start Streaming
        </button>
        <button onClick={stop} disabled={!isStreaming}>
          Stop Streaming
        </button>
      </div>

      <p>Live amplitude:</p>
      <div style={{ width: "100%", height: 24, background: "#eee", borderRadius: 4 }}>
        <div
          style={{
            height: "100%",
            width: `${Math.min(amplitude * 400, 100)}%`,
            background: "#4caf50",
            borderRadius: 4,
            transition: "width 50ms linear",
          }}
        />
      </div>
    </main>
  );
}