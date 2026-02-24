import { useState } from 'react';
import { Sidebar } from './components/Sidebar';
import { ChatInterface } from './components/ChatInterface';

function App() {
  const [selectedChannelId, setSelectedChannelId] = useState('1');

  return (
    <div className="flex h-screen w-full bg-gray-950 text-white overflow-hidden">
      <Sidebar 
        selectedChannelId={selectedChannelId} 
        onSelectChannel={setSelectedChannelId} 
      />
      <main className="flex-1 flex flex-col h-full relative">
        <ChatInterface />
      </main>
    </div>
  );
}

export default App;
