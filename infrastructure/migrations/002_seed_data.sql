-- JARVIS Seed Data
-- Migration: 002_seed_data
-- Created: 2024-01-01

-- Create a demo user (password: 'jarvis123')
INSERT INTO users (id, email, password_hash, name, email_verified) VALUES
(
    'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
    'tony@stark.industries',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.I4VWKDbzCFQ.cq',
    'Tony Stark',
    TRUE
);

-- Create demo user preferences
INSERT INTO user_preferences (user_id, timezone, voice_id, briefing_time, weather_location, news_categories) VALUES
(
    'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
    'America/New_York',
    'Brian',
    '07:00:00',
    'New York, NY',
    ARRAY['technology', 'business', 'science']
);

-- Create a sample conversation
INSERT INTO conversations (id, user_id, title) VALUES
(
    'b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22',
    'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
    'Welcome Conversation'
);

-- Add welcome messages
INSERT INTO messages (conversation_id, role, content) VALUES
(
    'b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22',
    'system',
    'You are JARVIS, a sophisticated AI assistant inspired by Tony Stark''s AI from Iron Man. You speak with a refined British accent and maintain a professional yet warm demeanor.'
),
(
    'b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22',
    'assistant',
    'Good morning, sir. I am JARVIS, your personal artificial intelligence assistant. All systems are operational and at your disposal. How may I assist you today?'
);

-- Create sample tasks
INSERT INTO tasks (user_id, title, description, type, priority, status) VALUES
(
    'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
    'Morning briefing',
    'Daily briefing at 7 AM',
    'scheduled_briefing',
    'medium',
    'pending'
),
(
    'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
    'Review calendar',
    'Check upcoming meetings for the week',
    'reminder',
    'low',
    'pending'
);

-- Create sample notification
INSERT INTO notifications (user_id, type, title, message, data) VALUES
(
    'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
    'system',
    'Welcome to JARVIS',
    'Your personal AI assistant is now ready to serve you, sir. All systems are operational.',
    '{"action": "welcome", "version": "0.1.0"}'
);
