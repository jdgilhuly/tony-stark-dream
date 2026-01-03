import SQLite, { SQLiteDatabase } from 'react-native-sqlite-storage';

// Enable promises
SQLite.enablePromise(true);

const DATABASE_NAME = 'jarvis.db';
const DATABASE_VERSION = 1;

interface Message {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  synced: boolean;
}

interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  synced: boolean;
}

interface CachedBriefing {
  id: string;
  date: string;
  data: string;
  created_at: string;
}

class SQLiteStorage {
  private db: SQLiteDatabase | null = null;

  async initialize(): Promise<void> {
    try {
      this.db = await SQLite.openDatabase({
        name: DATABASE_NAME,
        location: 'default',
      });

      await this.createTables();
      console.log('SQLite database initialized');
    } catch (error) {
      console.error('Failed to initialize SQLite:', error);
      throw error;
    }
  }

  private async createTables(): Promise<void> {
    if (!this.db) throw new Error('Database not initialized');

    // Conversations table
    await this.db.executeSql(`
      CREATE TABLE IF NOT EXISTS conversations (
        id TEXT PRIMARY KEY,
        title TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        synced INTEGER DEFAULT 0
      )
    `);

    // Messages table
    await this.db.executeSql(`
      CREATE TABLE IF NOT EXISTS messages (
        id TEXT PRIMARY KEY,
        conversation_id TEXT NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        synced INTEGER DEFAULT 0,
        FOREIGN KEY (conversation_id) REFERENCES conversations(id)
      )
    `);

    // Briefings cache table
    await this.db.executeSql(`
      CREATE TABLE IF NOT EXISTS briefings_cache (
        id TEXT PRIMARY KEY,
        date TEXT NOT NULL UNIQUE,
        data TEXT NOT NULL,
        created_at TEXT NOT NULL
      )
    `);

    // Pending sync queue
    await this.db.executeSql(`
      CREATE TABLE IF NOT EXISTS sync_queue (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT NOT NULL,
        payload TEXT NOT NULL,
        created_at TEXT NOT NULL,
        retries INTEGER DEFAULT 0
      )
    `);

    // Create indexes
    await this.db.executeSql(`
      CREATE INDEX IF NOT EXISTS idx_messages_conversation
      ON messages(conversation_id)
    `);

    await this.db.executeSql(`
      CREATE INDEX IF NOT EXISTS idx_messages_synced
      ON messages(synced)
    `);
  }

  // Conversation methods
  async saveConversation(conversation: Conversation): Promise<void> {
    if (!this.db) throw new Error('Database not initialized');

    await this.db.executeSql(
      `INSERT OR REPLACE INTO conversations (id, title, created_at, updated_at, synced)
       VALUES (?, ?, ?, ?, ?)`,
      [
        conversation.id,
        conversation.title,
        conversation.created_at,
        conversation.updated_at,
        conversation.synced ? 1 : 0,
      ]
    );
  }

  async getConversation(id: string): Promise<Conversation | null> {
    if (!this.db) throw new Error('Database not initialized');

    const [results] = await this.db.executeSql(
      'SELECT * FROM conversations WHERE id = ?',
      [id]
    );

    if (results.rows.length === 0) return null;

    const row = results.rows.item(0);
    return {
      id: row.id,
      title: row.title,
      created_at: row.created_at,
      updated_at: row.updated_at,
      synced: row.synced === 1,
    };
  }

  async getAllConversations(): Promise<Conversation[]> {
    if (!this.db) throw new Error('Database not initialized');

    const [results] = await this.db.executeSql(
      'SELECT * FROM conversations ORDER BY updated_at DESC'
    );

    const conversations: Conversation[] = [];
    for (let i = 0; i < results.rows.length; i++) {
      const row = results.rows.item(i);
      conversations.push({
        id: row.id,
        title: row.title,
        created_at: row.created_at,
        updated_at: row.updated_at,
        synced: row.synced === 1,
      });
    }

    return conversations;
  }

  // Message methods
  async saveMessage(message: Message): Promise<void> {
    if (!this.db) throw new Error('Database not initialized');

    await this.db.executeSql(
      `INSERT OR REPLACE INTO messages (id, conversation_id, role, content, timestamp, synced)
       VALUES (?, ?, ?, ?, ?, ?)`,
      [
        message.id,
        message.conversation_id,
        message.role,
        message.content,
        message.timestamp,
        message.synced ? 1 : 0,
      ]
    );
  }

  async getMessages(conversationId: string): Promise<Message[]> {
    if (!this.db) throw new Error('Database not initialized');

    const [results] = await this.db.executeSql(
      'SELECT * FROM messages WHERE conversation_id = ? ORDER BY timestamp ASC',
      [conversationId]
    );

    const messages: Message[] = [];
    for (let i = 0; i < results.rows.length; i++) {
      const row = results.rows.item(i);
      messages.push({
        id: row.id,
        conversation_id: row.conversation_id,
        role: row.role,
        content: row.content,
        timestamp: row.timestamp,
        synced: row.synced === 1,
      });
    }

    return messages;
  }

  async getUnsyncedMessages(): Promise<Message[]> {
    if (!this.db) throw new Error('Database not initialized');

    const [results] = await this.db.executeSql(
      'SELECT * FROM messages WHERE synced = 0 ORDER BY timestamp ASC'
    );

    const messages: Message[] = [];
    for (let i = 0; i < results.rows.length; i++) {
      const row = results.rows.item(i);
      messages.push({
        id: row.id,
        conversation_id: row.conversation_id,
        role: row.role,
        content: row.content,
        timestamp: row.timestamp,
        synced: false,
      });
    }

    return messages;
  }

  async markMessageSynced(id: string): Promise<void> {
    if (!this.db) throw new Error('Database not initialized');

    await this.db.executeSql(
      'UPDATE messages SET synced = 1 WHERE id = ?',
      [id]
    );
  }

  // Briefing cache methods
  async saveBriefingCache(date: string, data: object): Promise<void> {
    if (!this.db) throw new Error('Database not initialized');

    const id = `briefing-${date}`;
    const now = new Date().toISOString();

    await this.db.executeSql(
      `INSERT OR REPLACE INTO briefings_cache (id, date, data, created_at)
       VALUES (?, ?, ?, ?)`,
      [id, date, JSON.stringify(data), now]
    );
  }

  async getBriefingCache(date: string): Promise<object | null> {
    if (!this.db) throw new Error('Database not initialized');

    const [results] = await this.db.executeSql(
      'SELECT * FROM briefings_cache WHERE date = ?',
      [date]
    );

    if (results.rows.length === 0) return null;

    const row = results.rows.item(0);
    return JSON.parse(row.data);
  }

  async clearOldBriefings(daysToKeep: number = 7): Promise<void> {
    if (!this.db) throw new Error('Database not initialized');

    const cutoffDate = new Date();
    cutoffDate.setDate(cutoffDate.getDate() - daysToKeep);

    await this.db.executeSql(
      'DELETE FROM briefings_cache WHERE created_at < ?',
      [cutoffDate.toISOString()]
    );
  }

  // Sync queue methods
  async addToSyncQueue(type: string, payload: object): Promise<void> {
    if (!this.db) throw new Error('Database not initialized');

    await this.db.executeSql(
      `INSERT INTO sync_queue (type, payload, created_at)
       VALUES (?, ?, ?)`,
      [type, JSON.stringify(payload), new Date().toISOString()]
    );
  }

  async getSyncQueue(): Promise<Array<{ id: number; type: string; payload: object }>> {
    if (!this.db) throw new Error('Database not initialized');

    const [results] = await this.db.executeSql(
      'SELECT * FROM sync_queue ORDER BY created_at ASC'
    );

    const items: Array<{ id: number; type: string; payload: object }> = [];
    for (let i = 0; i < results.rows.length; i++) {
      const row = results.rows.item(i);
      items.push({
        id: row.id,
        type: row.type,
        payload: JSON.parse(row.payload),
      });
    }

    return items;
  }

  async removeFromSyncQueue(id: number): Promise<void> {
    if (!this.db) throw new Error('Database not initialized');

    await this.db.executeSql('DELETE FROM sync_queue WHERE id = ?', [id]);
  }

  // Utility methods
  async clearAll(): Promise<void> {
    if (!this.db) throw new Error('Database not initialized');

    await this.db.executeSql('DELETE FROM messages');
    await this.db.executeSql('DELETE FROM conversations');
    await this.db.executeSql('DELETE FROM briefings_cache');
    await this.db.executeSql('DELETE FROM sync_queue');
  }

  async close(): Promise<void> {
    if (this.db) {
      await this.db.close();
      this.db = null;
    }
  }
}

// Singleton instance
export const sqliteStorage = new SQLiteStorage();
