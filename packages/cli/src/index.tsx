#!/usr/bin/env node
import { render } from 'ink';
import { Command } from 'commander';
import { App } from './components/App.js';
import { LoginScreen } from './components/LoginScreen.js';
import { BriefingScreen } from './components/BriefingScreen.js';
import { Dashboard } from './components/Dashboard.js';
import { VoiceChat } from './components/VoiceChat.js';
import { ConfigManager } from './config.js';

const program = new Command();
const config = new ConfigManager();

function ensureInteractiveTerminal() {
  if (!process.stdin.isTTY) {
    console.error('Error: This command requires an interactive terminal.');
    console.error('Please run directly in a terminal, not through a script or pipe.');
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

// Default command - start chat
program.action(async () => {
  ensureInteractiveTerminal();
  const tokens = config.getTokens();
  const serverUrl = config.get('serverUrl') ?? 'http://localhost:3000';

  if (!tokens) {
    render(<LoginScreen serverUrl={serverUrl} onSuccess={(t) => config.setTokens(t)} />);
  } else {
    render(<App serverUrl={serverUrl} tokens={tokens} />);
  }
});

program.parse();
