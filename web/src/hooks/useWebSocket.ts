import { useEffect, useRef, useState, useCallback } from 'react';

export type WebSocketStatus = 'connecting' | 'connected' | 'disconnected' | 'error';

export interface ChatMessage {
  id: string;
  sender: 'user' | 'bot';
  content: string;
  timestamp: number;
}

export function useWebSocket(url: string) {
  const [status, setStatus] = useState<WebSocketStatus>('disconnected');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    // Only connect if url is provided
    if (!url) return;

    setStatus('connecting');
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setStatus('connected');
      console.log('WebSocket connected');
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        // Assuming the backend sends structured messages, otherwise handle plain text
        // If backend sends plain text, wrap it.
        // For now, let's assume simple string or JSON.
        // If the data structure is different, we adapt here.
        // Let's assume the backend sends just the text response for now based on common patterns,
        // or maybe a JSON with { type: 'message', content: '...' }
        
        // If it's a string, treat as message content
        const content = typeof data === 'string' ? data : (data.content || JSON.stringify(data));
        
        setMessages((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            sender: 'bot',
            content: content,
            timestamp: Date.now(),
          },
        ]);
      } catch (e) {
        // Fallback for non-JSON messages
        setMessages((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            sender: 'bot',
            content: event.data,
            timestamp: Date.now(),
          },
        ]);
      }
    };

    ws.onclose = () => {
      setStatus('disconnected');
      console.log('WebSocket disconnected');
    };

    ws.onerror = (error) => {
      setStatus('error');
      console.error('WebSocket error:', error);
    };

    return () => {
      if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
        ws.close();
      }
    };
  }, [url]);

  const sendMessage = useCallback((content: string) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(content);
      // Optimistically add user message
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          sender: 'user',
          content,
          timestamp: Date.now(),
        },
      ]);
    } else {
      console.warn('WebSocket is not connected');
    }
  }, []);

  return { status, messages, sendMessage, setMessages };
}
