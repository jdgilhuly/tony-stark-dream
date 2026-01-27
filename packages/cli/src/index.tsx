#!/usr/bin/env node
import { render } from 'ink';
import { Command } from 'commander';
import { App } from './components/App.js';
import { LoginScreen } from './components/LoginScreen.js';
import { BriefingScreen } from './components/BriefingScreen.js';
import { Dashboard } from './components/Dashboard.js';
import { VoiceChat } from './components/VoiceChat.js';
import { TaskRunner } from './components/TaskRunner.js';
import { MemoryManager } from './components/MemoryManager.js';
import { ResearchViewer } from './components/ResearchViewer.js';
import { ConfigManager } from './config.js';
import { MockAudioRecorder } from './audio/mock-recorder.js';

const program = new Command();
const config = new ConfigManager();

// Global option for TTY bypass
program.option('--no-tty-check', 'Skip TTY check for automated testing');

function ensureInteractiveTerminal() {
  const opts = program.opts();
  if (opts.noTtyCheck || opts.ttyCheck === false) {
    return;
  }
  if (!process.stdin.isTTY) {
    console.error('Error: This command requires an interactive terminal.');
    console.error('Please run directly in a terminal, not through a script or pipe.');
    console.error('For automated testing, use --no-tty-check flag.');
    process.exit(1);
  }
}

program
  .name('jarvis')
  .description('JARVIS - Just A Rather Very Intelligent System')
  .version('0.1.0');

program
  .command('chat')
  .description('Start a conversation with JARVIS')
  .option('-s, --server <url>', 'API server URL', 'http://localhost:3000')
  .action(async (options) => {
    ensureInteractiveTerminal();
    const tokens = config.getTokens();

    if (!tokens) {
      console.log('Please login first: jarvis login');
      process.exit(1);
    }

    render(<App serverUrl={options.server} tokens={tokens} />);
  });

program
  .command('login')
  .description('Login to JARVIS')
  .option('-s, --server <url>', 'API server URL', 'http://localhost:3000')
  .action(async (options) => {
    // If auth is disabled, login is not needed
    if (config.isAuthDisabled()) {
      console.log('Auth is disabled. Login not required.');
      console.log('All JARVIS commands are available without authentication.');
      return;
    }

    ensureInteractiveTerminal();
    render(
      <LoginScreen
        serverUrl={options.server}
        onSuccess={(tokens) => {
          config.setTokens(tokens);
        }}
      />
    );
  });

program
  .command('logout')
  .description('Logout from JARVIS')
  .action(() => {
    if (config.isAuthDisabled()) {
      console.log('Auth is disabled. Logout not applicable.');
      return;
    }
    config.clearTokens();
    console.log('Logged out successfully.');
  });

program
  .command('briefing')
  .description('Get your daily briefing from JARVIS')
  .option('-s, --server <url>', 'API server URL', 'http://localhost:3000')
  .action(async (options) => {
    ensureInteractiveTerminal();
    const tokens = config.getTokens();

    if (!tokens) {
      console.log('Please login first: jarvis login');
      process.exit(1);
    }

    render(<BriefingScreen serverUrl={options.server} tokens={tokens} />);
  });

program
  .command('config')
  .description('View or update configuration')
  .option('--server <url>', 'Set default server URL')
  .option('--show', 'Show current configuration')
  .action((options) => {
    if (options.show) {
      console.log('Configuration:');
      console.log(JSON.stringify(config.getAll(), null, 2));
    } else if (options.server) {
      config.set('serverUrl', options.server);
      console.log(`Server URL set to: ${options.server}`);
    } else {
      console.log('Use --show to view configuration or --server to set the server URL');
    }
  });

program
  .command('dashboard')
  .description('Open the JARVIS dashboard')
  .option('-s, --server <url>', 'API server URL', 'http://localhost:3000')
  .action(async (options) => {
    ensureInteractiveTerminal();
    const tokens = config.getTokens();

    if (!tokens) {
      console.log('Please login first: jarvis login');
      process.exit(1);
    }

    render(<Dashboard serverUrl={options.server} tokens={tokens} />);
  });

program
  .command('voice')
  .description('Start voice conversation with JARVIS')
  .option('-s, --server <url>', 'API server URL', 'http://localhost:3000')
  .action(async (options) => {
    ensureInteractiveTerminal();
    const tokens = config.getTokens();

    if (!tokens) {
      console.log('Please login first: jarvis login');
      process.exit(1);
    }

    render(<VoiceChat serverUrl={options.server} tokens={tokens} />);
  });

program
  .command('listen')
  .description('Activate wake word listening mode')
  .option('-s, --server <url>', 'API server URL', 'http://localhost:3000')
  .option('-w, --wake-word <word>', 'Wake word to listen for', 'jarvis')
  .action(async (options) => {
    ensureInteractiveTerminal();
    const tokens = config.getTokens();

    if (!tokens) {
      console.log('Please login first: jarvis login');
      process.exit(1);
    }

    console.log(`Listening for wake word: "${options.wakeWord}"...`);
    console.log('Press Ctrl+C to stop.');

    // In a full implementation, this would use a wake word detection library
    // like Porcupine or Snowboy to continuously listen for the wake word
    render(
      <VoiceChat
        serverUrl={options.server}
        tokens={tokens}
        onMessage={(msg) => console.log(`You said: ${msg}`)}
        onResponse={(res) => console.log(`JARVIS: ${res}`)}
      />
    );
  });

program
  .command('voice-test')
  .description('Test voice interface with mock audio (no microphone required)')
  .option('-s, --server <url>', 'API server URL', 'http://localhost:3000')
  .option('-f, --audio-file <path>', 'Audio file to use as input')
  .option('--auto-stop <ms>', 'Auto-stop after N milliseconds', '5000')
  .action(async (options) => {
    // No TTY check needed for test mode
    const tokens = config.getTokens();

    if (!tokens) {
      console.log('Please login first: jarvis login');
      process.exit(1);
    }

    const autoStopMs = parseInt(options.autoStop, 10);
    const mockRecorder = new MockAudioRecorder({
      autoStopMs,
      audioFile: options.audioFile,
    });

    console.log('Starting voice test mode...');
    console.log(`Auto-stop in ${autoStopMs}ms`);
    if (options.audioFile) {
      console.log(`Using audio file: ${options.audioFile}`);
    }

    render(
      <VoiceChat
        serverUrl={options.server}
        tokens={tokens}
        recorder={mockRecorder}
        onMessage={(msg) => console.log(`[Test] Transcribed: ${msg}`)}
        onResponse={(res) => console.log(`[Test] JARVIS: ${res}`)}
      />
    );
  });

// Natural language task execution
program
  .command('do <task>')
  .description('Execute any task using natural language')
  .option('-s, --server <url>', 'API server URL', 'http://localhost:3000')
  .action(async (task: string, options) => {
    const tokens = config.getTokens();

    if (!tokens) {
      console.log('Please login first: jarvis login');
      process.exit(1);
    }

    render(
      <TaskRunner
        serverUrl={options.server}
        tokens={tokens}
        task={task}
        taskType="do"
        onComplete={(result) => {
          if (!result.success) {
            process.exit(1);
          }
        }}
        onError={() => process.exit(1)}
      />
    );
  });

// Code task execution
program
  .command('code <task>')
  .description('Execute a coding task')
  .option('-s, --server <url>', 'API server URL', 'http://localhost:3000')
  .option('-d, --directory <path>', 'Working directory', '.')
  .option('--no-git', 'Disable git operations')
  .action(async (task: string, options) => {
    const tokens = config.getTokens();

    if (!tokens) {
      console.log('Please login first: jarvis login');
      process.exit(1);
    }

    render(
      <TaskRunner
        serverUrl={options.server}
        tokens={tokens}
        task={task}
        taskType="code"
        options={{
          workingDirectory: options.directory,
          useGit: options.git !== false,
        }}
        onComplete={(result) => {
          if (!result.success) {
            process.exit(1);
          }
        }}
        onError={() => process.exit(1)}
      />
    );
  });

// Research task
program
  .command('research <topic>')
  .description('Research a topic and synthesize findings')
  .option('-s, --server <url>', 'API server URL', 'http://localhost:3000')
  .option('-d, --depth <level>', 'Research depth: shallow, moderate, deep', 'moderate')
  .option('--no-sources', 'Exclude source URLs from output')
  .option('--no-save', 'Do not save to memory')
  .action(async (topic: string, options) => {
    const tokens = config.getTokens();

    if (!tokens) {
      console.log('Please login first: jarvis login');
      process.exit(1);
    }

    render(
      <ResearchViewer
        serverUrl={options.server}
        tokens={tokens}
        topic={topic}
        depth={options.depth}
        includeSources={options.sources !== false}
        saveToMemory={options.save !== false}
        onComplete={(result) => {
          // Exit after displaying results
        }}
        onError={() => process.exit(1)}
      />
    );
  });

// Remember (store memory)
program
  .command('remember <content>')
  .description('Store information in JARVIS memory')
  .option('-s, --server <url>', 'API server URL', 'http://localhost:3000')
  .option('-t, --type <type>', 'Memory type: fact, preference, event, conversation, skill', 'fact')
  .option('-i, --importance <level>', 'Importance level 0-1', '0.5')
  .action(async (content: string, options) => {
    const tokens = config.getTokens();

    if (!tokens) {
      console.log('Please login first: jarvis login');
      process.exit(1);
    }

    render(
      <MemoryManager
        serverUrl={options.server}
        tokens={tokens}
        mode="remember"
        content={content}
        options={{
          memoryType: options.type,
          importance: parseFloat(options.importance),
        }}
        onComplete={() => {
          // Exit after storing
        }}
        onError={() => process.exit(1)}
      />
    );
  });

// Recall (search memory)
program
  .command('recall <query>')
  .description('Search JARVIS memory')
  .option('-s, --server <url>', 'API server URL', 'http://localhost:3000')
  .option('-l, --limit <count>', 'Maximum results to return', '5')
  .action(async (query: string, options) => {
    const tokens = config.getTokens();

    if (!tokens) {
      console.log('Please login first: jarvis login');
      process.exit(1);
    }

    render(
      <MemoryManager
        serverUrl={options.server}
        tokens={tokens}
        mode="recall"
        query={query}
        options={{
          limit: parseInt(options.limit),
        }}
        onComplete={() => {
          // Exit after displaying
        }}
        onError={() => process.exit(1)}
      />
    );
  });

// Browser automation task
program
  .command('browse')
  .description('Execute browser automation tasks')
  .option('-s, --server <url>', 'API server URL', 'http://localhost:3000')
  .option('-u, --url <url>', 'URL to navigate to')
  .option('-t, --task <description>', 'Task description')
  .action(async (options) => {
    const tokens = config.getTokens();

    if (!tokens) {
      console.log('Please login first: jarvis login');
      process.exit(1);
    }

    if (!options.task) {
      console.log('Please specify a task with --task');
      process.exit(1);
    }

    render(
      <TaskRunner
        serverUrl={options.server}
        tokens={tokens}
        task={options.task}
        taskType="automation"
        options={{
          url: options.url,
        }}
        onComplete={(result) => {
          if (!result.success) {
            process.exit(1);
          }
        }}
        onError={() => process.exit(1)}
      />
    );
  });

// Default command - start chat
program.action(async () => {
  ensureInteractiveTerminal();
  const tokens = config.getTokens();
  const serverUrl = config.get('serverUrl') ?? 'http://localhost:3000';

  if (!tokens) {
    // Auth is required but no tokens - show login
    render(<LoginScreen serverUrl={serverUrl} onSuccess={(t) => config.setTokens(t)} />);
  } else {
    render(<App serverUrl={serverUrl} tokens={tokens} />);
  }
});

program.parse();
