#!/usr/bin/env node
/**
 * Usage Analytics Hook
 * This script tracks Codex usage patterns and generates analytics
 */

const fs = require('fs');
const path = require('path');
const os = require('os');

// Configuration
const ANALYTICS_DIR = path.join(os.homedir(), '.codex', 'analytics');
const DAILY_LOG = path.join(ANALYTICS_DIR, `usage-${new Date().toISOString().split('T')[0]}.json`);
const SUMMARY_FILE = path.join(ANALYTICS_DIR, 'usage-summary.json');

// Ensure analytics directory exists
if (!fs.existsSync(ANALYTICS_DIR)) {
    fs.mkdirSync(ANALYTICS_DIR, { recursive: true });
}

// Get environment variables
const eventType = process.env.CODEX_EVENT_TYPE || '';
const sessionId = process.env.CODEX_SESSION_ID || '';
const timestamp = process.env.CODEX_TIMESTAMP || new Date().toISOString();

/**
 * Load or create daily log
 */
function loadDailyLog() {
    if (fs.existsSync(DAILY_LOG)) {
        try {
            return JSON.parse(fs.readFileSync(DAILY_LOG, 'utf8'));
        } catch (error) {
            console.warn('Error reading daily log, creating new one:', error.message);
        }
    }
    
    return {
        date: new Date().toISOString().split('T')[0],
        sessions: {},
        events: [],
        summary: {
            total_sessions: 0,
            total_events: 0,
            total_commands: 0,
            total_tasks: 0,
            models_used: {},
            providers_used: {},
            session_durations: [],
            command_types: {},
            error_count: 0
        }
    };
}

/**
 * Save daily log
 */
function saveDailyLog(data) {
    fs.writeFileSync(DAILY_LOG, JSON.stringify(data, null, 2));
}

/**
 * Load or create usage summary
 */
function loadSummary() {
    if (fs.existsSync(SUMMARY_FILE)) {
        try {
            return JSON.parse(fs.readFileSync(SUMMARY_FILE, 'utf8'));
        } catch (error) {
            console.warn('Error reading summary, creating new one:', error.message);
        }
    }
    
    return {
        total_sessions: 0,
        total_events: 0,
        total_commands: 0,
        total_tasks: 0,
        first_use: null,
        last_use: null,
        models_used: {},
        providers_used: {},
        daily_stats: {},
        avg_session_duration: 0,
        most_used_commands: {},
        error_rate: 0
    };
}

/**
 * Save usage summary
 */
function saveSummary(data) {
    fs.writeFileSync(SUMMARY_FILE, JSON.stringify(data, null, 2));
}

/**
 * Track event
 */
function trackEvent() {
    const dailyLog = loadDailyLog();
    const summary = loadSummary();
    
    // Create event record
    const event = {
        type: eventType,
        session_id: sessionId,
        timestamp: timestamp,
        data: {}
    };
    
    // Add event-specific data
    switch (eventType) {
        case 'session_start':
            const model = process.env.CODEX_MODEL || 'unknown';
            const provider = process.env.CODEX_PROVIDER || 'openai';
            
            event.data = { model, provider };
            
            // Initialize session in daily log
            dailyLog.sessions[sessionId] = {
                start_time: timestamp,
                model: model,
                provider: provider,
                commands: 0,
                tasks: 0,
                errors: 0
            };
            
            // Update summary
            dailyLog.summary.total_sessions++;
            dailyLog.summary.models_used[model] = (dailyLog.summary.models_used[model] || 0) + 1;
            dailyLog.summary.providers_used[provider] = (dailyLog.summary.providers_used[provider] || 0) + 1;
            
            summary.total_sessions++;
            summary.models_used[model] = (summary.models_used[model] || 0) + 1;
            summary.providers_used[provider] = (summary.providers_used[provider] || 0) + 1;
            
            if (!summary.first_use) {
                summary.first_use = timestamp;
            }
            summary.last_use = timestamp;
            
            break;
            
        case 'session_end':
            const duration = process.env.CODEX_DURATION;
            if (duration && dailyLog.sessions[sessionId]) {
                const durationMs = parseInt(duration);
                event.data = { duration: durationMs };
                
                dailyLog.sessions[sessionId].end_time = timestamp;
                dailyLog.sessions[sessionId].duration = durationMs;
                dailyLog.summary.session_durations.push(durationMs);
                
                // Update average session duration
                const totalDuration = summary.daily_stats[dailyLog.date]?.total_duration || 0;
                const sessionCount = summary.daily_stats[dailyLog.date]?.sessions || 0;
                summary.avg_session_duration = sessionCount > 0 ? 
                    (totalDuration + durationMs) / (sessionCount + 1) : durationMs;
            }
            break;
            
        case 'command_start':
            const command = process.env.CODEX_COMMAND;
            if (command) {
                try {
                    const commandArray = JSON.parse(command);
                    const commandName = commandArray[0] || 'unknown';
                    event.data = { command: commandArray };
                    
                    if (dailyLog.sessions[sessionId]) {
                        dailyLog.sessions[sessionId].commands++;
                    }
                    
                    dailyLog.summary.total_commands++;
                    dailyLog.summary.command_types[commandName] = 
                        (dailyLog.summary.command_types[commandName] || 0) + 1;
                    
                    summary.total_commands++;
                    summary.most_used_commands[commandName] = 
                        (summary.most_used_commands[commandName] || 0) + 1;
                } catch (e) {
                    event.data = { command: command };
                }
            }
            break;
            
        case 'task_start':
            const taskId = process.env.CODEX_TASK_ID;
            const prompt = process.env.CODEX_PROMPT;
            event.data = { task_id: taskId, prompt: prompt };
            
            if (dailyLog.sessions[sessionId]) {
                dailyLog.sessions[sessionId].tasks++;
            }
            
            dailyLog.summary.total_tasks++;
            summary.total_tasks++;
            break;
            
        case 'error':
            const error = process.env.CODEX_ERROR;
            const context = process.env.CODEX_CONTEXT;
            event.data = { error: error, context: context };
            
            if (dailyLog.sessions[sessionId]) {
                dailyLog.sessions[sessionId].errors++;
            }
            
            dailyLog.summary.error_count++;
            break;
    }
    
    // Add event to daily log
    dailyLog.events.push(event);
    dailyLog.summary.total_events++;
    summary.total_events++;
    
    // Update daily stats in summary
    const today = dailyLog.date;
    if (!summary.daily_stats[today]) {
        summary.daily_stats[today] = {
            sessions: 0,
            events: 0,
            commands: 0,
            tasks: 0,
            errors: 0,
            total_duration: 0
        };
    }
    
    summary.daily_stats[today].events++;
    
    // Calculate error rate
    summary.error_rate = summary.total_events > 0 ? 
        (dailyLog.summary.error_count / summary.total_events) * 100 : 0;
    
    // Save data
    saveDailyLog(dailyLog);
    saveSummary(summary);
    
    console.log(`📊 Analytics: Tracked ${eventType} event for session ${sessionId}`);
}

/**
 * Generate usage report
 */
function generateReport() {
    const summary = loadSummary();
    
    console.log('\n📊 Codex Usage Analytics Report');
    console.log('================================');
    console.log(`Total Sessions: ${summary.total_sessions}`);
    console.log(`Total Events: ${summary.total_events}`);
    console.log(`Total Commands: ${summary.total_commands}`);
    console.log(`Total Tasks: ${summary.total_tasks}`);
    console.log(`Error Rate: ${summary.error_rate.toFixed(2)}%`);
    console.log(`Average Session Duration: ${(summary.avg_session_duration / 1000 / 60).toFixed(1)} minutes`);
    
    if (summary.first_use) {
        console.log(`First Use: ${new Date(summary.first_use).toLocaleDateString()}`);
    }
    if (summary.last_use) {
        console.log(`Last Use: ${new Date(summary.last_use).toLocaleDateString()}`);
    }
    
    console.log('\nMost Used Models:');
    Object.entries(summary.models_used)
        .sort(([,a], [,b]) => b - a)
        .slice(0, 5)
        .forEach(([model, count]) => {
            console.log(`  ${model}: ${count} sessions`);
        });
    
    console.log('\nMost Used Commands:');
    Object.entries(summary.most_used_commands)
        .sort(([,a], [,b]) => b - a)
        .slice(0, 10)
        .forEach(([command, count]) => {
            console.log(`  ${command}: ${count} times`);
        });
}

// Main execution
if (process.argv.includes('--report')) {
    generateReport();
} else if (eventType) {
    trackEvent();
} else {
    console.log('Usage: node track-usage.js [--report]');
    console.log('When run as a hook, CODEX_EVENT_TYPE should be set');
}
