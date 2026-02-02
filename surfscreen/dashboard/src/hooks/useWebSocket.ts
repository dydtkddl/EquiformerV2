'use client';

import { useEffect, useRef, useState, useCallback } from 'react';

export type WebSocketStatus = 'connecting' | 'connected' | 'disconnected' | 'error';

interface WebSocketMessage<T = unknown> {
  type: string;
  data: T;
  timestamp?: string;
}

interface UseWebSocketOptions {
  /** WebSocket server URL */
  url: string;
  /** Auto-connect on mount */
  autoConnect?: boolean;
  /** Reconnect on disconnect */
  autoReconnect?: boolean;
  /** Reconnect interval in ms */
  reconnectInterval?: number;
  /** Max reconnect attempts */
  maxReconnectAttempts?: number;
  /** Heartbeat interval in ms (0 to disable) */
  heartbeatInterval?: number;
  /** On open callback */
  onOpen?: () => void;
  /** On close callback */
  onClose?: () => void;
  /** On error callback */
  onError?: (error: Event) => void;
  /** On message callback */
  onMessage?: (message: WebSocketMessage) => void;
}

interface UseWebSocketReturn {
  /** Current connection status */
  status: WebSocketStatus;
  /** Whether the connection is open */
  isConnected: boolean;
  /** Last received message */
  lastMessage: WebSocketMessage | null;
  /** Send a message */
  sendMessage: <T = unknown>(type: string, data: T) => boolean;
  /** Connect to the server */
  connect: () => void;
  /** Disconnect from the server */
  disconnect: () => void;
  /** Reconnect attempts count */
  reconnectAttempts: number;
}

export function useWebSocket(options: UseWebSocketOptions): UseWebSocketReturn {
  const {
    url,
    autoConnect = true,
    autoReconnect = true,
    reconnectInterval = 3000,
    maxReconnectAttempts = 10,
    heartbeatInterval = 30000,
    onOpen,
    onClose,
    onError,
    onMessage,
  } = options;

  const [status, setStatus] = useState<WebSocketStatus>('disconnected');
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const [reconnectAttempts, setReconnectAttempts] = useState(0);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const heartbeatIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const shouldReconnectRef = useRef(autoReconnect);

  // Cleanup function
  const cleanup = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current);
      heartbeatIntervalRef.current = null;
    }
  }, []);

  // Connect function
  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    cleanup();
    setStatus('connecting');

    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        setStatus('connected');
        setReconnectAttempts(0);
        onOpen?.();

        // Start heartbeat
        if (heartbeatInterval > 0) {
          heartbeatIntervalRef.current = setInterval(() => {
            if (ws.readyState === WebSocket.OPEN) {
              ws.send(JSON.stringify({ type: 'ping', data: null }));
            }
          }, heartbeatInterval);
        }
      };

      ws.onclose = () => {
        setStatus('disconnected');
        cleanup();
        onClose?.();

        // Auto-reconnect logic
        if (shouldReconnectRef.current && reconnectAttempts < maxReconnectAttempts) {
          reconnectTimeoutRef.current = setTimeout(() => {
            setReconnectAttempts((prev) => prev + 1);
            connect();
          }, reconnectInterval);
        }
      };

      ws.onerror = (error) => {
        setStatus('error');
        onError?.(error);
      };

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          
          // Ignore pong messages
          if (message.type === 'pong') {
            return;
          }

          setLastMessage({
            ...message,
            timestamp: message.timestamp || new Date().toISOString(),
          });
          onMessage?.(message);
        } catch (err) {
          console.error('Failed to parse WebSocket message:', err);
        }
      };
    } catch (err) {
      console.error('Failed to create WebSocket connection:', err);
      setStatus('error');
    }
  }, [
    url,
    heartbeatInterval,
    maxReconnectAttempts,
    reconnectInterval,
    reconnectAttempts,
    cleanup,
    onOpen,
    onClose,
    onError,
    onMessage,
  ]);

  // Disconnect function
  const disconnect = useCallback(() => {
    shouldReconnectRef.current = false;
    cleanup();

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    setStatus('disconnected');
  }, [cleanup]);

  // Send message function
  const sendMessage = useCallback(<T = unknown>(type: string, data: T): boolean => {
    if (wsRef.current?.readyState !== WebSocket.OPEN) {
      console.warn('WebSocket is not connected');
      return false;
    }

    try {
      const message: WebSocketMessage<T> = {
        type,
        data,
        timestamp: new Date().toISOString(),
      };
      wsRef.current.send(JSON.stringify(message));
      return true;
    } catch (err) {
      console.error('Failed to send WebSocket message:', err);
      return false;
    }
  }, []);

  // Auto-connect on mount
  useEffect(() => {
    shouldReconnectRef.current = autoReconnect;

    if (autoConnect) {
      connect();
    }

    return () => {
      shouldReconnectRef.current = false;
      disconnect();
    };
  }, [autoConnect, autoReconnect, connect, disconnect]);

  return {
    status,
    isConnected: status === 'connected',
    lastMessage,
    sendMessage,
    connect,
    disconnect,
    reconnectAttempts,
  };
}

// Type-specific hooks for common use cases
export interface JobUpdateMessage {
  job_id: string;
  status: string;
  progress?: number;
  result?: unknown;
}

export function useJobUpdates(
  wsUrl: string,
  onJobUpdate?: (job: JobUpdateMessage) => void
) {
  return useWebSocket({
    url: wsUrl,
    onMessage: (msg) => {
      if (msg.type === 'job.update' && onJobUpdate) {
        onJobUpdate(msg.data as JobUpdateMessage);
      }
    },
  });
}

export default useWebSocket;
