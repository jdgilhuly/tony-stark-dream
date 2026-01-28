import { spawn } from 'node:child_process';
import type { ExecuteOptions } from '../types.js';

export class ClaudeExecutor {
  private defaultTimeout = 120000; // 2 minutes

  async execute(prompt: string, options: ExecuteOptions = {}): Promise<string> {
    const { timeout = this.defaultTimeout, cwd = process.cwd() } = options;

    return new Promise((resolve, reject) => {
      const args = ['-p', prompt, '--output-format', 'text'];

      const child = spawn('claude', args, {
        cwd,
        stdio: ['ignore', 'pipe', 'pipe'],
        env: { ...process.env },
      });

      let stdout = '';
      let stderr = '';

      child.stdout.on('data', (data) => {
        stdout += data.toString();
      });

      child.stderr.on('data', (data) => {
        stderr += data.toString();
      });

      const timeoutId = setTimeout(() => {
        child.kill('SIGTERM');
        reject(new Error(`Claude Code execution timed out after ${timeout}ms`));
      }, timeout);

      child.on('close', (code) => {
        clearTimeout(timeoutId);

        if (code === 0) {
          resolve(stdout.trim());
        } else {
          // Claude Code might output errors to stdout as well
          const errorMessage = stderr || stdout || `Process exited with code ${code}`;
          reject(new Error(errorMessage));
        }
      });

      child.on('error', (err) => {
        clearTimeout(timeoutId);
        if ((err as NodeJS.ErrnoException).code === 'ENOENT') {
          reject(new Error('Claude Code CLI not found. Please install it with: npm install -g @anthropic-ai/claude-code'));
        } else {
          reject(err);
        }
      });
    });
  }
}

export const claudeExecutor = new ClaudeExecutor();
