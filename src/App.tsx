import Chat from './Chat.tsx'

export default function App() {
  return (
    <div className="max-w-4xl mx-auto p-6 relative size-full h-screen">
      <div className="flex flex-col h-full">
        <h1 className="scroll-m-20 text-2xl lg:text-3xl">Pydantic AI Chat</h1>
        <Chat />
      </div>
    </div>
  )
}
