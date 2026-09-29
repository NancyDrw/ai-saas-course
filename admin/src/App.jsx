import { useCallback, useEffect, useMemo, useState } from "react";

const emptyTransaction = () => ({
  type: "income",
  amount: "",
  category: "",
  description: "",
  date: new Date().toISOString().slice(0, 10),
});

const typeLabels = {
  income: "Нарахування",
  expense: "Списання",
};

const filters = [
  { value: "all", label: "Усі" },
  { value: "income", label: "Нарахування" },
  { value: "expense", label: "Списання" },
];

const insightChatThreadStorageKey = "ai-insight-chat-thread";

async function fetchJson(path, options = {}) {
  const response = await fetch(path, options);
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const error = new Error(body?.detail || `API returned ${response.status}`);
    error.status = response.status;
    throw error;
  }
  return response.status === 204 ? null : response.json();
}

function formatDate(value) {
  return new Intl.DateTimeFormat("uk-UA", { dateStyle: "medium" }).format(
    new Date(`${value}T12:00:00`),
  );
}

function formatCredits(value) {
  return new Intl.NumberFormat("uk-UA", {
    maximumFractionDigits: 2,
    minimumFractionDigits: 0,
  }).format(Number(value));
}

export default function App() {
  const [accessPassword, setAccessPassword] = useState("");
  const [passwordInput, setPasswordInput] = useState("");
  const [accessError, setAccessError] = useState(null);
  const [authorizing, setAuthorizing] = useState(false);
  const [summary, setSummary] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [form, setForm] = useState(emptyTransaction);
  const [formOpen, setFormOpen] = useState(false);
  const [filter, setFilter] = useState("all");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [deletingId, setDeletingId] = useState(null);
  const [error, setError] = useState(null);
  const [formError, setFormError] = useState(null);
  const [insightChatMessages, setInsightChatMessages] = useState([]);
  const [insightChatInput, setInsightChatInput] = useState("");
  const [insightChatLoading, setInsightChatLoading] = useState(false);
  const [insightChatError, setInsightChatError] = useState(null);
  const [pendingAction, setPendingAction] = useState(null);
  const [actionProcessing, setActionProcessing] = useState(false);
  const [pendingActionError, setPendingActionError] = useState(null);
  const [insightChatThreadId, setInsightChatThreadId] = useState(
    () => window.sessionStorage.getItem(insightChatThreadStorageKey) || "",
  );

  const loadDashboard = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const [summaryData, transactionData] = await Promise.all([
        fetchJson("/api/summary", { headers: { "X-Admin-Password": accessPassword } }),
        fetchJson("/api/transactions", { headers: { "X-Admin-Password": accessPassword } }),
      ]);
      setSummary(summaryData);
      setTransactions(transactionData);
    } catch {
      setError(
        "Не вдалося отримати дані. Переконайтеся, що FastAPI працює на порту 8000.",
      );
    } finally {
      setLoading(false);
    }
  }, [accessPassword]);

  useEffect(() => {
    if (accessPassword) {
      loadDashboard();
    } else {
      setLoading(false);
    }
  }, [accessPassword, loadDashboard]);

  const categories = useMemo(
    () => [...new Set(transactions.map((transaction) => transaction.category))].sort(),
    [transactions],
  );

  const visibleTransactions = useMemo(
    () => transactions.filter((transaction) => (
      (filter === "all" || transaction.type === filter)
      && (categoryFilter === "all" || transaction.category === categoryFilter)
    )),
    [categoryFilter, filter, transactions],
  );

  const expenseStructure = useMemo(() => {
    const categoriesWithExpenses = new Map();
    for (const transaction of transactions) {
      if (transaction.type !== "expense") {
        continue;
      }
      categoriesWithExpenses.set(
        transaction.category,
        (categoriesWithExpenses.get(transaction.category) || 0) + Number(transaction.amount),
      );
    }

    const total = [...categoriesWithExpenses.values()].reduce((sum, amount) => sum + amount, 0);
    return [...categoriesWithExpenses.entries()]
      .map(([category, amount]) => ({ category, amount, share: total ? (amount / total) * 100 : 0 }))
      .sort((first, second) => second.amount - first.amount);
  }, [transactions]);

  const cards = [
    { label: "Нараховано", value: summary?.total_income ?? 0, icon: "✨" },
    { label: "Списано", value: summary?.total_expense ?? 0, icon: "🌿" },
    { label: "Баланс кредитів", value: summary?.balance ?? 0, icon: "💜" },
  ];

  async function handleAccess(event) {
    event.preventDefault();
    if (!passwordInput) {
      setAccessError("Введіть пароль адміністратора.");
      return;
    }

    setAuthorizing(true);
    setAccessError(null);
    try {
      await fetchJson("/api/admin/access", {
        method: "POST",
        headers: { "X-Admin-Password": passwordInput },
      });
      setAccessPassword(passwordInput);
      setPasswordInput("");
    } catch (requestError) {
      setAccessError(requestError.message || "Не вдалося перевірити пароль.");
    } finally {
      setAuthorizing(false);
    }
  }

  function handleChange(event) {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    const amount = Number(form.amount);

    if (!Number.isFinite(amount) || amount <= 0) {
      setFormError("Вкажіть суму кредитів, більшу за нуль.");
      return;
    }
    if (!form.category.trim()) {
      setFormError("Вкажіть категорію операції.");
      return;
    }

    setSubmitting(true);
    setFormError(null);
    try {
      await fetchJson("/api/transactions", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Admin-Password": accessPassword,
        },
        body: JSON.stringify({ ...form, amount }),
      });
      setForm(emptyTransaction());
      setFormOpen(false);
      await loadDashboard();
    } catch (requestError) {
      setFormError(
        requestError.message || "Не вдалося зберегти операцію. Спробуйте ще раз.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(transaction) {
    if (!window.confirm("Видалити операцію?")) {
      return;
    }

    setDeletingId(transaction.id);
    setError(null);
    try {
      await fetchJson(`/api/transactions/${transaction.id}`, {
        method: "DELETE",
        headers: { "X-Admin-Password": accessPassword },
      });
      await loadDashboard();
    } catch {
      setError("Не вдалося видалити операцію. Спробуйте ще раз.");
    } finally {
      setDeletingId(null);
    }
  }

  async function handleInsightChatSubmit(event) {
    event.preventDefault();
    const message = insightChatInput.trim();
    if (!message || insightChatLoading) {
      return;
    }

    setInsightChatMessages((current) => [...current, { role: "user", content: message }]);
    setInsightChatInput("");
    setInsightChatError(null);
    setInsightChatLoading(true);
    try {
      const result = await fetchJson("/api/ai/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Admin-Password": accessPassword,
        },
        body: JSON.stringify({ message, thread_id: insightChatThreadId || undefined }),
      });
      setInsightChatThreadId(result.thread_id);
      window.sessionStorage.setItem(insightChatThreadStorageKey, result.thread_id);
      setInsightChatMessages((current) => [...current, { role: "assistant", content: result.answer }]);
      if (result.pending_action) {
        setPendingAction(result.pending_action);
        setPendingActionError(null);
      }
    } catch (error) {
      setInsightChatError(
        error?.status === 429
          ? error.message
          : "Не вдалося отримати відповідь AI INSIGHT. Спробуйте ще раз трохи пізніше.",
      );
    } finally {
      setInsightChatLoading(false);
    }
  }

  function startNewInsightChat() {
    window.sessionStorage.removeItem(insightChatThreadStorageKey);
    setInsightChatThreadId("");
    setInsightChatMessages([]);
    setInsightChatInput("");
    setInsightChatError(null);
  }

  async function handleConfirmPendingAction() {
    if (!pendingAction || actionProcessing) {
      return;
    }

    setActionProcessing(true);
    setPendingActionError(null);
    try {
      const result = await fetchJson(`/api/ai/actions/${pendingAction.id}/confirm`, {
        method: "POST",
        headers: { "X-Admin-Password": accessPassword },
      });
      setPendingAction(null);
      setInsightChatMessages((current) => [
        ...current,
        { role: "assistant", content: "✅ Дію підтверджено. Ledger кредитів оновлено." },
      ]);
      await loadDashboard();
      return result;
    } catch (requestError) {
      setPendingActionError(
        requestError.message || "Не вдалося підтвердити запропоновану дію.",
      );
    } finally {
      setActionProcessing(false);
    }
  }

  async function handleCancelPendingAction() {
    if (!pendingAction || actionProcessing) {
      return;
    }

    setActionProcessing(true);
    setPendingActionError(null);
    try {
      await fetchJson(`/api/ai/actions/${pendingAction.id}/cancel`, {
        method: "POST",
        headers: { "X-Admin-Password": accessPassword },
      });
      setPendingAction(null);
      setInsightChatMessages((current) => [
        ...current,
        { role: "assistant", content: "Дію скасовано. Ledger кредитів не змінювався." },
      ]);
    } catch (requestError) {
      setPendingActionError(
        requestError.message || "Не вдалося скасувати запропоновану дію.",
      );
    } finally {
      setActionProcessing(false);
    }
  }

  if (!accessPassword) {
    return (
      <main className="access-screen">
        <section className="access-card">
          <p className="eyebrow">INTIMA · ADMIN</p>
          <h1>Кредити Intima</h1>
          <p className="subtitle">Введіть локальний пароль адміністратора, щоб відкрити ledger кредитів.</p>
          <form className="access-form" onSubmit={handleAccess}>
            <label>
              Пароль адміністратора
              <input
                autoComplete="current-password"
                onChange={(event) => setPasswordInput(event.target.value)}
                type="password"
                value={passwordInput}
              />
            </label>
            {accessError && <p className="form-error" role="alert">{accessError}</p>}
            <button className="submit-button" disabled={authorizing} type="submit">
              {authorizing ? "Перевіряємо…" : "Відкрити адмінку"}
            </button>
          </form>
        </section>
      </main>
    );
  }

  return (
    <main className="dashboard">
      <header className="hero">
        <div>
          <p className="eyebrow">INTIMA · ADMIN</p>
          <h1>Кредити Intima <span className="title-heart">♥</span></h1>
          <p className="subtitle">
            Керуйте нарахуваннями та списаннями кредитів для турботливих сервісів Intima.
          </p>
        </div>
        <div className="header-actions">
          <button className="logout-button" onClick={() => setAccessPassword("")}>Вийти</button>
          <button className="refresh-button" onClick={loadDashboard} disabled={loading}>
            {loading ? "Оновлюємо…" : "Оновити"}
          </button>
        </div>
      </header>

      {error && (
        <section className="error-state" role="alert">
          <p>{error}</p>
          <button onClick={loadDashboard}>Спробувати ще раз</button>
        </section>
      )}

      <section className="summary-grid" aria-label="Підсумок кредитів">
        {cards.map((card) => (
          <article className="summary-card" key={card.label}>
            <span aria-hidden="true">{card.icon}</span>
            <p>{card.label}</p>
            <strong>{formatCredits(card.value)}</strong>
          </article>
        ))}
      </section>

      <section className="ai-chat-section" aria-labelledby="ai-insight-chat-heading">
        <div className="section-heading">
          <div>
            <p className="eyebrow">AI INSIGHT CHAT · ✨</p>
            <h2 id="ai-insight-chat-heading">Помічник з кредитів Intima</h2>
            <p className="chat-intro">
              Запитайте про баланс, списання, категорії витрат або конкретний місяць. AI лише читає дані та нічого не змінює.
            </p>
          </div>
          <button className="new-chat-button" onClick={startNewInsightChat} type="button">
            Новий діалог
          </button>
        </div>

        <div className="chat-history" aria-live="polite">
          {insightChatMessages.length === 0 ? (
            <div className="chat-welcome">
              <span aria-hidden="true">✨</span>
              <p>Я можу показати баланс, найбільші списання або структуру витрат за місяць.</p>
            </div>
          ) : (
            insightChatMessages.map((message, index) => (
              <article className={`chat-message ${message.role}`} key={`${message.role}-${index}`}>
                <span>{message.role === "user" ? "Ви" : "AI INSIGHT"}</span>
                <p>{message.content}</p>
              </article>
            ))
          )}
          {insightChatLoading && (
            <article className="chat-message assistant chat-loading" role="status">
              <span>AI INSIGHT</span>
              <p>Читаю дані кредитів…</p>
            </article>
          )}
        </div>

        {insightChatError && <p className="chat-error" role="alert">{insightChatError}</p>}

        {pendingAction?.status === "pending" && (
          <section className="pending-action-card" aria-labelledby="pending-action-heading">
            <div>
              <p className="eyebrow">ПОТРІБНЕ ПІДТВЕРДЖЕННЯ · 🛡️</p>
              <h3 id="pending-action-heading">Запропонована дія</h3>
            </div>
            <dl className="pending-action-details">
              <div>
                <dt>Тип</dt>
                <dd>{pendingAction.payload.type === "expense" ? "Списання кредитів" : "Нарахування кредитів"}</dd>
              </div>
              <div>
                <dt>Кредити</dt>
                <dd>{formatCredits(pendingAction.payload.amount)}</dd>
              </div>
              <div>
                <dt>Категорія</dt>
                <dd>{pendingAction.payload.category}</dd>
              </div>
              <div>
                <dt>Дата</dt>
                <dd>{formatDate(pendingAction.payload.date)}</dd>
              </div>
              <div className="pending-action-description">
                <dt>Опис</dt>
                <dd>{pendingAction.payload.description || "—"}</dd>
              </div>
            </dl>
            {pendingActionError && <p className="pending-action-error" role="alert">{pendingActionError}</p>}
            <div className="pending-action-buttons">
              <button
                className="confirm-action-button"
                disabled={actionProcessing}
                onClick={handleConfirmPendingAction}
                type="button"
              >
                {actionProcessing ? "Обробляємо…" : "✓ Підтвердити"}
              </button>
              <button
                className="cancel-action-button"
                disabled={actionProcessing}
                onClick={handleCancelPendingAction}
                type="button"
              >
                Скасувати
              </button>
            </div>
          </section>
        )}

        <form className="chat-form" onSubmit={handleInsightChatSubmit}>
          <label className="visually-hidden" htmlFor="ai-insight-chat-input">Запит до AI INSIGHT</label>
          <textarea
            id="ai-insight-chat-input"
            disabled={insightChatLoading}
            onChange={(event) => setInsightChatInput(event.target.value)}
            placeholder="Наприклад: Який мій баланс і найбільші списання?"
            rows="2"
            value={insightChatInput}
          />
          <button className="chat-send-button" disabled={insightChatLoading || !insightChatInput.trim()} type="submit">
            {insightChatLoading ? "Аналізуємо…" : "Запитати"}
          </button>
        </form>
        <div className="chat-suggestions" aria-label="Приклади фінансових запитів">
          <button onClick={() => setInsightChatInput("Який поточний баланс кредитів?")} type="button">💜 Баланс</button>
          <button onClick={() => setInsightChatInput("Покажи найбільші списання")} type="button">🌿 Списання</button>
          <button onClick={() => setInsightChatInput("На що витратили найбільше кредитів?")} type="button">📊 Категорії</button>
          <button onClick={() => setInsightChatInput("Списати 3 кредити за AI-сесію сьогодні")} type="button">🛡️ Підготувати списання</button>
        </div>
      </section>

      <section className="transaction-form-section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">НОВА ОПЕРАЦІЯ · ✦</p>
            <h2>Додати кредити Intima</h2>
          </div>
          <button
            aria-expanded={formOpen}
            className="form-toggle"
            onClick={() => setFormOpen((isOpen) => !isOpen)}
            type="button"
          >
            {formOpen ? "Згорнути форму" : "＋ Додати операцію"}
          </button>
        </div>
        {!formOpen && <p className="form-hint">Нараховуйте бонуси або списуйте кредити за AI-сесії, вправи й персональні плани. 🫶</p>}
        {formOpen && <form className="transaction-form" onSubmit={handleSubmit}>
          <label>
            Тип
            <select name="type" value={form.type} onChange={handleChange}>
              <option value="income">Нарахування</option>
              <option value="expense">Списання</option>
            </select>
          </label>
          <label>
            Кредити
            <input name="amount" type="number" min="0.01" step="0.01" value={form.amount} onChange={handleChange} required />
          </label>
          <label>
            Категорія
            <input name="category" value={form.category} onChange={handleChange} placeholder="Наприклад, AI-сесія" required />
          </label>
          <label>
            Дата
            <input name="date" type="date" value={form.date} onChange={handleChange} required />
          </label>
          <label className="form-description">
            Опис <span>(необов’язково)</span>
            <textarea name="description" value={form.description} onChange={handleChange} placeholder="Наприклад, Списано 3 кредити за персональний план" rows="3" />
          </label>
          {formError && <p className="form-error" role="alert">{formError}</p>}
          <button className="submit-button" type="submit" disabled={submitting}>
            {submitting ? "Зберігаємо…" : "Додати операцію"}
          </button>
        </form>}
      </section>

      <section className="activity-section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">LEDGER</p>
            <h2>Історія кредитів</h2>
          </div>
          <div className="filter-group" aria-label="Фільтр операцій">
            {filters.map((item) => (
              <button
                className={filter === item.value ? "filter-button active" : "filter-button"}
                key={item.value}
                onClick={() => setFilter(item.value)}
                type="button"
              >
                {item.label}
              </button>
            ))}
            <label className="category-filter">
              <span className="visually-hidden">Категорія</span>
              <select value={categoryFilter} onChange={(event) => setCategoryFilter(event.target.value)}>
                <option value="all">Усі категорії</option>
                {categories.map((category) => <option key={category} value={category}>{category}</option>)}
              </select>
            </label>
          </div>
        </div>

        {loading ? (
          <p className="state-message">Завантажуємо дані з API…</p>
        ) : visibleTransactions.length === 0 ? (
          <p className="empty-state">Операцій ще немає. Додайте перше нарахування або списання кредитів.</p>
        ) : (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Дата</th>
                  <th>Тип</th>
                  <th>Кредити</th>
                  <th>Категорія</th>
                  <th>Опис</th>
                  <th><span className="visually-hidden">Дії</span></th>
                </tr>
              </thead>
              <tbody>
                {visibleTransactions.map((transaction) => (
                  <tr key={transaction.id}>
                    <td>{formatDate(transaction.date)}</td>
                    <td><span className={`type-badge ${transaction.type}`}>{typeLabels[transaction.type]}</span></td>
                    <td>{formatCredits(transaction.amount)}</td>
                    <td>{transaction.category}</td>
                    <td>{transaction.description || "—"}</td>
                    <td>
                      <button className="delete-button" onClick={() => handleDelete(transaction)} disabled={deletingId === transaction.id} type="button">
                        {deletingId === transaction.id ? "Видаляємо…" : "Видалити"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="insights-grid" aria-label="Статистика кредитів">
        <article className="insight-card">
          <p className="eyebrow">СТАТИСТИКА</p>
          <h2>{transactions.length} операцій</h2>
          <p className="insight-copy">
            {categories.length} {categories.length === 1 ? "категорія" : "категорій"} у ledger кредитів Intima.
          </p>
        </article>
        <article className="expense-structure">
          <div className="section-heading">
            <div>
              <p className="eyebrow">СТРУКТУРА СПИСАНЬ</p>
              <h2>Кредити за категоріями</h2>
            </div>
          </div>
          {expenseStructure.length === 0 ? (
            <p className="empty-state">Додайте списання, щоб побачити структуру витрат кредитів.</p>
          ) : (
            <ul className="expense-list">
              {expenseStructure.map((item) => (
                <li key={item.category}>
                  <div className="expense-label">
                    <span>{item.category}</span>
                    <strong>{formatCredits(item.amount)} кредитів · {Math.round(item.share)}%</strong>
                  </div>
                  <div className="expense-bar" aria-label={`${item.category}: ${Math.round(item.share)}%`}>
                    <span style={{ width: `${item.share}%` }} />
                  </div>
                </li>
              ))}
            </ul>
          )}
        </article>
      </section>
    </main>
  );
}
