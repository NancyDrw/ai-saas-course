import { useCallback, useEffect, useState } from "react";

const actionLabels = {
  couple_created: "Створено пару",
  menu_opened: "Відкрито меню",
  card_viewed: "Переглянуто картку",
  exercise_started: "Розпочато вправу",
};

async function fetchJson(path) {
  const response = await fetch(path);
  if (!response.ok) {
    throw new Error(`API returned ${response.status}`);
  }
  return response.json();
}

function formatDate(value) {
  return new Intl.DateTimeFormat("uk-UA", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export default function App() {
  const [summary, setSummary] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadDashboard = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const [summaryData, transactionData] = await Promise.all([
        fetchJson("/api/summary"),
        fetchJson("/api/transactions"),
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
  }, []);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  const cards = [
    { label: "Користувачі", value: summary?.total_users ?? 0, icon: "👤" },
    { label: "Створені пари", value: summary?.total_couples ?? 0, icon: "🤝" },
    { label: "Дії у боті", value: summary?.total_activities ?? 0, icon: "✨" },
  ];

  return (
    <main className="dashboard">
      <header className="hero">
        <div>
          <p className="eyebrow">INTIMA · ADMIN</p>
          <h1>Активність сервісу</h1>
          <p className="subtitle">
            Огляд користувачів, створених пар і безпечних подій у Telegram-боті.
          </p>
        </div>
        <button className="refresh-button" onClick={loadDashboard} disabled={loading}>
          {loading ? "Оновлюємо…" : "Оновити"}
        </button>
      </header>

      {loading && <p className="state-message">Завантажуємо дані з API…</p>}

      {error && (
        <section className="error-state" role="alert">
          <p>{error}</p>
          <button onClick={loadDashboard}>Спробувати ще раз</button>
        </section>
      )}

      {!loading && !error && (
        <>
          <section className="summary-grid" aria-label="Підсумок">
            {cards.map((card) => (
              <article className="summary-card" key={card.label}>
                <span aria-hidden="true">{card.icon}</span>
                <p>{card.label}</p>
                <strong>{card.value}</strong>
              </article>
            ))}
          </section>

          <section className="activity-section">
            <div className="section-heading">
              <div>
                <p className="eyebrow">READ-ONLY</p>
                <h2>Історія активності</h2>
              </div>
              <span>{transactions.length} подій</span>
            </div>

            {transactions.length === 0 ? (
              <p className="empty-state">
                Подій ще немає. Після дії в Telegram-боті вони з’являться тут.
              </p>
            ) : (
              <div className="table-wrapper">
                <table>
                  <thead>
                    <tr>
                      <th>Дата</th>
                      <th>Тип</th>
                      <th>ID пари</th>
                      <th>Категорія</th>
                      <th>Опис</th>
                    </tr>
                  </thead>
                  <tbody>
                    {transactions.map((transaction) => (
                      <tr key={transaction.id}>
                        <td>{formatDate(transaction.date)}</td>
                        <td>{actionLabels[transaction.type] ?? transaction.type}</td>
                        <td>{transaction.couple_id ?? "—"}</td>
                        <td>{transaction.category}</td>
                        <td>{transaction.description ?? "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      )}
    </main>
  );
}
