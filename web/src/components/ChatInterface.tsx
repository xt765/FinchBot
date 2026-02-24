import { useState, useEffect, useRef } from 'react';
import { Send, AlertCircle, Loader2, MessageSquare } from 'lucide-react';
import { useWebSocket } from '../hooks/useWebSocket';
import { MessageBubble } from './MessageBubble';
import { cn } from '../lib/utils';

export function ChatInterface() {
  const [clientId, setClientId] = useState<string>('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [inputValue, setInputValue] = useState('');
  
  // Generate or retrieve client ID
  useEffect(() => {
    let storedId = localStorage.getItem('finchbot_client_id');
    if (!storedId) {
      storedId = crypto.randomUUID();
      localStorage.setItem('finchbot_client_id', storedId);
    }
    setClientId(storedId);
  }, []);

  const wsUrl = clientId ? `ws://localhost:8000/ws/chat/${clientId}` : '';
  const { status, messages, sendMessage } = useWebSocket(wsUrl);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = () => {
    if (!inputValue.trim() || status !== 'connected') return;
    sendMessage(inputValue);
    setInputValue('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-full bg-gray-900 w-full relative">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-800 bg-gray-900/50 backdrop-blur-sm z-10 sticky top-0">
        <div className="flex items-center gap-2">
          <div className={cn(
            "w-2 h-2 rounded-full",
            status === 'connected' ? "bg-green-500" :
            status === 'connecting' ? "bg-yellow-500" : "bg-red-500"
          )} />
          <span className="text-sm font-medium text-gray-300">
            {status === 'connected' ? 'Connected' :
             status === 'connecting' ? 'Connecting...' : 'Disconnected'}
          </span>
        </div>
        <div className="text-xs text-gray-500">
          Client ID: {clientId.slice(0, 8)}...
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-thin scrollbar-thumb-gray-700 scrollbar-track-transparent">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-gray-500 gap-2 opacity-50">
            <MessageSquare className="w-12 h-12" />
            <p>Start a conversation...</p>
          </div>
        ) : (
          messages.map((msg) => (
            <MessageBubble 
              key={msg.id} 
              sender={msg.sender} 
              content={msg.content} 
              timestamp={msg.timestamp} 
            />
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="p-4 border-t border-gray-800 bg-gray-900">
        <div className="relative flex items-center bg-gray-800 rounded-lg border border-gray-700 focus-within:ring-2 focus-within:ring-blue-500 focus-within:border-transparent transition-all">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type a message..."
            className="flex-1 bg-transparent border-none outline-none text-gray-100 placeholder-gray-400 px-4 py-3"
            disabled={status !== 'connected'}
          />
          <button
            onClick={handleSend}
            disabled={!inputValue.trim() || status !== 'connected'}
            className="p-2 mr-2 text-gray-400 hover:text-blue-500 disabled:opacity-50 disabled:hover:text-gray-400 transition-colors"
          >
            {status === 'connecting' ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </button>
        </div>
        {status === 'error' && (
          <div className="mt-2 text-xs text-red-400 flex items-center gap-1">
            <AlertCircle className="w-3 h-3" />
            Connection error. Retrying...
          </div>
        )}
      </div>
    </div>
  );
}
