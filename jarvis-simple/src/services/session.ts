import { readFile, writeFile, unlink, access } from 'node:fs/promises';
import { join } from 'node:path';
import type { Session, Message } from '../types.js';
import { nanoid } from 'nanoid';

const SESSION_FILE = '.jarvis-session.md';

export class SessionManager {
  private filePath: string;
  private session: Session;

  constructor(cwd: string = process.cwd()) {
    this.filePath = join(cwd, SESSION_FILE);
    this.session = {
      startedAt: new Date(),
      messages: [],
    };
  }

  async load(): Promise<Session | null> {
    try {
      await access(this.filePath);
      const content = await readFile(this.filePath, 'utf-8');
      const parsed = this.parseMarkdown(content);
      if (parsed) {
        this.session = parsed;
        return this.session;
      }
    } catch {
      // File doesn't exist or is invalid
    }
    return null;
  }

  private parseMarkdown(content: string): Session | null {
    try {
      const lines = content.split('\n');
      const messages: Message[] = [];
      let startedAt = new Date();

      // Parse header
      const startedMatch = content.match(/Started: (.+)/);
      if (startedMatch) {
        startedAt = new Date(startedMatch[1]);
      }

      // Parse messages (format: ## HH:MM:SS - Role)
      const messageBlocks = content.split(/\n---\n/).slice(1);

      for (const block of messageBlocks) {
        const headerMatch = block.match(/## (\d{2}:\d{2}:\d{2}) - (User|JARVIS)/);
        if (headerMatch) {
          const [, time, role] = headerMatch;
          const contentStart = block.indexOf('\n', block.indexOf(headerMatch[0])) + 1;
          const messageContent = block.slice(contentStart).trim();

          if (messageContent) {
            messages.push({
              id: nanoid(),
              role: role === 'User' ? 'user' : 'assistant',
              content: messageContent,
              timestamp: new Date(`${startedAt.toDateString()} ${time}`),
            });
          }
        }
      }

      return { startedAt, messages };
    } catch {
      return null;
    }
  }

  async save(): Promise<void> {
    const content = this.toMarkdown();
    await writeFile(this.filePath, content, 'utf-8');
  }

  private toMarkdown(): string {
    const formatTime = (date: Date) =>
      date.toTimeString().split(' ')[0];

    const formatDate = (date: Date) =>
      date.toISOString().replace('T', ' ').split('.')[0];

    let md = `# JARVIS Session\nStarted: ${formatDate(this.session.startedAt)}\n`;

    for (const msg of this.session.messages) {
      const speaker = msg.role === 'user' ? 'User' : 'JARVIS';
      md += `\n---\n\n## ${formatTime(msg.timestamp)} - ${speaker}\n${msg.content}\n`;
    }

    return md;
  }

  addMessage(role: 'user' | 'assistant', content: string, voiceInput = false): Message {
    const message: Message = {
      id: nanoid(),
      role,
      content,
      timestamp: new Date(),
      voiceInput,
    };
    this.session.messages.push(message);
    return message;
  }

  getContextMessages(count: number = 10): { role: string; content: string }[] {
    const recent = this.session.messages.slice(-count);
    return recent.map((m) => ({
      role: m.role,
      content: m.content,
    }));
  }

  getMessages(): Message[] {
    return [...this.session.messages];
  }

  async clear(): Promise<void> {
    try {
      await unlink(this.filePath);
    } catch {
      // File might not exist
    }
    this.session = {
      startedAt: new Date(),
      messages: [],
    };
  }

  getSession(): Session {
    return this.session;
  }
}
