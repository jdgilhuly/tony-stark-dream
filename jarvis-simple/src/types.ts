export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  voiceInput?: boolean;
}

export interface Session {
  startedAt: Date;
  messages: Message[];
}

export interface ExecuteOptions {
  timeout?: number;
  cwd?: string;
}

export type VoiceState = 'idle' | 'recording' | 'transcribing' | 'speaking';
