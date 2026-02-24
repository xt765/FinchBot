import { MessageSquare, Hash, Settings, Plus, LayoutDashboard } from 'lucide-react';
import { cn } from '../lib/utils';

interface Channel {
  id: string;
  name: string;
  type: 'discord' | 'feishu' | 'wechat' | 'general';
  icon?: React.ReactNode;
}

const mockChannels: Channel[] = [
  { id: '1', name: 'General', type: 'general' },
  { id: '2', name: 'Discord Bot', type: 'discord' },
  { id: '3', name: 'Feishu Notifications', type: 'feishu' },
];

interface SidebarProps {
  className?: string;
  selectedChannelId?: string;
  onSelectChannel: (id: string) => void;
}

export function Sidebar({ className, selectedChannelId, onSelectChannel }: SidebarProps) {
  return (
    <div className={cn("flex flex-col h-full bg-gray-900 text-gray-300 w-64 border-r border-gray-800", className)}>
      <div className="p-4 border-b border-gray-800 flex items-center gap-2">
        <LayoutDashboard className="w-6 h-6 text-blue-500" />
        <h1 className="font-bold text-xl text-white">FinchBot</h1>
      </div>

      <div className="flex-1 overflow-y-auto py-4">
        <div className="px-4 mb-2 text-xs font-semibold text-gray-500 uppercase tracking-wider">
          Channels
        </div>
        <div className="space-y-1 px-2">
          {mockChannels.map((channel) => (
            <button
              key={channel.id}
              onClick={() => onSelectChannel(channel.id)}
              className={cn(
                "w-full flex items-center gap-3 px-3 py-2 rounded-md transition-colors text-sm",
                selectedChannelId === channel.id
                  ? "bg-gray-800 text-white"
                  : "hover:bg-gray-800/50 hover:text-white"
              )}
            >
              {channel.type === 'discord' ? (
                <MessageSquare className="w-4 h-4" />
              ) : channel.type === 'feishu' ? (
                <MessageSquare className="w-4 h-4 text-green-500" />
              ) : (
                <Hash className="w-4 h-4" />
              )}
              <span>{channel.name}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="p-4 border-t border-gray-800">
        <button className="flex items-center gap-3 w-full px-3 py-2 rounded-md hover:bg-gray-800 transition-colors text-sm text-gray-400 hover:text-white">
          <Plus className="w-4 h-4" />
          <span>Add Channel</span>
        </button>
        <button className="flex items-center gap-3 w-full px-3 py-2 rounded-md hover:bg-gray-800 transition-colors text-sm text-gray-400 hover:text-white mt-1">
          <Settings className="w-4 h-4" />
          <span>Settings</span>
        </button>
      </div>
    </div>
  );
}
