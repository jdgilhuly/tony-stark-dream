declare module 'node-record-lpcm16' {
  interface RecordOptions {
    sampleRate?: number;
    channels?: number;
    threshold?: number;
    silence?: string;
    recorder?: string;
    audioType?: string;
  }

  interface Recording {
    stream(): NodeJS.ReadableStream;
    stop(): void;
  }

  export function record(options?: RecordOptions): Recording;
}

declare module 'play-sound' {
  interface Player {
    play(path: string, callback?: (err: Error | null) => void): void;
  }

  function playSound(options?: object): Player;
  export default playSound;
}

declare module 'lame' {
  export class Decoder {
    on(event: string, callback: (...args: any[]) => void): this;
    pipe<T extends NodeJS.WritableStream>(destination: T): T;
  }

  export class Encoder {
    on(event: string, callback: (...args: any[]) => void): this;
    pipe<T extends NodeJS.WritableStream>(destination: T): T;
  }
}
