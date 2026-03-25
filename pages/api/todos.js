import { kv } from '@vercel/kv';

const KEY = 'todos';

async function getTodos() {
  return (await kv.get(KEY)) ?? [];
}

async function saveTodos(todos) {
  await kv.set(KEY, todos);
}

export default async function handler(req, res) {
  if (req.method === 'GET') {
    const todos = await getTodos();
    return res.status(200).json(todos);
  }

  if (req.method === 'POST') {
    const { text } = req.body;
    if (!text?.trim()) return res.status(400).json({ error: 'text required' });
    const todos = await getTodos();
    const todo = { id: Date.now().toString(), text: text.trim(), completed: false, createdAt: new Date().toISOString() };
    todos.unshift(todo);
    await saveTodos(todos);
    return res.status(201).json(todo);
  }

  if (req.method === 'DELETE') {
    const { id } = req.query;
    const todos = await getTodos();
    await saveTodos(todos.filter(t => t.id !== id));
    return res.status(204).end();
  }

  if (req.method === 'PATCH') {
    const { id } = req.query;
    const { completed } = req.body;
    const todos = await getTodos();
    const todo = todos.find(t => t.id === id);
    if (!todo) return res.status(404).json({ error: 'not found' });
    todo.completed = completed;
    await saveTodos(todos);
    return res.status(200).json(todo);
  }

  res.status(405).end();
}
