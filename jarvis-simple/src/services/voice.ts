import { spawn, exec } from 'node:child_process';
import { writeFile, unlink } from 'node:fs/promises';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { promisify } from 'node:util';

const execAsync = promisify(exec);

export class VoiceService {
  private recording: ReturnType<typeof spawn> | null = null;
  private audioChunks: Buffer[] = [];
  private isRecording = false;

  async startRecording(): Promise<void> {
    if (this.isRecording) return;

    this.audioChunks = [];
    this.isRecording = true;

    // Use sox for cross-platform audio recording
    // Falls back to arecord on Linux, rec on macOS
    const platform = process.platform;
    let cmd: string;
    let args: string[];

    if (platform === 'darwin') {
      // macOS - use sox/rec
      cmd = 'rec';
      args = ['-q', '-t', 'wav', '-r', '16000', '-c', '1', '-'];
    } else {
      // Linux - use arecord
      cmd = 'arecord';
      args = ['-q', '-f', 'S16_LE', '-r', '16000', '-c', '1', '-t', 'wav', '-'];
    }

    this.recording = spawn(cmd, args, {
      stdio: ['ignore', 'pipe', 'ignore'],
    });

    this.recording.stdout?.on('data', (chunk) => {
      this.audioChunks.push(chunk);
    });

    this.recording.on('error', (err) => {
      console.error('Recording error:', err.message);
      this.isRecording = false;
    });
  }

  async stopRecording(): Promise<Buffer> {
    return new Promise((resolve) => {
      if (!this.recording || !this.isRecording) {
        resolve(Buffer.concat(this.audioChunks));
        return;
      }

      this.recording.on('close', () => {
        this.isRecording = false;
        resolve(Buffer.concat(this.audioChunks));
      });

      this.recording.kill('SIGTERM');
      this.recording = null;
    });
  }

  async transcribe(audio: Buffer): Promise<string> {
    // Save audio to temp file
    const tempFile = join(tmpdir(), `jarvis-audio-${Date.now()}.wav`);

    try {
      await writeFile(tempFile, audio);

      // Use whisper CLI (whisper.cpp or openai-whisper)
      // Try whisper.cpp first (faster), then fallback to whisper
      try {
        const { stdout } = await execAsync(
          `whisper "${tempFile}" --model base.en --output_format txt --output_dir "${tmpdir()}" 2>/dev/null`
        );
        // Whisper outputs to a .txt file
        const txtFile = tempFile.replace('.wav', '.txt');
        const { stdout: text } = await execAsync(`cat "${txtFile}" 2>/dev/null || echo ""`);
        await unlink(txtFile).catch(() => {});
        return text.trim() || stdout.trim();
      } catch {
        // Try whisper.cpp main binary
        const { stdout } = await execAsync(
          `whisper-cpp -m ~/.whisper/ggml-base.en.bin -f "${tempFile}" 2>/dev/null`
        );
        return stdout.trim();
      }
    } finally {
      await unlink(tempFile).catch(() => {});
    }
  }

  async speak(text: string): Promise<void> {
    const platform = process.platform;

    return new Promise((resolve, reject) => {
      let cmd: string;
      let args: string[];

      if (platform === 'darwin') {
        // macOS - use built-in 'say' command with Daniel voice (British)
        cmd = 'say';
        args = ['-v', 'Daniel', text];
      } else {
        // Linux - use espeak or pico2wave
        cmd = 'espeak';
        args = ['-v', 'en-gb', text];
      }

      const child = spawn(cmd, args, {
        stdio: ['ignore', 'ignore', 'ignore'],
      });

      child.on('close', () => resolve());
      child.on('error', (err) => {
        // TTS is optional, don't fail if not available
        console.error('TTS not available:', err.message);
        resolve();
      });
    });
  }

  isCurrentlyRecording(): boolean {
    return this.isRecording;
  }
}

export const voiceService = new VoiceService();
