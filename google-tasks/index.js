#!/usr/bin/env node
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { CallToolRequestSchema, ListToolsRequestSchema } from '@modelcontextprotocol/sdk/types.js';
import { google } from 'googleapis';
import fs from 'fs';
import path from 'path';

const TOKEN_PATH = path.join(process.env.HOME, '.config', 'google-docs-mcp', 'token.json');
const _genv = Object.fromEntries(fs.readFileSync(path.join(process.env.HOME, "services", "secrets", "google.env"), "utf8").split("\n").filter(l => l.includes("=")).map(l => { const i = l.indexOf("="); return [l.slice(0, i).trim(), l.slice(i + 1).trim()]; }));
const CLIENT_ID = _genv.GOOGLE_CLIENT_ID;
const CLIENT_SECRET = _genv.GOOGLE_CLIENT_SECRET;


function getAuth() {
  const auth = new google.auth.OAuth2(CLIENT_ID, CLIENT_SECRET);
  auth.setCredentials(JSON.parse(fs.readFileSync(TOKEN_PATH)));
  return auth;
}

const server = new Server({ name: 'google-tasks', version: '1.0.0' }, { capabilities: { tools: {} } });

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    { name: 'tasks_list', description: 'List all task lists and their tasks', inputSchema: { type: 'object', properties: {} } },
    { name: 'tasks_add', description: 'Add a new task', inputSchema: { type: 'object', properties: { title: { type: 'string', description: 'Task title' }, due: { type: 'string', description: 'Due date in YYYY-MM-DD format (optional)' } }, required: ['title'] } },
    { name: 'tasks_complete', description: 'Mark a task as complete', inputSchema: { type: 'object', properties: { taskId: { type: 'string' }, listId: { type: 'string' } }, required: ['taskId', 'listId'] } },
    { name: 'tasks_delete', description: 'Delete a task', inputSchema: { type: 'object', properties: { taskId: { type: 'string' }, listId: { type: 'string' } }, required: ['taskId', 'listId'] } },
  ]
}));

server.setRequestHandler(CallToolRequestSchema, async (req) => {
  const tasks = google.tasks({ version: 'v1', auth: getAuth() });
  const { name, arguments: args } = req.params;

  if (name === 'tasks_list') {
    const lists = await tasks.tasklists.list({ maxResults: 10 });
    const all = await Promise.all((lists.data.items || []).map(async l => {
      const t = await tasks.tasks.list({ tasklist: l.id, showCompleted: false, maxResults: 20 });
      return { list: l.title, listId: l.id, tasks: (t.data.items || []).map(t => ({ id: t.id, title: t.title, due: t.due, notes: t.notes })) };
    }));
    return { content: [{ type: 'text', text: JSON.stringify(all, null, 2) }] };
  }

  if (name === 'tasks_add') {
    const lists = await tasks.tasklists.list({ maxResults: 1 });
    const listId = lists.data.items?.[0]?.id;
    const body = { title: args.title };
    if (args.due) body.due = new Date(args.due).toISOString();
    const t = await tasks.tasks.insert({ tasklist: listId, requestBody: body });
    return { content: [{ type: 'text', text: `Task added: ${t.data.title} (ID: ${t.data.id})` }] };
  }

  if (name === 'tasks_complete') {
    await tasks.tasks.update({ tasklist: args.listId, task: args.taskId, requestBody: { id: args.taskId, status: 'completed' } });
    return { content: [{ type: 'text', text: 'Task marked as complete' }] };
  }

  if (name === 'tasks_delete') {
    await tasks.tasks.delete({ tasklist: args.listId, task: args.taskId });
    return { content: [{ type: 'text', text: 'Task deleted' }] };
  }

  throw new Error(`Unknown tool: ${name}`);
});

const transport = new StdioServerTransport();
await server.connect(transport);
