import { useState, useEffect, useRef, useCallback } from 'react';

export function useWebSocket({ onReportVerified }) {
  const [status, setStatus] = useState('connecting'); // 'connecting' | 'connected' | 'disconnected'
  const [lastEvent, setLastEvent] = useState(null);
  const socketRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const isMountedRef = useRef(true);

  const connect = useCallback(() => {
    if (!isMountedRef.current) return;

    try {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/ws`;
      
      setStatus('connecting');
      const ws = new WebSocket(wsUrl);
      socketRef.current = ws;

      ws.onopen = () => {
        if (!isMountedRef.current) return;
        setStatus('connected');
        console.log('[WebSocket] Connected to real-time feed');
      };

      ws.onmessage = (event) => {
        if (!isMountedRef.current) return;
        try {
          const data = JSON.parse(event.data);
          console.log('[WebSocket] Event received:', data);
          setLastEvent({
            ...data,
            receivedAt: new Date().toISOString(),
          });

          if (data.event === 'report_verified') {
            if (onReportVerified) {
              onReportVerified(data);
            }
          }
        } catch (err) {
          console.error('[WebSocket] Parse error:', err);
        }
      };

      ws.onerror = (err) => {
        console.warn('[WebSocket] Connection error:', err);
        if (ws.readyState === WebSocket.OPEN) {
          ws.close();
        }
      };

      ws.onclose = () => {
        if (!isMountedRef.current) return;
        setStatus('disconnected');
        console.log('[WebSocket] Disconnected. Reconnecting in 3s...');
        reconnectTimeoutRef.current = setTimeout(() => {
          connect();
        }, 3000);
      };
    } catch (err) {
      console.error('[WebSocket] Setup error:', err);
      setStatus('disconnected');
      reconnectTimeoutRef.current = setTimeout(() => {
        connect();
      }, 3000);
    }
  }, [onReportVerified]);

  useEffect(() => {
    isMountedRef.current = true;
    connect();

    return () => {
      isMountedRef.current = false;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (socketRef.current) {
        socketRef.current.close();
      }
    };
  }, [connect]);

  return {
    status,
    isConnected: status === 'connected',
    lastEvent,
  };
}
