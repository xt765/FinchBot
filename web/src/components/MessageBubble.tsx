import { cn } from '../lib/utils';
import { User, Bot } from 'lucide-react';

interface MessageBubbleProps {
  sender: 'user' | 'bot';
  content: string;
  timestamp: number;
}

export function MessageBubble({ sender, content, timestamp }: MessageBubbleProps) {
  const isUser = sender === 'user';
  
  return (
    <div className={cn(
      "flex w-full mb-4",
      isUser ? "justify-end" : "justify-start"
    )}>
      <div className={cn(
        "flex max-w-[80%] gap-2",
        isUser ? "flex-row-reverse" : "flex-row"
      )}>
        <div className={cn(
          "w-8 h-8 rounded-full flex items-center justify-center shrink-0",
          isUser ? "bg-blue-600" : "bg-purple-600"
        )}>
          {isUser ? <User size={16} className="text-white" /> : <Bot size={16} className="text-white" />}
        </div>
        
        <div className={cn(
          "p-3 rounded-lg text-sm leading-relaxed shadow-sm",
          isUser 
            ? "bg-blue-600 text-white rounded-tr-none" 
            : "bg-gray-800 text-gray-100 rounded-tl-none border border-gray-700"
        )}>
          <div className="whitespace-pre-wrap">{content}</div>
          <div className={cn(
            "text-[10px] mt-1 opacity-70",
            isUser ? "text-blue-100" : "text-gray-400"
          )}>
            {new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </div>
        </div>
      </div>
    </div>
  );
}
