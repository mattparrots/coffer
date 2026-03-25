import { useState, useEffect, useRef } from 'react';
import Head from 'next/head';

function timeAgo(iso) {
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1) return 'just now';
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

export default function Home() {
  const [todos, setTodos] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const inputRef = useRef(null);

  useEffect(() => {
    fetch('/api/todos')
      .then(r => r.json())
      .then(data => { setTodos(data); setLoading(false); })
      .catch(() => { setError('Failed to load todos'); setLoading(false); });
  }, []);

  async function addTodo(e) {
    e.preventDefault();
    if (!input.trim()) return;
    setError(null);
    try {
      const res = await fetch('/api/todos', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: input.trim() }),
      });
      if (!res.ok) throw new Error();
      const todo = await res.json();
      setTodos(prev => [todo, ...prev]);
      setInput('');
      inputRef.current?.focus();
    } catch {
      setError('Failed to add todo');
    }
  }

  async function toggleTodo(id, completed) {
    setTodos(prev => prev.map(t => t.id === id ? { ...t, completed } : t));
    try {
      await fetch(`/api/todos?id=${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ completed }),
      });
    } catch {
      setTodos(prev => prev.map(t => t.id === id ? { ...t, completed: !completed } : t));
      setError('Failed to update todo');
    }
  }

  async function deleteTodo(id) {
    setTodos(prev => prev.filter(t => t.id !== id));
    try {
      await fetch(`/api/todos?id=${id}`, { method: 'DELETE' });
    } catch {
      setError('Failed to delete todo');
    }
  }

  const pending = todos.filter(t => !t.completed);
  const done = todos.filter(t => t.completed);

  return (
    <>
      <Head>
        <title>Coffer</title>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <meta name="theme-color" content="#0f0f0f" />
        <link rel="manifest" href="/manifest.json" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
        <meta name="apple-mobile-web-app-title" content="Coffer" />
      </Head>

      <h1>Coffer</h1>

      {error && <div className="error">{error}</div>}

      <form className="add-form" onSubmit={addTodo}>
        <input
          ref={inputRef}
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder="Add a task for Claude..."
          autoComplete="off"
          autoCorrect="off"
        />
        <button type="submit" aria-label="Add">+</button>
      </form>

      {loading ? (
        <p className="empty">Loading...</p>
      ) : (
        <>
          {pending.length > 0 && (
            <>
              <p className="section-label">Pending — {pending.length}</p>
              <ul className="todo-list">
                {pending.map(todo => (
                  <li key={todo.id} className="todo-item">
                    <input
                      type="checkbox"
                      checked={false}
                      onChange={() => toggleTodo(todo.id, true)}
                    />
                    <div className="todo-text">
                      {todo.text}
                      <div className="todo-meta">{timeAgo(todo.createdAt)}</div>
                    </div>
                    <button className="delete-btn" onClick={() => deleteTodo(todo.id)} aria-label="Delete">×</button>
                  </li>
                ))}
              </ul>
            </>
          )}

          {pending.length === 0 && done.length === 0 && (
            <p className="empty">No tasks yet. Add something for Claude to work on.</p>
          )}

          {done.length > 0 && (
            <>
              <p className="section-label">Done — {done.length}</p>
              <ul className="todo-list">
                {done.map(todo => (
                  <li key={todo.id} className="todo-item done">
                    <input
                      type="checkbox"
                      checked={true}
                      onChange={() => toggleTodo(todo.id, false)}
                    />
                    <div className="todo-text">
                      {todo.text}
                      <div className="todo-meta">{timeAgo(todo.createdAt)}</div>
                    </div>
                    <button className="delete-btn" onClick={() => deleteTodo(todo.id)} aria-label="Delete">×</button>
                  </li>
                ))}
              </ul>
            </>
          )}
        </>
      )}
    </>
  );
}
